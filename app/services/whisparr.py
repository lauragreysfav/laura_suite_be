import httpx
from app.config import settings

WHISPARR_URL = settings.whisparr_url
API_KEY = settings.whisparr_api_key
TIMEOUT = 15


def _headers() -> dict:
    return {"X-Api-Key": API_KEY}


def _get(path: str, params: dict = None) -> dict | list:
    url = f"{WHISPARR_URL}/api/v3{path}"
    r = httpx.get(url, headers=_headers(), params=params or {}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_movies() -> list:
    return _get("/series")


def get_history(page: int = 1, page_size: int = 20) -> dict:
    return _get("/history", {"page": page, "pageSize": page_size})


def get_calendar(start: str = None, end: str = None) -> list:
    params = {}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    return _get("/calendar", params)


def lookup_movie(term: str) -> list:
    return _get("/series/lookup", {"term": term})
