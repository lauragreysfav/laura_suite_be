"""Check TorBox for newly completed downloads and trigger Stash processing."""

import logging
import time
from datetime import datetime, timezone

import httpx

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import TorboxDownload
from app.services import torbox
from app.config import settings
from app.services import stash
from app.services.emailer import notify_pipeline_complete

logger = logging.getLogger("laura.tasks.torbox_sync")

STASH_GRAPHQL = f"{settings.stash_url}/graphql"
STASH_HEADERS = {}
if settings.stash_api_key:
    STASH_HEADERS["ApiKey"] = settings.stash_api_key


def _stash_query(query: str, variables: dict = None) -> dict:
    body = {"query": query, "variables": variables or {}}
    r = httpx.post(STASH_GRAPHQL, json=body, headers=STASH_HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def _wait_for_stash_jobs(timeout: int = 600, poll_interval: int = 5) -> bool:
    """Poll stash job queue until empty or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        q = "{ jobQueue { id status description } }"
        try:
            res = _stash_query(q)
            jobs = res.get("data", {}).get("jobQueue") or []
            running = [j for j in jobs if j.get("status") in ("RUNNING", "READY")]
            if not running:
                return True
        except Exception:
            pass
        time.sleep(poll_interval)
    return False


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def check_torbox_completions(self):
    """Poll TorBox for newly finished downloads. Trigger full Stash pipeline."""
    try:
        data = torbox.list_torrents(bypass_cache=True)
        torrents = data.get("data", [])
    except Exception as e:
        logger.error(f"Failed to list TorBox torrents: {e}")
        return {"checked": 0, "new": 0}

    db = SessionLocal()
    try:
        existing_hashes = set(r[0] for r in db.query(TorboxDownload.info_hash).all())
    except Exception:
        existing_hashes = set()

    new_count = 0
    for t in torrents:
        finished = t.get("download_finished", False)
        if not finished:
            continue

        info_hash = t.get("hash", "")
        if not info_hash or info_hash in existing_hashes:
            continue

        name = t.get("name") or t.get("filename") or "unknown"
        size = str(t.get("size", ""))
        torbox_id = t.get("id")

        download = TorboxDownload(
            info_hash=info_hash, name=name, size=size,
            torbox_id=torbox_id, stash_scanned=False, stash_identified=False,
        )
        db.add(download)
        new_count += 1
        logger.info(f"New TorBox completion detected: {name}")

    if new_count > 0:
        db.commit()

    # Process any unprocessed downloads
    unprocessed = db.query(TorboxDownload).filter(
        TorboxDownload.stash_scanned == False  # noqa: E712
    ).all()

    processed = 0
    for dl in unprocessed:
        try:
            # Step 1: Full Stash scan (all generation flags enabled)
            scan_vars = {
                "input": {
                    "paths": ["/data/torbox"],
                    "scanGenerateCovers": True,
                    "scanGeneratePreviews": True,
                    "scanGenerateSprites": True,
                    "scanGeneratePhashes": True,
                    "scanGenerateImagePhashes": True,
                    "scanGenerateThumbnails": True,
                    "scanGenerateClipPreviews": True,
                }
            }
            _stash_query("""
                mutation MetadataScan($input: ScanMetadataInput!) {
                  metadataScan(input: $input)
                }
            """, scan_vars)

            # Wait for scan to finish
            _wait_for_stash_jobs(timeout=600)
            dl.stash_scanned = True
            db.commit()

            # Step 2: Identify from StashDB
            identify_query = """
            mutation {
              metadataIdentify(input: {
                sources: [{
                  source: { stash_box_endpoint: "https://stashdb.org/graphql" }
                  options: { setCoverImage: true includeMalePerformers: true skipSingleNamePerformers: false }
                }]
                paths: ["/data/torbox"]
              })
            }
            """
            _stash_query(identify_query)
            _wait_for_stash_jobs(timeout=600)
            dl.stash_identified = True
            db.commit()

            # Step 3: Auto-tag performers/studios from filenames
            stash.trigger_auto_tag(paths=["/data/torbox"])
            _wait_for_stash_jobs(timeout=300)

            # Step 4: Generate previews, sprites, phashes for the scene
            stash.trigger_generate(
                previews=True, sprites=True, phashes=True,
                covers=False, image_thumbnails=False, markers=True,
                marker_screenshots=True, clip_previews=True,
                image_previews=False, image_phashes=False,
                overwrite=False,
            )
            _wait_for_stash_jobs(timeout=600)

            # Step 5: Look up the scene in stash by hash and store its ID
            scene = stash.find_scene_by_hash(dl.info_hash)
            if scene:
                dl.stash_scene_id = int(scene["id"])
                dl.stash_scene_name = scene.get("title", "")[:500]

            dl.processed_at = datetime.now(timezone.utc)
            db.commit()
            processed += 1
            logger.info(f"Full Stash pipeline complete for: {dl.name}")

            # Send email notification
            scene_info = f"Scene #{dl.stash_scene_id}: {dl.stash_scene_name}" if dl.stash_scene_id else "Not yet identified"
            notify_pipeline_complete(
                item_name=dl.name,
                source="torbox",
                extra_info=scene_info,
                related_type="torbox_sync",
            )
        except Exception as e:
            logger.warning(f"Failed to process {dl.name}: {e}")

    db.close()
    return {"checked": len(torrents), "new": new_count, "processed": processed}
