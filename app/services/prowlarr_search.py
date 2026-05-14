import logging
import asyncio
from app.services import prowlarr
from app.services.searcher import detect_quality

logger = logging.getLogger("laura.services.prowlarr_search")

JAV_INDEXER_IDS = {4, 3, 47, 27}
WESTERN_INDEXER_IDS = {17, 8, 21, 9, 11, 10, 12, 16, 15, 23, 7, 18, 14, 19, 13, 1, 2, 5, 6}


def classify_xxx_type(indexer_id: int, indexer_name: str = "") -> str:
    name_lower = indexer_name.lower()
    if indexer_id in JAV_INDEXER_IDS:
        return "jav"
    if any(kw in name_lower for kw in ["jav", "sukebei", "nyaa"]):
        return "jav"
    if indexer_id in WESTERN_INDEXER_IDS:
        return "western"
    return "both"


def dedup_results(results: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for r in results:
        ih = r.get("infoHash", "")
        if ih and ih not in seen:
            seen.add(ih)
            unique.append(r)
    return unique


def rank_results(results: list[dict]) -> list[dict]:
    QUALITY_MAP = {"8K": 100, "4K": 80, "1080p": 60, "720p": 40, "540p": 20, "Unknown": 0}

    def score(r):
        quality = detect_quality(r.get("title", ""))
        q_score = QUALITY_MAP.get(quality, 0)
        seeders = r.get("seeders") or 0
        leechers = r.get("leechers") or 0
        return q_score + min(seeders, 200) * 0.3 + min(leechers, 50) * 0.1

    return sorted(results, key=score, reverse=True)


async def stream_search(
    query: str,
    categories: list[int] | None = None,
    indexer_ids: list[int] | None = None,
    xxx_type: str = "both",
    search_type: str = "search",
) -> list[dict]:
    results = await asyncio.to_thread(
        prowlarr.search,
        query=query,
        categories=categories,
        indexer_ids=indexer_ids,
        search_type=search_type,
    )

    if not results:
        return []

    unique = dedup_results(results)

    if categories and any(6000 <= c < 7000 for c in (categories or [])):
        if xxx_type != "both":
            unique = [
                r for r in unique
                if classify_xxx_type(r.get("indexerId", 0), r.get("indexer", "")) == xxx_type
            ]

    ranked = rank_results(unique)

    return ranked[:200]
