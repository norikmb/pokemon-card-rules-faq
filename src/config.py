"""設定ファイル"""

import os

# スクレイピング設定
BASE_URL = "https://www.pokemon-card.com/rules/faq/search.php?freeword=&regulation_faq_main_item1=all"
OUTPUT_FILE = "faq_data.json"
DIFF_REPORT_FILE = "diff_report.json"
DIFF_MARKDOWN_FILE = "diff_report.md"

# リトライ設定
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒
REQUEST_TIMEOUT = 30  # 秒

# 待機時間設定（サーバーへの負荷を考慮）
SLEEP_MIN = 0.5
SLEEP_MAX = 2.0

# ログ設定
LOG_FILE = "faq_update.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"

# note連携設定
NOTE_AUTO_POST = os.getenv("NOTE_AUTO_POST", "false").lower() == "true"
NOTE_COOKIE = os.getenv("NOTE_COOKIE", "")
NOTE_USERNAME = os.getenv("NOTE_USERNAME", "")
NOTE_API_BASE_URL = os.getenv("NOTE_API_BASE_URL", "https://note.com")
NOTE_USER_AGENT = os.getenv(
    "NOTE_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
)
