import logging
import os

import resend

logger = logging.getLogger("newsletter.email")


def send_email(subject, to_email, text, html=None):
    """
    Sends an email via Resend.

    Parameters:
    subject (str): The subject line.
    to_email (str): The recipient address.
    text (str): The plain-text body; always sent, as the fallback for HTML.
    html (str | None): An optional HTML body, shown by clients that render HTML.
    """
    resend.api_key = os.environ.get("RESEND_API_KEY")

    params: resend.Emails.SendParams = {
        "from": os.environ["RESEND_FROM"],
        "to": [to_email],
        "subject": subject,
        "text": text,
    }
    if html is not None:
        params["html"] = html

    result = resend.Emails.send(params)
    logger.info("Email sent to %s (id: %s)", to_email, result["id"])
