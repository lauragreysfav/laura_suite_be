import logging
import httpx
from pathlib import Path
from app.config import settings

logger = logging.getLogger("laura.services.torbox")

BASE = "https://api.torbox.app/v1/api"
HEADERS = {"Authorization": f"Bearer {settings.torbox_api_key}"}

# Global timeout for all TorBox operations (10 minutes)
TIMEOUT = 600

def list_torrents(bypass_cache: bool = False) -> dict:
    params = {}
    if bypass_cache:
        params["bypass_cache"] = "true"
    r = httpx.get(f"{BASE}/torrents/mylist", headers=HEADERS, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def create_torrent(magnet: str, seed: int = 1) -> dict:
    data = {"magnet": magnet, "seed": str(seed)}
    r = httpx.post(f"{BASE}/torrents/createtorrent", headers=HEADERS, data=data, timeout=TIMEOUT)
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(f"torbox_create_error: status={r.status_code}, body={r.text}")
        raise Exception(f"TorBox API Error: {r.text}")
    return r.json()


def add_magnet(magnet: str, seed: int = 1) -> dict:
    return create_torrent(magnet, seed)


def create_torrent_from_file(content: bytes, filename: str, seed: int = 1, name: str = "") -> dict:
    data = {"seed": str(seed)}
    if name:
        data["name"] = name
    files = {"file": (filename, content, "application/x-bittorrent")}
    r = httpx.post(f"{BASE}/torrents/createtorrent", headers=HEADERS, data=data, files=files, timeout=TIMEOUT)
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(f"torbox_upload_error: status={r.status_code}, body={r.text}")
        raise Exception(f"TorBox Upload Error: {r.text}")
    return r.json()


def create_torrent_from_download_url(download_url: str, seed: int = 1, name: str = "") -> dict:
    file_resp = httpx.get(download_url, timeout=TIMEOUT, follow_redirects=True)
    file_resp.raise_for_status()
    filename = Path(download_url.split("?")[0]).name or "download.torrent"
    if not filename.endswith(".torrent"):
        filename = f"{filename}.torrent"
    return create_torrent_from_file(file_resp.content, filename, seed=seed, name=name)


def control_torrent(torrent_id: str, operation: str = "delete") -> dict:
    data = {"torrent_id": int(torrent_id), "operation": operation}
    headers = {**HEADERS, "Content-Type": "application/json"}
    r = httpx.post(f"{BASE}/torrents/controltorrent", headers=headers, json=data, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def check_cache(hashes: list[str]) -> dict:
    data = {"hash": ",".join(hashes)}
    r = httpx.post(f"{BASE}/torrents/checkcached", headers=HEADERS, data=data, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_user_info() -> dict:
    r = httpx.get(f"{BASE}/user/me", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def refresh_webdav() -> bool:
    try:
        auth = (settings.torbox_webdav_user, settings.torbox_webdav_pass)
        r = httpx.get("https://webdav.torbox.app/refresh", auth=auth, timeout=TIMEOUT, follow_redirects=True)
        ok = r.status_code == 200
        if not ok:
            logger.warning("webdav_refresh_failed", extra={"status": r.status_code, "url": str(r.url)})
        return ok
    except httpx.HTTPError as e:
        logger.error("webdav_refresh_error", extra={"error": str(e), "error_type": type(e).__name__})
        return False


def get_torrent_info(torrent_id: str) -> dict:
    r = httpx.get(f"{BASE}/torrents/mylist", headers=HEADERS, timeout=TIMEOUT)
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
