from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Tracker, TrackerJob, TrackedRelease
from app.tasks.tracker_tasks import check_all_trackers
import logging

logger = logging.getLogger("laura.api.trackers")

router = APIRouter(prefix="/trackers", tags=["trackers"])


class TrackerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern=r"^(performer|studio|keyword)$")
    query: str = Field(None, max_length=500)


class TrackerUpdate(BaseModel):
    name: str = Field(None, max_length=255)
    type: str = Field(None, pattern=r"^(performer|studio|keyword)$")
    query: str = Field(None, max_length=500)
    enabled: bool = None


@router.get("/")
def list_trackers(db: Session = Depends(get_db)):
    trackers = db.query(Tracker).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "type": t.type,
            "query": t.query,
            "enabled": t.enabled,
            "created_at": t.created_at,
        }
        for t in trackers
    ]


@router.get("/{tracker_id}/discoveries")
def list_discoveries(tracker_id: int, db: Session = Depends(get_db)):
    t = db.query(Tracker).filter(Tracker.id == tracker_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tracker not found")
    releases = db.query(TrackedRelease).filter(
        TrackedRelease.tracker_id == tracker_id
    ).order_by(TrackedRelease.created_at.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "info_hash": r.info_hash,
            "magnet": r.magnet,
            "source": r.source,
            "size": r.size,
            "quality": r.quality,
            "seeders": r.seeders,
            "leechers": r.leechers,
            "released_at": r.released_at,
            "downloaded": r.downloaded,
            "created_at": r.created_at,
        }
        for r in releases
    ]


@router.post("/")
def create_tracker(body: TrackerCreate, db: Session = Depends(get_db)):
    t = Tracker(name=body.name, type=body.type, query=body.query)
    db.add(t)
    db.commit()
    db.refresh(t)
    logger.info("tracker_created", extra={"tracker_id": t.id, "tracker_name": t.name, "tracker_type": t.type})
    return {"id": t.id, "name": t.name, "type": t.type}


@router.put("/{tracker_id}")
def update_tracker(tracker_id: int, body: TrackerUpdate, db: Session = Depends(get_db)):
    t = db.query(Tracker).filter(Tracker.id == tracker_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tracker not found")
    if body.name is not None:
        t.name = body.name
    if body.type is not None:
        t.type = body.type
    if body.query is not None:
        t.query = body.query
    if body.enabled is not None:
        t.enabled = body.enabled
    db.commit()
    logger.info("tracker_updated", extra={"tracker_id": tracker_id, "enabled": t.enabled})
    return {"id": t.id, "status": "updated"}


@router.delete("/{tracker_id}")
def delete_tracker(tracker_id: int, db: Session = Depends(get_db)):
    t = db.query(Tracker).filter(Tracker.id == tracker_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tracker not found")
    db.query(TrackerJob).filter(TrackerJob.tracker_id == tracker_id).delete()
    db.query(TrackedRelease).filter(TrackedRelease.tracker_id == tracker_id).delete()
    db.delete(t)
    db.commit()
    logger.info("tracker_deleted", extra={"tracker_id": tracker_id})
    return {"status": "deleted"}


@router.post("/trigger/{tracker_id}")
def trigger_tracker(tracker_id: int, db: Session = Depends(get_db)):
    t = db.query(Tracker).filter(Tracker.id == tracker_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tracker not found")
    check_all_trackers.delay(tracker_id)
    return {"status": "triggered", "tracker_id": tracker_id}


@router.get("/jobs")
def list_tracker_jobs(db: Session = Depends(get_db)):
    jobs = db.query(TrackerJob).order_by(TrackerJob.started_at.desc()).limit(50).all()
    return [
        {
            "id": j.id,
            "tracker_id": j.tracker_id,
            "status": j.status,
            "result": j.result,
            "started_at": j.started_at,
            "completed_at": j.completed_at,
            "error": j.error,
        }
        for j in jobs
    ]
