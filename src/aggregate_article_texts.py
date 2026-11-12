import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("newsletter.aggregate")

# Paywalls and bot walls often answer 200 with a short "subscribe" stub.
MIN_ARTICLE_CHARS = 200
BLOCKED_STATUSES = {401, 402, 403, 451}


def with_title(article, text):
    # The feed prompt relies on the "## <title>" markers to tell posts apart.
    title = article.get("title")
    return f"## {title}\n{text}" if title else text


def aggregate_article_texts(articles, text_limit=4000, wanted=None):
    """
    Fetches and aggregates text from a list of article URLs, in order.

    Articles that fail to download or yield too little text are skipped, so
    passing more candidates than `wanted` lets paywalled stories fall through
    to the next one. Articles that already carry enough 'text' are not downloaded.

    Parameters:
    articles (list): Dictionaries with the 'url' and optionally the 'text' of an article.
    text_limit (int): Maximum number of characters to include from each article.
    wanted (int | None): Stop after this many readable articles; None reads all.

    Returns:
    tuple: The aggregated text of the readable articles (up to `text_limit`
    characters each), and the set of URLs that looked paywalled.
    """
    aggregated_texts = []
    paywalled_urls = set()

    for article in articles:
        if wanted is not None and len(aggregated_texts) >= wanted:
            break
        url = article.get("url", "unknown")
        # A feed teaser is too short to summarise, so those articles are downloaded.
        provided = article.get("text") or ""
        if len(provided) >= MIN_ARTICLE_CHARS:
            aggregated_texts.append(with_title(article, provided[:text_limit]))
            logger.info("Using provided text (%d chars): %s", len(provided), url)
            continue
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
            if text_len < MIN_ARTICLE_CHARS:
                logger.warning(
                    "Skipping article (paywall? only %d chars): %s", text_len, url
                )
                paywalled_urls.add(url)
                continue
            aggregated_texts.append(with_title(article, text[:text_limit]))
            logger.info(
                "Parsed article (%d chars, limited to %d): %s",
                text_len,
                text_limit,
                url,
            )
        except requests.HTTPError as error:
            status = error.response.status_code if error.response is not None else "?"
            reason = "paywall/bot wall" if status in BLOCKED_STATUSES else "HTTP error"
            logger.warning("Skipping article (%s, HTTP %s): %s", reason, status, url)
            if status in BLOCKED_STATUSES:
                paywalled_urls.add(url)
        except requests.RequestException as error:
            logger.warning(
                "Skipping article (unreachable: %s): %s", type(error).__name__, url
            )
        except Exception:
            logger.exception("Error parsing article from %s", url)

    logger.info("Aggregated %d articles", len(aggregated_texts))
    return "\n\n".join(aggregated_texts), paywalled_urls
