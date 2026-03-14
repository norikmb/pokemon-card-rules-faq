import json
import logging
import re
from datetime import datetime
from pathlib import Path
from urllib import request

from bs4 import BeautifulSoup

import config

PRODUCTS_URL = "https://www.pokemon-card.com/products/index.html"
PRODUCTS_TOP_LIST_API_URL = "https://www.pokemon-card.com/products/topList.php"
# 発売日がこの日数以内なら「直近」とみなす
RECENT_DAYS_THRESHOLD = 7

logger = logging.getLogger(__name__)


def product_type_priority(product_type: str) -> int:
    """商品種別の優先度（小さいほど優先）。"""
    priorities = {
        "拡張パック": 0,
        "構築デッキ": 1,
    }
    return priorities.get(product_type, 99)


def has_diff(report: dict) -> bool:
    """差分が存在するかどうか"""
    summary = report.get("summary", {})
    return any(summary.get(key, 0) > 0 for key in ["added", "removed", "modified"])


def fetch_recent_relevant_products(
    today: datetime | None = None,
) -> list[tuple[str, datetime]]:
    """商品ページから直近の拡張パック/構築デッキ名と発売日を返す。

    直近（RECENT_DAYS_THRESHOLD 日以内）の発売がなければ空配列を返す。
    """
    if today is None:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # 1) 公式API(JSON)から取得（最優先）
    try:
        req = request.Request(PRODUCTS_TOP_LIST_API_URL)
        with request.urlopen(req, timeout=config.REQUEST_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))

        products = payload.get("products", [])
        date_re = re.compile(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日")

        api_candidates: list[tuple[str, datetime, str]] = []
        for product in products:
            product_type = str(product.get("productType", "")).strip()
            if product_type not in {"拡張パック", "構築デッキ"}:
                continue

            title = str(product.get("productTitle", "")).strip()
            release_date_text = str(product.get("releaseDate", ""))
            date_m = date_re.search(release_date_text)
            if not date_m:
                continue

            year, month, day = (
                int(date_m.group(1)),
                int(date_m.group(2)),
                int(date_m.group(3)),
            )
            try:
                sale_date = datetime(year, month, day)
            except ValueError:
                continue

            if sale_date > today:
                continue
            if (today - sale_date).days > RECENT_DAYS_THRESHOLD:
                continue

            quoted = re.findall(r"「([^」]+)」", title)
            if quoted:
                name = quoted[-1]
            else:
                name = re.sub(r"^\s*(拡張パック|構築デッキ)\s*", "", title).strip()

            if name:
                api_candidates.append((name, sale_date, product_type))

        if api_candidates:
            api_candidates.sort(
                key=lambda x: (-x[1].toordinal(), product_type_priority(x[2]), x[0])
            )
            unique_candidates: list[tuple[str, datetime]] = []
            seen: set[tuple[str, datetime]] = set()
            for name, sale_date, _product_type in api_candidates:
                candidate = (name, sale_date)
                if candidate in seen:
                    continue
                seen.add(candidate)
                unique_candidates.append(candidate)
            return unique_candidates

    except Exception as e:
        logger.warning(
            "商品APIの取得に失敗したためHTML解析へフォールバックします: %s", e
        )

    # 2) フォールバック: HTML解析
    try:
        req = request.Request(PRODUCTS_URL)
        with request.urlopen(req, timeout=config.REQUEST_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("商品ページの取得に失敗しました: %s", e)
        return []

    soup = BeautifulSoup(html, "html.parser")
    # 「拡張パック販売日」「構築デッキ販売日」を含むテキストノードを探す
    sale_label_re = re.compile(r"(拡張パック|構築デッキ)販売日")
    date_re = re.compile(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日")

    candidates: list[tuple[str, datetime, str]] = []

    for node in soup.find_all(string=sale_label_re):
        # テキストノード → 親要素 → 祖父要素の順で広いコンテキストを用意
        contexts = [str(node)]
        if node.parent:
            contexts.append(node.parent.get_text(" ", strip=True))
        if node.parent and node.parent.parent:
            contexts.append(node.parent.parent.get_text(" ", strip=True))

        # 日付を見つける（狭いコンテキストから順に試みる）
        text = contexts[0]
        date_m = date_re.search(text)
        if not date_m:
            for ctx in contexts[1:]:
                date_m = date_re.search(ctx)
                if date_m:
                    text = ctx
                    break
        if not date_m:
            continue

        year, month, day = (
            int(date_m.group(1)),
            int(date_m.group(2)),
            int(date_m.group(3)),
        )
        try:
            sale_date = datetime(year, month, day)
        except ValueError:
            continue

        # 未発売はスキップ
        if sale_date > today:
            continue

        # 商品名を抽出: コンテキストを広げながら「...」を探す
        name = ""
        for ctx in contexts:
            quoted = re.findall(r"「([^」]+)」", ctx)
            if quoted:
                name = quoted[-1]
                break

        if not name:
            # 「...」がない場合は販売日ラベルより前のテキストを使う
            label_m = sale_label_re.search(text)
            before = text[: label_m.start()].strip() if label_m else ""
            tokens = [t for t in re.split(r"\s+", before) if t]
            name = tokens[-1] if tokens else ""

        product_type = ""
        for ctx in contexts:
            if "拡張パック" in ctx:
                product_type = "拡張パック"
                break
            if "構築デッキ" in ctx:
                product_type = "構築デッキ"
                break

        if name:
            candidates.append((name, sale_date, product_type))

    if not candidates:
        return []

    candidates.sort(
        key=lambda x: (-x[1].toordinal(), product_type_priority(x[2]), x[0])
    )
    filtered_candidates = [
        (name, sale_date, product_type)
        for name, sale_date, product_type in candidates
        if (today - sale_date).days <= RECENT_DAYS_THRESHOLD
    ]

    # 同一商品の重複を除去しつつ順序は保持
    unique_candidates: list[tuple[str, datetime]] = []
    seen: set[tuple[str, datetime]] = set()
    for name, sale_date, _product_type in filtered_candidates:
        candidate = (name, sale_date)
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_candidates.append(candidate)

    return unique_candidates


def fetch_latest_relevant_product(
    today: datetime | None = None,
) -> tuple[str, datetime] | None:
    """後方互換のため、直近商品の先頭1件を返す。"""
    products = fetch_recent_relevant_products(today)
    return products[0] if products else None


def build_diff_markdown(report: dict) -> str:
    """差分レポートをMarkdownに変換"""
    summary = report["summary"]
    title_date = datetime.now().strftime("%Y/%m/%d")

    product_infos = fetch_recent_relevant_products()
    if product_infos:
        products_text = "、".join(
            f"「{pname}」（{pdate.month}月{pdate.day}日発売）"
            for pname, pdate in product_infos
        )
        intro = f"{products_text}に伴い、更新されたQ&Aをまとめています。"
    else:
        intro = "今週更新されたQ&Aをまとめています。"

    lines = [
        f"# {title_date} ポケモンカードQ&Aサイレント修正一覧",
        "",
        intro,
        "",
        "## 更新サマリ",
        "",
        f"- 追加: {summary['added']}件",
        f"- 削除: {summary['removed']}件",
        f"- 変更: {summary['modified']}件",
        "",
    ]

    def append_items(title: str, items: list[dict], answer_key: str = "answer") -> None:
        lines.append(f"## {title}")
        lines.append("")
        if not items:
            lines.append("該当なし")
            lines.append("")
            return

        for item in items:
            question = item.get("question", "")
            answer = item.get(answer_key, "")
            lines.append(f"### Q: {question}")
            lines.append("")
            lines.append(answer)
            lines.append("")

    append_items("削除されたQ&A", report.get("removed", []))
    append_items("追加されたQ&A", report.get("added", []))

    lines.append("## 変更されたQ&A")
    lines.append("")
    modified = report.get("modified", [])
    if not modified:
        lines.append("該当なし")
        lines.append("")
    else:
        for item in modified:
            question = item.get("question", "")
            old_answer = item.get("old_answer", "")
            new_answer = item.get("new_answer", "")

            lines.append(f"### Q: {question}")
            lines.append("")
            lines.append("**変更前**")
            lines.append("")
            lines.append(old_answer)
            lines.append("")
            lines.append("**変更後**")
            lines.append("")
            lines.append(new_answer)
            lines.append("")

    # 末尾タグ
    lines += [
        "---",
        "",
        "#ポケカ #ポケモンカード #ルール #QA",
    ]

    return "\n".join(lines)


def save_diff_markdown(markdown_text: str) -> None:
    """ブログ用Markdownをファイルに保存"""
    try:
        Path(config.BLOG_MARKDOWN_FILE).write_text(markdown_text, encoding="utf-8")
        logger.info(f"ブログ用Markdownを保存: {config.BLOG_MARKDOWN_FILE}")
    except Exception as e:
        logger.error(f"ブログ用Markdownの保存に失敗: {e}")


def generate_blog_markdown(report: dict) -> None:
    """差分のブログ用Markdownを生成して保存する。"""

    markdown_text = build_diff_markdown(report)
    save_diff_markdown(markdown_text)
    title = f"{datetime.now().strftime('%Y/%m/%d')} ポケモンカードQ&Aサイレント修正一覧"
    logger.info("ブログ用Markdownを生成しました: %s", config.BLOG_MARKDOWN_FILE)
    logger.info("ブログタイトル案: %s", title)
