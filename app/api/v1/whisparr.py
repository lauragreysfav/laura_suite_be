from fastapi import APIRouter, HTTPException, Query, Request
from app.services import whisparr, torbox, stash
from app.services.prowlarr_results import normalize_result

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
        normalized = normalize_result({
            "title": release.get("title") or payload.get("movie", {}).get("title", ""),
            "magnetUrl": release.get("magnetUrl"),
            "magnetUri": release.get("magnetUri"),
            "infoHash": release.get("infoHash"),
            "downloadUrl": release.get("downloadUrl"),
            "downloadId": release.get("downloadId"),
        })
        try:
            if normalized.get("magnetUrl"):
                torbox.create_torrent(normalized["magnetUrl"], seed=1)
                return {"status": "ok", "message": "Added to TorBox", "link_type": normalized.get("linkType")}
            if normalized.get("downloadUrl"):
                torbox.create_torrent_from_download_url(
                    normalized["downloadUrl"],
                    seed=1,
                    name=normalized.get("title") or payload.get("movie", {}).get("title", "")
                )
                return {"status": "ok", "message": "Added to TorBox via torrent file", "link_type": normalized.get("linkType")}
            return {"status": "skipped", "message": "No magnet, infoHash, or torrent URL in payload"}
        except Exception as e:
            return {"status": "error", "message": f"TorBox add failed: {e}"}

    if event_type in ("Download", "Import"):
        try:
            stash.trigger_scan(paths=["/data/torbox"])
            return {"status": "ok", "message": "TorBox scan triggered"}
        except Exception as e:
            return {"status": "error", "message": f"TorBox scan failed: {e}"}

    return {"status": "ok", "message": f"Unhandled event type: {event_type}"}
