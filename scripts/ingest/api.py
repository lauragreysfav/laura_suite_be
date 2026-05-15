import logging

import httpx

from scripts.ingest.rate_limiter import TokenBucket

logger = logging.getLogger("ingest.api")

STASHDB_URL = "https://stashdb.org/graphql"
PER_PAGE = 100

PERFORMER_QUERY = """
query SearchPerformers($input: PerformerQueryInput!) {
  queryPerformers(input: $input) {
    count
    performers {
      id name aliases gender
      images { url }
      scene_count career_end_year birth_date
      urls { url type }
      studios { studio { id name } }
    }
  }
}
"""

STUDIO_QUERY = """
query GetStudio($id: ID!) {
  findStudio(id: $id) {
    id name images { url } parent { id name } urls { url type }
  }
}
"""

SCENES_QUERY = """
query StudioScenes($input: SceneQueryInput!) {
  queryScenes(input: $input) {
    count
    scenes {
      id title details release_date duration
      images { url }
      studio { id name }
      performers { performer { id name } }
      fingerprints { algorithm hash duration }
      tags { name }
    }
  }
}
"""


class StashDBClient:
    def __init__(self, api_key: str, rate_limiter: TokenBucket | None = None) -> None:
        self.headers = {"ApiKey": api_key} if api_key else {}
        self.rate_limiter = rate_limiter or TokenBucket(capacity=5, rate=1.0)

    async def _query(self, query: str, variables: dict) -> dict:
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                STASHDB_URL,
                json={"query": query, "variables": variables},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def fetch_performers_page(self, name: str, page: int = 1) -> tuple[list[dict], int]:
        try:
            data = await self._query(PERFORMER_QUERY, {
                "input": {"names": name, "page": page, "per_page": PER_PAGE}
            })
            d = data.get("data") or {}
            qp = d.get("queryPerformers") or {}
            return qp.get("performers", []), qp.get("count", 0)
        except Exception as e:
            logger.warning("performers_fetch_error", extra={"prefix": name, "page": page, "error": str(e)})
            return [], 0

    async def fetch_studio(self, studio_id: str) -> dict | None:
        try:
            data = await self._query(STUDIO_QUERY, {"id": studio_id})
            return (data.get("data") or {}).get("findStudio")
        except Exception as e:
            logger.warning("studio_fetch_error", extra={"id": studio_id, "error": str(e)})
            return None

    async def fetch_scenes_by_performer(self, performer_id: str, page: int = 1) -> tuple[list[dict], int]:
        try:
            data = await self._query(SCENES_QUERY, {
                "input": {
                    "performers": {"value": [performer_id], "modifier": "INCLUDES"},
                    "page": page,
                    "per_page": PER_PAGE,
                }
            })
            d = data.get("data") or {}
            qs = d.get("queryScenes") or {}
            return qs.get("scenes", []), qs.get("count", 0)
        except Exception as e:
            logger.warning("performer_scenes_fetch_error", extra={"performer": performer_id, "page": page, "error": str(e)})
            return [], 0
