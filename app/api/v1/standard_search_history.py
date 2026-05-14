import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import StandardSearchHistory
from app.auth.dependencies import get_current_user

logger = logging.getLogger("laura.api.standard_search_history")
router = APIRouter(prefix="/standard-search", tags=["standard_search_history"])


@router.get("/history")
def get_history(
    limit: int | None = Query(None, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(StandardSearchHistory).filter_by(user_id=user["sub"]).order_by(StandardSearchHistory.id.desc())
    rows = q.limit(limit).all() if limit else q.all()
    return [
        {
            "id": h.id,
            "query": h.query,
            "filters": h.filters,
            "result_count": h.result_count,
            "status": h.status,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in rows
    ]
