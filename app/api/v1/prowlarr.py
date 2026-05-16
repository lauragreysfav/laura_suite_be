import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from app.services import prowlarr

router = APIRouter(prefix="/prowlarr", tags=["prowlarr"])


@router.get("/indexers")
def get_indexers():
    try:
        return prowlarr.list_indexers()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/indexers")
async def create_indexer(request: Request):
    try:
        data = await request.json()
        return prowlarr.add_indexer(data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.put("/indexers/{indexer_id}")
async def update_indexer(indexer_id: int, request: Request):
    try:
        data = await request.json()
        return prowlarr.update_indexer(indexer_id, data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/indexers/{indexer_id}")
def delete_indexer(indexer_id: int):
    try:
        prowlarr.delete_indexer(indexer_id)
        return {"status": "ok"}
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
def search_indexers(query: str = Query(..., min_length=1, max_length=500), indexer_ids: str = Query(None)):
    try:
        ids = [int(x) for x in indexer_ids.split(",") if x.strip().isdigit()] if indexer_ids else None
        return prowlarr.search(query=query, indexer_ids=ids)
    except httpx.HTTPStatusError as e:
        detail = "Prowlarr search failed"
        try:
            body = e.response.text
            if e.response.status_code == 400 and "unavailable" in body.lower():
                detail = "Selected indexers are unavailable"
            elif body:
                detail = body
        except Exception:
            pass
        raise HTTPException(status_code=e.response.status_code or 502, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
