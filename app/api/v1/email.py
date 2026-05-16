from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import EmailConfig, EmailLog
from app.tasks.email_tasks import send_email
from datetime import datetime, timezone
import logging

logger = logging.getLogger("laura.api.email")

router = APIRouter(prefix="/email", tags=["email"])


class EmailConfigUpdate(BaseModel):
    host: str = Field(None, max_length=255)
    port: int = Field(None, ge=1, le=65535)
    user: str = Field(None, max_length=255)
    password: str = Field(None, max_length=255)
    from_addr: str = Field(None, max_length=255)
    enabled: bool = None
    notify_on_job_complete: bool = None
    notify_on_tracker_find: bool = None


@router.post("/test")
def test_email(db: Session = Depends(get_db)):
    cfg = db.query(EmailConfig).first()
    if not cfg or not cfg.enabled:
        raise HTTPException(status_code=400, detail="Email not configured or disabled")
    to = cfg.from_addr or cfg.user
    if not to:
        raise HTTPException(status_code=400, detail="No recipient address configured (set from_addr or user)")
    send_email.delay(
        to=to,
        subject="Laura Suite — Test Email",
        body="<h2>Test Email</h2><p>If you're reading this, email is working correctly!</p>",
    )
    logger.info("test_email_dispatched", extra={"to": to})
    return {"status": "dispatched", "to": to}


def _serialize_config(cfg: EmailConfig) -> dict:
    return {
        "id": cfg.id,
        "host": cfg.host,
        "port": cfg.port,
        "user": cfg.user,
        "from_addr": cfg.from_addr,
        "enabled": cfg.enabled,
        "notify_on_job_complete": cfg.notify_on_job_complete,
        "notify_on_tracker_find": cfg.notify_on_tracker_find,
    }


@router.get("/config")
def get_email_config(db: Session = Depends(get_db)):
    cfg = db.query(EmailConfig).first()
    if not cfg:
        return {
            "host": "smtp.gmail.com",
            "port": 587,
            "user": "",
            "from_addr": "",
            "enabled": False,
            "notify_on_job_complete": True,
            "notify_on_tracker_find": True,
        }
    return _serialize_config(cfg)


@router.put("/config")
def update_email_config(body: EmailConfigUpdate, db: Session = Depends(get_db)):
    cfg = db.query(EmailConfig).first()
    if not cfg:
        cfg = EmailConfig()
        db.add(cfg)
    changed = []
    if body.host is not None:
        cfg.host = body.host
        changed.append("host")
    if body.port is not None:
        cfg.port = body.port
        changed.append("port")
    if body.user is not None:
        cfg.user = body.user
        changed.append("user")
    if body.password is not None:
        cfg.password = body.password
        changed.append("password")
    if body.from_addr is not None:
        cfg.from_addr = body.from_addr
        changed.append("from_addr")
    if body.enabled is not None:
        cfg.enabled = body.enabled
        changed.append("enabled")
    if body.notify_on_job_complete is not None:
        cfg.notify_on_job_complete = body.notify_on_job_complete
    if body.notify_on_tracker_find is not None:
        cfg.notify_on_tracker_find = body.notify_on_tracker_find
    db.commit()
    logger.info("email_config_updated", extra={"changed_fields": changed})
    return {"status": "updated", "config": _serialize_config(cfg)}


@router.get("/logs")
def get_email_logs(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    logs = db.query(EmailLog).order_by(EmailLog.sent_at.desc()).limit(limit).all()
    return {
        "data": [
            {
                "id": l.id,
                "to_addr": l.to_addr,
                "subject": l.subject,
                "status": l.status,
                "related_type": l.related_type,
                "related_name": l.related_name,
                "error_message": l.error_message,
                "sent_at": l.sent_at.isoformat() if l.sent_at else None,
            }
            for l in logs
        ]
    }
