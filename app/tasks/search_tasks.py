import logging
from datetime import datetime, timezone
from app.celery_app import celery_app
from app.tasks import LoggedTask
from app.database import SessionLocal
from app.models import SearchJob, SearchResult
from app.services.searcher import dedup_results, detect_quality, rank_torrent, search_prowlarr

logger = logging.getLogger("laura.tasks.search")


@celery_app.task(base=LoggedTask, bind=True, max_retries=3, default_retry_delay=10)
def batch_search(self, job_id: int):
    logger.info("search_job_started", extra={"job_id": job_id})
    db = SessionLocal()
    try:
        job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
        if not job:
            logger.error("search_job_not_found", extra={"job_id": job_id})
            return

        job.status = "running"
        db.commit()

        queries = [job.query]
        logger.info("search_querying_prowlarr", extra={"job_id": job_id, "query": job.query})

        all_results = []
        for q in queries:
            try:
                results = search_prowlarr(q)
                logger.info("search_prowlarr_results", extra={"job_id": job_id, "query": q, "count": len(results)})
                all_results.extend(results)
            except Exception as e:
                logger.error("search_prowlarr_error", extra={"job_id": job_id, "query": q, "error": str(e)})

        job.progress = 50
        db.commit()

        unique = dedup_results(all_results)
        logger.info("search_dedup", extra={"job_id": job_id, "before": len(all_results), "after": len(unique)})

        ranked = sorted(unique, key=rank_torrent, reverse=True)
        total = len(ranked)

        for i, r in enumerate(ranked[:100]):
            sr = SearchResult(
                job_id=job_id,
                title=r.get("title", ""),
                info_hash=r.get("infoHash", ""),
                magnet=r.get("magnetUri", ""),
                source=r.get("source", ""),
                indexer=r.get("indexer", ""),
                size=str(r.get("size", "")),
                quality=detect_quality(r.get("title", "")),
                seeders=r.get("seeders") or 0,
                leechers=r.get("leechers") or 0,
                relevance=float(total - i),
            )
            db.add(sr)

        job.status = "completed"
        job.progress = 100
        job.result_count = min(total, 100)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("search_job_completed", extra={"job_id": job_id, "results": job.result_count})

    except Exception as e:
        logger.exception("search_job_failed", extra={"job_id": job_id, "error": str(e)})
        if db:
            try:
                job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
                if job:
                    job.status = "failed"
                    job.error = str(e)[:500]
                    db.commit()
            except Exception:
                pass
        self.retry(exc=e)
    finally:
        db.close()
