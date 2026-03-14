import json
import logging
from pathlib import Path

import config
from blog_markdown import generate_blog_markdown, has_diff

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
)
logger = logging.getLogger(__name__)


def main() -> None:
    diff_path = Path(config.DIFF_REPORT_FILE)
    if not diff_path.exists():
        logger.info("差分レポートが存在しないため、Markdown生成をスキップします")
        return

    report = json.loads(diff_path.read_text(encoding="utf-8"))
    if not has_diff(report):
        logger.info("差分がないため、Markdown生成をスキップします")
        return

    generate_blog_markdown(report)


if __name__ == "__main__":
    main()
