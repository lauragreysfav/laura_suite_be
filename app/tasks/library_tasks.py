from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import LibraryBulkJob, LibraryTorrent
from app.services import prowlarr, stash
import logging

logger = logging.getLogger(__name__)

MEGAPACK_KEYWORDS = ["megapack", "mega pack", "collection", "complete pack", "full collection", "xxx-ViDEOS", "complete", "全集", "全作品"]


@celery_app.task(name="library.get_the_past")
def get_the_past(job_id: int, query: str, indexer_ids: list[int] = None):
    db = SessionLocal()
    try:
        job = db.query(LibraryBulkJob).get(job_id)
        if not job:
            return

        # Search exact query
        results = prowlarr.search(query=query, indexer_ids=indexer_ids)
        
        # Search megapacks
        for kw in ["megapack", "collection", "complete"]:
            try:
                results.extend(prowlarr.search(query=f"{query} {kw}", indexer_ids=indexer_ids))
            except:
                continue
            
        found_hashes = set()
        torrents = []
        
        for r in results:
            h = r.get("infoHash")
            if not h or h in found_hashes:
                continue
            found_hashes.add(h)
            
            title = r.get("title", "")
            size = r.get("size", 0)
            
            # Megapack detection
            is_mega = any(kw.lower() in title.lower() for kw in MEGAPACK_KEYWORDS) or size > 10 * 1024 * 1024 * 1024
            
            # Local Stash Dedup Check
            try:
                local_check = stash.check_scene_exists(info_hash=h, title=title)
            except:
                local_check = {"exists": False, "path": None}
            
            t = LibraryTorrent(
                info_hash=h,
                title=title,
                size=str(size),
                seeders=r.get("seeders", 0),
                source=r.get("indexer"),
                magnet=r.get("magnetUrl"),
                torrent_url=r.get("downloadUrl"),
                is_megapack=is_mega,
                is_local_stash=local_check["exists"],
                local_stash_path=local_check["path"]
            )
            torrents.append(t)
            
        # Add found torrents to DB
        for t in torrents:
            db.merge(t)
            
        job.total_found = len(torrents)
        job.status = "completed"
        db.commit()
    except Exception as e:
        db.rollback()
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
        logger.exception("get_the_past_failed")
    finally:
        db.close()


@celery_app.task(name="library.search_megapacks")
def search_megapacks(job_id: int, query: str, tag: str = None):
    db = SessionLocal()
    job = db.query(LibraryBulkJob).get(job_id)
    if not job:
        db.close()
        return

    try:
        keywords = ["megapack", "collection", "complete", "全集"]
        results = []
        for kw in keywords:
            try:
                results.extend(prowlarr.search(query=f"{query} {kw}", tag=tag))
            except:
                continue

        found_hashes = set()
        torrents = []
        
        # Megapacks: size > 30GB or keyword match
        for r in results:
            h = r.get("infoHash")
            if not h or h in found_hashes:
                continue
            found_hashes.add(h)

            title = r.get("title", "")
            size = r.get("size", 0)
            
            # Strict Megapack filter: > 30GB OR explicit keyword in title
            is_mega = any(kw.lower() in title.lower() for kw in keywords) or size > 30 * 1024 * 1024 * 1024
            
            if not is_mega:
                continue

            local_check = {"exists": False, "path": None}
            try:
                local_check = stash.check_scene_exists(info_hash=h, title=title)
            except:
                pass

            t = LibraryTorrent(
                info_hash=h,
                title=title,
                size=str(size),
                seeders=r.get("seeders", 0),
                source=r.get("indexer"),
                magnet=r.get("magnetUrl"),
                torrent_url=r.get("downloadUrl"),
                is_megapack=True,
                is_local_stash=local_check["exists"],
                local_stash_path=local_check["path"]
            )
            db.merge(t)
            torrents.append(t)

        job.total_found = len(torrents)
        job.status = "completed"
        db.commit()
    except Exception as e:
        db.rollback()
        job.status = "failed"
        job.error = str(e)
        db.commit()
        logger.exception("search_megapacks_failed")
    finally:
        db.close()
