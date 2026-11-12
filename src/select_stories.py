import logging
import random

logger = logging.getLogger("newsletter.select")

DEFAULT_SELECTION_MODE = "top"
VALID_SELECTION_MODES = ("top", "random")

TOP_COUNT = 1
RANDOM_COUNT = 5


def select_stories(hn_stories, lobsters_stories, selection_mode):
    """
    Orders the candidate stories to summarise from each source.

    Every story is returned as a candidate so that unreadable (e.g. paywalled)
    articles can be skipped in favour of the next one; the caller summarises
    the first `wanted` readable ones. An unrecognised selection_mode falls back
    to the default mode rather than aborting the run.

    Parameters:
    hn_stories (list): Stories fetched from Hacker News.
    lobsters_stories (list): Stories fetched from Lobsters.
    selection_mode (str): Either 'top' or 'random'.

    Returns:
    tuple: HN candidates, Lobsters candidates, and how many of each to summarise.
    """
    if selection_mode not in VALID_SELECTION_MODES:
        logger.warning(
            "Unknown SELECTION_MODE %r, falling back to %r",
            selection_mode,
            DEFAULT_SELECTION_MODE,
        )
        selection_mode = DEFAULT_SELECTION_MODE

    if selection_mode == "random":
        return (
            random.sample(hn_stories, len(hn_stories)),
            random.sample(lobsters_stories, len(lobsters_stories)),
            RANDOM_COUNT,
        )

    return list(hn_stories), list(lobsters_stories), TOP_COUNT
