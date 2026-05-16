from fastapi import APIRouter, HTTPException, Query, Depends, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.services import stash, torbox, prowlarr, stashdb_public
from app.database import get_db
from app.models import LibraryTorrent, LibraryAction, LibraryBulkJob
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/library", tags=["library"])


class ManualAddRequest(BaseModel):
    info_hash: str = Field(..., min_length=1)
    magnet: str | None = None
    download_url: str | None = None
    title: str = Field(..., min_length=1)


@router.get("/manual-search")
def manual_search(query: str, tag: Optional[str] = None):
    try:
        results = prowlarr.search(query=query, tag=tag)
        enriched = []
        for r in results:
            h = r.get("infoHash")
            if not h:
                continue

            # 1. Local Dedup Check
            local = {"exists": False, "path": None}
            try:
                local = stash.check_scene_exists(info_hash=h)
            except:
                pass

            # 2. StashDB Match
            sdb_scene = None
            try:
                sdb_res = stashdb_public.find_by_hash(h)
                scenes = sdb_res.get("data", {}).get("findScenes", {}).get("scenes", [])
                if scenes:
                    sdb_scene = scenes[0]
            except:
                pass

            enriched.append({
                "title": r.get("title"),
                "size": r.get("size"),
                "seeders": r.get("seeders"),
                "indexer": r.get("indexer"),
                "infoHash": h,
                "magnetUrl": r.get("magnetUrl"),
                "downloadUrl": r.get("downloadUrl"),
                "linkType": r.get("linkType"),
                "is_local": local.get("exists", False),
                "local_path": local.get("path"),
                "stashdb_meta": sdb_scene
            })
        return enriched
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/manual-add")
def manual_add(body: ManualAddRequest, db: Session = Depends(get_db)):
    try:
        if body.magnet:
            torbox.add_magnet(body.magnet)
        elif body.download_url:
            torbox.create_torrent_from_download_url(body.download_url, seed=1, name=body.title)
        else:
            raise Exception("No magnet or download_url provided")

        # 2. Log in DB
        torrent = db.query(LibraryTorrent).filter(LibraryTorrent.info_hash == body.info_hash).first()
        if not torrent:
            torrent = LibraryTorrent(
                info_hash=body.info_hash,
                title=body.title,
                magnet=body.magnet,
                torrent_url=body.download_url,
                is_cached_torbox=True,
                added_to_torbox_at=datetime.utcnow()
            )
            db.add(torrent)
            db.flush()
        else:
            torrent.is_cached_torbox = True
            torrent.added_to_torbox_at = datetime.utcnow()
            torrent.magnet = body.magnet or torrent.magnet
            torrent.torrent_url = body.download_url or torrent.torrent_url

        action = LibraryAction(
            torrent_id=torrent.id,
            action_type="sent"
        )
        db.add(action)
        db.commit()

        return {"status": "ok"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/get-the-past")
def trigger_get_the_past(query: str = Body(..., embed=True), tag: Optional[str] = Body(None, embed=True), db: Session = Depends(get_db)):
    try:
        from app.tasks.library_tasks import get_the_past
        job = LibraryBulkJob(
            performer_or_studio=query,
            query_type="performer",
            status="running"
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        get_the_past.delay(job.id, query, tag)
        return {"status": "started", "job_id": job.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/get-the-past/megapack")
def trigger_megapack_search(query: str = Body(..., embed=True), tag: Optional[str] = Body(None, embed=True), db: Session = Depends(get_db)):
    try:
        from app.tasks.library_tasks import search_megapacks
        job = LibraryBulkJob(
            performer_or_studio=query,
            query_type="megapack",
            status="running"
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        search_megapacks.delay(job.id, query, tag)
        return {"status": "started", "job_id": job.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/bulk-jobs/{job_id}")
def get_bulk_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(LibraryBulkJob).filter(LibraryBulkJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Return results if completed
    results = []
    if job.status == "completed":
        results = db.query(LibraryTorrent).filter(
            LibraryTorrent.title.ilike(f"%{job.performer_or_studio}%")
        ).all()
        # Transform for frontend
        results = [{
            "infoHash": t.info_hash,
            "title": t.title,
            "size": int(t.size) if t.size and t.size.isdigit() else 0,
            "seeders": t.seeders,
            "indexer": t.source,
            "is_megapack": t.is_megapack,
            "is_local": t.is_local_stash,
            "local_path": t.local_stash_path,
            "magnetUrl": t.magnet,
            "downloadUrl": t.torrent_url,
            "linkType": "torrent-file" if t.torrent_url and not t.magnet else "direct" if t.magnet else "unavailable",
        } for t in results]

    return {
        "status": job.status,
        "total_found": job.total_found,
        "results": results,
        "error": job.error
    }


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
    return {
        "status": "ok" if ok else "unavailable",
        "detail": None if ok else "WebDAV refresh failed — check credentials or TorBox service status"
    }
