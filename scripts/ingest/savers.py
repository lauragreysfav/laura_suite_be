import logging
from app.models import StashDBPerformerCache, StashDBStudioCache, StashDBSceneCache

logger = logging.getLogger("ingest.savers")


def _performer_to_pg(p: dict) -> StashDBPerformerCache:
    imgs = p.get("images", [])
    urls = p.get("urls", [])
    return StashDBPerformerCache(
        stashdb_id=p["id"],
        name=p.get("name", ""),
        aliases=p.get("aliases", ""),
        gender=p.get("gender", ""),
        birthdate=p.get("birth_date"),
        image_url=imgs[0]["url"] if imgs else None,
        scene_count=p.get("scene_count", 0),
        urls=[{"url": u["url"], "type": u["type"]} for u in urls],
        raw_json=p,
    )


def _performer_to_ts(p: dict) -> dict:
    imgs = p.get("images", [])
    aliases_raw = p.get("aliases", "") or ""
    return {
        "id": p["id"],
        "name": p.get("name", ""),
        "aliases": [a.strip() for a in aliases_raw.split(",") if a.strip()],
        "image_url": imgs[0]["url"] if imgs else None,
        "gender": p.get("gender", ""),
        "birthdate": p.get("birth_date"),
        "scene_count": p.get("scene_count", 0),
    }


def _studio_to_pg(s: dict) -> StashDBStudioCache:
    imgs = s.get("images", [])
    parent = s.get("parent") or {}
    urls = s.get("urls") or []
    return StashDBStudioCache(
        stashdb_id=s["id"],
        name=s.get("name", ""),
        image_url=imgs[0]["url"] if imgs else None,
        scene_count=s.get("scene_count", 0),
        parent_studio=parent.get("name"),
        urls=[{"url": u["url"], "type": u["type"]} for u in urls],
        raw_json=s,
    )


def _studio_to_ts(s: dict) -> dict:
    imgs = s.get("images", [])
    return {
        "id": s["id"],
        "name": s.get("name", ""),
        "image_url": imgs[0]["url"] if imgs else None,
        "scene_count": s.get("scene_count", 0),
    }


def _scene_to_pg(sc: dict) -> StashDBSceneCache | None:
    if not sc.get("release_date") or sc["release_date"] < "2000-01-01":
        return None
    imgs = sc.get("images", [])
    pdata = sc.get("performers") or []
    fprints = sc.get("fingerprints") or []
    tags = sc.get("tags") or []
    studio_data = sc.get("studio") or {}
    return StashDBSceneCache(
        stashdb_id=sc["id"],
        title=sc.get("title", ""),
        details=sc.get("details"),
        release_date=sc.get("release_date"),
        duration=sc.get("duration"),
        studio_id=studio_data.get("id"),
        studio_name=studio_data.get("name", ""),
        performer_names=[p.get("performer", {}).get("name") for p in pdata if p.get("performer")],
        performer_ids=[p.get("performer", {}).get("id") for p in pdata if p.get("performer")],
        tags=[t.get("name") for t in tags if t.get("name")],
        fingerprints=[{"algorithm": fp.get("algorithm"), "hash": fp.get("hash"), "duration": fp.get("duration")} for fp in fprints],
        images=[i["url"] for i in imgs] if imgs else [],
        raw_json=sc,
    )


def _scene_to_ts(sc: dict) -> dict | None:
    if not sc.get("release_date") or sc["release_date"] < "2000-01-01":
        return None
    imgs = sc.get("images", [])
    pdata = sc.get("performers") or []
    fprints = sc.get("fingerprints") or []
    tags = sc.get("tags") or []
    studio_data = sc.get("studio") or {}
    return {
        "id": sc["id"],
        "title": sc.get("title", ""),
        "details": sc.get("details"),
        "release_date": sc.get("release_date"),
        "duration": sc.get("duration"),
        "studio_name": studio_data.get("name", ""),
        "performer_names": [p.get("performer", {}).get("name") for p in pdata if p.get("performer")],
        "tags": [t.get("name") for t in tags if t.get("name")],
        "fingerprints": [fp.get("hash") for fp in fprints if fp.get("hash")],
        "images": [i["url"] for i in imgs] if imgs else [],
    }


def _bulk_write(session, ts, collection: str, pg_rows: list, ts_docs: list[dict]) -> int:
    try:
        ts.bulk_upsert(collection, ts_docs)
        session.bulk_save_objects(pg_rows)
        session.commit()
        return len(pg_rows)
    except Exception:
        session.rollback()
        raise


def batch_save_performers(session, ts, performers: list[dict]) -> int:
    females = [p for p in performers if p.get("gender") == "female"]
    if not females:
        skipped = len(performers)
        if skipped:
            logger.debug("skipped_non_female_performers", extra={"count": skipped})
        return 0
    pg_rows = [_performer_to_pg(p) for p in females]
    ts_docs = [_performer_to_ts(p) for p in females]
    saved = _bulk_write(session, ts, "stashdb_performers", pg_rows, ts_docs)
    logger.info("saved_performers", extra={"count": saved})
    return saved


def batch_save_studios(session, ts, studios: list[dict]) -> int:
    if not studios:
        return 0
    pg_rows = [_studio_to_pg(s) for s in studios]
    ts_docs = [_studio_to_ts(s) for s in studios]
    saved = _bulk_write(session, ts, "stashdb_studios", pg_rows, ts_docs)
    logger.info("saved_studios", extra={"count": saved})
    return saved


def batch_save_scenes(session, ts, scenes: list[dict]) -> int:
    pg_rows = []
    ts_docs = []
    for sc in scenes:
        pg = _scene_to_pg(sc)
        if pg:
            pg_rows.append(pg)
        tsd = _scene_to_ts(sc)
        if tsd:
            ts_docs.append(tsd)
    if not pg_rows:
        return 0
    saved = _bulk_write(session, ts, "stashdb_scenes", pg_rows, ts_docs)
    logger.info("saved_scenes", extra={"count": saved})
    return saved
