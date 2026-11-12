import logging
import random

logger = logging.getLogger("newsletter.select")

DEFAULT_SELECTION_MODE = "top"
VALID_SELECTION_MODES = ("top", "random")

TOP_COUNT = 1
RANDOM_COUNT = 5


def select_stories(stories, selection_mode):
    """
    Orders one source's candidate stories to summarise.

    Every story is returned as a candidate so that unreadable (e.g. paywalled)
    articles can be skipped in favour of the next one; the caller summarises
    the first `wanted` readable ones. An unrecognised selection_mode falls back
    to the default mode rather than aborting the run.

    Parameters:
    stories (list): Stories fetched from one source, best first.
    selection_mode (str): Either 'top' or 'random'.

    Returns:
    tuple: The candidates, and how many of them to summarise.
    """
    if selection_mode not in VALID_SELECTION_MODES:
        logger.warning(
            "Unknown SELECTION_MODE %r, falling back to %r",
            selection_mode,
            DEFAULT_SELECTION_MODE,
        )
        selection_mode = DEFAULT_SELECTION_MODE

    if selection_mode == "random":
        return random.sample(stories, len(stories)), RANDOM_COUNT

    return list(stories), TOP_COUNT
