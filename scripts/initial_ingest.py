"""
Initial stashdb ingest: performers by name prefix -> studios -> scenes (date >= 2000).

Usage:
    docker compose exec laura-backend python scripts/initial_ingest.py

Requires STASHDB_API_KEY in .env (stashdb.org -> Settings -> ApiKeys -> Create).
"""
import logging
import sys
import time
import string
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from app.config import settings
from app.database import SessionLocal
from app.models import StashDBPerformerCache, StashDBStudioCache, StashDBSceneCache
from app.services.typesense_client import TypesenseClient
from app.library.common.typesense_schema import SCHEMAS

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("initial_ingest")

STASHDB_URL = "https://stashdb.org/graphql"
HEADERS = {"ApiKey": settings.stashdb_api_key} if settings.stashdb_api_key else {}
PER_PAGE = 100
MAX_SCENES_PER_STUDIO = 500
NAME_PREFIXES = [c for c in string.ascii_lowercase] + [str(i) for i in range(10)]

ts: TypesenseClient | None = None


def require_api_key():
    if not settings.stashdb_api_key:
        logger.error("STASHDB_API_KEY not set -- add it to .env (Settings -> ApiKeys -> Create on stashdb.org)")
        sys.exit(1)


def graphql(query: str, variables: dict = None) -> dict:
    r = httpx.post(
        STASHDB_URL,
        json={"query": query, "variables": variables or {}},
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def fetch_performers_by_name(name: str, page: int = 1) -> dict:
    q = """
    query SearchPerformers($input: PerformerQueryInput!) {
      queryPerformers(input: $input) {
        count
        performers {
          id name aliases gender
          images { url }
          scene_count career_end_year birth_date
          urls { url type }
          studios { studio { id name } }
        }
      }
    }
    """
    return graphql(q, {"input": {"names": name, "page": page, "per_page": PER_PAGE}})


def find_studio_by_id(studio_id: str) -> dict | None:
    q = """
    query GetStudio($id: ID!) {
      findStudio(id: $id) {
        id name
        images { url }
        scene_count
        parent { id name }
        urls { url type }
      }
    }
    """
    try:
        data = graphql(q, {"id": studio_id})
        return (data.get("data") or {}).get("findStudio")
    except Exception as e:
        logger.warning("studio_fetch_error", extra={"id": studio_id, "error": str(e)})
        return None


def fetch_scenes_by_studio(studio_id: str, page: int = 1) -> dict:
    q = """
    query StudioScenes($input: SceneQueryInput!) {
      queryScenes(input: $input) {
        count
        scenes {
          id title details release_date duration
          images { url }
          studio { id name }
          performers { performer { id name } }
          fingerprints { algorithm hash duration }
          tags { name }
        }
      }
    }
    """
    return graphql(q, {
        "input": {
            "studios": {"value": [studio_id], "modifier": "INCLUDES"},
            "page": page,
            "per_page": PER_PAGE,
            "date": {"value": "2001-01-01", "modifier": "GREATER_THAN"},
        }
    })


def should_include_scene(release_date: str | None) -> bool:
    if not release_date:
        return False
    return release_date >= "2000-01-01"


def rate_limit():
    time.sleep(settings.stashdb_rate_limit_seconds)


def save_performer(session, p):
    gender = p.get("gender", "")
    if gender != "female":
        return

    pid = p.get("id")
    imgs = p.get("images", [])
    urls = p.get("urls", [])

    cache = StashDBPerformerCache(
        stashdb_id=pid,
        name=p.get("name", ""),
        aliases=p.get("aliases", ""),
        gender=gender,
        birthdate=p.get("birth_date"),
        image_url=imgs[0]["url"] if imgs else None,
        scene_count=p.get("scene_count", 0),
        urls=[{"url": u["url"], "type": u["type"]} for u in (urls or [])],
        raw_json=p,
    )
    session.merge(cache)
    session.commit()

    ts.upsert("stashdb_performers", {
        "id": pid,
        "name": p.get("name", ""),
        "aliases": p.get("aliases", ""),
        "gender": gender,
        "birthdate": p.get("birth_date"),
        "scene_count": p.get("scene_count", 0),
    })


def save_studio(session, s):
    imgs = s.get("images", [])
    parent = s.get("parent") or {}
    urls = s.get("urls") or []

    cache = StashDBStudioCache(
        stashdb_id=s["id"],
        name=s.get("name", ""),
        image_url=imgs[0]["url"] if imgs else None,
        scene_count=s.get("scene_count", 0),
        parent_studio=parent.get("name"),
        urls=[{"url": u["url"], "type": u["type"]} for u in urls],
        raw_json=s,
    )
    session.merge(cache)
    session.commit()

    ts.upsert("stashdb_studios", {
        "id": s["id"],
        "name": s.get("name", ""),
        "scene_count": s.get("scene_count", 0),
    })


def save_scene(session, sc):
    if not should_include_scene(sc.get("release_date")):
        return

    imgs = sc.get("images", [])
    pdata = sc.get("performers") or []
    fprints = sc.get("fingerprints") or []
    tags = sc.get("tags") or []
    studio_data = sc.get("studio") or {}
    sname = studio_data.get("name", "")

    cache = StashDBSceneCache(
        stashdb_id=sc["id"],
        title=sc.get("title", ""),
        details=sc.get("details"),
        release_date=sc.get("release_date"),
        duration=sc.get("duration"),
        studio_id=studio_data.get("id"),
        studio_name=sname,
        performer_names=[p.get("performer", {}).get("name") for p in pdata if p.get("performer")],
        performer_ids=[p.get("performer", {}).get("id") for p in pdata if p.get("performer")],
        tags=[t.get("name") for t in tags if t.get("name")],
        fingerprints=[{"algorithm": fp.get("algorithm"), "hash": fp.get("hash"), "duration": fp.get("duration")} for fp in fprints],
        images=[i["url"] for i in imgs] if imgs else [],
        raw_json=sc,
    )
    session.merge(cache)
    session.commit()

    ts.upsert("stashdb_scenes", {
        "id": sc["id"],
        "title": sc.get("title", ""),
        "details": sc.get("details"),
        "release_date": sc.get("release_date"),
        "duration": sc.get("duration"),
        "studio_name": sname,
        "performer_names": [p.get("performer", {}).get("name") for p in pdata if p.get("performer")],
        "tags": [t.get("name") for t in tags if t.get("name")],
        "fingerprints": [fp.get("hash") for fp in fprints if fp.get("hash")],
        "images": [i["url"] for i in imgs] if imgs else [],
    })


def ingest_performers():
    session = SessionLocal()
    seen_ids = set()
    seen_studio_ids = set()
    total = 0

    for prefix in NAME_PREFIXES:
        page = 1
        while True:
            try:
                data = fetch_performers_by_name(prefix, page)
            except Exception as e:
                logger.warning("performer_fetch_error", extra={"prefix": prefix, "page": page, "error": str(e)})
                break
            d = data.get("data") or {}
            qp = d.get("queryPerformers") or {}
            performers = qp.get("performers", [])
            if not performers:
                break

            for p in performers:
                pid = p.get("id")
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)

                studios = p.get("studios") or []
                for s_rel in studios:
                    s = s_rel.get("studio") or {}
                    if s.get("id"):
                        seen_studio_ids.add(s["id"])

                save_performer(session, p)
                total += 1

            logger.info("indexed_performers", extra={"prefix": prefix, "page": page, "count": len(performers), "total": total})
            page += 1
            rate_limit()

    session.close()
    logger.info("done_performers", extra={"total": total})
    return seen_studio_ids


