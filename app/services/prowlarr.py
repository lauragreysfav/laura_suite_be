import httpx
from app.config import settings

PROWLARR_URL = settings.prowlarr_url
API_KEY = settings.prowlarr_api_key
TIMEOUT = 10


def _get(path: str) -> dict | list:
    url = f"{PROWLARR_URL}/api/v1{path}"
    params = {}
    if API_KEY:
        params["apikey"] = API_KEY
    r = httpx.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


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
    qs_params = {}
    if API_KEY:
        qs_params["apikey"] = API_KEY
    qs_params["query"] = query
    if indexer_ids:
        qs_params["indexerIds"] = [str(i) for i in indexer_ids]
    r = httpx.get(url, params=qs_params, timeout=60)
    r.raise_for_status()
    return r.json()
