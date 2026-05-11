from fastapi import APIRouter, HTTPException
from app.services import stash, torbox

router = APIRouter(prefix="/library", tags=["library"])


@router.post("/scan")
def scan_library():
    try:
        data = stash.trigger_scan()
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/refresh-webdav")
def refresh_webdav():
    ok = torbox.refresh_webdav()
    return {"status": "ok" if ok else "unavailable", "detail": "TorBox service may be experiencing an outage" if not ok else None}
