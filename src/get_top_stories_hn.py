import logging
import time

logger = logging.getLogger("newsletter.hn")

ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


async def get_top_stories_hn(session, last_hours=12, top_n=5):
    """
    Fetches the highest-scoring Hacker News stories of the last hours.

    Uses the free HN Algolia API, which returns titles and points for all
    matching stories in one request.

    Parameters:
    session (aiohttp.ClientSession): The session used for HTTP requests.
    last_hours (int): Number of hours to look back for stories. Defaults to 12.
    top_n (int): Number of top stories to return. Defaults to 5.

    Returns:
    list: Stories as dicts with title, url, comments_url and score.
    """
    since = int(time.time()) - last_hours * 3600
    params = {
        "tags": "story",
        "numericFilters": f"created_at_i>{since}",
        "hitsPerPage": "200",
    }
    async with session.get(ALGOLIA_SEARCH_URL, params=params) as response:
        response.raise_for_status()
        hits = (await response.json())["hits"]
    logger.info("Got %d HN stories from the last %d hours", len(hits), last_hours)

    top_hits = sorted(hits, key=lambda hit: hit.get("points") or 0, reverse=True)
    stories = [
        {
            "title": hit["title"],
            # Ask HN and other text posts have no url.
            "url": hit.get("url") or "",
            "comments_url": f"https://news.ycombinator.com/item?id={hit['objectID']}",
            "score": hit.get("points") or 0,
        }
        for hit in top_hits[:top_n]
    ]
    for story in stories:
        logger.info("HN story: [%d pts] %s", story["score"], story["title"])
    return stories
