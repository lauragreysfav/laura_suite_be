import logging
import httpx
from app.config import settings

logger = logging.getLogger("laura.services.torbox")

BASE = "https://api.torbox.app/v1/api"
HEADERS = {"Authorization": f"Bearer {settings.torbox_api_key}"}


def list_torrents(bypass_cache: bool = False) -> dict:
    params = {}
    if bypass_cache:
        params["bypass_cache"] = "true"
    r = httpx.get(f"{BASE}/torrents/mylist", headers=HEADERS, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def create_torrent(magnet: str, seed: int = 1) -> dict:
    data = {"magnet": magnet, "seed": str(seed)}
    r = httpx.post(f"{BASE}/torrents/createtorrent", headers=HEADERS, data=data, timeout=10)
    r.raise_for_status()
    return r.json()


def control_torrent(torrent_id: str, operation: str = "delete") -> dict:
    data = {"torrent_id": torrent_id, "operation": operation}
    r = httpx.post(f"{BASE}/torrents/controltorrent", headers=HEADERS, data=data, timeout=10)
    r.raise_for_status()
    return r.json()


def check_cache(hashes: list[str]) -> dict:
    data = {"hash": ",".join(hashes)}
    r = httpx.post(f"{BASE}/torrents/checkcached", headers=HEADERS, data=data, timeout=10)
    r.raise_for_status()
    return r.json()


def get_user_info() -> dict:
    r = httpx.get(f"{BASE}/user/me", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def refresh_webdav() -> bool:
    try:
        auth = (settings.torbox_webdav_user, settings.torbox_webdav_pass)
        r = httpx.get("https://webdav.torbox.app/refresh", auth=auth, timeout=10, follow_redirects=True)
        ok = r.status_code == 200
        if not ok:
            logger.warning("webdav_refresh_failed", extra={"status": r.status_code, "url": str(r.url)})
        return ok
    except httpx.HTTPError as e:
        logger.error("webdav_refresh_error", extra={"error": str(e), "error_type": type(e).__name__})
        return False


def get_torrent_info(torrent_id: str) -> dict:
    r = httpx.get(f"{BASE}/torrents/mylist", headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()
    for torrent in data.get("data", []):
        if str(torrent.get("id")) == torrent_id:
            return torrent
    return {}


def get_stream_url(file_id: str) -> str:
    return f"https://api.torbox.app/v1/api/torrents/files/{file_id}/download?token={settings.torbox_api_key}"


def get_torrent_files(torrent_id: str) -> list[dict]:
    info = get_torrent_info(torrent_id)
    return info.get("files", [])
