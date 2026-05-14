import httpx
import logging
from app.config import settings

STASHDB_URL = "https://stashdb.org/graphql"
logger = logging.getLogger("laura.services.stashdb_public")


def _query(query: str, variables: dict = None) -> dict:
    headers = {"ApiKey": settings.stashdb_api_key} if settings.stashdb_api_key else {}
    try:
        r = httpx.post(STASHDB_URL, json={"query": query, "variables": variables or {}}, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        logger.warning("stashdb_http_error", extra={"status": e.response.status_code, "body": str(e.response.text)[:300]})
        return {"data": None}
    except Exception as e:
        logger.warning("stashdb_query_error", extra={"error": str(e)})
        return {"data": None}


def search_performers(query: str):
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
    return _query(q, {"input": {"names": query, "page": 1, "per_page": 20}})


def find_by_hash(info_hash: str):
    q = """
    query FindByHash($fp: FingerprintQueryInput!) {
      findSceneByFingerprint(fingerprint: $fp) {
        id
        title
        details
        images { url }
        studio { name }
        performers { name }
      }
    }
    """
    return _query(q, {"fp": {"hash": info_hash, "algorithm": "MD5"}})


def batch_find_by_hashes(info_hashes: list[str]):
    """Find scenes by multiple info hashes, called per-hash since GraphQL only supports single fingerprint lookup."""
    results = {}
    for h in info_hashes:
        try:
            data = find_by_hash(h)
            d = data.get("data") or {}
            scene = d.get("findSceneByFingerprint")
            if scene:
                results[h] = scene
        except Exception as e:
            logger.debug("batch_find_skip", extra={"hash": h[:8], "error": str(e)})
    return results


def get_performer(performer_id: str):
    q = """
    query GetPerformer($id: ID!) {
      findPerformer(id: $id) {
        id
        name
        aliases
        gender
        urls { url type }
        images { url }
      }
    }
    """
    return _query(q, {"id": performer_id})


def suggest(query: str, search_type: str = "all") -> list[dict]:
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
                data = _query(q, {"input": {"names": query, "page": 1, "per_page": 5}})
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
                data = _query(q, {"input": {"names": query, "page": 1, "per_page": 5}})
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
                data = _query(q, {"input": {"title": query, "page": 1, "per_page": 5}})
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


def get_studio(studio_id: str):
    q = """
    query GetStudio($id: ID!) {
      findStudio(id: $id) {
        id
        name
        images { url }
      }
    }
    """
    return _query(q, {"id": studio_id})


def get_scene(scene_id: str):
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
      }
    }
    """
    return _query(q, {"id": scene_id})


def enrich_by_hashes(info_hashes: list[str]) -> dict[str, dict]:
    if not info_hashes:
        return {}

    result = {}
    for h in info_hashes:
        try:
            data = find_by_hash(h)
            d = data.get("data") or {}
            scene = d.get("findSceneByFingerprint")
            if not scene:
                continue
            imgs = scene.get("images", [])
            performers = scene.get("performers", []) or []
            studio = scene.get("studio", {}) or {}
            result[h] = {
                "title": scene.get("title"),
                "images": [i["url"] for i in imgs] if imgs else [],
                "performers": [p["name"] for p in performers],
                "studio": studio.get("name"),
            }
        except Exception as e:
            logger.debug("enrich_skip", extra={"hash": h[:8], "error": str(e)})
    return result
