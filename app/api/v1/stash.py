import re
from fastapi import APIRouter, HTTPException, Query, Depends
from app.services import stash as stash_service
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/stash", tags=["stash"])

_STASH_HOST_RE = re.compile(r'^https?://[^/]+')


def _normalize_paths(obj):
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            if key in ('screenshot', 'stream', 'preview', 'image_path') and isinstance(value, str):
                obj[key] = _STASH_HOST_RE.sub('', value)
            elif key == 'paths' and isinstance(value, dict):
                _normalize_paths(value)
            else:
                _normalize_paths(value)
    elif isinstance(obj, list):
        for item in obj:
            _normalize_paths(item)
    return obj


@router.get("/overview")
def get_overview(user: dict = Depends(get_current_user)):
    try:
        data = stash_service.overview()
        d = data.get("data", {})
        stats = d.get("stats", {}) if d.get("stats") else {}
        return {
            "stats": {
                "scene_count": stats.get("scene_count", 0),
                "performer_count": stats.get("performer_count", 0),
                "studio_count": stats.get("studio_count", 0),
                "scenes_size": stats.get("scenes_size", 0),
            },
            "job_queue": d.get("jobQueue") or [],
            "scenes_with_studio": (d.get("scenes_with_studio") or {}).get("count", 0),
            "scenes_without_studio": (d.get("scenes_without_studio") or {}).get("count", 0),
            "scenes_organized": (d.get("scenes_organized") or {}).get("count", 0),
            "scenes_with_tags": (d.get("scenes_with_tags") or {}).get("count", 0),
            "scenes_without_tags": (d.get("scenes_without_tags") or {}).get("count", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/stats")
def get_stats():
    try:
        data = stash_service.stats()
        return data.get("data", {}).get("stats", {})
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/scenes")
def get_scenes(
    q: str = "",
    page: int = Query(1, ge=1),
    per_page: int = Query(40, ge=1, le=200),
    sort: str = "date",
    direction: str = "DESC",
):
    try:
        data = stash_service.find_scenes(q, page, per_page, sort, direction)
        result = data.get("data", {}).get("findScenes", {})
        return _normalize_paths(result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/scenes/{id}")
def get_scene(id: str):
    try:
        data = stash_service.find_scene(id)
        scene = data.get("data", {}).get("findScene")
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")
        return _normalize_paths(scene)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/performers")
def get_performers(
    q: str = "",
    page: int = Query(1, ge=1),
    per_page: int = Query(40, ge=1, le=200),
):
    try:
        data = stash_service.find_performers(q, page, per_page)
        result = data.get("data", {}).get("findPerformers", {})
        return _normalize_paths(result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/performers/{id}")
def get_performer(id: str):
    try:
        data = stash_service.find_performer(id)
        performer = data.get("data", {}).get("findPerformer")
        if not performer:
            raise HTTPException(status_code=404, detail="Performer not found")
        return _normalize_paths(performer)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/studios")
def get_studios(
    q: str = "",
    page: int = Query(1, ge=1),
    per_page: int = Query(40, ge=1, le=200),
):
    try:
        data = stash_service.find_studios(q, page, per_page)
        result = data.get("data", {}).get("findStudios", {})
        return _normalize_paths(result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/studios/{id}")
def get_studio(id: str):
    try:
        data = stash_service.find_studio(id)
        studio = data.get("data", {}).get("findStudio")
        if not studio:
            raise HTTPException(status_code=404, detail="Studio not found")
        scenes_data = stash_service.find_scenes_by_studio(id)
        scenes_result = scenes_data.get("data", {}).get("findScenes", {})
        studio["scenes"] = scenes_result.get("scenes", [])
        return _normalize_paths(studio)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
