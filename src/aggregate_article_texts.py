import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("newsletter.aggregate")


def aggregate_article_texts(articles, text_limit=4000):
    """
    Fetches and aggregates text from a list of article URLs.

    Parameters:
    articles (list): A list of dictionaries, each containing the 'url' of an article.
    text_limit (int): Maximum number of characters to include from each article.

    Returns:
    str: Aggregated text from all articles, up to `text_limit` characters each.
    """
    aggregated_texts = []

    for article in articles:
        url = article.get("url", "unknown")
        try:
            logger.info("Downloading article: %s", url)
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()

            content = soup.find("article") or soup.find("main") or soup.body
            text = content.get_text(separator=" ", strip=True) if content else ""

            text_len = len(text)
            aggregated_texts.append(text[:text_limit])
            logger.info(
                "Parsed article (%d chars, limited to %d): %s",
                text_len,
                text_limit,
                url,
            )
        except Exception:
            logger.exception("Error fetching article from %s", url)

    logger.info("Aggregated %d articles", len(aggregated_texts))
    return " ".join(aggregated_texts)
