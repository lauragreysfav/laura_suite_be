import re
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.services import torbox
from app.services.magnet import build_magnet
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/torrents", tags=["torrents"])


class PauseResumeRequest(BaseModel):
    operation: str


class AddMagnetRequest(BaseModel):
    magnet: str
    seed: int = 1


class BatchAddMagnetRequest(BaseModel):
    magnets: list[str]
    seed: int = 1


class BatchAddMagnetItem(BaseModel):
    magnet: str | None = None
    info_hash: str | None = None
    title: str | None = None


class BatchAddMagnetRequestV2(BaseModel):
    items: list[BatchAddMagnetItem]
    seed: int = 1


@router.get("/")
def get_torrents(bypass_cache: bool = False):
    try:
        data = torbox.list_torrents(bypass_cache)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/add")
def add_torrent(body: AddMagnetRequest):
    try:
        data = torbox.create_torrent(body.magnet, body.seed)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/add/batch")
def add_torrents_batch(body: BatchAddMagnetRequest):
    results = []
    for magnet in body.magnets:
        try:
            data = torbox.create_torrent(magnet, body.seed)
            results.append({"magnet": magnet[:60], "status": "ok", "data": data})
        except Exception as e:
            results.append({"magnet": magnet[:60], "status": "error", "error": str(e)})
    return {"results": results}


_IH_RE = re.compile(r"^[a-fA-F0-9]{40}$")

def _valid_info_hash(s: str) -> bool:
    return bool(_IH_RE.match(s))

def add_torrents_batch_v2(body: BatchAddMagnetRequestV2):
    results = []
    for item in body.items:
        magnet = item.magnet or ""
        if (not magnet or not magnet.startswith("magnet:?xt=urn:btih:")):
            if item.info_hash and _valid_info_hash(item.info_hash):
                magnet = build_magnet(item.info_hash, item.title or "")
            else:
                results.append({"magnet": magnet[:60], "status": "error", "error": "no valid magnet or info_hash"})
                continue
        try:
            data = torbox.create_torrent(magnet, body.seed)
            results.append({"magnet": magnet[:60], "status": "ok", "data": data})
        except Exception as e:
            results.append({"magnet": magnet[:60], "status": "error", "error": str(e)})
    return {"results": results}


@router.patch("/{torrent_id}")
def control_torrent(torrent_id: str, body: PauseResumeRequest):
    try:
        data = torbox.control_torrent(torrent_id, body.operation)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/queue")
def get_queue():
    try:
        data = torbox.list_torrents(bypass_cache=False)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/{torrent_id}")
def remove_torrent(torrent_id: str):
    try:
        data = torbox.control_torrent(torrent_id, "delete")
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/whisparr-webhook")
async def whisparr_webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = body.get("eventType", "")
    if event != "Grab":
        return {"status": "ignored", "event": event}

    release = body.get("release", {}) or {}
    magnet_url = release.get("magnetUrl") or ""
    download_id = release.get("downloadId") or ""
    release_title = release.get("title") or body.get("movie", {}).get("title", "unknown")

    magnet = magnet_url
    if not magnet and download_id:
        magnet = f"magnet:?xt=urn:btih:{download_id}&dn={release_title}"

    if not magnet:
        return {"status": "error", "detail": "no magnet or downloadId in payload"}

    result = torbox.create_torrent(magnet, 1)
    return {"status": "ok", "torrent": release_title, "result": result}


@router.get("/{torrent_id}/files")
def list_torrent_files(torrent_id: str, user: dict = Depends(get_current_user)):
    try:
        files = torbox.get_torrent_files(torrent_id)
        return {"torrent_id": torrent_id, "files": files}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/stream/{file_id}")
def get_stream(file_id: str, user: dict = Depends(get_current_user)):
    try:
        url = torbox.get_stream_url(file_id)
        return {"url": url, "file_id": file_id}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
