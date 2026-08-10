import asyncio
import logging
import os
import random
import sys

import aiohttp

from aggregate_article_texts import aggregate_article_texts
from format_newsletter import create_html_newsletter
from generate_exec_summary_mistral import generate_executive_summary_mistral
from get_top_stories_hn import get_top_stories_hn
from get_top_stories_lobsters import get_top_stories_lobsters
from send_email import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("newsletter")


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

    # Depending on the selection_mode, select stories
    if selection_mode == "random":
        selected_hn_stories = random.sample(hn_stories, min(len(hn_stories), 5))
        selected_lobsters_stories = random.sample(
            lobsters_stories, min(len(lobsters_stories), 5)
        )
    elif selection_mode == "top":
        selected_hn_stories = hn_stories[:1]
        selected_lobsters_stories = lobsters_stories[:1]

    logger.info(
        "Selected %d HN and %d Lobsters stories",
        len(selected_hn_stories),
        len(selected_lobsters_stories),
    )

    logger.info("Aggregating article texts...")
    aggregated_hn = aggregate_article_texts(selected_hn_stories)
    aggregated_lobsters = aggregate_article_texts(selected_lobsters_stories)

    logger.info("Generating summaries via GPT...")
    summary_hn = generate_executive_summary_mistral(aggregated_hn)
    summary_lobsters = generate_executive_summary_mistral(aggregated_lobsters)
    logger.info("Summaries generated")

    logger.info("Formatting newsletter HTML...")
    newsletter_html = create_html_newsletter(
        summary_hn, summary_lobsters, hn_stories, lobsters_stories
    )

    recipient = os.environ.get("NL_RECIPIENT")
    logger.info("Sending newsletter to %s...", recipient)
    send_email("Daily Digest with Summary", newsletter_html, recipient, html=True)
    logger.info("Newsletter sent successfully")


if __name__ == "__main__":
    asyncio.run(main())
