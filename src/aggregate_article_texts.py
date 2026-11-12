import ipaddress
import logging
import socket
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("newsletter.aggregate")

# Paywalls and bot walls often answer 200 with a short "subscribe" stub.
MIN_ARTICLE_CHARS = 200
BLOCKED_STATUSES = {401, 402, 403, 451}

# Stories sometimes link to datasets, videos or ISOs; the Pi must not load those.
MAX_ARTICLE_BYTES = 2_000_000
# requests' timeout only bounds each read, so a slow drip could otherwise run forever.
DOWNLOAD_SECONDS = 30
READABLE_TYPES = ("text/html", "application/xhtml+xml", "text/plain")


MAX_REDIRECTS = 5


class UnreadableArticle(Exception):
    pass


def ensure_public(url):
    """
    Refuses URLs that resolve to the Pi's own network.

    Story links come from strangers on HN and Lobsters; without this, a link
    to e.g. http://192.168.1.1/ would make the Pi fetch from the home LAN.

    Raises:
    UnreadableArticle: The URL is not http(s) or resolves to a non-public address.
    requests.ConnectionError: The host name does not resolve.
    """
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise UnreadableArticle(f"not an http(s) URL: {url}")
    try:
        infos = socket.getaddrinfo(parts.hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as error:
        raise requests.ConnectionError(error) from error
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global or address.is_multicast:
            raise UnreadableArticle(f"refusing non-public address {address}")


def get_public(url):
    # Redirects are followed by hand so that every hop is checked, not just the first.
    for _ in range(MAX_REDIRECTS + 1):
        ensure_public(url)
        response = requests.get(url, timeout=10, stream=True, allow_redirects=False)
        if not response.is_redirect:
            return response
        response.close()
        url = urljoin(url, response.headers["Location"])
    raise UnreadableArticle("too many redirects")


def download_page(url):
    """
    Downloads a web page without ever holding more than MAX_ARTICLE_BYTES.

    Parameters:
    url (str): The article URL.

    Returns:
    bytes: The start of the page body; truncated after MAX_ARTICLE_BYTES or
    DOWNLOAD_SECONDS, whichever comes first.

    Raises:
    requests.RequestException: The download failed.
    UnreadableArticle: The response is not a web page (e.g. a PDF or video),
    or the URL or a redirect points to a non-public address.
    """
    response = get_public(url)
    try:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if content_type and not content_type.startswith(READABLE_TYPES):
            raise UnreadableArticle(f"not a web page: {content_type}")

        deadline = time.monotonic() + DOWNLOAD_SECONDS
        body = bytearray()
        for chunk in response.iter_content(64 * 1024):
            body += chunk
            if len(body) >= MAX_ARTICLE_BYTES or time.monotonic() > deadline:
                logger.info("Truncated download after %d bytes: %s", len(body), url)
                break
        return bytes(body[:MAX_ARTICLE_BYTES])
    finally:
        response.close()


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
            soup = BeautifulSoup(download_page(url), "html.parser")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()

            content = soup.find("article") or soup.find("main") or soup.body or soup
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
        except UnreadableArticle as error:
            logger.warning("Skipping article (%s): %s", error, url)
        except requests.RequestException as error:
            logger.warning(
                "Skipping article (unreachable: %s): %s", type(error).__name__, url
            )
        except Exception:
            logger.exception("Error parsing article from %s", url)

    logger.info("Aggregated %d articles", len(aggregated_texts))
    return "\n\n".join(aggregated_texts), paywalled_urls
