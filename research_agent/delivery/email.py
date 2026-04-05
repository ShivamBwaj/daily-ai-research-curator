"""Send daily report via SMTP (Gmail-compatible)."""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

from utils.config import Config

logger = logging.getLogger(__name__)


def send_email_report(
    config: Config,
    subject: str,
    body_text: str,
) -> bool:
    """Send plain-text email if EMAIL_USER, EMAIL_PASS, and EMAIL_TO are set."""
    if not config.email_user or not config.email_pass or not config.email_to:
        logger.debug("Email not fully configured; skipping SMTP send.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.email_user
    msg["To"] = config.email_to
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(config.email_smtp_host, config.email_smtp_port, timeout=45) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(config.email_user, config.email_pass)
            smtp.sendmail(config.email_user, [config.email_to], msg.as_string())
        logger.info("Email sent successfully to %s", config.email_to)
        return True
    except smtplib.SMTPException as e:
        logger.error("SMTP error: %s", e)
    except OSError as e:
        logger.error("Email network error: %s", e)
    except Exception as e:
        logger.exception("Unexpected email failure: %s", e)
    return False
