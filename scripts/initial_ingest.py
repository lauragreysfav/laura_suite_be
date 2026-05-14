"""
Async StashDB ingestion pipeline.

Usage:
    docker compose exec laura-backend python scripts/initial_ingest.py [--resume]

Migrates all StashDB data (performers, studios, scenes >= 2000) to
PostgreSQL + Typesense using async parallel requests with checkpoint/resume.

Requires STASHDB_API_KEY in .env (stashdb.org -> Settings -> ApiKeys -> Create).
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from scripts.ingest.pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("initial_ingest")


def main():
    parser = argparse.ArgumentParser(description="StashDB ingestion pipeline")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    args = parser.parse_args()

    if not settings.stashdb_api_key:
        logger.error("STASHDB_API_KEY not set -- add it to .env")
        sys.exit(1)

    asyncio.run(run_pipeline(resume=args.resume))


if __name__ == "__main__":
    main()
