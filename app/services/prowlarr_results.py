import re

from app.services.magnet import build_magnet

_IH_RE = re.compile(r"^[a-fA-F0-9]{40}$")


def _clean_hash(value: object) -> str:
    text = str(value or "").strip()
    return text if _IH_RE.fullmatch(text) else ""


def normalize_result(item: dict) -> dict:
    data = dict(item)

    title = data.get("title") or ""
    direct_magnet = data.get("magnetUrl") or data.get("magnetUri") or ""
    download_url = data.get("downloadUrl") or ""
    info_hash = _clean_hash(data.get("infoHash")) or _clean_hash(data.get("downloadId"))
    magnet_source = "none"

    if direct_magnet:
        magnet_source = "direct"
    elif info_hash:
        direct_magnet = build_magnet(info_hash, title)
        magnet_source = "synthesized"
    elif download_url:
        magnet_source = "torrent-file"

    data["infoHash"] = info_hash or data.get("infoHash") or data.get("downloadId") or ""
    data["magnetUrl"] = direct_magnet
    data["downloadUrl"] = download_url
    data["magnetSource"] = magnet_source
    data["linkType"] = magnet_source
    data["canSubmitToTorbox"] = magnet_source in {"direct", "synthesized", "torrent-file"}
    return data


def normalize_results(items: list[dict]) -> list[dict]:
    return [normalize_result(item) for item in items]
