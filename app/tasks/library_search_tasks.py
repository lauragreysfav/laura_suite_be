import logging
import time
from app.celery_app import celery_app
from app.library.common.repository import ensure_indices
from app.library.standard_search.service import suggest, _cache_live_results

logger = logging.getLogger("laura.tasks.library_search")


@celery_app.task(name="library_search.prime_suggest_cache")
def prime_suggest_cache():
    """Prime the OpenSearch cache by searching common terms.
    Runs every 6h to keep frequently-accessed entities warm."""
    ensure_indices()
    common_terms = ["a", "ma", "mi", "mo", "st"]
    for term in common_terms:
        try:
            for st in ("performer", "studio", "scene"):
                suggest(term, st)
        except Exception as e:
            logger.debug("prime_skip", extra={"term": term, "error": str(e)})
        time.sleep(0.2)
    logger.info("suggest_cache_primed")
