from unittest.mock import MagicMock, patch

from aggregate_article_texts import aggregate_article_texts
from format_newsletter import (
    create_html_newsletter,
    create_text_newsletter,
    format_summary,
    newsletter_subject,
    story_url,
)
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


def test_select_stories_top_mode_keeps_ranking_and_wants_one():
    hn = [{"title": f"hn{i}"} for i in range(5)]
    lobsters = [{"title": f"lob{i}"} for i in range(5)]

    hn_candidates, lobsters_candidates, wanted = select_stories(hn, lobsters, "top")

    assert hn_candidates == hn
    assert lobsters_candidates == lobsters
    assert wanted == 1


def test_select_stories_random_mode_shuffles_all_and_wants_five():
    hn = [{"title": f"hn{i}"} for i in range(10)]
    lobsters = [{"title": f"lob{i}"} for i in range(3)]

    hn_candidates, lobsters_candidates, wanted = select_stories(hn, lobsters, "random")

    assert sorted(s["title"] for s in hn_candidates) == sorted(s["title"] for s in hn)
    assert len(lobsters_candidates) == 3
    assert wanted == 5


def test_select_stories_unknown_mode_falls_back_to_top():
    # An unrecognised SELECTION_MODE used to leave the selection unbound,
    # crashing the run with NameError.
    hn = [{"title": "hn0"}, {"title": "hn1"}]
    lobsters = [{"title": "lob0"}, {"title": "lob1"}]

    assert select_stories(hn, lobsters, "definitely-not-real") == (hn, lobsters, 1)


def test_select_stories_handles_empty_sources():
    assert select_stories([], [], "random") == ([], [], 5)
    assert select_stories([], [], "top") == ([], [], 1)


def test_aggregate_article_texts_skips_failed_requests():
    articles = [{"url": "https://example.com/1"}, {"url": "https://example.com/2"}]

    def fake_get(url, timeout):
        if "1" in url:
            raise ConnectionError("network down")
        mock_response = MagicMock()
        mock_response.text = (
            f"<html><body><p>Good content {'x' * 300}</p></body></html>"
        )
        mock_response.raise_for_status = MagicMock()
        return mock_response

    with patch("aggregate_article_texts.requests.get", side_effect=fake_get):
        result, _ = aggregate_article_texts(articles)

    assert "Good content" in result


def test_create_html_newsletter_omits_missing_summaries():
    stories = [{"url": "https://example.com/hn", "title": "HN Story"}]

    html = create_html_newsletter(None, "Title: T\nSummary: S", stories, stories)

    assert "Hacker News Top Story Summary" not in html
    assert "Lobsters Top Story Summary" in html
    assert "https://example.com/hn" in html


def test_summary_skips_mistral_when_there_is_no_text():
    from generate_exec_summary_mistral import generate_executive_summary_mistral

    with patch("generate_exec_summary_mistral.get_client") as get_client:
        assert generate_executive_summary_mistral("  ") is None

    get_client.assert_not_called()


def test_summarise_returns_none_when_mistral_fails():
    from main import summarise

    with patch(
        "main.generate_executive_summary_mistral",
        side_effect=RuntimeError("429 Rate limit exceeded"),
    ):
        assert summarise("some text") is None


def test_story_titles_and_urls_are_escaped():
    stories = [
        {"url": 'https://example.com/?a=1&b="x"', "title": "<script>x</script> & co"}
    ]

    html = create_html_newsletter(None, None, stories, [])

    assert "<script>" not in html
    assert "&lt;script&gt;x&lt;/script&gt; &amp; co" in html
    assert 'href="https://example.com/?a=1&amp;b=&quot;x&quot;"' in html


def test_story_url_rejects_non_http_schemes():
    story = {"id": 7, "url": "javascript:alert(1)", "title": "T"}
    assert story_url(story) == "https://news.ycombinator.com/item?id=7"


def test_format_summary_escapes_llm_markup():
    raw = 'Title: <a href="https://evil.example">Click</a>\n\nSummary: <img src=x> ok'
    result = format_summary(raw)
    assert "<a " not in result
    assert "<img" not in result
    assert result.startswith("<b>&lt;a href=")


def test_failed_run_reports_and_exits_nonzero():
    import main

    with (
        patch("main.main", side_effect=RuntimeError("boom")),
        patch("main.report_failure") as report_failure,
    ):
        assert main.run() == 1

    assert "RuntimeError: boom" in report_failure.call_args.args[0]


