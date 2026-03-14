import json
import logging
import re
from datetime import datetime
from html import escape
from pathlib import Path
from urllib import request

from bs4 import BeautifulSoup

import config

PRODUCTS_URL = "https://www.pokemon-card.com/products/index.html"
# 発売日がこの日数以内なら「直近」とみなす
RECENT_DAYS_THRESHOLD = 7

logger = logging.getLogger(__name__)


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

    try:
        req = request.Request(
            PRODUCTS_URL,
            headers={"User-Agent": config.NOTE_USER_AGENT},
        )
        with request.urlopen(req, timeout=config.REQUEST_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("商品ページの取得に失敗しました: %s", e)
        return []

    soup = BeautifulSoup(html, "html.parser")
    # 「拡張パック販売日」「構築デッキ販売日」を含むテキストノードを探す
    sale_label_re = re.compile(r"(拡張パック|構築デッキ)販売日")
    date_re = re.compile(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日")

    candidates: list[tuple[str, datetime]] = []

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

        if name:
            candidates.append((name, sale_date))

    if not candidates:
        return []

    candidates.sort(key=lambda x: x[1], reverse=True)
    filtered_candidates = [
        (name, sale_date)
        for name, sale_date in candidates
        if (today - sale_date).days <= RECENT_DAYS_THRESHOLD
    ]

    # 同一商品の重複を除去しつつ順序は保持
    unique_candidates: list[tuple[str, datetime]] = []
    seen: set[tuple[str, datetime]] = set()
    for candidate in filtered_candidates:
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
    """差分Markdownをファイルに保存"""
    try:
        Path(config.DIFF_MARKDOWN_FILE).write_text(markdown_text, encoding="utf-8")
        logger.info(f"差分Markdownを保存: {config.DIFF_MARKDOWN_FILE}")
    except Exception as e:
        logger.error(f"差分Markdownの保存に失敗: {e}")


def markdown_to_html(markdown_text: str) -> str:
    """簡易Markdown→HTML変換（note投稿用）"""
    html_lines: list[str] = []
    in_code_block = False
    in_list = False

    for line in markdown_text.splitlines():
        stripped = line.strip()

        if stripped == "```":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<pre><code>" if not in_code_block else "</code></pre>")
            in_code_block = not in_code_block
            continue

        if in_code_block:
            html_lines.append(escape(line))
            continue

        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue

        if stripped.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3>{escape(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{escape(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{escape(stripped[2:])}</h1>")
        elif stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{escape(stripped[2:])}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{escape(stripped)}</p>")

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def create_note_draft(title: str, html_body: str) -> tuple[int, str]:
    """note下書きを作成してID/キーを返す"""
    url = f"{config.NOTE_API_BASE_URL}/api/v1/text_notes"
    payload = {
        "name": title,
        "body": html_body,
        "template_key": None,
    }
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": config.NOTE_USER_AGENT,
            "Cookie": config.NOTE_COOKIE,
        },
    )

    with request.urlopen(req, timeout=config.REQUEST_TIMEOUT) as response:
        response_data = json.loads(response.read().decode("utf-8"))

    data = response_data["data"]
    return data["id"], data["key"]


def update_note_draft(note_id: int, title: str, html_body: str) -> None:
    """note下書きを更新"""
    url = f"{config.NOTE_API_BASE_URL}/api/v1/text_notes/{note_id}"
    payload = {
        "name": title,
        "body": html_body,
        "status": "draft",
    }
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="PUT",
        headers={
            "Content-Type": "application/json",
            "User-Agent": config.NOTE_USER_AGENT,
            "Cookie": config.NOTE_COOKIE,
        },
    )

    with request.urlopen(req, timeout=config.REQUEST_TIMEOUT):
        return


def post_diff_to_note(report: dict) -> None:
    """差分をnoteに下書き投稿"""
    if not config.NOTE_AUTO_POST:
        logger.info("note自動投稿は無効です")
        return

    if not config.NOTE_COOKIE:
        logger.warning("NOTE_COOKIE が未設定のためnote投稿をスキップします")
        return

    markdown_text = build_diff_markdown(report)
    save_diff_markdown(markdown_text)
    html_body = markdown_to_html(markdown_text)
    title = f"{datetime.now().strftime('%Y/%m/%d')} ポケモンカードQ&Aサイレント修正一覧"

    note_id, note_key = create_note_draft(title=title, html_body=html_body)
    update_note_draft(note_id=note_id, title=title, html_body=html_body)
    if config.NOTE_USERNAME:
        note_url = f"{config.NOTE_API_BASE_URL}/{config.NOTE_USERNAME}/n/{note_key}"
    else:
        note_url = f"{config.NOTE_API_BASE_URL}/n/{note_key}"
    logger.info(f"note下書き投稿が完了しました: {note_url}")
