import httpx
import logging
from app.config import settings

STASHDB_URL = "https://stashdb.org/graphql"
logger = logging.getLogger("laura.services.stashdb_public")


async def _query(query: str, variables: dict = None) -> dict:
    headers = {"ApiKey": settings.stashdb_api_key} if settings.stashdb_api_key else {}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(STASHDB_URL, json={"query": query, "variables": variables or {}}, headers=headers, timeout=15)
            if r.status_code == 422:
                logger.error(f"stashdb_validation_error: {r.text}")
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        logger.warning("stashdb_http_error", extra={"status": e.response.status_code, "body": str(e.response.text)[:500]})
        return {"data": None}
    except Exception as e:
        logger.warning("stashdb_query_error", extra={"error": str(e)})
        return {"data": None}


async def search_performers(query: str):
    q = """
    query SearchPerformers($input: PerformerQueryInput!) {
      queryPerformers(input: $input) {
        count
        performers { 
          id 
          name 
          aliases 
          images { url } 
        }
      }
    }
    """
    # Use 'name' instead of 'names' for StashDB criteria
    return await _query(q, {"input": {"name": query, "page": 1, "per_page": 20}})


async def find_by_hash(info_hash: str):
    # Optimized FindByHash query for Public StashDB
    q = """
    query FindByHash($input: SceneQueryInput!) {
      queryScenes(input: $input) {
        scenes {
          id
          title
          details
          release_date
          duration
          images { url }
          studio { id name }
          performers { performer { id name } }
        }
      }
    }
    """
    # Use standard 'fingerprints' criterion for Stash-Box
    result = await _query(q, {"input": {"fingerprints": {"value": [info_hash], "modifier": "INCLUDES"}}})
    d = result.get("data") or {}
    scenes = (d.get("queryScenes") or {}).get("scenes")
    
    if scenes and isinstance(scenes, list) and len(scenes) > 0:
        # Return in the format expected by the caller (simulating findSceneByFingerprint)
        return {"data": {"findSceneByFingerprint": scenes[0]}}
    return {"data": None}


async def batch_find_by_hashes(info_hashes: list[str]):
    """Find scenes by multiple info hashes, called per-hash since GraphQL only supports single fingerprint lookup."""
    results = {}
    for h in info_hashes:
        try:
            data = await find_by_hash(h)
            d = data.get("data") or {}
            scene = d.get("findSceneByFingerprint")
            if scene:
                results[h] = scene
        except Exception as e:
            logger.debug("batch_find_skip", extra={"hash": h[:8], "error": str(e)})
    return results


async def get_performer(performer_id: str):
    q = """
    query GetPerformer($id: ID!) {
      findPerformer(id: $id) {
        id
        name
        aliases
        gender
        birth_date
        career_start_year
        career_end_year
        ethnicity
        country
        eye_color
        hair_color
        height
        measurements
        details
        death_date
        urls { url type }
        images { url }
      }
    }
    """
    return await _query(q, {"id": performer_id})


async def suggest(query: str, search_type: str = "all") -> list[dict]:
    results = []
    types_to_search = ["performer", "studio", "scene"] if search_type == "all" else [search_type]

    for st in types_to_search:
        try:
            if st == "performer":
                q = """
                query SuggestPerformers($input: PerformerQueryInput!) {
                  queryPerformers(input: $input) {
                    performers { id name images { url } }
                  }
                }
                """
                # Correct field 'name' for StashDB
                data = await _query(q, {"input": {"name": query, "page": 1, "per_page": 5}})
                d = data.get("data") or {}
                for p in (d.get("queryPerformers") or {}).get("performers", []):
                    imgs = p.get("images", [])
                    results.append({
                        "id": p["id"], "name": p["name"],
                        "type": "performer",
                        "image_url": imgs[0]["url"] if imgs else None
                    })

            elif st == "studio":
                q = """
                query SuggestStudios($input: StudioQueryInput!) {
                  queryStudios(input: $input) {
                    studios { id name images { url } }
                  }
                }
                """
                # Correct field 'name' for StashDB
                data = await _query(q, {"input": {"name": query, "page": 1, "per_page": 5}})
                d = data.get("data") or {}
                for s in (d.get("queryStudios") or {}).get("studios", []):
                    imgs = s.get("images", [])
                    results.append({
                        "id": s["id"], "name": s["name"],
                        "type": "studio",
                        "image_url": imgs[0]["url"] if imgs else None
                    })

            elif st == "scene":
                q = """
                query SuggestScenes($input: SceneQueryInput!) {
                  queryScenes(input: $input) {
                    scenes { id title images { url } studio { name } }
                  }
                }
                """
                # Correct field 'name' or 'title' for StashDB. Stash-Box SceneQueryInput usually uses 'name'.
                data = await _query(q, {"input": {"name": query, "page": 1, "per_page": 5}})
                d = data.get("data") or {}
                for s in (d.get("queryScenes") or {}).get("scenes", []):
                    imgs = s.get("images", [])
                    studio = s.get("studio", {}) or {}
                    results.append({
                        "id": s["id"], "name": s["title"],
                        "type": "scene",
                        "image_url": imgs[0]["url"] if imgs else None,
                        "studio_name": studio.get("name")
                    })
        except Exception as e:
            logger.warning("stashdb_suggest_error", extra={"type": st, "error": str(e)})
            continue

    return results


async def get_studio(studio_id: str):
    q = """
    query GetStudio($id: ID!) {
      findStudio(id: $id) {
        id
        name
        details
        urls { url type }
        images { url }
        parent { id name }
      }
    }
    """
    return await _query(q, {"id": studio_id})


async def get_scene(scene_id: str):
    q = """
    query GetScene($id: ID!) {
      findScene(id: $id) {
        id
        title
        details
        release_date
        duration
        images { url }
        studio { id name }
        performers { performer { id name } }
        tags { name }
        fingerprints { algorithm hash duration }
      }
    }
    """
    return await _query(q, {"id": scene_id})


async def search_scenes(title: str, limit: int = 1):
    q = """
    query SearchScenes($input: SceneQueryInput!) {
      queryScenes(input: $input) {
        scenes { id title images { url } studio { name } }
      }
    }
    """
    # Correct field 'name' for StashDB SceneQueryInput
    data = await _query(q, {"input": {"name": title, "page": 1, "per_page": limit}})
    d = data.get("data") or {}
    return (d.get("queryScenes") or {}).get("scenes", [])


async def enrich_by_hashes(info_hashes: list[str]) -> dict[str, dict]:
    if not info_hashes:
        return {}

    result = {}
    for h in info_hashes:
        try:
            data = await find_by_hash(h)
            d = data.get("data") or {}
            scene = d.get("findSceneByFingerprint")
            if not scene:
                continue
            result[h] = scene
        except Exception as e:
            logger.debug("enrich_skip", extra={"hash": h[:8], "error": str(e)})
    return result
