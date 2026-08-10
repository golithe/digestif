import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger("newsletter.lobsters")


async def get_top_stories_lobsters(session, last_hours=12, top_n=5):
    """
    Asynchronously fetches the top stories from Lobsters within the last specified hours.

    Parameters:
    session (aiohttp.ClientSession): The session used for HTTP requests.
    last_hours (int): Number of hours to look back for top stories. Defaults to 12.
    top_n (int): Number of top stories to return. Defaults to 5.

    Returns:
    list: A list of top stories from Lobsters.
    """
    logger.info("Fetching hottest stories from Lobsters API...")
    async with session.get("https://lobste.rs/hottest.json") as response:
        stories = await response.json()
    logger.info("Got %d stories from Lobsters", len(stories))

    current_time = datetime.now(UTC)

    # Convert Lobsters' created_at to datetime and filter stories
    def filter_stories(story):
        story_time = datetime.fromisoformat(story["created_at"].rstrip("Z"))
        return current_time - story_time < timedelta(hours=last_hours)

    filtered_stories = list(filter(filter_stories, stories))
    logger.info(
        "Filtered to %d Lobsters stories from last %d hours",
        len(filtered_stories),
        last_hours,
    )

    # Sort and select top N stories based on score
    top_stories = sorted(filtered_stories, key=lambda x: x["score"], reverse=True)[
        :top_n
    ]
    for story in top_stories:
        logger.info(
            "Lobsters story: [%d pts] %s",
            story.get("score", 0),
            story.get("title", "?"),
        )

    return top_stories
