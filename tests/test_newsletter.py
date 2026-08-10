from unittest.mock import MagicMock, patch

from aggregate_article_texts import aggregate_article_texts
from format_newsletter import create_html_newsletter, format_summary, story_url
from select_stories import select_stories


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


def test_story_url_prefers_the_article_link():
    story = {"url": "https://example.com/article", "id": 123}
    assert story_url(story) == "https://example.com/article"


def test_story_url_falls_back_to_hn_discussion_for_text_posts():
    # Ask HN and job posts come back from the HN API with no "url" key.
    story = {"id": 42, "title": "Ask HN: anything?"}
    assert story_url(story) == "https://news.ycombinator.com/item?id=42"


def test_story_url_falls_back_to_lobsters_comments_for_empty_url():
    story = {"url": "", "comments_url": "https://lobste.rs/s/abc123", "title": "T"}
    assert story_url(story) == "https://lobste.rs/s/abc123"


def test_create_html_newsletter_handles_stories_without_url():
    hn_stories = [{"id": 42, "title": "Ask HN: anything?"}]
    lobsters_stories = [
        {"url": "", "comments_url": "https://lobste.rs/s/abc123", "title": "Lob Text"}
    ]

    html = create_html_newsletter(
        "Title: T\nSummary: S", "Title: T\nSummary: S", hn_stories, lobsters_stories
    )

    assert "https://news.ycombinator.com/item?id=42" in html
    assert "https://lobste.rs/s/abc123" in html
    assert 'href=""' not in html


def test_select_stories_top_mode_takes_the_highest_ranked():
    hn = [{"title": f"hn{i}"} for i in range(5)]
    lobsters = [{"title": f"lob{i}"} for i in range(5)]

    selected_hn, selected_lobsters = select_stories(hn, lobsters, "top")

    assert selected_hn == [{"title": "hn0"}]
    assert selected_lobsters == [{"title": "lob0"}]


def test_select_stories_random_mode_samples_up_to_five():
    hn = [{"title": f"hn{i}"} for i in range(10)]
    lobsters = [{"title": f"lob{i}"} for i in range(3)]

    selected_hn, selected_lobsters = select_stories(hn, lobsters, "random")

    assert len(selected_hn) == 5
    assert len(selected_lobsters) == 3
    assert all(story in hn for story in selected_hn)


def test_select_stories_unknown_mode_falls_back_to_top():
    # An unrecognised SELECTION_MODE used to leave the selection unbound,
    # crashing the run with NameError.
    hn = [{"title": "hn0"}, {"title": "hn1"}]
    lobsters = [{"title": "lob0"}, {"title": "lob1"}]

    selected_hn, selected_lobsters = select_stories(hn, lobsters, "definitely-not-real")

    assert selected_hn == [{"title": "hn0"}]
    assert selected_lobsters == [{"title": "lob0"}]


def test_select_stories_handles_empty_sources():
    assert select_stories([], [], "random") == ([], [])
    assert select_stories([], [], "top") == ([], [])


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
