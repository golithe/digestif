import logging
import os

import resend

logger = logging.getLogger("newsletter.email")


def send_email(subject, body, to_email, html=False):
    resend.api_key = os.environ.get("RESEND_API_KEY")

    params: resend.Emails.SendParams = {
        "from": os.environ["RESEND_FROM"],
        "to": [to_email],
        "subject": subject,
    }
    if html:
        params["html"] = body
    else:
        params["text"] = body

    result = resend.Emails.send(params)
    logger.info("Email sent to %s (id: %s)", to_email, result["id"])
