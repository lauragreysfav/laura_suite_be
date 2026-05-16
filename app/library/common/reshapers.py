import logging

logger = logging.getLogger("laura.library.common.reshapers")

def reshape_scene(sc: dict) -> dict:
    """
    Reshapes a scene object to the standard shape expected by the frontend.
    Handles both raw GraphQL output and flattened search results.
    """
    if not sc:
        return {}

    # Handle images
    imgs = sc.get("images") or []
    # GraphQL uses list of dicts with 'url'
    if imgs and isinstance(imgs[0], dict):
        screenshot = imgs[0].get("url")
    # Search results might just be list of strings
    elif imgs and isinstance(imgs[0], str):
        screenshot = imgs[0]
    else:
        screenshot = None

    # Handle studio
    studio_raw = sc.get("studio") or {}
    studio_name = sc.get("studio_name") or studio_raw.get("name")
    studio_id = sc.get("studio_id") or studio_raw.get("id")

    # Handle performers
    performers_raw = sc.get("performers") or []
    performers = []
    
    # Performer names might be in a separate list (search result)
    performer_names = sc.get("performer_names") or []
    performer_ids = sc.get("performer_ids") or []

    if performers_raw:
        for p in performers_raw:
            # GraphQL structure: { "performer": { "id": "...", "name": "..." } }
            if isinstance(p, dict) and p.get("performer"):
                perf = p.get("performer")
                performers.append({"id": perf.get("id"), "name": perf.get("name")})
            # Simplified structure: { "id": "...", "name": "..." }
            elif isinstance(p, dict) and p.get("id"):
                performers.append({"id": p.get("id"), "name": p.get("name")})
            # Just a string (name)
            elif isinstance(p, str):
                performers.append({"name": p})
    
    # Fallback to lists if performers_raw was empty
    if not performers and (performer_names or performer_ids):
        for i, name in enumerate(performer_names):
            p_id = performer_ids[i] if i < len(performer_ids) else None
            performers.append({"id": p_id, "name": name})

    # Handle tags
    tags_raw = sc.get("tags") or []
    tags = []
    for t in tags_raw:
        if isinstance(t, dict):
            tags.append({"name": t.get("name")})
        elif isinstance(t, str):
            tags.append({"name": t})

    # Handle duration
    duration = sc.get("duration")
    if not duration and sc.get("file"):
        duration = sc.get("file", {}).get("duration")

    return {
        "id": sc.get("id") or sc.get("stashdb_id"),
        "title": sc.get("title", ""),
        "date": sc.get("release_date") or sc.get("date"),
        "details": sc.get("details"),
        "paths": {"screenshot": screenshot} if screenshot else None,
        "file": {"duration": duration} if duration else None,
        "studio": {"id": studio_id, "name": studio_name} if studio_name else None,
        "performers": performers,
        "tags": tags,
    }

def reshape_performer(p: dict) -> dict:
    if not p:
        return {}
    imgs = p.get("images") or []
    image_url = p.get("image_url")
    if not image_url and imgs:
        image_url = imgs[0].get("url") if isinstance(imgs[0], dict) else imgs[0]
        
    return {
        "id": p.get("id") or p.get("stashdb_id"),
        "name": p.get("name", ""),
        "image_path": image_url,
        "images": [img.get("url") if isinstance(img, dict) else img for img in imgs] if imgs else [],
        "scene_count": p.get("scene_count", 0),
        "aliases": p.get("aliases") or [],
        "gender": p.get("gender"),
        "birthdate": p.get("birth_date") or p.get("birthdate"),
        "career_start_year": p.get("career_start_year"),
        "career_end_year": p.get("career_end_year"),
        "details": p.get("details"),
        "ethnicity": p.get("ethnicity"),
        "country": p.get("country"),
        "eye_color": p.get("eye_color"),
        "hair_color": p.get("hair_color"),
        "height": p.get("height"),
        "measurements": p.get("measurements"),
        "urls": p.get("urls") or [],
    }

def reshape_studio(s: dict) -> dict:
    if not s:
        return {}
    imgs = s.get("images") or []
    image_url = s.get("image_url")
    if not image_url and imgs:
        image_url = imgs[0].get("url") if isinstance(imgs[0], dict) else imgs[0]

    return {
        "id": s.get("id") or s.get("stashdb_id"),
        "name": s.get("name", ""),
        "image_path": image_url,
        "images": [img.get("url") if isinstance(img, dict) else img for img in imgs] if imgs else [],
        "scene_count": s.get("scene_count", 0),
        "details": s.get("details"),
        "parent_studio": s.get("parent") or s.get("parent_studio"),
        "urls": s.get("urls") or [],
    }
