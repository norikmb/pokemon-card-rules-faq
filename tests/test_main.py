"""スクレイピング機能のテスト"""

import pytest
from bs4 import BeautifulSoup

from main import (
    Faq,
    ScraperError,
    generate_diff_report,
    get_total_pages,
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
