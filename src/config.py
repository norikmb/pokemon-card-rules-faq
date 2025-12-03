"""設定ファイル"""

# スクレイピング設定
BASE_URL = "https://www.pokemon-card.com/rules/faq/search.php"
OUTPUT_FILE = "faq_data.json"
DIFF_REPORT_FILE = "diff_report.json"

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
