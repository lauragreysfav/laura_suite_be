import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from app.celery_app import celery_app
from app.tasks import LoggedTask
from app.database import SessionLocal
from app.models import Tracker, TrackerJob, TrackedRelease
from app.services.searcher import search_prowlarr, detect_quality

logger = logging.getLogger("laura.tasks.tracker")


@celery_app.task(base=LoggedTask, bind=True, max_retries=2, default_retry_delay=30)
def check_all_trackers(self, tracker_id: int = None):
    db = SessionLocal()
    try:
        if tracker_id:
            trackers = db.query(Tracker).filter(Tracker.id == tracker_id, Tracker.enabled == True).all()
            logger.info("tracker_check_single", extra={"tracker_id": tracker_id})
        else:
            trackers = db.query(Tracker).filter(Tracker.enabled == True).all()
            logger.info("tracker_check_all", extra={"count": len(trackers)})

        for t in trackers:
            job = TrackerJob(tracker_id=t.id, status="running")
            db.add(job)
            db.commit()
            db.refresh(job)

            try:
                logger.info("tracker_querying", extra={"tracker_id": t.id, "tracker_name": t.name, "query": t.query})
                results = search_prowlarr(t.query or t.name)
                since = datetime.now(timezone.utc) - timedelta(hours=24)

                new_count = 0
                for r in results:
                    pub_date = r.get("publishDate", "")
                    if pub_date:
                        try:
                            pd = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                            if pd < since:
                                continue
                        except ValueError:
                            pass

                    ih = r.get("infoHash", "")
                    if not ih:
                        continue

                    try:
                        rel = TrackedRelease(
                            tracker_id=t.id,
                            title=r.get("title", ""),
                            info_hash=ih,
                            magnet=r.get("magnetUrl", ""),
                            source=r.get("source", ""),
                            size=str(r.get("size", "")),
                            quality=detect_quality(r.get("title", "")),
                            seeders=r.get("seeders") or 0,
                            leechers=r.get("leechers") or 0,
                        )
                        db.add(rel)
                        db.flush()
                        new_count += 1
                    except IntegrityError:
                        db.rollback()
                        logger.warning("tracker_duplicate_skipped", extra={"tracker_id": t.id, "info_hash": ih})
                        continue

                db.commit()
                job.status = "completed"
                job.result = {"found": new_count, "tracker": t.name}
                job.completed_at = datetime.now(timezone.utc)
                db.commit()

                logger.info("tracker_check_completed", extra={"tracker_id": t.id, "tracker_name": t.name, "new_releases": new_count})

            except Exception as e:
                logger.exception("tracker_check_failed", extra={"tracker_id": t.id, "tracker_name": t.name, "error": str(e)})
                job.status = "failed"
                job.error = str(e)[:500]
                db.commit()

    except Exception as e:
        logger.exception("tracker_run_failed", extra={"error": str(e)})
        self.retry(exc=e)
    finally:
        db.close()
