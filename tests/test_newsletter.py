from unittest.mock import MagicMock, patch

from aggregate_article_texts import aggregate_article_texts
from format_newsletter import create_html_newsletter, format_summary


def test_format_summary_extracts_title_and_summary():
    raw = "Title: My Article\n\nSummary: This is the key point."
    result = format_summary(raw)
    assert "<b>My Article</b>" in result
    assert "This is the key point." in result


def test_format_summary_strips_markdown_bold():
    raw = "**Title:** Bold Title\n\nSummary: Clean text."
    result = format_summary(raw)
    assert "**" not in result


def test_format_summary_fallback_on_unrecognised_input():
    raw = "Some completely unstructured text with no labels."
    result = format_summary(raw)
    assert result == raw


def test_create_html_newsletter_contains_story_links():
    hn_stories = [{"url": "https://example.com/hn", "title": "HN Story"}]
    lobsters_stories = [{"url": "https://example.com/lob", "title": "Lob Story"}]
    html = create_html_newsletter(
        "Title: T\nSummary: S", "Title: T\nSummary: S", hn_stories, lobsters_stories
    )
    assert "https://example.com/hn" in html
    assert "HN Story" in html
    assert "https://example.com/lob" in html
    assert "Lob Story" in html


def test_aggregate_article_texts_skips_failed_requests():
    articles = [{"url": "https://example.com/1"}, {"url": "https://example.com/2"}]

    def fake_get(url, timeout):
        if "1" in url:
            raise ConnectionError("network down")
        mock_response = MagicMock()
        mock_response.text = "<html><body><p>Good content</p></body></html>"
        mock_response.raise_for_status = MagicMock()
        return mock_response

    with patch("aggregate_article_texts.requests.get", side_effect=fake_get):
        result = aggregate_article_texts(articles)

    assert "Good content" in result
