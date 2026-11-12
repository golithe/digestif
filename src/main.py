import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime

import aiohttp

from aggregate_article_texts import aggregate_article_texts
from alerting import report_failure
from format_newsletter import (
    create_html_newsletter,
    create_text_newsletter,
    newsletter_subject,
)
from generate_exec_summary_mistral import generate_executive_summary_mistral
from get_daily_papers_hf import get_daily_papers_hf
from get_top_stories_hn import get_top_stories_hn
from get_top_stories_lobsters import get_top_stories_lobsters
from section import Section
from select_stories import select_stories
from send_email import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("newsletter")


def summarise(aggregated_texts):
    # A failed summary must not cost the whole email; the story links still go out.
    try:
        return generate_executive_summary_mistral(aggregated_texts)
    except Exception:
        logger.exception("Summary generation failed, sending newsletter without it")
        return None


SOURCES = (
    ("Hacker News", get_top_stories_hn),
    ("Lobsters", get_top_stories_lobsters),
    ("Hugging Face Daily Papers", get_daily_papers_hf),
)


def build_section(name, stories, selection_mode):
    # One broken source must not cost the whole email; it shows up as unavailable.
    if isinstance(stories, BaseException):
        logger.error("Fetching %s failed", name, exc_info=stories)
        return Section(name, [], failed=True)

    candidates, wanted = select_stories(stories, selection_mode)
    logger.info("%s: summarising up to %d readable stories", name, wanted)
    text, paywalled_urls = aggregate_article_texts(candidates, wanted=wanted)
    return Section(name, stories, summarise(text), paywalled_urls)


async def main():
    logger.info("Starting newsletter generation")
    selection_mode = os.environ.get("SELECTION_MODE", "top")
    logger.info("Selection mode: %s", selection_mode)

    async with aiohttp.ClientSession() as session:
        logger.info("Fetching stories from %d sources...", len(SOURCES))
        results = await asyncio.gather(
            *(fetch(session) for _, fetch in SOURCES), return_exceptions=True
        )

    sections = [
        build_section(name, stories, selection_mode)
        for (name, _), stories in zip(SOURCES, results, strict=True)
    ]
    if all(section.failed for section in sections):
        raise RuntimeError("Every source failed, not sending an empty newsletter")

    logger.info("Formatting newsletter...")
    newsletter_html = create_html_newsletter(sections)
    newsletter_text = create_text_newsletter(sections)

    recipient = os.environ.get("NL_RECIPIENT")
    logger.info("Sending newsletter to %s...", recipient)
    subject = newsletter_subject(datetime.now())
    send_email(subject, recipient, text=newsletter_text, html=newsletter_html)
    logger.info("Newsletter sent successfully")


def run():
    try:
        asyncio.run(main())
    except Exception:
        logger.exception("Newsletter run failed")
        report_failure(traceback.format_exc())
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
