import httpx
from app.config import settings

STASHDB_URL = "https://stashdb.org/graphql"


def _query(query: str, variables: dict = None) -> dict:
    headers = {"ApiKey": settings.stashdb_api_key} if settings.stashdb_api_key else {}
    r = httpx.post(STASHDB_URL, json={"query": query, "variables": variables or {}}, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()


def search_performers(query: str):
    q = """
    query SearchPerformers($input: PerformerQueryInput!) {
      queryPerformers(input: $input) {
        count
        performers { 
          id 
          name 
          aliases 
          images { url } 
        }
      }
    }
    """
    return _query(q, {"input": {"names": query, "page": 1, "per_page": 20}})


def find_by_hash(info_hash: str):
    q = """
    query FindByHash($hash: String!) {
      findScenes(scene_filter: { fingerprint: { value: $hash, modifier: EQUALS } }) {
        scenes { 
          id 
          title 
          details 
          images { url } 
          studio { name } 
          performers { name } 
        }
      }
    }
    """
    return _query(q, {"hash": info_hash})


def get_performer(performer_id: str):
    q = """
    query GetPerformer($id: ID!) {
      findPerformer(id: $id) {
        id
        name
        aliases
        gender
        urls { url type }
        images { url }
      }
    }
    """
    return _query(q, {"id": performer_id})
