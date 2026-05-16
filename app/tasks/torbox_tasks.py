"""TorBox background tasks: check stalled downloads, auto-delete slow ones."""

import logging
import time as time_module
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Setting, DeletedTorrent, CronJobLog, AutoDeleteExclude
from app.services import torbox

logger = logging.getLogger("laura.tasks.torbox")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def check_stalled_downloads(self):
    """Check all TorBox torrents. Auto-delete any below threshold after time limit."""
    start = time_module.time()
    db = SessionLocal()
    try:
        time_minutes = int((db.query(Setting).filter(Setting.key == "torbox_auto_delete_minutes").first() or Setting(value="30")).value)
        percent_threshold = int((db.query(Setting).filter(Setting.key == "torbox_auto_delete_percent").first() or Setting(value="50")).value)
    except Exception:
        time_minutes = 30
        percent_threshold = 50
    finally:
        db.close()

    try:
        data = torbox.list_torrents()
        torrents = data.get("data", [])
    except Exception as e:
        logger.error(f"Failed to list TorBox torrents: {e}")
        return {"checked": 0, "deleted": 0, "error": str(e)}

    # Load protected hashes
    protect_db = SessionLocal()
    try:
        excluded = set(r[0] for r in protect_db.query(AutoDeleteExclude.info_hash).all())
    except Exception:
        excluded = set()
    finally:
        protect_db.close()

    now = datetime.now(timezone.utc)
    deleted_count = 0
    deleted_items = []

    for t in torrents:
        info_hash = t.get("hash", "")
        if info_hash in excluded:
            logger.debug(f"Skipping protected torrent: {t.get('name', info_hash)}")
            continue

        progress = t.get("progress") or 0
        state = t.get("download_state", "")
        finished = t.get("download_finished", False)
        if finished or state == "completed" or state == "paused" or state == "cached":
            continue
        if progress >= percent_threshold:
            continue

        added_raw = t.get("added_at") or t.get("created_at")
        if not added_raw:
            continue

        try:
            if isinstance(added_raw, str):
                added_at = datetime.fromisoformat(added_raw.replace("Z", "+00:00"))
            else:
                added_at = datetime.fromtimestamp(added_raw, tz=timezone.utc)
        except Exception:
            continue

        elapsed = (now - added_at).total_seconds() / 60
        if elapsed < time_minutes:
            continue

        tid = t.get("id")
        if not tid:
            continue

        try:
            torbox.control_torrent(str(tid), "delete")
            info_hash = t.get("hash", "")
            title = t.get("name") or t.get("filename") or "unknown"
            size = str(t.get("size", ""))
            magnet = ""
            if info_hash:
                from app.services.magnet import build_magnet
                magnet = build_magnet(info_hash, title)

            db2 = SessionLocal()
            try:
                existing = db2.query(DeletedTorrent).filter(DeletedTorrent.info_hash == info_hash).first()
                if not existing:
                    dt = DeletedTorrent(info_hash=info_hash, title=title, magnet=magnet, size=size, reason="stalled")
                    db2.add(dt)
                    db2.commit()
            finally:
                db2.close()

            deleted_count += 1
            deleted_items.append({"title": title, "info_hash": info_hash, "size": size})
            logger.info(f"Auto-deleted stalled torrent: {title} ({progress}% after {elapsed:.0f}min)")
        except Exception as e:
            logger.warning(f"Failed to delete torrent {tid}: {e}")

    # Log this cron run
    duration = int((time_module.time() - start) * 1000)
    log_db = SessionLocal()
    try:
        log_entry = CronJobLog(
            job_name="check_stalled_downloads",
            checked_count=len(torrents),
            deleted_count=deleted_count,
            deleted_items=deleted_items if deleted_items else None,
            duration_ms=duration,
        )
        log_db.add(log_entry)
        log_db.commit()
    except Exception as e:
        logger.error(f"Failed to log cron run: {e}")
    finally:
        log_db.close()

    return {"checked": len(torrents), "deleted": deleted_count}