def ingest_studios(studio_ids: set):
    session = SessionLocal()
    total = 0
    for sid in sorted(studio_ids):
        s = find_studio_by_id(sid)
        if not s:
            rate_limit()
            continue
        save_studio(session, s)
        total += 1
        rate_limit()
    session.close()
    logger.info("done_studios", extra={"total": total})


def ingest_scenes():
    session = SessionLocal()
    total = 0

    for prefix in NAME_PREFIXES:
        page = 1
        while True:
            try:
                data = fetch_performers_by_name(prefix, page)
            except Exception as e:
                break
            d = data.get("data") or {}
            qp = d.get("queryPerformers") or {}
            performers = qp.get("performers", [])
            if not performers:
                break

            for p in performers:
                studios = p.get("studios") or []
                for s_rel in studios:
                    s = s_rel.get("studio") or {}
                    sid = s.get("id")
                    sname = s.get("name", sid)
                    if not sid:
                        continue

                    spage = 1
                    while True:
                        try:
                            sdata = fetch_scenes_by_studio(sid, spage)
                        except Exception as e:
                            logger.warning("scene_page_error", extra={"studio": sname, "page": spage, "error": str(e)})
                            break
                        sd = sdata.get("data") or {}
                        qs = sd.get("queryScenes") or {}
                        scenes = qs.get("scenes", [])
                        if not scenes:
                            break

                        for sc in scenes:
                            save_scene(session, sc)
                            total += 1

                        logger.info("indexed_scenes", extra={"studio": sname, "page": spage, "count": len(scenes), "total": total})
                        spage += 1
                        if spage > 10:
                            break
                        rate_limit()

            page += 1
            rate_limit()

    session.close()
    logger.info("done_scenes", extra={"total": total})


def main():
    global ts
    require_api_key()
    logger.info("starting_initial_ingest")

    ts = TypesenseClient()
    ts.ensure_collections(SCHEMAS)

    logger.info("phase_1: fetching performers by name prefix")
    studio_ids = ingest_performers()
    logger.info("phase_1_done", extra={"studios_found": len(studio_ids)})

    logger.info("phase_2: fetching studio details")
    ingest_studios(studio_ids)

    logger.info("phase_3: fetching scenes per studio")
    ingest_scenes()

    logger.info("ingest_complete")


if __name__ == "__main__":
    main()
