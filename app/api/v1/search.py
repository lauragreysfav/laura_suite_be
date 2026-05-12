from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SearchJob, SearchResult
from app.tasks.search_tasks import batch_search

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    indexers: list[int] = None


@router.post("/")
def start_search(body: SearchRequest, db: Session = Depends(get_db)):
    job = SearchJob(query=body.query, type="general")
    db.add(job)
    db.commit()
    db.refresh(job)
    batch_search.delay(job.id)
    return {"job_id": job.id, "status": job.status}


@router.get("/status/{job_id}")
def get_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "query": job.query,
        "status": job.status,
        "progress": job.progress,
        "result_count": job.result_count,
        "error": job.error,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }


@router.get("/results/{job_id}")
def get_results(job_id: int, db: Session = Depends(get_db)):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    results = db.query(SearchResult).filter(SearchResult.job_id == job_id).order_by(SearchResult.relevance.desc()).all()
    return {
        "job_id": job_id,
        "status": job.status,
        "results": [
            {
                "id": r.id,
                "title": r.title,
                "info_hash": r.info_hash,
                "magnet": r.magnet,
                "source": r.source,
                "indexer": r.indexer,
                "size": r.size,
                "quality": r.quality,
                "seeders": r.seeders,
                "leechers": r.leechers,
                "relevance": r.relevance,
            }
            for r in results
        ],
    }
