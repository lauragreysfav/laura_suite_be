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


def batch_save_performers(session, ts, performers: list[dict], batch_size: int = 100) -> int:
    females = [p for p in performers if p.get("gender") == "female"]
    if not females:
        return 0
    pg_rows = [_performer_to_pg(p) for p in females]
    ts_docs = [_performer_to_ts(p) for p in females]
    session.bulk_save_objects(pg_rows)
    session.commit()
    ts.bulk_upsert("stashdb_performers", ts_docs)
    logger.info("saved_performers", extra={"count": len(females)})
    return len(females)


def batch_save_studios(session, ts, studios: list[dict], batch_size: int = 100) -> int:
    if not studios:
        return 0
    pg_rows = [_studio_to_pg(s) for s in studios]
    ts_docs = [_studio_to_ts(s) for s in studios]
    session.bulk_save_objects(pg_rows)
    session.commit()
    ts.bulk_upsert("stashdb_studios", ts_docs)
    logger.info("saved_studios", extra={"count": len(studios)})
    return len(studios)


def batch_save_scenes(session, ts, scenes: list[dict], batch_size: int = 100) -> int:
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
    session.bulk_save_objects(pg_rows)
    session.commit()
    ts.bulk_upsert("stashdb_scenes", ts_docs)
    logger.info("saved_scenes", extra={"count": len(pg_rows)})
    return len(pg_rows)
