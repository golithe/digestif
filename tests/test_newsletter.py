from unittest.mock import MagicMock, patch

from aggregate_article_texts import aggregate_article_texts
from format_newsletter import (
    create_html_newsletter,
    create_text_newsletter,
    format_summary,
    newsletter_subject,
    story_url,
)
from section import Section
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
    html = create_html_newsletter(
        [
            Section("Hacker News", [{"url": "https://example.com/hn", "title": "HN"}]),
            Section("Lobsters", [{"url": "https://example.com/lob", "title": "Lob"}]),
        ]
    )
    assert "https://example.com/hn" in html
    assert "https://example.com/lob" in html
    assert html.index("Hacker News") < html.index("HN") < html.index("Lobsters")


def test_story_url_prefers_the_article_link():
    story = {"url": "https://example.com/article", "comments_url": "https://hn/1"}
    assert story_url(story) == "https://example.com/article"


def test_story_url_falls_back_to_lobsters_comments_for_empty_url():
    story = {"url": "", "comments_url": "https://lobste.rs/s/abc123", "title": "T"}
    assert story_url(story) == "https://lobste.rs/s/abc123"


def test_create_html_newsletter_handles_stories_without_url():
    stories = [
        {"url": "", "comments_url": "https://lobste.rs/s/abc123", "title": "Text"},
        {"title": "Nowhere to link"},
    ]

    html = create_html_newsletter([Section("Lobsters", stories)])

    assert "https://lobste.rs/s/abc123" in html
    assert "<li>Nowhere to link</li>" in html
    assert 'href=""' not in html


def test_select_stories_top_mode_keeps_ranking_and_wants_one():
    stories = [{"title": f"s{i}"} for i in range(5)]
    assert select_stories(stories, "top") == (stories, 1)


def test_select_stories_random_mode_shuffles_all_and_wants_five():
    stories = [{"title": f"s{i}"} for i in range(10)]

    candidates, wanted = select_stories(stories, "random")

    assert sorted(s["title"] for s in candidates) == sorted(s["title"] for s in stories)
    assert wanted == 5


def test_select_stories_unknown_mode_falls_back_to_top():
    # An unrecognised SELECTION_MODE used to leave the selection unbound,
    # crashing the run with NameError.
    stories = [{"title": "s0"}, {"title": "s1"}]
    assert select_stories(stories, "definitely-not-real") == (stories, 1)


def test_select_stories_handles_empty_sources():
    assert select_stories([], "random") == ([], 5)
    assert select_stories([], "top") == ([], 1)


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


def test_sections_render_missing_summary_empty_and_failed_sources():
    stories = [{"url": "https://example.com/hn", "title": "HN Story"}]
    sections = [
        Section("Hacker News", stories),
        Section("Lobsters", []),
        Section("Hugging Face Daily Papers", [], failed=True),
    ]

    for rendered in (
        create_html_newsletter(sections),
        create_text_newsletter(sections),
    ):
        assert "https://example.com/hn" in rendered
        assert "Nothing new since the last issue." in rendered
        assert "Could not be fetched this time." in rendered


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

    html = create_html_newsletter([Section("<b>HN</b>", stories)])

    assert "<script>" not in html
    assert "&lt;b&gt;HN&lt;/b&gt;" in html
    assert "&lt;script&gt;x&lt;/script&gt; &amp; co" in html
    assert 'href="https://example.com/?a=1&amp;b=&quot;x&quot;"' in html


def test_story_url_rejects_non_http_schemes():
    story = {"url": "javascript:alert(1)", "comments_url": "https://hn/7"}
    assert story_url(story) == "https://hn/7"
    assert story_url({"url": "javascript:alert(1)"}) is None


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
    section = Section("HN", stories, paywalled_urls={"https://wsj.example/a"})

    html = create_html_newsletter([section])

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
        [
            Section(
                "Hacker News",
                hn,
                summary="**Title:** Big News\n\nSummary: It happened.",
                paywalled_urls={"https://wsj.example/a"},
            ),
            Section("Lobsters", lobsters),
        ]
    )

    assert "Hacker News\n-----------\nBig News\n\nIt happened." in text
    assert "1. Locked & <loaded> (paywall)\n   https://wsj.example/a" in text
    assert "Lobsters\n--------\n1. Lob\n   https://lobste.rs/s/x" in text
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


def test_aggregate_uses_provided_text_without_downloading():
    papers = [{"url": "https://arxiv.org/abs/1", "text": "An abstract. " * 30}]

    with patch("aggregate_article_texts.requests.get") as get:
        result, paywalled = aggregate_article_texts(papers, wanted=1)

    get.assert_not_called()
    assert result.startswith("An abstract.")
    assert paywalled == set()


