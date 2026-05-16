import re
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.models import AutoDeleteExclude
from app.services import torbox
from app.services.magnet import build_magnet
from app.services.prowlarr_results import normalize_result
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import DeletedTorrent

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
    download_url: str | None = None


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


def _submit_release_to_torbox(release: dict, title_fallback: str = "unknown") -> dict:
    normalized = normalize_result({
        "title": release.get("title") or title_fallback,
        "magnetUrl": release.get("magnetUrl"),
        "magnetUri": release.get("magnetUri"),
        "infoHash": release.get("infoHash"),
        "downloadUrl": release.get("downloadUrl"),
        "downloadId": release.get("downloadId"),
    })

    magnet = normalized.get("magnetUrl") or ""
    download_url = normalized.get("downloadUrl") or ""
    title = normalized.get("title") or title_fallback

    if magnet:
        return torbox.create_torrent(magnet, 1)
    if download_url:
        return torbox.create_torrent_from_download_url(download_url, seed=1, name=title)
    raise ValueError("no magnet, infoHash, or downloadUrl in payload")

@router.post("/add/batch/v2")
def add_torrents_batch_v2(body: BatchAddMagnetRequestV2):
    from concurrent.futures import ThreadPoolExecutor
    
    def process_item(item):
        magnet = item.magnet or ""
        if not magnet or not magnet.startswith("magnet:?xt=urn:btih:"):
            if item.info_hash and _valid_info_hash(item.info_hash):
                magnet = build_magnet(item.info_hash, item.title or "")
            elif item.download_url:
                try:
                    data = torbox.create_torrent_from_download_url(item.download_url, seed=body.seed, name=item.title or "")
                    return {"magnet": item.download_url[:60], "status": "ok", "data": data}
                except Exception as e:
                    return {"magnet": item.download_url[:60], "status": "error", "error": str(e)}
            else:
                return {"magnet": magnet[:60], "status": "error", "error": "no valid magnet, info_hash, or download_url"}
        
        try:
            data = torbox.create_torrent(magnet, body.seed)
            return {"magnet": magnet[:60], "status": "ok", "data": data}
        except Exception as e:
            return {"magnet": magnet[:60], "status": "error", "error": str(e)}

    # Process up to 5 items in parallel to speed up response
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_item, body.items))
        
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
    release_title = release.get("title") or body.get("movie", {}).get("title", "unknown")
    try:
        result = _submit_release_to_torbox(release, release_title)
        return {"status": "ok", "torrent": release_title, "result": result}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


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


class AutoDeleteConfig(BaseModel):
    time_minutes: int = 30
    percent_threshold: int = 50


