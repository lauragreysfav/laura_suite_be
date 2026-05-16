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
    # Group results by infoHash
    groups: dict[str, list[dict]] = {}
    no_hash_results = []

    for r in results:
        ih = r.get("infoHash", "").lower()
        if not ih:
            no_hash_results.append(r)
            continue
        if ih not in groups:
            groups[ih] = []
        groups[ih].append(r)

    unique = []
    for ih, group in groups.items():
        # Sort each group by seeders (highest first) to find the best primary source
        group.sort(key=lambda x: x.get("seeders") or 0, reverse=True)
        primary = group[0]
        
        # Attach all other sources to the primary so the user can see them
        if len(group) > 1:
            primary["alternateSources"] = [
                {
                    "indexer": r.get("indexer"),
                    "seeders": r.get("seeders") or 0,
                    "leechers": r.get("leechers") or 0
                }
                for r in group[1:]
            ]
        else:
            primary["alternateSources"] = []
            
        unique.append(primary)
        
    # Add items that didn't have hashes back in (keep them all)
    return unique + no_hash_results


def rank_results(results: list[dict]) -> list[dict]:
    QUALITY_MAP = {"8K": 100, "4K": 80, "1080p": 60, "720p": 40, "540p": 20, "Unknown": 0}

    def score(r):
        quality = detect_quality(r.get("title", ""))
        q_score = QUALITY_MAP.get(quality, 0)
        seeders = r.get("seeders") or 0
        leechers = r.get("leechers") or 0
        
        # PENALTY: 0 seeders makes a file very low priority regardless of quality
        if seeders == 0:
            return -1000 + q_score
            
        # WEIGHTING: 1 seeder is worth a lot; high seeder counts (up to 500) give diminishing returns
        # Resolution (q_score) is the secondary tie-breaker
        return (min(seeders, 500) * 10) + q_score + min(leechers, 50) * 0.1

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

    return ranked
