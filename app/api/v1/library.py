from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from app.services import stash, torbox, prowlarr, stashdb_public
from app.database import get_db
from app.models import LibraryTorrent, LibraryAction
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/manual-search")
def manual_search(query: str, tag: Optional[str] = None):
    try:
        results = prowlarr.search(query, tag)
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
                "is_local": local.get("exists", False),
                "local_path": local.get("path"),
                "stashdb_meta": sdb_scene
            })
        return enriched
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/manual-add")
def manual_add(info_hash: str, magnet: str, title: str, db: Session = Depends(get_db)):
    try:
        # 1. Send to TorBox
        ok = torbox.add_magnet(magnet)
        if not ok:
            raise Exception("Failed to add to TorBox")

        # 2. Log in DB
        torrent = db.query(LibraryTorrent).filter(LibraryTorrent.info_hash == info_hash).first()
        if not torrent:
            torrent = LibraryTorrent(
                info_hash=info_hash,
                title=title,
                magnet=magnet,
                is_cached_torbox=True,
                added_to_torbox_at=datetime.utcnow()
            )
            db.add(torrent)
        else:
            torrent.is_cached_torbox = True
            torrent.added_to_torbox_at = datetime.utcnow()

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
