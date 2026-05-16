import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from app.config import settings
from app.database import SessionLocal
from app.models import EmailConfig, EmailLog

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


def notify_pipeline_complete(
    item_name: str,
    source: str,
    extra_info: str = "",
    related_type: str = "torbox_sync",
) -> bool:
    """Send pipeline completion notification and log it. Returns True if sent."""
    db = SessionLocal()
    try:
        cfg = db.query(EmailConfig).first()
        if not cfg or not cfg.enabled or not cfg.notify_on_job_complete:
            return False

        to = cfg.from_addr or cfg.user
        if not to:
            return False

        if source == "torbox":
            subject = f"TorBox Pipeline Complete: {item_name}"
        elif source == "lauramedia":
            subject = f"LauraMedia Pipeline Complete: {item_name}"
        elif source == "reidentify":
            subject = f"Re-Identify Complete: {item_name}"
        else:
            subject = f"Pipeline Complete: {item_name}"

        body_html = f"""<h2>Pipeline Complete</h2>
<p><strong>Source:</strong> {source}</p>
<p><strong>Item:</strong> {item_name}</p>
{f'<p><strong>Details:</strong> {extra_info}</p>' if extra_info else ''}
<p><em>Laura Suite</em></p>"""

        ok = send_email_sync(to=to, subject=subject, body=body_html)

        log_entry = EmailLog(
            to_addr=to,
            subject=subject,
            status="sent" if ok else "failed",
            related_type=related_type,
            related_name=item_name,
            error_message=None if ok else "send failed",
            sent_at=datetime.now(timezone.utc),
        )
        db.add(log_entry)
        db.commit()
        return ok
    except Exception as e:
        logger.warning(f"notify_pipeline_complete error: {e}")
        return False
    finally:
        db.close()
