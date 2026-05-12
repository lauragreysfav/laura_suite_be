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


def _get(path: str) -> dict | list:
    url = f"{PROWLARR_URL}/api/v1{path}"
    try:
        r = httpx.get(url, headers=_headers(), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        logger.error("prowlarr_http_error", extra={"path": path, "status": e.response.status_code})
        raise
    except Exception as e:
        logger.exception("prowlarr_request_failed", extra={"path": path, "error": str(e)})
        raise


def list_indexers() -> list:
    return _get("/indexer")


def list_applications() -> list:
    return _get("/applications")


def system_status() -> dict:
    return _get("/system/status")


def search(query: str, indexer_ids: list[int] = None) -> list:
    params = {"query": query}
    if indexer_ids:
        params["indexerIds"] = ",".join(str(i) for i in indexer_ids)
    url = f"{PROWLARR_URL}/api/v1/search"
    try:
        r = httpx.get(url, params=params, headers=_headers(), timeout=60)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        logger.error("prowlarr_search_http_error", extra={"query": query, "status": e.response.status_code})
        raise
    except Exception as e:
        logger.exception("prowlarr_search_failed", extra={"query": query, "error": str(e)})
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
