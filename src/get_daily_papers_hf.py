import logging
from datetime import UTC, datetime, time, timedelta

logger = logging.getLogger("newsletter.hf")

DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"


def completed_days(now, last_hours):
    """
    Returns the UTC days whose list was completed within the last hours.

    A day's list keeps growing and being upvoted until midnight UTC, so it is
    only ranked once it ends, and each day lands in exactly one issue.
    """
    cutoff = now - timedelta(hours=last_hours)
    day = cutoff.date()
    days = []
    while day < now.date():
        day_end = datetime.combine(day + timedelta(days=1), time(), tzinfo=UTC)
        if cutoff < day_end <= now:
            days.append(day)
        day += timedelta(days=1)
    return days


async def get_daily_papers_hf(session, last_hours=12, top_n=5):
    """
    Fetches the most upvoted Hugging Face Daily Papers of days that just ended.

    Each paper carries its abstract as 'text', so no article download is needed.

    Parameters:
    session (aiohttp.ClientSession): The session used for HTTP requests.
    last_hours (int): Number of hours to look back. Defaults to 12.
    top_n (int): Number of top papers to return. Defaults to 5.

    Returns:
    list: Papers as dicts with title, url, comments_url, score and text.
    """
    days = completed_days(datetime.now(UTC), last_hours)
    entries = []
    for day in days:
        params = {"date": day.isoformat()}
        async with session.get(DAILY_PAPERS_URL, params=params) as response:
            response.raise_for_status()
            entries += await response.json()
    logger.info("Got %d HF papers from completed days %s", len(entries), days)

    top_papers = sorted(
        (entry["paper"] for entry in entries),
        key=lambda paper: paper["upvotes"],
        reverse=True,
    )
    papers = [
        {
            "title": paper["title"],
            "url": f"https://arxiv.org/abs/{paper['id']}",
            "comments_url": f"https://huggingface.co/papers/{paper['id']}",
            "score": paper["upvotes"],
            "text": paper["summary"],
        }
        for paper in top_papers[:top_n]
    ]
    for paper in papers:
        logger.info("HF paper: [%d upvotes] %s", paper["score"], paper["title"])
    return papers
