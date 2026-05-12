from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import WatchHistory
from pydantic import BaseModel

router = APIRouter(prefix="/watch", tags=["watch"])


class WatchSyncRequest(BaseModel):
    scene_id: int
    resume_time: float = 0.0
    play_count: int = 0
    play_duration: float = 0.0


@router.get("/continue")
def get_continue_watching(db: Session = Depends(get_db)):
    entries = (
        db.query(WatchHistory)
        .filter(WatchHistory.resume_time > 0)
        .order_by(WatchHistory.last_played_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": w.id,
            "scene_id": w.scene_id,
            "resume_time": w.resume_time,
            "play_count": w.play_count,
            "play_duration": w.play_duration,
            "last_played_at": w.last_played_at,
        }
        for w in entries
    ]


@router.post("/sync")
def sync_watch(body: WatchSyncRequest, db: Session = Depends(get_db)):
    entry = db.query(WatchHistory).filter(WatchHistory.scene_id == body.scene_id).first()
    if entry:
        entry.resume_time = body.resume_time
        entry.play_count = body.play_count
        entry.play_duration = body.play_duration
        entry.last_played_at = datetime.now(timezone.utc)
    else:
        entry = WatchHistory(
            scene_id=body.scene_id,
            resume_time=body.resume_time,
            play_count=body.play_count,
            play_duration=body.play_duration,
        )
        db.add(entry)
    db.commit()
    return {"status": "synced", "scene_id": body.scene_id}
