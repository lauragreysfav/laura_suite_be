import logging
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.library.standard_search import service as std_search_service
from app.library.common.repository import get_document
from app.library.common.schema import (
    STASHDB_INDEX_PERFORMERS,
    STASHDB_INDEX_STUDIOS,
    STASHDB_INDEX_SCENES,
)
from app.models import StashDBPerformerCache, StashDBStudioCache, StashDBSceneCache
from app.services import stash as stash_service
from app.services import stashdb_public as stashdb_live

logger = logging.getLogger("laura.api.stashdb")
router = APIRouter(prefix="/stashdb", tags=["stashdb"])


@router.get("/suggest")
def suggest(
    q: str = Query(..., min_length=1, max_length=200),
    type: str = Query("all", regex="^(performer|studio|scene|all)$"),
):
    try:
        results = std_search_service.suggest(q, search_type=type)
        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}


def _reshape_performer(doc: dict) -> dict:
    return {
        "id": doc["id"],
        "name": doc.get("name", ""),
        "image_path": doc.get("image_url"),
        "scene_count": doc.get("scene_count", 0),
        "aliases": doc.get("aliases"),
        "gender": doc.get("gender"),
        "details": doc.get("details"),
    }


def _reshape_studio(doc: dict) -> dict:
    return {
        "id": doc["id"],
        "name": doc.get("name", ""),
        "image_path": doc.get("image_url"),
        "scene_count": doc.get("scene_count", 0),
        "details": doc.get("details"),
    }


def _reshape_scene(doc: dict) -> dict:
    images = doc.get("images") or []
    tags = doc.get("tags") or []
    performer_names = doc.get("performer_names") or []
    return {
        "id": doc["id"],
        "title": doc.get("title", ""),
        "date": doc.get("release_date"),
        "details": doc.get("details"),
        "paths": {"screenshot": images[0]} if images else None,
        "file": {"duration": doc.get("duration")} if doc.get("duration") else None,
        "studio": {"name": doc.get("studio_name")} if doc.get("studio_name") else None,
        "performers": [{"name": n} for n in performer_names],
        "tags": [{"name": t} for t in tags],
    }


INDEX_MAP = {
    "performer": (STASHDB_INDEX_PERFORMERS, _reshape_performer),
    "studio": (STASHDB_INDEX_STUDIOS, _reshape_studio),
    "scene": (STASHDB_INDEX_SCENES, _reshape_scene),
}


def _try_pg(entity_type: str, id: str, db: Session) -> dict | None:
    try:
        if entity_type == "performer":
            row = db.query(StashDBPerformerCache).filter(StashDBPerformerCache.stashdb_id == id).first()
        elif entity_type == "studio":
            row = db.query(StashDBStudioCache).filter(StashDBStudioCache.stashdb_id == id).first()
        else:
            row = db.query(StashDBSceneCache).filter(StashDBSceneCache.stashdb_id == id).first()
        if row and row.raw_json:
            return row.raw_json
        return None
    except Exception:
        return None


def _try_typesense(entity_type: str, id: str) -> dict | None:
    if entity_type not in INDEX_MAP:
        return None
    index, _ = INDEX_MAP[entity_type]
    doc = get_document(index, id)
    if not doc:
        return None
    _, reshape = INDEX_MAP[entity_type]
    return reshape(doc)


def _try_live(entity_type: str, id: str) -> dict | None:
    return _try_stashdb_live(entity_type, id)


def _resolve_entity(entity_type: str, id: str, db: Session) -> dict | None:
    result = _try_pg(entity_type, id, db)
    if result:
        return result
    result = _try_typesense(entity_type, id)
    if result:
        return result
    result = _try_live(entity_type, id)
    if result:
        return result
    return None


def _try_local_stash(entity_type: str, id: str) -> dict | None:
    try:
        if entity_type == "performer":
            data = stash_service.find_performer(id)
            return data.get("data", {}).get("findPerformer")
        elif entity_type == "studio":
            data = stash_service.find_studio(id)
            return data.get("data", {}).get("findStudio")
        else:
            data = stash_service.find_scene(id)
            return data.get("data", {}).get("findScene")
    except Exception:
        return None


def _try_stashdb_live(entity_type: str, id: str) -> dict | None:
    try:
        if entity_type == "performer":
            data = stashdb_live.get_performer(id)
            d = data.get("data") or {}
            p = d.get("findPerformer")
            if not p:
                return None
            imgs = p.get("images") or []
            return {
                "id": p["id"],
                "name": p.get("name", ""),
                "image_path": imgs[0]["url"] if imgs else None,
                "scene_count": 0,
                "aliases": p.get("aliases"),
                "gender": p.get("gender"),
            }
        elif entity_type == "studio":
            data = stashdb_live.get_studio(id)
            d = data.get("data") or {}
            s = d.get("findStudio")
            if not s:
                return None
            imgs = s.get("images") or []
            return {
                "id": s["id"],
                "name": s.get("name", ""),
                "image_path": imgs[0]["url"] if imgs else None,
                "scene_count": 0,
            }
        else:
            data = stashdb_live.get_scene(id)
            d = data.get("data") or {}
            sc = d.get("findScene")
            if not sc:
                return None
            imgs = sc.get("images") or []
            performers = sc.get("performers") or []
            studio = sc.get("studio") or {}
            tags = sc.get("tags") or []
            return {
                "id": sc["id"],
                "title": sc.get("title", ""),
                "date": sc.get("release_date"),
                "details": sc.get("details"),
                "file": {"duration": sc.get("duration")} if sc.get("duration") else None,
                "paths": {"screenshot": imgs[0]["url"]} if imgs else None,
                "studio": {"name": studio.get("name")} if studio.get("name") else None,
                "performers": [
                    {"name": p.get("performer", {}).get("name")}
                    for p in performers if p.get("performer")
                ],
                "tags": [{"name": t.get("name")} for t in tags if t.get("name")],
            }
    except Exception as e:
        logger.warning("stashdb_live_entity_error", extra={"type": entity_type, "id": id, "error": str(e)})
        return None


@router.get("/entity")
def get_entity(
    type: str = Query(..., regex="^(performer|studio|scene)$"),
    id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    result = _resolve_entity(type, id, db)
    if result:
        return result

    local = _try_local_stash(type, id)
    if local:
        from app.api.v1.stash import _normalize_paths
        return _normalize_paths(local)

    raise HTTPException(status_code=404, detail=f"{type} {id} not found")
