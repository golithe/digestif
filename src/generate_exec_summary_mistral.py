import logging
import os
from functools import cache

from mistralai.client import Mistral

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
    return Mistral(api_key=os.environ["MISTRAL_API_KEY"])


def generate_executive_summary_mistral(aggregated_texts):
    """
    Generates an executive summary for the given aggregated article text using Mistral.

    Parameters:
    aggregated_texts (str): The aggregated texts of articles.

    Returns:
    str: The executive summary of the aggregated texts.
    """
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
