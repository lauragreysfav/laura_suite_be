import httpx
from app.config import settings

STASH_GRAPHQL = f"{settings.stash_url}/graphql"
HEADERS = {}
if settings.stash_api_key:
    HEADERS["ApiKey"] = settings.stash_api_key


def _query(query: str, variables: dict = None) -> dict:
    body = {"query": query, "variables": variables or {}}
    r = httpx.post(STASH_GRAPHQL, json=body, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def status() -> dict:
    q = "{ systemStatus { databasePath databaseSchema } }"
    return _query(q)


def trigger_scan(paths: list[str] = None) -> dict:
    q = """
    mutation MetadataScan($input: ScanMetadataInput!) {
      metadataScan(input: $input)
    }
    """
    variables = {
        "input": {
            "rescan": False,
            "scanGenerateCovers": True,
            "scanGeneratePreviews": True,
            "scanGenerateSprites": True,
            "scanGeneratePhashes": True,
            "scanGenerateImagePhashes": True,
            "scanGenerateThumbnails": True,
            "scanGenerateClipPreviews": True,
        }
    }
    if paths:
        variables["input"]["paths"] = paths
    return _query(q, variables)


def trigger_identify() -> dict:
    q = "mutation { metadataIdentify(input: {}) { queued } }"
    return _query(q)


def stats() -> dict:
    q = "{ stats { scene_count performer_count studio_count scenes_size } }"
    return _query(q)


def find_scenes(query: str = "", page: int = 1, per_page: int = 40, sort: str = "date", direction: str = "DESC") -> dict:
    filter = {"page": page, "per_page": per_page, "sort": sort, "direction": direction}
    if query:
        filter["q"] = query
    q = """
    query FindScenes($filter: FindFilterType!) {
      findScenes(filter: $filter) {
        count
        scenes {
          id
          title
          date
          rating100
          paths { screenshot stream preview }
          files { duration }
          studio { id name image_path }
          performers { id name image_path }
          tags { id name }
        }
      }
    }
    """
    return _query(q, {"filter": filter})


def find_scene(id: str) -> dict:
    q = """
    query FindScene($id: ID!) {
      findScene(id: $id) {
        id
        title
        details
        date
        rating100
        o_counter
        paths { screenshot stream preview }
        files { duration }
        studio { id name image_path }
        performers { id name image_path favorite scene_count }
        tags { id name }
      }
    }
    """
    return _query(q, {"id": id})


def find_performers(query: str = "", page: int = 1, per_page: int = 40) -> dict:
    filter = {"page": page, "per_page": per_page}
    if query:
        filter["q"] = query
    q = """
    query FindPerformers($filter: FindFilterType!) {
      findPerformers(filter: $filter) {
        count
        performers {
          id
          name
          image_path
          favorite
          scene_count
          tags { name }
        }
      }
    }
    """
    return _query(q, {"filter": filter})


def find_performer(id: str) -> dict:
    q = """
    query FindPerformer($id: ID!) {
      findPerformer(id: $id) {
        id
        name
        image_path
        favorite
        scene_count
        details
        tags { name }
        scenes {
          id
          title
          date
          rating100
          paths { screenshot stream }
          studio { name }
        }
      }
    }
    """
    return _query(q, {"id": id})


def find_studios(query: str = "", page: int = 1, per_page: int = 40) -> dict:
    filter = {"page": page, "per_page": per_page}
    if query:
        filter["q"] = query
    q = """
    query FindStudios($filter: FindFilterType!) {
      findStudios(filter: $filter) {
        count
        studios {
          id
          name
          image_path
          scene_count
        }
      }
    }
    """
    return _query(q, {"filter": filter})


def find_studio(id: str) -> dict:
    q = """
    query FindStudio($id: ID!) {
      findStudio(id: $id) {
        id
        name
        image_path
        scene_count
        details
      }
    }
    """
    return _query(q, {"id": id})


def find_scenes_by_studio(studio_id: str, page: int = 1, per_page: int = 100) -> dict:
    filter = {"page": page, "per_page": per_page, "sort": "date", "direction": "DESC"}
    scene_filter = {"studios": {"value": [studio_id], "modifier": "INCLUDES"}}
    q = """
    query FindScenesByStudio($filter: FindFilterType!, $scene_filter: SceneFilterType!) {
      findScenes(filter: $filter, scene_filter: $scene_filter) {
        count
        scenes {
          id
          title
          date
          rating100
          paths { screenshot stream }
          studio { name }
          performers { name }
        }
      }
    }
    """
    return _query(q, {"filter": filter, "scene_filter": scene_filter})