def test_one_failing_source_does_not_stop_the_newsletter():
    import asyncio

    import main

    async def broken(session):
        raise RuntimeError("API down")

    async def working(session):
        return [{"url": "https://example.com/a", "title": "Works", "text": "x" * 300}]

    with (
        patch.object(
            main,
            "SOURCES",
            (("Broken", broken, "story"), ("Working", working, "story")),
        ),
        patch("main.summarise", return_value="Title: T\nSummary: S"),
        patch("main.send_email") as send,
    ):
        asyncio.run(main.main())

    html = send.call_args.kwargs["html"]
    assert "Could not be fetched this time." in html
    assert "https://example.com/a" in html


def test_all_sources_failing_raises_so_the_failure_alert_fires():
    import asyncio

    import pytest

    import main

    async def broken(session):
        raise RuntimeError("API down")

    with (
        patch.object(main, "SOURCES", (("Broken", broken, "story"),)),
        patch("main.send_email") as send,
        pytest.raises(RuntimeError, match="Every source failed"),
    ):
        asyncio.run(main.main())

    send.assert_not_called()


def test_each_hf_day_is_sent_in_exactly_one_issue():
    from datetime import UTC, date, datetime

    from get_daily_papers_hf import completed_days

    # Cron runs at 07:00 and 16:00 Swiss time, i.e. 06:00 and 15:00 UTC in winter.
    morning = datetime(2026, 11, 12, 6, 0, tzinfo=UTC)
    afternoon = datetime(2026, 11, 12, 15, 0, tzinfo=UTC)

    assert completed_days(morning, 12) == [date(2026, 11, 11)]
    assert completed_days(afternoon, 12) == []


def test_feed_items_are_filtered_to_the_window_and_stripped_of_html():
    import asyncio
    import time
    from email.utils import formatdate

    from get_feed_items import get_feed_items

    now = time.time()
    rss = f"""<?xml version="1.0"?><rss version="2.0"><channel><title>F</title>
    <item><title>New</title><link>https://example.com/new</link>
      <pubDate>{formatdate(now - 3600)}</pubDate>
      <description>&lt;p&gt;Fresh &lt;b&gt;post&lt;/b&gt;&lt;/p&gt;</description></item>
    <item><title>Old</title><link>https://example.com/old</link>
      <pubDate>{formatdate(now - 48 * 3600)}</pubDate></item>
    </channel></rss>""".encode()

    response = MagicMock()
    response.read = MagicMock(return_value=asyncio.sleep(0, rss))
    session = MagicMock()
    session.get.return_value.__aenter__.return_value = response

    items = asyncio.run(get_feed_items(session, "https://example.com/feed"))

    assert [(item["title"], item["text"]) for item in items] == [("New", "Fresh post")]


def test_short_provided_text_falls_back_to_downloading():
    teaser = [{"url": "https://open.example", "text": "Read more..."}]
    pages = {"https://open.example": "Full article. " * 30}

    with patch("aggregate_article_texts.requests.get", side_effect=fake_site(pages)):
        result, _ = aggregate_article_texts(teaser)

    assert result.startswith("Full article.")


def test_feed_sections_put_each_one_line_summary_under_its_post():
    import main

    items = [
        {"url": f"https://example.com/{i}", "title": f"Post {i}", "text": "x" * 300}
        for i in (1, 2, 3)
    ]
    answer = "1: First point.\n- 3. Third point.\nSome chatter"

    with patch("main.summarise", return_value=answer) as summarise:
        section = main.build_section("Feed", items, "feed", "top")

    sent_text = summarise.call_args.args[0]
    assert "## 1. Post 1" in sent_text and "## 3. Post 3" in sent_text
    assert [story.get("blurb") for story in section.stories] == [
        "First point.",
        None,
        "Third point.",
    ]
    assert section.summary is None

    text = create_text_newsletter([section])
    assert "1. Post 1\n   First point.\n   https://example.com/1" in text
    assert "2. Post 2\n   https://example.com/2" in text
    html = create_html_newsletter([section])
    assert "Post 1</a><br>First point.</li>" in html


def test_each_section_kind_gets_its_own_prompt():
    from generate_exec_summary_mistral import generate_executive_summary_mistral

    with patch("generate_exec_summary_mistral.get_client") as get_client:
        complete = get_client.return_value.chat.complete
        complete.return_value.choices[0].message.content = "ok"
        for kind in ("story", "paper", "feed"):
            generate_executive_summary_mistral("text", kind)

    prompts = [c.kwargs["messages"][0]["content"] for c in complete.call_args_list]
    assert len(set(prompts)) == 3
    assert all("engineer" in prompt for prompt in prompts)
    assert "one line" in prompts[2]


def test_feed_input_marks_each_post_with_its_title():
    posts = [
        {"url": "https://a.example", "title": "First", "text": "a " * 150},
        {"url": "https://b.example", "title": "Second", "text": "b " * 150},
    ]

    result, _ = aggregate_article_texts(posts)

    assert result.startswith("## First\na a")
    assert "\n\n## Second\nb b" in result


def test_one_line_per_post_summaries_keep_their_line_breaks():
    result = format_summary("- First: a point.\n- Second: <b>another</b>.")
    assert result == "- First: a point.<br>- Second: &lt;b&gt;another&lt;/b&gt;."
