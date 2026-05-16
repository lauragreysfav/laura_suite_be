import urllib.parse

import httpx
import logging
from app.config import settings
from app.services.prowlarr_results import normalize_results

logger = logging.getLogger("laura.services.prowlarr")

PROWLARR_URL = settings.prowlarr_url
API_KEY = settings.prowlarr_api_key
TIMEOUT = 10
# Kestrel default request line limit is 8192; safe margin at 6000
_MAX_QS = 6000


def _estimate_url_length(params: dict) -> int:
    """Estimate serialized query string length for URL constraint checking."""
    length = len(f"{PROWLARR_URL}/api/v1/search?")
    for key, value in params.items():
        if isinstance(value, list):
            for item in value:
                length += len(key) + 1 + len(str(item))
        elif isinstance(value, str):
            length += len(key) + 1 + len(urllib.parse.quote(value))
        elif value is not None:
            length += len(key) + 1 + len(str(value))
    return length


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
    Automatically chunks categories and/or indexerIds to keep each URL
    under Prowlarr's query-string length limit (~8K).
    """
    params: dict = {"type": search_type}
    if query:
        params["query"] = query
    if categories:
        params["categories"] = categories
    if tag:
        params["tags"] = tag
    if imdbid:
        params["imdbid"] = imdbid
    if tmdbid:
        params["tmdbid"] = tmdbid
    if tvmazeid:
        params["tvmazeid"] = tvmazeid
    if tvdbid:
        params["tvdbid"] = tvdbid
    if season is not None:
        params["season"] = season
    if ep is not None:
        params["ep"] = ep

    # ---- helpers ---------------------------------------------------------------
    def _url_fits(p: dict) -> bool:
        return _estimate_url_length(p) <= _MAX_QS

    def _send(p: dict) -> list:
        return _do_prowlarr_request(p)

    def _chunk_and_send(p: dict, key: str, vals: list) -> list:
        """Binary-search for the largest safe sub-chunk of *vals* so *p* fits."""
        lo, hi = 1, len(vals)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            test = {**p, key: vals[:mid]}
            if not _url_fits(test):
                hi = mid - 1
            else:
                lo = mid
        chunk_size = lo
        merged = []
        for i in range(0, len(vals), chunk_size):
            sub = vals[i:i + chunk_size]
            try:
                r = _send({**p, key: sub})
                if isinstance(r, list):
                    merged.extend(r)
            except Exception as e:
                logger.warning(f"prowlarr_chunk_{key}_failed: {str(e)}")
        return merged
    # ---------------------------------------------------------------------------

    # CASE 1 — All indexers (no indexer_ids, single request or category-chunked)
    if not indexer_ids:
        if _url_fits(params):
            return _send(params)
        if categories and len(categories) > 1:
            return _chunk_and_send(params, "categories", categories)
        return _send(params)

    # CASE 2 — Specific indexers
    idx_list = list(indexer_ids)

    # Find a safe indexerId chunk-count so each URL stays under the limit
    idx_chunk = min(40, len(idx_list))
    while idx_chunk > 0:
        test = {**params, "indexerIds": idx_list[:idx_chunk]}
        if _url_fits(test):
            break
        idx_chunk //= 2
    if idx_chunk < 1:
        idx_chunk = 1

    all_results: list[dict] = []
    for i in range(0, len(idx_list), idx_chunk):
        chunk_params = {**params, "indexerIds": idx_list[i:i + idx_chunk]}

        if _url_fits(chunk_params):
            try:
                r = _send(chunk_params)
                if isinstance(r, list):
                    all_results.extend(r)
            except Exception as e:
                logger.warning(f"prowlarr_chunk_failed: {str(e)}")
        elif categories and len(categories) > 1:
            # URL still too long — also chunk categories
            all_results.extend(_chunk_and_send(chunk_params, "categories", categories))
        else:
            try:
                r = _send(chunk_params)
                if isinstance(r, list):
                    all_results.extend(r)
            except Exception as e:
                logger.warning(f"prowlarr_chunk_failed: {str(e)}")

    return normalize_results(all_results)


def _do_prowlarr_request(params: dict) -> list:
    url = f"{PROWLARR_URL}/api/v1/search"
    # httpx will expand list params correctly: ?indexerIds=1&indexerIds=2
    r = httpx.get(url, params=params, headers=_headers(), timeout=1500)
    
    if r.status_code != 200:
        logger.error(f"prowlarr_api_error: status={r.status_code}, body={r.text[:500]}")
    r.raise_for_status()
    
    data = r.json()
    if isinstance(data, list):
        return normalize_results(data)
    return data


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
