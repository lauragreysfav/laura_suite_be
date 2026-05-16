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


def trigger_identify(
    stash_box_endpoint: str = "https://stashdb.org/graphql",
    paths: list[str] = None,
    set_cover_image: bool = True,
    include_male_performers: bool = True,
    skip_single_name_performers: bool = False,
    set_organized: bool = False,
) -> dict:
    q = """
    mutation MetadataIdentify($input: IdentifyMetadataInput!) {
      metadataIdentify(input: $input)
    }
    """
    sources = [{
        "source": {"stash_box_endpoint": stash_box_endpoint},
        "options": {
            "setCoverImage": set_cover_image,
            "includeMalePerformers": include_male_performers,
            "skipSingleNamePerformers": skip_single_name_performers,
        },
    }]
    variables = {
        "input": {
            "sources": sources,
            "options": {"setCoverImage": set_cover_image, "setOrganized": set_organized},
        }
    }
    if paths:
        variables["input"]["paths"] = paths
    return _query(q, variables)


def trigger_generate(
    scene_ids: list[int] = None,
    previews: bool = True,
    sprites: bool = True,
    phashes: bool = True,
    markers: bool = True,
    marker_screenshots: bool = True,
    covers: bool = True,
    image_thumbnails: bool = True,
    transcodes: bool = False,
    clip_previews: bool = True,
    image_previews: bool = True,
    image_phashes: bool = True,
    interactive_heatmaps: bool = False,
    overwrite: bool = False,
) -> dict:
    q = """
    mutation MetadataGenerate($input: GenerateMetadataInput!) {
      metadataGenerate(input: $input)
    }
    """
    variables = {
        "input": {
            "previews": previews,
            "sprites": sprites,
            "phashes": phashes,
            "markers": markers,
            "markerScreenshots": marker_screenshots,
            "covers": covers,
            "imageThumbnails": image_thumbnails,
            "transcodes": transcodes,
            "clipPreviews": clip_previews,
            "imagePreviews": image_previews,
            "imagePhashes": image_phashes,
            "interactiveHeatmapsSpeeds": interactive_heatmaps,
            "overwrite": overwrite,
        }
    }
    if scene_ids:
        variables["input"]["sceneIDs"] = scene_ids
    return _query(q, variables)


def trigger_auto_tag(paths: list[str] = None) -> dict:
    q = """
    mutation MetadataAutoTag($input: AutoTagMetadataInput!) {
      metadataAutoTag(input: $input)
    }
    """
    variables = {"input": {}}
    if paths:
        variables["input"]["paths"] = paths
    return _query(q, variables)


def job_queue() -> list[dict]:
    q = """
    query {
      jobQueue {
        id
        status
        description
        subTasks
      }
    }
    """
    res = _query(q)
    return (res.get("data") or {}).get("jobQueue") or []


def wait_for_jobs(job_id_prefix: str = None, timeout: int = 300, poll_interval: int = 5) -> bool:
    """Poll stash job queue until no running jobs match the prefix."""
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        jobs = job_queue()
        running = [j for j in jobs if j.get("status") in ("RUNNING", "READY")]
        if not running:
            return True
        time.sleep(poll_interval)
    return False


def overview() -> dict:
    """Return combined dashboard data: stats, job queue, and scene counts by status."""
    q = """
    query Overview {
      stats { scene_count performer_count studio_count scenes_size }
      jobQueue { id status description subTasks }
      scenes_with_studio: findScenes(scene_filter: { studios: { modifier: NOT_NULL } }) { count }
      scenes_without_studio: findScenes(scene_filter: { studios: { modifier: IS_NULL } }) { count }
      scenes_organized: findScenes(scene_filter: { organized: true }) { count }
      scenes_with_tags: findScenes(scene_filter: { tags: { modifier: NOT_NULL } }) { count }
      scenes_without_tags: findScenes(scene_filter: { tags: { modifier: IS_NULL } }) { count }
    }
    """
    return _query(q)


def find_scene_by_hash(info_hash: str) -> dict | None:
    q = """
    query FindSceneByHash($hash: String!) {
      findScenes(filter: {q: $hash}) {
        scenes {
          id
          title
          files { path }
        }
      }
    }
    """
    res = _query(q, {"hash": info_hash})
    scenes = res.get("data", {}).get("findScenes", {}).get("scenes", [])
    if scenes:
        return scenes[0]
    return None


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


def check_scene_exists(info_hash: str = None, title: str = None) -> dict:
    # First try hash if available
    if info_hash:
        q = """
        query FindScenesByHash($hash: String!) {
          findScenes(filter: {q: $hash}) {
            scenes { id files { path } }
          }
        }
        """
        res = _query(q, {"hash": info_hash})
        scenes = res.get("data", {}).get("findScenes", {}).get("scenes", [])
        if scenes:
            return {"exists": True, "path": scenes[0]["files"][0]["path"]}

    # Fallback to title search
    if title:
        res = find_scenes(query=title, per_page=1)
        scenes = res.get("data", {}).get("findScenes", {}).get("scenes", [])
        if scenes:
            return {"exists": True, "path": scenes[0]["files"][0]["path"]}

    return {"exists": False, "path": None}
