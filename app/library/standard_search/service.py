import logging
from app.database import SessionLocal
from app.services import stashdb_public as stashdb_live
from app.services.typesense_client import TypesenseClient
from app.library.standard_search import repository as local_repo
from app.library.common.repository import index_document
from app.library.common.schema import STASHDB_INDEX_SCENES
from app.models import StashDBSceneCache

logger = logging.getLogger("laura.library.standard_search.service")


def suggest(query: str, search_type: str = "all") -> list[dict]:
    results = []
    types_to_search = ["performer", "studio", "scene"] if search_type == "all" else [search_type]

    for st in types_to_search:
        try:
            if st == "performer":
                local = local_repo.suggest_performers(query)
                if local:
                    for p in local:
                        results.append({
                            "id": p["id"], "name": p["name"],
                            "type": "performer", "image_url": p.get("image_url"),
                        })
                else:
                    live = stashdb_live.suggest(query, "performer")
                    results.extend(live)
                    _cache_live_results("performer", live)

            elif st == "studio":
                local = local_repo.suggest_studios(query)
                if local:
                    for s in local:
                        results.append({
                            "id": s["id"], "name": s["name"],
                            "type": "studio", "image_url": s.get("image_url"),
                        })
                else:
                    live = stashdb_live.suggest(query, "studio")
                    results.extend(live)
                    _cache_live_results("studio", live)

            elif st == "scene":
                local = local_repo.suggest_scenes(query)
                if local:
                    for s in local:
                        results.append({
                            "id": s["id"], "name": s["title"],
                            "type": "scene", "image_url": s.get("images", [None])[0],
                            "studio_name": s.get("studio_name"),
                        })
                else:
                    live = stashdb_live.suggest(query, "scene")
                    results.extend(live)
                    _cache_live_results("scene", live)
        except Exception as e:
            logger.warning("suggest_error", extra={"type": st, "error": str(e)})
            continue

    return results


def enrich_by_hashes(info_hashes: list[str]) -> dict[str, dict]:
    local = local_repo.enrich_by_hashes(info_hashes)
    missing = [h for h in info_hashes if h not in local]
    if missing:
        try:
            live = stashdb_live.enrich_by_hashes(missing)
            if live:
                db = SessionLocal()
                try:
                    ts = TypesenseClient()
                    for h, data in live.items():
                        local[h] = data
                        db.merge(StashDBSceneCache(
                            stashdb_id=data.get("id"),
                            title=data.get("title"),
                            details=data.get("details"),
                            release_date=data.get("release_date"),
                            duration=(data.get("file") or {}).get("duration"),
                            studio_name=(data.get("studio") or {}).get("name"),
                            performer_names=[p.get("name") for p in data.get("performers", [])],
                            tags=[t.get("name") for t in data.get("tags", [])],
                            images=[(data.get("paths") or {}).get("screenshot")] if (data.get("paths") or {}).get("screenshot") else [],
                            raw_json=data,
                        ))
                        ts.upsert("stashdb_scenes", {
                            "id": data.get("id"),
                            "title": data.get("title", ""),
                            "details": data.get("details"),
                            "release_date": data.get("release_date"),
                            "duration": (data.get("file") or {}).get("duration"),
                            "studio_name": (data.get("studio") or {}).get("name"),
                            "performer_names": [p.get("name") for p in data.get("performers", [])],
                            "tags": [t.get("name") for t in data.get("tags", [])],
                            "images": [(data.get("paths") or {}).get("screenshot")] if (data.get("paths") or {}).get("screenshot") else [],
                        })
                    db.commit()
                finally:
                    db.close()
        except Exception as e:
            logger.warning("enrich_live_fallback_error", extra={"error": str(e)})
    return local


def _cache_live_results(entity_type: str, results: list[dict]):
    for item in results:
        try:
            if entity_type == "performer":
                body = {
                    "name": item["name"],
                    "image_url": item.get("image_url"),
                    "scene_count": 0,
                }
                index_document("stashdb_performers", item["id"], body)
            elif entity_type == "studio":
                body = {
                    "name": item["name"],
                    "image_url": item.get("image_url"),
                    "scene_count": 0,
                }
                index_document("stashdb_studios", item["id"], body)
            elif entity_type == "scene":
                body = {
                    "title": item.get("name", ""),
                    "images": [item["image_url"]] if item.get("image_url") else [],
                    "studio_name": item.get("studio_name"),
                }
                index_document(STASHDB_INDEX_SCENES, item["id"], body)
        except Exception as e:
            logger.warning("cache_skip", extra={"error": str(e)})
