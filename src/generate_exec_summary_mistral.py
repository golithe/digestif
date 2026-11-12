import logging
import os
from functools import cache

from mistralai.client import Mistral
from mistralai.client.utils import BackoffStrategy, RetryConfig

logger = logging.getLogger("newsletter.llm")


@cache
def get_client():
    """
    Returns the Mistral client, built on first use and reused afterwards.

    Building it lazily rather than at import time keeps this module importable
    without credentials, so the test suite can import the whole pipeline.

    Returns:
    Mistral: The API client.
    """
    return Mistral(
        api_key=os.environ["MISTRAL_API_KEY"],
        # The free tier rate-limits bursts; the SDK retries 429/5xx with this backoff.
        retry_config=RetryConfig(
            "backoff",
            BackoffStrategy(
                initial_interval=2_000,
                max_interval=30_000,
                exponent=2,
                max_elapsed_time=120_000,
            ),
            retry_connection_errors=True,
        ),
    )


def generate_executive_summary_mistral(aggregated_texts):
    """
    Generates an executive summary for the given aggregated article text using Mistral.

    Parameters:
    aggregated_texts (str): The aggregated texts of articles.

    Returns:
    str | None: The executive summary, or None when there was no text to summarise.
    """
    if not aggregated_texts.strip():
        logger.warning("No article text to summarise, skipping Mistral request")
        return None

    logger.info(
        "Requesting Mistral summary (%d chars of input)...", len(aggregated_texts)
    )
    response = get_client().chat.complete(
        model="mistral-small-latest",
        messages=[
            {
                "role": "system",
                "content": "Act like an Insightful Business Analyst. Please create a very concise executive summary for the story. Stick to one or two key points. Your output should be structured as follows:\n\nTitle: [Insert Title Here]\n\nSummary: [Insert Summary Here].",
            },
            {"role": "user", "content": aggregated_texts},
        ],
    )
    message = response.choices[0].message
    summary = message.content if message else None
    if not isinstance(summary, str):
        raise TypeError(
            f"Expected text back from Mistral, got {type(summary).__name__}"
        )

    logger.info("Mistral summary received (%d chars)", len(summary))
    return summary
