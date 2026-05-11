from fastapi import APIRouter, HTTPException, Query
from app.services import prowlarr

router = APIRouter(prefix="/prowlarr", tags=["prowlarr"])


@router.get("/indexers")
def get_indexers():
    try:
        return prowlarr.list_indexers()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/applications")
def get_applications():
    try:
        return prowlarr.list_applications()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/status")
def get_status():
    try:
        return prowlarr.system_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/search")
def search_indexers(query: str = Query(..., min_length=1), indexer_ids: str = Query(None)):
    try:
        ids = [int(x) for x in indexer_ids.split(",") if x.strip().isdigit()] if indexer_ids else None
        return prowlarr.search(query, ids)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
