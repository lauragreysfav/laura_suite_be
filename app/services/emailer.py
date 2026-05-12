import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

logger = logging.getLogger("laura.services.emailer")


def send_email_sync(to: str, subject: str, body: str) -> bool:
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("email_not_configured", extra={"to": to})
        return False

    msg = MIMEMultipart()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        logger.info("email_connecting", extra={"to": to, "host": settings.smtp_host, "port": settings.smtp_port})
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
        server.quit()
        logger.info("email_sent", extra={"to": to, "subject": subject[:50]})
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("email_auth_failed", extra={"to": to, "user": settings.smtp_user})
        return False
    except smtplib.SMTPException as e:
        logger.error("email_smtp_error", extra={"to": to, "error": str(e)})
        return False
    except Exception as e:
        logger.exception("email_failed", extra={"to": to, "error": str(e)})
        return False
