import logging
import os

from send_email import send_email

logger = logging.getLogger("newsletter.alerting")


def report_failure(error_text):
    """
    Emails the traceback of a failed run to NL_RECIPIENT.

    Parameters:
    error_text (str): The formatted traceback of the failure.
    """
    recipient = os.environ.get("NL_RECIPIENT")
    if not recipient:
        return
    try:
        send_email("digestif run failed", error_text, recipient)
    except Exception:
        logger.exception("Could not send the failure email either")
