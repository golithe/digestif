import logging
import os

from mistralai.client import Mistral

logger = logging.getLogger("newsletter.llm")

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])


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
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {
                "role": "system",
                "content": "Act like an Insightful Business Analyst. Please create a very concise executive summary for the story. Stick to one or two key points. Your output should be structured as follows:\n\nTitle: [Insert Title Here]\n\nSummary: [Insert Summary Here].",
            },
            {"role": "user", "content": aggregated_texts},
        ],
    )
    summary = response.choices[0].message.content
    logger.info("Mistral summary received (%d chars)", len(summary))
    return summary
