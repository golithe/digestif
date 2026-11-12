import asyncio
import logging
import os
import sys
import traceback

import aiohttp

from aggregate_article_texts import aggregate_article_texts
from alerting import report_failure
from format_newsletter import create_html_newsletter
from generate_exec_summary_mistral import generate_executive_summary_mistral
from get_top_stories_hn import get_top_stories_hn
from get_top_stories_lobsters import get_top_stories_lobsters
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


async def main():
    logger.info("Starting newsletter generation")
    selection_mode = os.environ.get("SELECTION_MODE", "top")
    logger.info("Selection mode: %s", selection_mode)

    async with aiohttp.ClientSession() as session:
        logger.info("Fetching stories from Hacker News...")
        hn_stories = await get_top_stories_hn(session)
        logger.info("Fetched %d HN stories", len(hn_stories))

        logger.info("Fetching stories from Lobsters...")
        lobsters_stories = await get_top_stories_lobsters(session)
        logger.info("Fetched %d Lobsters stories", len(lobsters_stories))

    hn_candidates, lobsters_candidates, wanted = select_stories(
        hn_stories, lobsters_stories, selection_mode
    )
    logger.info("Summarising up to %d readable stories per source", wanted)

    logger.info("Aggregating article texts...")
    aggregated_hn, paywalled_hn = aggregate_article_texts(hn_candidates, wanted=wanted)
    aggregated_lobsters, paywalled_lobsters = aggregate_article_texts(
        lobsters_candidates, wanted=wanted
    )

    logger.info("Generating summaries via Mistral...")
    summary_hn = summarise(aggregated_hn)
    summary_lobsters = summarise(aggregated_lobsters)

    logger.info("Formatting newsletter HTML...")
    newsletter_html = create_html_newsletter(
        summary_hn,
        summary_lobsters,
        hn_stories,
        lobsters_stories,
        paywalled_urls=paywalled_hn | paywalled_lobsters,
    )

    recipient = os.environ.get("NL_RECIPIENT")
    logger.info("Sending newsletter to %s...", recipient)
    send_email("Daily Digest with Summary", newsletter_html, recipient, html=True)
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
