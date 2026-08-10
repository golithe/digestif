import logging
import random

logger = logging.getLogger("newsletter.select")

DEFAULT_SELECTION_MODE = "top"
VALID_SELECTION_MODES = ("top", "random")

TOP_COUNT = 1
RANDOM_COUNT = 5


def select_stories(hn_stories, lobsters_stories, selection_mode):
    """
    Selects the stories to summarise from each source.

    An unrecognised selection_mode falls back to the default mode rather than
    aborting the run.

    Parameters:
    hn_stories (list): Stories fetched from Hacker News.
    lobsters_stories (list): Stories fetched from Lobsters.
    selection_mode (str): Either 'top' or 'random'.

    Returns:
    tuple: The selected HN stories and the selected Lobsters stories.
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
            random.sample(hn_stories, min(len(hn_stories), RANDOM_COUNT)),
            random.sample(lobsters_stories, min(len(lobsters_stories), RANDOM_COUNT)),
        )

    return hn_stories[:TOP_COUNT], lobsters_stories[:TOP_COUNT]
