import logging
from typing import Optional
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
async def suggest(
    q: str = Query(..., min_length=1, max_length=200),
    type: str = Query("all", pattern="^(performer|studio|scene|all)$"),
):
    try:
        results = await std_search_service.suggest(q, search_type=type)
        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}


from app.library.common.reshapers import (
    reshape_scene as _reshape_raw_scene,
    reshape_performer as _reshape_raw_performer,
    reshape_studio as _reshape_raw_studio,
)

def _reshape_performer(doc: dict) -> dict:
    return _reshape_raw_performer(doc)


def _reshape_studio(doc: dict) -> dict:
    return _reshape_raw_studio(doc)


def _reshape_scene(doc: dict) -> dict:
    return _reshape_raw_scene(doc)


INDEX_MAP = {
    "performer": (STASHDB_INDEX_PERFORMERS, _reshape_performer),
    "studio": (STASHDB_INDEX_STUDIOS, _reshape_studio),
    "scene": (STASHDB_INDEX_SCENES, _reshape_scene),
}


import json

def _try_pg(entity_type: str, id: str, db: Session) -> dict | None:
    try:
        if entity_type == "performer":
            row = db.query(StashDBPerformerCache).filter(StashDBPerformerCache.stashdb_id == id).first()
            if row and row.raw_json:
                data = json.loads(row.raw_json) if isinstance(row.raw_json, str) else row.raw_json
                res = _reshape_raw_performer(data)
                
                # Optimized JSON lookup
                scenes = db.query(StashDBSceneCache).filter(StashDBSceneCache.performer_ids.contains(id)).limit(50).all()
                res["scenes"] = []
                for sc in scenes:
                    sc_data = json.loads(sc.raw_json) if isinstance(sc.raw_json, str) else sc.raw_json
                    res["scenes"].append(_reshape_raw_scene(sc_data))
                return res

        elif entity_type == "studio":
            row = db.query(StashDBStudioCache).filter(StashDBStudioCache.stashdb_id == id).first()
            if row and row.raw_json:
                data = json.loads(row.raw_json) if isinstance(row.raw_json, str) else row.raw_json
                res = _reshape_raw_studio(data)
                
                scenes = db.query(StashDBSceneCache).filter(StashDBSceneCache.studio_id == id).limit(50).all()
                res["scenes"] = []
                for sc in scenes:
                    sc_data = json.loads(sc.raw_json) if isinstance(sc.raw_json, str) else sc.raw_json
                    res["scenes"].append(_reshape_raw_scene(sc_data))
                return res

        else:
            row = db.query(StashDBSceneCache).filter(StashDBSceneCache.stashdb_id == id).first()
            if row and row.raw_json:
                data = json.loads(row.raw_json) if isinstance(row.raw_json, str) else row.raw_json
                return _reshape_raw_scene(data)
        return None
    except Exception as e:
        logger.error(f"try_pg_error: {str(e)}")
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


async def _try_live(entity_type: str, id: str) -> dict | None:
    return await _try_stashdb_live(entity_type, id)


async def _resolve_entity(entity_type: str, id: str, db: Session) -> dict | None:
    result = _try_pg(entity_type, id, db)
    if result:
        return result
    result = _try_typesense(entity_type, id)
    if result:
        return result
    result = await _try_live(entity_type, id)
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


async def _try_stashdb_live(entity_type: str, id: str) -> dict | None:
    try:
        if entity_type == "performer":
            data = await stashdb_live.get_performer(id)
            d = data.get("data") or {}
            p = d.get("findPerformer")
            if not p:
                return None
            return _reshape_raw_performer(p)
        elif entity_type == "studio":
            data = await stashdb_live.get_studio(id)
            d = data.get("data") or {}
            s = d.get("findStudio")
            if not s:
                return None
            return _reshape_raw_studio(s)
        else:
            data = await stashdb_live.get_scene(id)
            d = data.get("data") or {}
            sc = d.get("findScene")
            if not sc:
                return None
            return _reshape_raw_scene(sc)
    except Exception as e:
        logger.warning("stashdb_live_entity_error", extra={"type": entity_type, "id": id, "error": str(e)})
        return None


from pydantic import BaseModel

class ResolveRequest(BaseModel):
    title: str
    info_hash: Optional[str] = None

@router.post("/resolve")
async def resolve_scene(req: ResolveRequest):
    try:
        result = await std_search_service.find_and_enrich_scene(req.title, req.info_hash)
        if result:
            return result
        raise HTTPException(status_code=404, detail="Scene could not be resolved on StashDB")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"resolve_error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entity")
async def get_entity(
    type: str = Query(..., regex="^(performer|studio|scene)$"),
    id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    result = await _resolve_entity(type, id, db)
    if result:
        return result

    local = _try_local_stash(type, id)
    if local:
        from app.api.v1.stash import _normalize_paths
        return _normalize_paths(local)

    raise HTTPException(status_code=404, detail=f"{type} {id} not found")
