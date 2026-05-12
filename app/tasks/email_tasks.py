import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.celery_app import celery_app
from app.tasks import LoggedTask
from app.config import settings

logger = logging.getLogger("laura.tasks.email")


@celery_app.task(base=LoggedTask, bind=True, max_retries=3, default_retry_delay=30, soft_time_limit=30)
def send_email(self, to: str, subject: str, body: str):
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("email_not_configured", extra={"to": to})
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.smtp_from or settings.smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        logger.info("email_connecting", extra={"to": to, "host": settings.smtp_host, "port": settings.smtp_port})

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        logger.info("email_sent", extra={"to": to, "subject": subject[:50]})
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("email_auth_failed", extra={"to": to, "user": settings.smtp_user})
        return False
    except smtplib.SMTPException as e:
        logger.error("email_smtp_error", extra={"to": to, "error": str(e)})
        self.retry(exc=e)
        return False
    except Exception as e:
        logger.exception("email_failed", extra={"to": to, "error": str(e)})
        self.retry(exc=e)
        return False
