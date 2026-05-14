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

                new_females = [p for p in performers if p.get("gender") == "female" and p.get("id") not in seen_ids]
                for p in new_females:
                    seen_ids.add(p["id"])
                    for s_rel in (p.get("studios") or []):
                        s = s_rel.get("studio") or {}
                        if s.get("id"):
                            seen_studio_ids.add(s["id"])

                if new_females:
                    saved = batch_save_performers(db, ts, new_females)
                    total += saved

                logger.info("performers_progress", extra={"prefix": prefix, "page": page, "batch": len(new_females), "total": total})
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


async def _phase_studios(client: StashDBClient, ts: TypesenseClient, cp: Checkpoint, studio_ids: set[str]) -> None:
    db = SessionLocal()
    try:
        done = set(cp.get("studios_done", []))
        ids_to_fetch = sorted(studio_ids - done)
        start_idx = cp.get("studios_idx", 0)
        total = len(done)
        batch = []

        for idx in range(start_idx, len(ids_to_fetch)):
            sid = ids_to_fetch[idx]
            studio = await client.fetch_studio(sid)
            if studio:
                batch.append(studio)
                if len(batch) >= 10:
                    saved = batch_save_studios(db, ts, batch)
                    total += saved
                    batch = []
            done.add(sid)
            cp.set("studios_done", list(done))
            cp.set("studios_idx", idx + 1)
            cp.save()

            if idx % 50 == 0:
                logger.info("studios_progress", extra={"fetched": len(done), "total": len(ids_to_fetch)})

        if batch:
            saved = batch_save_studios(db, ts, batch)
            total += saved

        logger.info("studios_done", extra={"total": total})
    finally:
        db.close()


async def _phase_scenes(client: StashDBClient, ts: TypesenseClient, cp: Checkpoint, studio_ids: set[str]) -> None:
    db = SessionLocal()
    try:
        ids_list = sorted(studio_ids)
        start_idx = cp.get("scenes_studio_idx", 0)
        total_scenes = 0

        for idx in range(start_idx, len(ids_list)):
            sid = ids_list[idx]
            page = cp.get("scenes_page", 1) if idx == start_idx else 1
            studio_scenes = 0

            while True:
                scenes, _ = await client.fetch_scenes_page(sid, page)
                if not scenes:
                    break

                saved = batch_save_scenes(db, ts, scenes)
                studio_scenes += saved
                total_scenes += saved

                logger.info("scenes_progress", extra={"studio": sid, "page": page, "batch": len(scenes), "total": total_scenes})
                cp.set("scenes_studio_idx", idx)
                cp.set("scenes_page", page + 1)
                cp.save()
                page += 1
                if page > MAX_SCENE_PAGES_PER_STUDIO:
                    logger.warning("studio_max_pages", extra={"studio": sid, "pages": page})
                    break

            cp.set("scenes_page", 1)
            cp.save()

        logger.info("scenes_done", extra={"total": total_scenes})
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
        studio_ids = await _phase_performers(client, ts, cp)
        cp.set("phase", "studios")
        cp.set("studios_done", [])
        cp.set("studios_idx", 0)
        cp.save()
    else:
        studio_ids = set(cp.get("seen_studio_ids", []))

    if current_phase in ("performers", "studios"):
        logger.info("phase_2_studios")
        await _phase_studios(client, ts, cp, studio_ids)
        cp.set("phase", "scenes")
        cp.set("scenes_studio_idx", 0)
        cp.set("scenes_page", 1)
        cp.save()

    logger.info("phase_3_scenes")
    await _phase_scenes(client, ts, cp, studio_ids)
    cp.set("phase", "done")
    cp.save()
    logger.info("pipeline_complete")
