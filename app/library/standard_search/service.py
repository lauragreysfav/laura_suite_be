import logging
from typing import Optional
from app.database import SessionLocal
from app.services import stashdb_public as stashdb_live
from app.services.typesense_client import TypesenseClient
from app.library.standard_search import repository as local_repo
from app.library.common.repository import index_document
from app.library.common.schema import STASHDB_INDEX_SCENES
from app.models import StashDBSceneCache

logger = logging.getLogger("laura.library.standard_search.service")


from app.library.common.reshapers import reshape_scene, reshape_performer, reshape_studio

async def find_and_enrich_scene(title: str, hash: Optional[str] = None) -> Optional[dict]:
    # 1. Try local cache by hash first
    if hash:
        local = local_repo.enrich_by_hashes([hash])
        if hash.lower() in local:
            return reshape_scene(local[hash.lower()])

    # 2. Try live search on StashDB
    try:
        # Search by hash if available, otherwise by title
        if hash:
            live = await stashdb_live.enrich_by_hashes([hash])
            if hash.lower() in live:
                data = live[hash.lower()]
                # enrich_by_hashes already reshapes and handles caching
                return data

        # Fallback to title search
        search_results = await stashdb_live.search_scenes(title, limit=1)
        if search_results:
            scene_id = search_results[0]["id"]
            # Fetch full scene details
            resp = await stashdb_live.get_scene(scene_id)
            full_scene = (resp.get("data") or {}).get("findScene")
            if full_scene:
                return reshape_scene(full_scene)
    except Exception as e:
        logger.warning("find_and_enrich_error", extra={"title": title, "hash": hash, "error": str(e)})

    return None


async def suggest(query: str, search_type: str = "all") -> list[dict]:
    results = []
    types_to_search = ["performer", "studio", "scene"] if search_type == "all" else [search_type]

    for st in types_to_search:
        try:
            if st == "performer":
                local = local_repo.suggest_performers(query)
                if local:
                    for p in local:
                        reshaped = reshape_performer(p)
                        results.append({
                            "id": reshaped["id"], "name": reshaped["name"],
                            "type": "performer", "image_url": reshaped.get("image_path"),
                        })
                else:
                    live = await stashdb_live.suggest(query, "performer")
                    results.extend(live)
                    _cache_live_results("performer", live)

            elif st == "studio":
                local = local_repo.suggest_studios(query)
                if local:
                    for s in local:
                        reshaped = reshape_studio(s)
                        results.append({
                            "id": reshaped["id"], "name": reshaped["name"],
                            "type": "studio", "image_url": reshaped.get("image_path"),
                        })
                else:
                    live = await stashdb_live.suggest(query, "studio")
                    results.extend(live)
                    _cache_live_results("studio", live)

            elif st == "scene":
                local = local_repo.suggest_scenes(query)
                if local:
                    for s in local:
                        reshaped = reshape_scene(s)
                        results.append({
                            "id": reshaped["id"], "name": reshaped["title"],
                            "type": "scene", "image_url": (reshaped.get("paths") or {}).get("screenshot"),
                            "studio_name": (reshaped.get("studio") or {}).get("name"),
                        })
                else:
                    live = await stashdb_live.suggest(query, "scene")
                    results.extend(live)
                    _cache_live_results("scene", live)
        except Exception as e:
            logger.warning("suggest_error", extra={"type": st, "error": str(e)})
            continue

    return results


async def enrich_by_hashes(info_hashes: list[str]) -> dict[str, dict]:
    # Lowercase all input hashes for consistent lookup
    lookup_hashes = [h.lower() for h in info_hashes if h]
    if not lookup_hashes:
        return {}

    local = local_repo.enrich_by_hashes(lookup_hashes)
    # The repository returns lowercased keys, but let's be safe
    reshaped_local = {str(h).lower(): reshape_scene(data) for h, data in local.items()}
    
    missing = [h for h in lookup_hashes if h not in reshaped_local]
    if missing:
        try:
            # StashDB live also expects list of strings
            live = await stashdb_live.enrich_by_hashes(missing)
            if live:
                db = SessionLocal()
                try:
                    ts = TypesenseClient()
                    for h, data in live.items():
                        h_lower = str(h).lower()
                        reshaped_local[h_lower] = reshape_scene(data)
                        
                        # Cache the raw data
                        imgs = data.get("images", [])
                        performers = data.get("performers", []) or []
                        studio = data.get("studio", {}) or {}
                        tags = data.get("tags", []) or []
                        
                        db.merge(StashDBSceneCache(
                            stashdb_id=data.get("id"),
                            title=data.get("title"),
                            details=data.get("details"),
                            release_date=data.get("release_date"),
                            duration=data.get("duration"),
                            studio_name=studio.get("name"),
                            studio_id=studio.get("id"),
                            performer_names=[p.get("performer", {}).get("name") for p in performers if p.get("performer")],
                            performer_ids=[p.get("performer", {}).get("id") for p in performers if p.get("performer")],
                            tags=[t.get("name") for t in tags if t.get("name")],
                            images=[i.get("url") for i in imgs if i.get("url")],
                            raw_json=data,
                        ))
                        
                        ts.upsert("stashdb_scenes", {
                            "id": data.get("id"),
                            "title": data.get("title", ""),
                            "details": data.get("details"),
                            "release_date": data.get("release_date"),
                            "duration": data.get("duration"),
                            "studio_name": studio.get("name"),
                            "performer_names": [p.get("performer", {}).get("name") for p in performers if p.get("performer")],
                            "tags": [t.get("name") for t in tags if t.get("name")],
                            "images": [i.get("url") for i in imgs if i.get("url")],
                        })
                    db.commit()
                finally:
                    db.close()
        except Exception as e:
            logger.warning("enrich_live_fallback_error", extra={"error": str(e)})
    return reshaped_local


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
