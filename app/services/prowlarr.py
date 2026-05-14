import httpx
import logging
from app.config import settings

logger = logging.getLogger("laura.services.prowlarr")

PROWLARR_URL = settings.prowlarr_url
API_KEY = settings.prowlarr_api_key
TIMEOUT = 10


def _headers() -> dict:
    h = {}
    if API_KEY:
        h["X-Api-Key"] = API_KEY
    return h


def _get(path: str, params: dict = None) -> dict | list:
    url = f"{PROWLARR_URL}/api/v1{path}"
    try:
        r = httpx.get(url, headers=_headers(), params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        logger.error("prowlarr_http_error", extra={"path": path, "status": e.response.status_code})
        raise
    except Exception as e:
        logger.exception("prowlarr_request_failed", extra={"path": path, "error": str(e)})
        raise


def list_indexers() -> list:
    """List all configured indexers and their capabilities."""
    return _get("/indexer")


def get_categories() -> list:
    """List all standard categories supported by Prowlarr."""
    return _get("/indexer/categories")


def get_default_categories() -> list:
    """List default categories used for general searches."""
    return _get("/indexer/defaultcategories")


def list_applications() -> list:
    return _get("/applications")


def system_status() -> dict:
    return _get("/system/status")


def search(
    query: str = None,
    categories: list[int] = None,
    indexer_ids: list[int] = None,
    search_type: str = "search",
    imdbid: str = None,
    tmdbid: int = None,
    tvmazeid: int = None,
    tvdbid: int = None,
    season: int = None,
    ep: int = None,
    tag: str = None,
) -> list:
    """
    Perform an advanced search using Prowlarr's search endpoint.
    Supports all Torznab standard parameters.
    """
    params = {"type": search_type}
    
    if query:
        params["query"] = query
    if categories:
        params["categories"] = categories
    if indexer_ids:
        params["indexerIds"] = indexer_ids
    if tag:
        params["tags"] = tag
        
    # Metadata IDs
    if imdbid:
        params["imdbid"] = imdbid
    if tmdbid:
        params["tmdbid"] = tmdbid
    if tvmazeid:
        params["tvmazeid"] = tvmazeid
    if tvdbid:
        params["tvdbid"] = tvdbid
        
    # TV Specific
    if season is not None:
        params["season"] = season
    if ep is not None:
        params["ep"] = ep

    url = f"{PROWLARR_URL}/api/v1/search"
    try:
        # Search often takes longer than other operations
        r = httpx.get(url, params=params, headers=_headers(), timeout=1500)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            "prowlarr_search_http_error", 
            extra={"query": query, "type": search_type, "status": e.response.status_code}
        )
        raise
    except Exception as e:
        logger.exception(
            "prowlarr_search_failed", 
            extra={"query": query, "type": search_type, "error": str(e)}
        )
        raise


def get_indexer(indexer_id: int) -> dict:
    return _get(f"/indexer/{indexer_id}")


def add_indexer(data: dict) -> dict:
    url = f"{PROWLARR_URL}/api/v1/indexer"
    r = httpx.post(url, json=data, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def update_indexer(indexer_id: int, data: dict) -> dict:
    url = f"{PROWLARR_URL}/api/v1/indexer/{indexer_id}"
    r = httpx.put(url, json=data, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def delete_indexer(indexer_id: int) -> None:
    url = f"{PROWLARR_URL}/api/v1/indexer/{indexer_id}"
    r = httpx.delete(url, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
