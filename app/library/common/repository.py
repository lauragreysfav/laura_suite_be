import logging
from app.services.typesense_client import TypesenseClient

logger = logging.getLogger("laura.library.common.repository")

_client: TypesenseClient | None = None


def get_client() -> TypesenseClient:
    global _client
    if _client is None:
        _client = TypesenseClient()
    return _client


def search_index(index: str, query_text: str, fields: list[str] | None = None, size: int = 20, filters: dict | None = None) -> list[dict]:
    client = get_client()
    filter_by = None
    if filters:
        clauses = [f"{k}:={v}" for k, v in filters.items() if v]
        filter_by = " && ".join(clauses) if clauses else None
    query_by = [f.split("^")[0] for f in (fields or ["name", "title", "aliases", "details"])]
    return client.search(index, query_text or "*", query_by, per_page=size, filters=filter_by)


def suggest_index(index: str, prefix: str, field: str = "name", size: int = 10) -> list[dict]:
    return get_client().search(index, prefix, [field], per_page=size)


def index_document(index: str, doc_id: str, body: dict) -> None:
    get_client().upsert(index, {**body, "id": doc_id})


def bulk_index(index: str, documents: list[dict], id_field: str = "stashdb_id") -> None:
    docs = [{**d, "id": d.get(id_field)} for d in documents if d.get(id_field)]
    get_client().bulk_upsert(index, docs)


def get_document(index: str, doc_id: str) -> dict | None:
    return get_client().get(index, doc_id)


def delete_document(index: str, doc_id: str) -> None:
    get_client().delete(index, doc_id)


def search_by_hashes(index: str, hashes: list[str]) -> dict[str, dict]:
    docs = get_client().search_by_hashes(index, hashes)
    result: dict[str, dict] = {}
    for d in docs:
        fps = d.get("fingerprints") or []
        for fp in fps:
            val = str(fp).lower()
            if val in [h.lower() for h in hashes]:
                result[val] = d
    return result
