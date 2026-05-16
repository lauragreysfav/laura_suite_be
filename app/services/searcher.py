import re
import logging
from app.services import prowlarr

logger = logging.getLogger("laura.services.searcher")

QUALITY_TIERS = [
    (r"4320[pP]|8[Kk]|UHD-?2", "8K"),
    (r"2160[pP]|4[Kk]\b|UHD|UltraHD", "4K"),
    (r"1080[pP]|FHD|FullHD", "1080p"),
    (r"720[pP]|HD", "720p"),
    (r"540[pP]|SD", "540p"),
]


def detect_quality(title: str) -> str:
    for pattern, label in QUALITY_TIERS:
        if re.search(pattern, title):
            return label
    return "Unknown"


def rank_torrent(t: dict) -> float:
    seeders = t.get("seeders") or 0
    leechers = t.get("leechers") or 0
    quality = detect_quality(t.get("title", ""))
    q_map = {"8K": 100, "4K": 80, "1080p": 60, "720p": 40, "540p": 20, "Unknown": 0}
    score = q_map.get(quality, 0)
    score += min(seeders, 100) * 0.3
    score += min(leechers, 50) * 0.1
    if t.get("size"):
        try:
            size_gb = float(t["size"]) / (1024 ** 3)
            score += min(size_gb, 50) * 0.2
        except (ValueError, TypeError):
            pass
    return score


def dedup_results(results: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for r in results:
        ih = r.get("infoHash", "")
        if ih and ih not in seen:
            seen.add(ih)
            unique.append(r)
    return unique


def search_prowlarr(query: str, indexers: list[int] = None) -> list[dict]:
    try:
        data = prowlarr.search(query=query, indexer_ids=indexers)
        logger.info("prowlarr_search_ok", extra={"query": query, "results": len(data)})
        return data
    except Exception as e:
        logger.exception("prowlarr_search_error", extra={"query": query, "error": str(e)})
        raise
