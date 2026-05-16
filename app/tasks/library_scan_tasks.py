"""Periodic tasks for scanning LauraMedia folders and re-identifying unmatched scenes."""

import logging

from app.celery_app import celery_app
from app.services import stash
from app.services.emailer import notify_pipeline_complete

logger = logging.getLogger("laura.tasks.library_scan")


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def scan_lauramedia(self):
    """Scan LauraMedia folders for new files, then identify + generate."""
    lauramedia_paths = [
        "/data/lauramedia/Scenes",
        "/data/lauramedia/Clips",
        "/data/lauramedia/Favorites",
        "/data/lauramedia/GIFs",
        "/data/lauramedia/Images",
    ]

    try:
        # Step 1: Scan with all generation flags
        stash.trigger_scan(paths=lauramedia_paths)
        stash.wait_for_jobs(timeout=600)
        logger.info("LauraMedia scan complete")

        # Step 2: Identify from StashDB
        stash.trigger_identify(paths=lauramedia_paths)
        stash.wait_for_jobs(timeout=600)
        logger.info("Re-identify complete")

        notify_pipeline_complete(
            item_name=f"Re-identified {count} scenes",
            source="reidentify",
            extra_info=f"Library size: {count}",
            related_type="reidentify",
        )

        return {"status": "ok", "library_size": count}
    except Exception as e:
        logger.error(f"Re-identify failed: {e}")
        return {"status": "error", "error": str(e)}
