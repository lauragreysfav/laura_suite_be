import json
import logging
from sqlalchemy.dialects.postgresql import insert
from app.models import StashDBPerformerCache, StashDBStudioCache, StashDBSceneCache
from app.services.typesense_client import TypesenseClient

logger = logging.getLogger("ingest.savers")


def _performer_to_pg(p: dict) -> StashDBPerformerCache:
    imgs = p.get("images", [])
    return StashDBPerformerCache(
        stashdb_id=p["id"],
        name=p.get("name"),
        aliases=p.get("aliases", []),
        gender=p.get("gender"),
        image_url=imgs[0]["url"] if imgs else None,
        urls=p.get("urls", []),
        scene_count=p.get("scene_count", 0),
        raw_json=json.dumps(p),
    )


def _performer_to_ts(p: dict) -> dict:
    imgs = p.get("images", [])
    aliases_raw = p.get("aliases", "")
    if isinstance(aliases_raw, list):
        aliases = [str(a).strip() for a in aliases_raw if a]
    else:
        aliases = [a.strip() for a in (aliases_raw or "").split(",") if a.strip()]

    return {
        "id": p["id"],
        "name": p.get("name", ""),
        "aliases": aliases,
        "image_url": imgs[0]["url"] if imgs else None,
        "gender": p.get("gender", ""),
        "birthdate": p.get("birth_date"),
        "scene_count": p.get("scene_count", 0),
    }


def _studio_to_pg(s: dict) -> StashDBStudioCache:
    imgs = s.get("images", [])
    parent = s.get("parent") or {}
    return StashDBStudioCache(
        stashdb_id=s["id"],
        name=s.get("name"),
        parent_id=parent.get("id"),
        image_url=imgs[0]["url"] if imgs else None,
        urls=s.get("urls", []),
        raw_json=json.dumps(s),
    )


def _studio_to_ts(s: dict) -> dict:
    imgs = s.get("images", [])
    return {
        "id": s["id"],
        "name": s.get("name", ""),
        "image_url": imgs[0]["url"] if imgs else None,
    }


def _scene_to_pg(sc: dict) -> StashDBSceneCache:
    imgs = sc.get("images", [])
    studio = sc.get("studio") or {}
    return StashDBSceneCache(
        stashdb_id=sc["id"],
        title=sc.get("title"),
        release_date=sc.get("release_date"),
        studio_id=studio.get("id"),
        image_url=imgs[0]["url"] if imgs else None,
        raw_json=json.dumps(sc),
    )


def _scene_to_ts(sc: dict) -> dict:
    imgs = sc.get("images", [])
    studio_data = sc.get("studio") or {}
    pdata = sc.get("performers") or []
    tags = sc.get("tags") or []
    fprints = sc.get("fingerprints") or []
    return {
        "id": sc["id"],
        "title": sc.get("title", ""),
        "details": sc.get("details"),
        "release_date": sc.get("release_date"),
        "duration": sc.get("duration"),
        "studio_id": studio_data.get("id"),
        "studio_name": studio_data.get("name", ""),
        "performer_ids": [p.get("performer", {}).get("id") for p in pdata if p.get("performer") and p.get("performer", {}).get("id")],
        "performer_names": [p.get("performer", {}).get("name") for p in pdata if p.get("performer")],
        "tags": [t.get("name") for t in tags if t.get("name")],
        "fingerprints": [fp.get("hash") for fp in fprints if fp.get("hash")],
        "images": [i["url"] for i in imgs] if imgs else [],
    }


def _bulk_write(session, ts: TypesenseClient, collection: str, pg_rows: list, ts_docs: list) -> int:
    if not pg_rows:
        return 0

    try:
        # PostgreSQL Upsert
        for row in pg_rows:
            data = {
                c.name: getattr(row, c.name)
                for c in row.__table__.columns
                if c.name not in ("id", "created_at", "updated_at")
            }
            stmt = insert(row.__class__).values(**data)

            # Conflict resolution: update everything except IDs and creation date
            update_cols = {
                c.name: stmt.excluded[c.name]
                for c in row.__table__.columns
                if c.name not in ("id", "stashdb_id", "created_at")
            }

            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["stashdb_id"], set_=update_cols
            )
            session.execute(upsert_stmt)

        session.commit()

        # Typesense Upsert
        if ts_docs:
            ts.bulk_upsert(collection, ts_docs)

        return len(pg_rows)
    except Exception as e:
        logger.error(f"bulk_write_error: {str(e)}")
        session.rollback()
        raise


def batch_save_performers(session, ts, performers: list[dict]) -> int:
    if not performers:
        return 0
    # Only save female performers
    female_performers = [p for p in performers if p.get("gender", "").lower() == "female"]
    if not female_performers:
        return 0
    pg_rows = [_performer_to_pg(p) for p in female_performers]
    ts_docs = [_performer_to_ts(p) for p in female_performers]
    saved = _bulk_write(session, ts, "stashdb_performers", pg_rows, ts_docs)
    logger.info(f"SAVED_PERFORMERS: count={saved}")
    return saved


def batch_save_studios(session, ts, studios: list[dict]) -> int:
    if not studios:
        return 0
    pg_rows = [_studio_to_pg(s) for s in studios]
    ts_docs = [_studio_to_ts(s) for s in studios]
    saved = _bulk_write(session, ts, "stashdb_studios", pg_rows, ts_docs)
    logger.info(f"SAVED_STUDIOS: count={saved}")
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
    logger.info(f"SAVED_SCENES: count={saved}")
    return saved
