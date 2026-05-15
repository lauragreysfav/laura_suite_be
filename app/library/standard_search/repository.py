from app.library.common.repository import (
    suggest_index,
    search_index,
    search_by_hashes,
    get_document,
)
from app.library.common.schema import (
    STASHDB_INDEX_PERFORMERS,
    STASHDB_INDEX_STUDIOS,
    STASHDB_INDEX_SCENES,
)


def suggest_performers(prefix: str, size: int = 10) -> list[dict]:
    return suggest_index(STASHDB_INDEX_PERFORMERS, prefix, field="name", size=size)


def suggest_studios(prefix: str, size: int = 10) -> list[dict]:
    return suggest_index(STASHDB_INDEX_STUDIOS, prefix, field="name", size=size)


def suggest_scenes(prefix: str, size: int = 10) -> list[dict]:
    return suggest_index(STASHDB_INDEX_SCENES, prefix, field="title", size=size)


def search_performers(query: str, size: int = 20) -> list[dict]:
    return search_index(STASHDB_INDEX_PERFORMERS, query, fields=["name^3", "aliases^2"], size=size)


def search_studios(query: str, size: int = 20) -> list[dict]:
    return search_index(STASHDB_INDEX_STUDIOS, query, fields=["name^3"], size=size)


def search_scenes(query: str, size: int = 20) -> list[dict]:
    return search_index(STASHDB_INDEX_SCENES, query, fields=["title^3", "details"], size=size)


def get_performer(stashdb_id: str) -> dict | None:
    return get_document(STASHDB_INDEX_PERFORMERS, stashdb_id)


def get_studio(stashdb_id: str) -> dict | None:
    return get_document(STASHDB_INDEX_STUDIOS, stashdb_id)


def get_scene(stashdb_id: str) -> dict | None:
    return get_document(STASHDB_INDEX_SCENES, stashdb_id)


def enrich_by_hashes(info_hashes: list[str]) -> dict[str, dict]:
    return search_by_hashes(STASHDB_INDEX_SCENES, info_hashes)