@router.get("/stats")
def get_torrent_stats(user: dict = Depends(get_current_user)):
    try:
        user_info = torbox.get_user_info()
        data = user_info.get("data", {})
        plan = data.get("plan", 0)
        torrents = torbox.list_torrents()
        tdata = torrents.get("data", [])
        active = sum(1 for t in tdata if t.get("status") == "downloading" or (t.get("progress") or 0) < 100)
        total_size = sum(t.get("size", 0) or 0 for t in tdata)
        return {
            "plan": plan,
            "active_downloads": active,
            "total_torrents": len(tdata),
            "total_size": total_size,
            "webdav_ok": True,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/deleted")
def list_deleted_torrents(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    deleted = db.query(DeletedTorrent).filter(DeletedTorrent.restored_at.is_(None)).order_by(DeletedTorrent.deleted_at.desc()).all()
    return {"data": [{"id": d.id, "info_hash": d.info_hash, "title": d.title, "magnet": d.magnet, "size": d.size, "reason": d.reason, "deleted_at": d.deleted_at.isoformat() if d.deleted_at else None} for d in deleted]}


class RestoreRequest(BaseModel):
    info_hash: str
    magnet: str | None = None
    title: str = "unknown"


@router.post("/{deleted_id}/restore")
def restore_deleted_torrent(deleted_id: int, body: RestoreRequest, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    magnet = body.magnet
    if not magnet or not magnet.startswith("magnet:?xt=urn:btih:"):
        from app.services.magnet import build_magnet
        magnet = build_magnet(body.info_hash, body.title) if body.info_hash else body.magnet
    try:
        result = torbox.create_torrent(magnet, 1)
        deleted = db.query(DeletedTorrent).filter(DeletedTorrent.id == deleted_id).first()
        if deleted:
            deleted.restored_at = func.now()
            db.commit()
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/auto-delete-config")
def get_auto_delete_config(user: dict = Depends(get_current_user)):
    from app.models import Setting
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        time_minutes = db.query(Setting).filter(Setting.key == "torbox_auto_delete_minutes").first()
        percent = db.query(Setting).filter(Setting.key == "torbox_auto_delete_percent").first()
        return {
            "time_minutes": int(time_minutes.value) if time_minutes else 30,
            "percent_threshold": int(percent.value) if percent else 50,
        }
    finally:
        db.close()


class AutoDeleteConfigUpdate(BaseModel):
    key: str
    value: str


@router.put("/auto-delete-config")
def update_auto_delete_config(body: AutoDeleteConfigUpdate, user: dict = Depends(get_current_user)):
    from app.models import Setting
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        setting = db.query(Setting).filter(Setting.key == body.key).first()
        if setting:
            setting.value = body.value
        else:
            setting = Setting(key=body.key, value=body.value)
            db.add(setting)
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()


@router.get("/cron-history")
def get_cron_history(limit: int = Query(50, ge=1, le=200), user: dict = Depends(get_current_user)):
    from app.models import CronJobLog
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        logs = db.query(CronJobLog).order_by(CronJobLog.ran_at.desc()).limit(limit).all()
        return {
            "data": [
                {
                    "id": l.id,
                    "job_name": l.job_name,
                    "checked_count": l.checked_count,
                    "deleted_count": l.deleted_count,
                    "deleted_items": l.deleted_items or [],
                    "duration_ms": l.duration_ms,
                    "ran_at": l.ran_at.isoformat() if l.ran_at else None,
                }
                for l in logs
            ]
        }
    finally:
        db.close()


@router.get("/sync-history")
def get_sync_history(limit: int = Query(10, ge=1, le=50), user: dict = Depends(get_current_user)):
    from app.models import TorboxDownload
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        downloads = db.query(TorboxDownload).order_by(TorboxDownload.detected_at.desc()).limit(limit).all()
        return {
            "data": [
                {
                    "id": d.id,
                    "name": d.name,
                    "info_hash": d.info_hash,
                    "size": d.size,
                    "stash_scanned": d.stash_scanned,
                    "stash_identified": d.stash_identified,
                    "stash_scene_id": d.stash_scene_id,
                    "stash_scene_name": d.stash_scene_name,
                    "detected_at": d.detected_at.isoformat() if d.detected_at else None,
                    "processed_at": d.processed_at.isoformat() if d.processed_at else None,
                }
                for d in downloads
            ]
        }
    finally:
        db.close()


@router.post("/trigger-sync")
def trigger_manual_sync(user: dict = Depends(get_current_user)):
    from app.tasks.torbox_sync_tasks import check_torbox_completions
    task = check_torbox_completions.delay()
    return {"status": "ok", "task_id": task.id}


class ProtectBody(BaseModel):
    info_hash: str


@router.post("/{torrent_id}/protect")
def protect_torrent(torrent_id: str, body: ProtectBody, user: dict = Depends(get_current_user)):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        existing = db.query(AutoDeleteExclude).filter(AutoDeleteExclude.info_hash == body.info_hash).first()
        if not existing:
            db.add(AutoDeleteExclude(info_hash=body.info_hash))
            db.commit()
        return {"status": "ok", "protected": True}
    finally:
        db.close()


@router.post("/{torrent_id}/unprotect")
def unprotect_torrent(torrent_id: str, body: ProtectBody, user: dict = Depends(get_current_user)):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        db.query(AutoDeleteExclude).filter(AutoDeleteExclude.info_hash == body.info_hash).delete()
        db.commit()
        return {"status": "ok", "protected": False}
    finally:
        db.close()


@router.get("/protected")
def list_protected(user: dict = Depends(get_current_user)):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        hashes = [r.info_hash for r in db.query(AutoDeleteExclude).all()]
        return {"data": hashes}
    finally:
        db.close()
