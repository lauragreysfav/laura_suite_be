import httpx

STASHDB_URL = "https://stashdb.org/graphql"


def _query(query: str, variables: dict = None) -> dict:
    r = httpx.post(STASHDB_URL, json={"query": query, "variables": variables or {}}, timeout=15)
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
          gender
          urls { url type }
          images { url }
          career_start_year
          career_end_year
        }
      }
    }
    """
    return _query(q, {"input": {"names": query, "page": 1, "per_page": 20}})


def search_studios(query: str):
    q = """
    query SearchStudios($input: StudioQueryInput!) {
      queryStudios(input: $input) {
        count
        studios {
          id
          name
          aliases
          urls { url type }
          images { url }
        }
      }
    }
    """
    return _query(q, {"input": {"name": query, "page": 1, "per_page": 20}})


def get_performer(performer_id: str):
    q = """
    query GetPerformer($id: ID!) {
      findPerformer(id: $id) {
        id
        name
        aliases
        gender
        birthdate
        ethnicity
        country
        eye_color
        hair_color
        height
        measurements
        breast_type
        tattoos { location description }
        piercings { location description }
        urls { url type }
        images { url }
        career_start_year
        career_end_year
      }
    }
    """
    return _query(q, {"id": performer_id})
