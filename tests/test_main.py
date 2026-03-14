"""スクレイピング機能のテスト"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from blog_markdown import (
    build_diff_markdown,
    fetch_latest_relevant_product,
    fetch_recent_relevant_products,
    has_diff,
)
from main import (
    Faq,
    ScraperError,
    build_faq_page_url,
    generate_diff_report,
    get_total_pages,
    is_busy_page,
)
from tests.fixtures.sample_html import SAMPLE_FAQ_LIST_HTML


def test_faq_dataclass():
    """Faqデータクラスのテスト"""
    faq = Faq(question_hash="abc123", question="テスト質問", answer="テスト回答")
    assert faq.question_hash == "abc123"
    assert faq.question == "テスト質問"
    assert faq.answer == "テスト回答"


def test_get_total_pages():
    """総ページ数取得のテスト"""
    soup = BeautifulSoup(SAMPLE_FAQ_LIST_HTML, "html.parser")
    total_pages = get_total_pages(soup)
    assert total_pages == 10


def test_get_total_pages_invalid_html():
    """不正なHTMLでの総ページ数取得のテスト"""
    soup = BeautifulSoup("<html></html>", "html.parser")
    with pytest.raises(ScraperError):
        get_total_pages(soup)


def test_get_total_pages_fallback_by_text():
    """.AllNum がない場合でもテキストから総ページ数を取得できる"""
    html = """
        <html>
            <body>
                <div>検索結果 1 / 25</div>
            </body>
        </html>
        """
    soup = BeautifulSoup(html, "html.parser")
    assert get_total_pages(soup) == 25


def test_get_total_pages_fallback_by_links():
    """.AllNum がない場合でもページリンクから総ページ数を取得できる"""
    html = """
        <html>
            <body>
                <a href="/rules/faq/search.php?ses=1&page=1">1</a>
                <a href="/rules/faq/search.php?ses=1&page=2">2</a>
                <a href="/rules/faq/search.php?ses=1&page=38">38</a>
            </body>
        </html>
        """
    soup = BeautifulSoup(html, "html.parser")
    assert get_total_pages(soup) == 38


def test_is_busy_page_true():
    """アクセス集中エラーページを判定できる"""
    html = """
        <html>
            <body>
                <h1>ERROR</h1>
                <p>ただいま、アクセスが集中しております。</p>
            </body>
        </html>
        """
    soup = BeautifulSoup(html, "html.parser")
    assert is_busy_page(soup) is True


def test_is_busy_page_false():
    """通常のページはアクセス集中エラーとして扱わない"""
    soup = BeautifulSoup(SAMPLE_FAQ_LIST_HTML, "html.parser")
    assert is_busy_page(soup) is False


def test_build_faq_page_url():
    """BASE_URLの既存クエリを保持してpageを付与する"""
    url = build_faq_page_url(7)
    assert "search.php" in url
    assert "freeword=" in url
    assert "regulation_faq_main_item1=all" in url
    assert "page=7" in url


def test_generate_diff_report_no_changes():
    """変更なしの差分レポート生成テスト"""
    old_data = [
        {"question_hash": "hash1", "question": "Q1", "answer": "A1"},
        {"question_hash": "hash2", "question": "Q2", "answer": "A2"},
    ]
    new_data = old_data.copy()

    report = generate_diff_report(old_data, new_data)

    assert report["summary"]["total_old"] == 2
    assert report["summary"]["total_new"] == 2
    assert report["summary"]["added"] == 0
    assert report["summary"]["removed"] == 0
    assert report["summary"]["modified"] == 0


def test_generate_diff_report_with_additions():
    """追加ありの差分レポート生成テスト"""
    old_data = [
        {"question_hash": "hash1", "question": "Q1", "answer": "A1"},
    ]
    new_data = [
        {"question_hash": "hash1", "question": "Q1", "answer": "A1"},
        {"question_hash": "hash2", "question": "Q2", "answer": "A2"},
    ]

    report = generate_diff_report(old_data, new_data)

    assert report["summary"]["added"] == 1
    assert report["summary"]["removed"] == 0
    assert len(report["added"]) == 1
    assert report["added"][0]["question_hash"] == "hash2"


def test_generate_diff_report_with_removals():
    """削除ありの差分レポート生成テスト"""
    old_data = [
        {"question_hash": "hash1", "question": "Q1", "answer": "A1"},
        {"question_hash": "hash2", "question": "Q2", "answer": "A2"},
    ]
    new_data = [
        {"question_hash": "hash1", "question": "Q1", "answer": "A1"},
    ]

    report = generate_diff_report(old_data, new_data)

    assert report["summary"]["added"] == 0
    assert report["summary"]["removed"] == 1
    assert len(report["removed"]) == 1
    assert report["removed"][0]["question_hash"] == "hash2"


def test_generate_diff_report_with_modifications():
    """変更ありの差分レポート生成テスト"""
    old_data = [
        {"question_hash": "hash1", "question": "Q1", "answer": "A1"},
    ]
    new_data = [
        {"question_hash": "hash1", "question": "Q1", "answer": "A1 (updated)"},
    ]

    report = generate_diff_report(old_data, new_data)

    assert report["summary"]["modified"] == 1
    assert len(report["modified"]) == 1
    assert report["modified"][0]["old_answer"] == "A1"
    assert report["modified"][0]["new_answer"] == "A1 (updated)"


def _make_products_html(entries: list[tuple[str, str]]) -> bytes:
    """商品ページのモックHTMLを生成する。
    entries: [(product_name, date_text), ...]
      date_text 例: "2026年 3月13日（金）"
    """
    items = ""
    for name, date_text in entries:
        items += f"""
        <div class="item">
          <p class="name">{name}</p>
          <p class="detail">拡張パック販売日{date_text}希望小売価格180円（税込）</p>
        </div>
        """
    return f"<html><body>{items}</body></html>".encode("utf-8")


def _mock_urlopen(html_bytes: bytes) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.read.return_value = html_bytes
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_fetch_recent_relevant_products_from_top_list_api_json():
    """topList.php(JSON)から直近の拡張パック/構築デッキを取得できる"""
    today = datetime(2026, 3, 14)
    payload = {
        "result": 1,
        "products": [
            {
                "productTitle": "拡張パック 「ニンジャスピナー」",
                "productType": "拡張パック",
                "releaseDate": "2026年 3月13日（金）",
            },
            {
                "productTitle": "スターターセットMEGA メガゲンガーex",
                "productType": "構築デッキ",
                "releaseDate": "2026年 3月12日（木）",
            },
            {
                "productTitle": "カードイラストフィギュアコレクション",
                "productType": "その他の商品",
                "releaseDate": "2026年 3月13日（金）",
            },
        ],
    }
    response_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    with patch(
        "blog_markdown.request.urlopen",
        return_value=_mock_urlopen(response_bytes),
    ):
        result = fetch_recent_relevant_products(today)

    assert result == [
        ("ニンジャスピナー", datetime(2026, 3, 13)),
        ("スターターセットMEGA メガゲンガーex", datetime(2026, 3, 12)),
    ]


def test_fetch_latest_relevant_product_found():
    """直近7日以内の発売商品が正しく取得できる"""
    today = datetime(2026, 3, 14)
    html = _make_products_html([("「ニンジャスピナー」", "2026年 3月13日（金）")])
    with patch("blog_markdown.request.urlopen", return_value=_mock_urlopen(html)):
        result = fetch_latest_relevant_product(today)
    assert result is not None
    name, sale_date = result
    assert name == "ニンジャスピナー"
    assert sale_date == datetime(2026, 3, 13)


def test_fetch_latest_relevant_product_too_old():
    """8日以上前の発売商品はNoneを返す"""
    today = datetime(2026, 3, 14)
    html = _make_products_html([("「ニンジャスピナー」", "2026年 3月 5日（木）")])
    with patch("blog_markdown.request.urlopen", return_value=_mock_urlopen(html)):
        result = fetch_latest_relevant_product(today)
    assert result is None


def test_fetch_latest_relevant_product_future_skipped():
    """未発売商品はスキップされ、発売済みの最新商品が選ばれる"""
    today = datetime(2026, 3, 14)
    html = _make_products_html(
        [
            ("「未来のカード」", "2026年 3月20日（金）"),
            ("「ニンジャスピナー」", "2026年 3月13日（金）"),
        ]
    )
    with patch("blog_markdown.request.urlopen", return_value=_mock_urlopen(html)):
        result = fetch_latest_relevant_product(today)
    assert result is not None
    assert result[0] == "ニンジャスピナー"


def test_fetch_recent_relevant_products_multiple_found():
    """直近7日以内に複数商品がある場合は複数返す"""
    today = datetime(2026, 3, 14)
    html = _make_products_html(
        [
            ("「ニンジャスピナー」", "2026年 3月13日（金）"),
            ("「スターターセットMEGA メガゲンガーex」", "2026年 3月12日（木）"),
            ("「古いカード」", "2026年 3月 1日（日）"),
        ]
    )
    with patch("blog_markdown.request.urlopen", return_value=_mock_urlopen(html)):
        result = fetch_recent_relevant_products(today)
    assert result == [
        ("ニンジャスピナー", datetime(2026, 3, 13)),
        ("スターターセットMEGA メガゲンガーex", datetime(2026, 3, 12)),
    ]


def test_fetch_latest_relevant_product_network_error():
    """ネットワークエラー時はNoneを返す"""
    today = datetime(2026, 3, 14)
    with patch("blog_markdown.request.urlopen", side_effect=OSError("network error")):
        result = fetch_latest_relevant_product(today)
    assert result is None


@patch("blog_markdown.fetch_recent_relevant_products", return_value=[])
def test_build_diff_markdown_intro_no_product(mock_fetch):
    """直近商品がない場合は「今週」イントロになる"""
    report = {
        "summary": {
            "total_old": 1,
            "total_new": 1,
            "added": 0,
            "removed": 0,
            "modified": 1,
        },
        "added": [],
        "removed": [],
        "modified": [
            {
                "question_hash": "h",
                "question": "Q",
                "old_answer": "old",
                "new_answer": "new",
            }
        ],
    }
    markdown = build_diff_markdown(report)
    assert "今週" in markdown


@patch(
    "blog_markdown.fetch_recent_relevant_products",
    return_value=[("ニンジャスピナー", datetime(2026, 3, 13))],
)
def test_build_diff_markdown_intro_with_product(mock_fetch):
    """直近商品がある場合は商品名と発売日がイントロに入る"""
    report = {
        "summary": {
            "total_old": 1,
            "total_new": 1,
            "added": 0,
            "removed": 0,
            "modified": 1,
        },
        "added": [],
        "removed": [],
        "modified": [
            {
                "question_hash": "h",
                "question": "Q",
                "old_answer": "old",
                "new_answer": "new",
            }
        ],
    }
    markdown = build_diff_markdown(report)
    assert "「ニンジャスピナー」" in markdown
    assert "3月13日" in markdown


@patch(
    "blog_markdown.fetch_recent_relevant_products",
    return_value=[
        ("ニンジャスピナー", datetime(2026, 3, 13)),
        ("スターターセットMEGA メガゲンガーex", datetime(2026, 3, 12)),
    ],
)
def test_build_diff_markdown_intro_with_multiple_products(mock_fetch):
    """直近商品が複数ある場合は複数商品名がイントロに入る"""
    report = {
        "summary": {
            "total_old": 1,
            "total_new": 1,
            "added": 0,
            "removed": 0,
            "modified": 1,
        },
        "added": [],
        "removed": [],
        "modified": [
            {
                "question_hash": "h",
                "question": "Q",
                "old_answer": "old",
                "new_answer": "new",
            }
        ],
    }
    markdown = build_diff_markdown(report)
    assert "「ニンジャスピナー」" in markdown
    assert "「スターターセットMEGA メガゲンガーex」" in markdown

    """追加削除がなくても変更があれば差分あり"""
    report = {
        "summary": {
            "total_old": 1,
            "total_new": 1,
            "added": 0,
            "removed": 0,
            "modified": 1,
        }
    }
    assert has_diff(report) is True


@patch("blog_markdown.fetch_recent_relevant_products", return_value=[])
def test_build_diff_markdown_contains_sections(mock_fetch):
    """差分Markdownに主要セクションが含まれる"""
    report = {
        "summary": {
            "total_old": 2,
            "total_new": 3,
            "added": 1,
            "removed": 0,
            "modified": 1,
        },
        "added": [
            {
                "question_hash": "hash-new",
                "question": "Q_new",
                "answer": "A_new",
            }
        ],
        "removed": [],
        "modified": [
            {
                "question_hash": "hash-mod",
                "question": "Q_mod",
                "old_answer": "A_old",
                "new_answer": "A_new",
            }
        ],
    }

    markdown = build_diff_markdown(report)

    assert "## 更新サマリ" in markdown
    assert "## 削除されたQ&A" in markdown
    assert "## 追加されたQ&A" in markdown
    assert "## 変更されたQ&A" in markdown
    assert "Q: Q_new" in markdown
    assert "**変更前**" in markdown
    assert "**変更後**" in markdown
    assert "#ポケカ" in markdown
