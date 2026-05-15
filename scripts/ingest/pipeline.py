import asyncio
import logging
import string

from app.config import settings
from app.database import SessionLocal
from app.services.typesense_client import TypesenseClient
from app.library.common.typesense_schema import SCHEMAS
from scripts.ingest.checkpoint import Checkpoint
from scripts.ingest.api import StashDBClient
from scripts.ingest.rate_limiter import TokenBucket
from scripts.ingest.savers import batch_save_performers, batch_save_studios, batch_save_scenes

logger = logging.getLogger("ingest.pipeline")

NAME_PREFIXES = [c for c in string.ascii_lowercase] + [str(i) for i in range(10)]
MAX_SCENE_PAGES_PER_STUDIO = 50


async def _phase_performers(client: StashDBClient, ts: TypesenseClient, cp: Checkpoint) -> set[str]:
    db = SessionLocal()
    try:
        start_idx = cp.get("performers_prefix_idx", 0)
        seen_ids = set(cp.get("seen_performer_ids", []))
        seen_studio_ids = set(cp.get("seen_studio_ids", []))
        total = len(seen_ids)

        for idx in range(start_idx, len(NAME_PREFIXES)):
            prefix = NAME_PREFIXES[idx]
            page = cp.get("performers_page", 1) if idx == start_idx else 1
            while True:
                performers, _ = await client.fetch_performers_page(prefix, page)
                if not performers:
                    break

                new_performers = [p for p in performers if p.get("id") not in seen_ids]
                for p in new_performers:
                    seen_ids.add(p["id"])
                    for s_rel in (p.get("studios") or []):
                        s = s_rel.get("studio") or {}
                        if s.get("id"):
                            seen_studio_ids.add(s["id"])

                if new_performers:
                    saved = batch_save_performers(db, ts, new_performers)
                    total += saved

                logger.info(f"PERFORMER_BATCH: prefix={prefix}, page={page}, found={len(new_performers)}, total_so_far={total}")
                cp.set("performers_prefix_idx", idx)
                cp.set("performers_page", page + 1)
                cp.set("seen_performer_ids", list(seen_ids))
                cp.set("seen_studio_ids", list(seen_studio_ids))
                cp.save()
                page += 1

            cp.set("performers_page", 1)
            cp.save()

        logger.info("performers_done", extra={"total": total, "unique_studios": len(seen_studio_ids)})
        return seen_studio_ids
    finally:
        db.close()


async def _phase_performer_scenes(client: StashDBClient, ts: TypesenseClient, cp: Checkpoint) -> None:
    db = SessionLocal()
    try:
        performer_ids = cp.get("seen_performer_ids", [])
        start_idx = cp.get("performer_scenes_idx", 0)
        seen_studio_ids = set(cp.get("seen_studio_ids", []))
        total_scenes = 0

        logger.info(f"phase_2_performer_scenes_starting: total_performers={len(performer_ids)}, starting_at={start_idx}")

        for idx in range(start_idx, len(performer_ids)):
            pid = performer_ids[idx]
            page = 1
            
            while True:
                scenes, count = await client.fetch_scenes_by_performer(pid, page)
                if not scenes:
                    break

                # Save scenes
                saved = batch_save_scenes(db, ts, scenes)
                total_scenes += saved

                # Discover and fetch new studios
                for scene in scenes:
                    studio = scene.get("studio")
                    if studio and studio.get("id") and studio["id"] not in seen_studio_ids:
                        sid = studio["id"]
                        logger.info("new_studio_discovered", extra={"id": sid, "name": studio.get("name")})
                        s_data = await client.fetch_studio(sid)
                        if s_data:
                            batch_save_studios(db, ts, [s_data])
                        seen_studio_ids.add(sid)

                if page * 100 >= count:
                    break
                page += 1

            if idx % 10 == 0:
                cp.set("performer_scenes_idx", idx)
                cp.set("seen_studio_ids", list(seen_studio_ids))
                cp.save()
                logger.info("performer_scenes_progress", extra={"idx": idx, "total": len(performer_ids), "scenes_saved": total_scenes})

        cp.set("phase", "done")
        cp.save()
        logger.info("performer_scenes_done", extra={"total_scenes": total_scenes})
    finally:
        db.close()


async def run_pipeline(resume: bool = True) -> None:
    logger.info("pipeline_starting")
    ts = TypesenseClient()
    ts.ensure_collections(SCHEMAS)

    rate_limiter = TokenBucket(
        capacity=settings.stashdb_ingest_concurrency,
        rate=1.0 / settings.stashdb_rate_limit_seconds,
    )
    client = StashDBClient(
        api_key=settings.stashdb_api_key,
        rate_limiter=rate_limiter,
    )

    cp = Checkpoint()
    if resume:
        cp.load()

    current_phase = cp.get("phase", "performers")

    if current_phase == "performers":
        logger.info("phase_1_performers")
        await _phase_performers(client, ts, cp)
        cp.set("phase", "performer_scenes")
        cp.set("performer_scenes_idx", 0)
        cp.save()
        current_phase = "performer_scenes"

    # Handle legacy state 'studios' or 'scenes' by mapping to 'performer_scenes'
    if current_phase in ("studios", "scenes", "performer_scenes"):
        logger.info("phase_2_performer_scenes")
        await _phase_performer_scenes(client, ts, cp)

    logger.info("pipeline_complete")
