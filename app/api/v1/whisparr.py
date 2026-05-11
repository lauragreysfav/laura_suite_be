from fastapi import APIRouter, HTTPException, Query, Request
from app.services import whisparr, torbox, stash

router = APIRouter(prefix="/whisparr", tags=["whisparr"])


@router.get("/movies")
def get_movies():
    try:
        return whisparr.get_movies()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/history")
def get_history(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    try:
        return whisparr.get_history(page, page_size)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/calendar")
def get_calendar(start: str = None, end: str = None):
    try:
        return whisparr.get_calendar(start, end)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/lookup")
def lookup_movie(term: str = Query(..., min_length=1)):
    try:
        return whisparr.lookup_movie(term)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/webhook")
async def whisparr_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    event_type = payload.get("eventType", "")

    if event_type == "Test":
        return {"status": "ok", "message": "Webhook test received"}

    if event_type == "Grab":
        release = payload.get("release", {})
        magnet = release.get("magnetUrl", "")
        if magnet:
            try:
                torbox.create_torrent(magnet, seed=1)
                return {"status": "ok", "message": "Added to TorBox"}
            except Exception as e:
                return {"status": "error", "message": f"TorBox add failed: {e}"}
        return {"status": "skipped", "message": "No magnet URL in payload"}

    if event_type in ("Download", "Import"):
        try:
            stash.trigger_scan(paths=["/data/torbox"])
            return {"status": "ok", "message": "TorBox scan triggered"}
        except Exception as e:
            return {"status": "error", "message": f"TorBox scan failed: {e}"}

    return {"status": "ok", "message": f"Unhandled event type: {event_type}"}
