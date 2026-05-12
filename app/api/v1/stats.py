from fastapi import APIRouter, Query
from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.models import SearchJob, TrackerJob

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/torrents")
def get_torrent_stats(days: int = Query(7, ge=1, le=90)):
    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        jobs = db.query(SearchJob).filter(SearchJob.created_at >= since).all()
        track_jobs = db.query(TrackerJob).filter(TrackerJob.started_at >= since).all()

        daily = {}
        for i in range(days):
            day = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            daily[day] = 0

        for j in jobs:
            day = j.created_at.strftime("%Y-%m-%d") if j.created_at else ""
            if day in daily:
                daily[day] += 1

        result = [{"date": k, "count": v} for k, v in sorted(daily.items())]
        return result
    finally:
        db.close()


@router.get("/library")
def get_library_stats():
    return {}