def test_failure_email_errors_do_not_escape(monkeypatch):
    from alerting import report_failure

    monkeypatch.setenv("NL_RECIPIENT", "me@example.com")
    with patch("alerting.send_email", side_effect=RuntimeError("resend down")):
        report_failure("trace")


def fake_site(pages):
    def fake_get(url, timeout):
        if pages[url] is None:
            raise ConnectionError("403 Forbidden")
        response = MagicMock()
        response.text = f"<html><body><article>{pages[url]}</article></body></html>"
        return response

    return fake_get


def test_aggregate_falls_through_paywalled_story_to_the_next_one():
    long_text = "Readable article. " * 30
    pages = {
        "https://paywalled.example": None,
        "https://stub.example": "Subscribe to keep reading.",
        "https://open.example": long_text,
        "https://never-fetched.example": long_text,
    }
    articles = [{"url": url} for url in pages]

    with patch(
        "aggregate_article_texts.requests.get", side_effect=fake_site(pages)
    ) as get:
        result, paywalled = aggregate_article_texts(articles, wanted=1)

    assert result == long_text.strip()
    assert get.call_count == 3
    assert paywalled == {"https://stub.example"}


def test_blocked_article_logs_a_warning_without_traceback(caplog):
    import requests

    def forbidden(url, timeout):
        response = requests.Response()
        response.status_code = 403
        response.url = url
        return response

    with patch("aggregate_article_texts.requests.get", side_effect=forbidden):
        aggregate_article_texts([{"url": "https://paywalled.example"}])

    [record] = [
        r
        for r in caplog.records
        if r.name == "newsletter.aggregate" and r.levelname == "WARNING"
    ]
    assert "paywall" in record.getMessage()
    assert "HTTP 403" in record.getMessage()
    assert record.exc_info is None


def test_blocked_article_is_reported_as_paywalled():
    import requests

    def forbidden(url, timeout):
        response = requests.Response()
        response.status_code = 403
        response.url = url
        return response

    with patch("aggregate_article_texts.requests.get", side_effect=forbidden):
        _, paywalled = aggregate_article_texts([{"url": "https://wsj.example/a"}])

    assert paywalled == {"https://wsj.example/a"}


def test_paywalled_stories_are_labelled_in_the_email():
    stories = [
        {"url": "https://wsj.example/a", "title": "Locked"},
        {"url": "https://open.example/b", "title": "Open"},
    ]

    html = create_html_newsletter(
        None, None, stories, [], paywalled_urls={"https://wsj.example/a"}
    )

    assert html.count("(paywall)") == 1
    assert html.index("Locked") < html.index("(paywall)") < html.index("Open")


def test_newsletter_subject_names_day_and_edition():
    from datetime import datetime

    assert newsletter_subject(datetime(2026, 11, 12, 7, 0)) == (
        "Daily Digest – Thu 12 Nov, morning"
    )
    assert newsletter_subject(datetime(2026, 11, 2, 16, 0)) == (
        "Daily Digest – Mon 2 Nov, afternoon"
    )


def test_text_newsletter_has_summaries_links_and_paywall_labels():
    hn = [{"url": "https://wsj.example/a", "title": "Locked & <loaded>"}]
    lobsters = [{"url": "", "comments_url": "https://lobste.rs/s/x", "title": "Lob"}]

    text = create_text_newsletter(
        "**Title:** Big News\n\nSummary: It happened.",
        None,
        hn,
        lobsters,
        paywalled_urls={"https://wsj.example/a"},
    )

    assert "Hacker News Top Story Summary" in text
    assert "Big News\n\nIt happened." in text
    assert "Lobsters Top Story Summary" not in text
    assert "1. Locked & <loaded> (paywall)\n   https://wsj.example/a" in text
    assert "1. Lob\n   https://lobste.rs/s/x" in text
    assert "<" not in text.replace("<loaded>", "")


def test_send_email_sends_text_and_optional_html(monkeypatch):
    from send_email import send_email

    monkeypatch.setenv("RESEND_FROM", "digest@example.com")
    with patch("send_email.resend.Emails.send", return_value={"id": "1"}) as send:
        send_email("S", "me@example.com", text="plain", html="<p>rich</p>")
        send_email("S", "me@example.com", text="only plain")

    first, second = (call.args[0] for call in send.call_args_list)
    assert first["text"] == "plain" and first["html"] == "<p>rich</p>"
    assert second["text"] == "only plain" and "html" not in second
