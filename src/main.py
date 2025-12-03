import hashlib
import json
import logging
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib import error, request

from bs4 import BeautifulSoup

import config

# ログ設定
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Faq:
    question_hash: str
    question: str
    answer: str


class ScraperError(Exception):
    """スクレイピング関連のエラー"""

    pass


def get_total_pages(soup: BeautifulSoup) -> int:
    """総ページ数を取得"""
    try:
        all_num_text = soup.select_one(".AllNum").get_text(strip=True)
        total_pages = all_num_text.split("/")[-1]
        pages = int(total_pages)
        logger.info(f"総ページ数: {pages}")
        return pages
    except (AttributeError, ValueError, IndexError) as e:
        logger.error(f"総ページ数の取得に失敗: {e}")
        raise ScraperError(f"総ページ数の取得に失敗: {e}") from e


def get_faq_from_page(page_num: int, retry_count: int = 0) -> list[Faq]:
    """指定ページのFAQを取得（リトライ機能付き）"""
    url = f"{config.BASE_URL}?ses=1&page={page_num}"

    try:
        # サーバーへの負荷を考慮した待機
        wait_time = random.uniform(config.SLEEP_MIN, config.SLEEP_MAX)
        time.sleep(wait_time)

        logger.debug(f"ページ {page_num} を取得中... (URL: {url})")
        response = request.urlopen(url, timeout=config.REQUEST_TIMEOUT)
        soup = BeautifulSoup(response, "html.parser")
        response.close()

        faq_items = soup.select(".FAQResultList_item")
        if not faq_items:
            logger.warning(f"ページ {page_num} にFAQアイテムが見つかりません")
            return []

        faq_list: list[Faq] = []
        for i, item in enumerate(faq_items, start=1):
            try:
                question = item.select_one(".QuestionArea .BodyArea").get_text(
                    strip=True
                )
                answer = item.select_one(".AnswerArea .BodyArea").get_text(
                    separator="\n", strip=True
                )
                question_hash = hashlib.sha256(question.encode()).hexdigest()
                faq_list.append(
                    Faq(question_hash=question_hash, question=question, answer=answer)
                )
            except AttributeError as e:
                logger.warning(f"ページ {page_num} のアイテム {i} の解析に失敗: {e}")
                continue

        logger.info(f"ページ {page_num}: {len(faq_list)} 件のFAQを取得")
        return faq_list

    except error.URLError as e:
        if retry_count < config.MAX_RETRIES:
            retry_delay = config.RETRY_DELAY * (retry_count + 1)
            logger.warning(
                f"ページ {page_num} の取得に失敗。{retry_delay}秒後にリトライします... "
                f"(試行 {retry_count + 1}/{config.MAX_RETRIES}): {e}"
            )
            time.sleep(retry_delay)
            return get_faq_from_page(page_num, retry_count + 1)
        else:
            logger.error(
                f"ページ {page_num} の取得に {config.MAX_RETRIES} 回失敗しました: {e}"
            )
            raise ScraperError(f"ページ {page_num} の取得に失敗: {e}") from e
    except Exception as e:
        logger.error(f"ページ {page_num} の処理中に予期しないエラー: {e}")
        raise ScraperError(f"ページ {page_num} の処理中にエラー: {e}") from e


def load_existing_data() -> list[dict]:
    """既存のFAQデータを読み込み"""
    output_path = Path(config.OUTPUT_FILE)
    if output_path.exists():
        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
            logger.info(f"既存データを読み込みました: {len(data)} 件")
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"既存データの読み込みに失敗: {e}")
            return []
    return []


def generate_diff_report(old_data: list[dict], new_data: list[dict]) -> dict:
    """差分レポートを生成"""
    old_hashes = {faq["question_hash"]: faq for faq in old_data}
    new_hashes = {faq["question_hash"]: faq for faq in new_data}

    added = [new_hashes[h] for h in (set(new_hashes.keys()) - set(old_hashes.keys()))]
    removed = [old_hashes[h] for h in (set(old_hashes.keys()) - set(new_hashes.keys()))]

    # 変更されたもの（ハッシュは同じだが内容が異なる）
    modified = []
    for h in set(old_hashes.keys()) & set(new_hashes.keys()):
        if old_hashes[h]["answer"] != new_hashes[h]["answer"]:
            modified.append(
                {
                    "question_hash": h,
                    "question": new_hashes[h]["question"],
                    "old_answer": old_hashes[h]["answer"],
                    "new_answer": new_hashes[h]["answer"],
                }
            )

    report = {
        "summary": {
            "total_old": len(old_data),
            "total_new": len(new_data),
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
        },
        "added": added[:10],  # 最初の10件のみ保存
        "removed": removed[:10],
        "modified": modified[:10],
    }

    logger.info(f"差分レポート: {report['summary']}")
    return report


def save_diff_report(report: dict) -> None:
    """差分レポートをファイルに保存"""
    try:
        Path(config.DIFF_REPORT_FILE).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"差分レポートを保存: {config.DIFF_REPORT_FILE}")
    except Exception as e:
        logger.error(f"差分レポートの保存に失敗: {e}")


def main():
    logger.info("FAQ更新処理を開始")

    try:
        # 既存データの読み込み
        old_data = load_existing_data()

        # 初回ページの取得
        url = f"{config.BASE_URL}?ses=1&page=1"
        logger.info(f"初回ページを取得中: {url}")
        response = request.urlopen(url, timeout=config.REQUEST_TIMEOUT)
        soup = BeautifulSoup(response, "html.parser")
        response.close()

        # 全FAQを取得
        all_faq_list: list[Faq] = []
        total_pages = get_total_pages(soup=soup)

        for i in range(1, total_pages + 1):
            faq_list = get_faq_from_page(i)
            all_faq_list.extend(faq_list)

        logger.info(f"合計 {len(all_faq_list)} 件のFAQを取得しました")

        # ハッシュでソート
        sorted_all_faq_list = sorted(all_faq_list, key=lambda faq: faq.question_hash)
        new_data = [asdict(faq) for faq in sorted_all_faq_list]

        # 差分レポート生成
        diff_report = generate_diff_report(old_data, new_data)
        save_diff_report(diff_report)

        # データ保存
        Path(config.OUTPUT_FILE).write_text(
            json.dumps(new_data, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )

        logger.info(f"FAQデータを保存: {config.OUTPUT_FILE}")
        logger.info("FAQ更新処理が正常に完了しました")

        # 変更があった場合のみ終了コード0
        if diff_report["summary"]["added"] > 0 or diff_report["summary"]["removed"] > 0:
            logger.info("変更が検出されました")
        else:
            logger.info("変更はありませんでした")

    except ScraperError as e:
        logger.error(f"スクレイピングエラー: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
