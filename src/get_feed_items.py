import calendar
import logging
import time

import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger("newsletter.feed")


def entry_text(entry):
    # Full posts sit in 'content'; many feeds only carry a teaser in 'summary'.
    content = entry.get("content")
    raw = content[0].get("value", "") if content else entry.get("summary", "")
    return BeautifulSoup(raw, "html.parser").get_text(separator=" ", strip=True)


async def get_feed_items(session, url, last_hours=12):
    """
    Fetches the items an RSS or Atom feed published in the last hours.

    Feeds are not ranked, so every recent item is returned, newest first.

    Parameters:
    session (aiohttp.ClientSession): The session used for HTTP requests.
    url (str): The feed URL.
    last_hours (int): Number of hours to look back. Defaults to 12.

    Returns:
    list: Items as dicts with title, url and text.
    """
    async with session.get(url) as response:
        response.raise_for_status()
        feed = feedparser.parse(await response.read())

    cutoff = time.time() - last_hours * 3600
    items = [
        {
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "text": entry_text(entry),
            "published": calendar.timegm(published),
        }
        for entry in feed.entries
        if (published := entry.get("published_parsed") or entry.get("updated_parsed"))
        and calendar.timegm(published) >= cutoff
    ]
    items.sort(key=lambda item: item["published"], reverse=True)
    logger.info(
        "Got %d items from %s, %d from the last %d hours",
        len(feed.entries),
        url,
        len(items),
        last_hours,
    )
    return items
