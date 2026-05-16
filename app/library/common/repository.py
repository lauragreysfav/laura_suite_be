import json
import logging
from app.library.common.schema import (
    STASHDB_INDEX_PERFORMERS,
    STASHDB_INDEX_STUDIOS,
    STASHDB_INDEX_SCENES,
)
from app.services.typesense_client import TypesenseClient
from app.database import SessionLocal
from app.models import StashDBPerformerCache, StashDBStudioCache, StashDBSceneCache

logger = logging.getLogger("laura.library.common.repository")

_client: TypesenseClient | None = None


def _get_model_class(index: str):
    if index == STASHDB_INDEX_PERFORMERS:
        return StashDBPerformerCache
    elif index == STASHDB_INDEX_STUDIOS:
        return StashDBStudioCache
    elif index == STASHDB_INDEX_SCENES:
        return StashDBSceneCache
    return None


def ensure_indices() -> None:
    from app.library.common.typesense_schema import SCHEMAS
    get_client().ensure_collections(SCHEMAS)


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
    hits = client.search(index, query_text or "*", query_by, per_page=size, filters=filter_by)
    
    if not hits:
        return []
        
    model_class = _get_model_class(index)
    if not model_class:
        return hits
        
    doc_ids = [hit.get("stashdb_id") or hit.get("id") for hit in hits]
    
    db = SessionLocal()
    try:
        records = db.query(model_class).filter(model_class.stashdb_id.in_(doc_ids)).all()
        # Map by id
        record_map = {}
        for r in records:
            record_map[r.stashdb_id] = r.raw_json
            
        # Preserve search order
        hydrated_results = []
        for hit in hits:
            doc_id = hit.get("stashdb_id") or hit.get("id")
            if doc_id in record_map:
                hydrated_results.append(record_map[doc_id])
            else:
                hydrated_results.append(hit)
                
        return hydrated_results
    finally:
        db.close()


def suggest_index(index: str, prefix: str, field: str = "name", size: int = 10) -> list[dict]:
    return get_client().search(index, prefix, [field], per_page=size)


def index_document(index: str, doc_id: str, body: dict) -> None:
    get_client().upsert(index, {**body, "id": doc_id})


def bulk_index(index: str, documents: list[dict], id_field: str = "stashdb_id") -> None:
    docs = [{**d, "id": d.get(id_field)} for d in documents if d.get(id_field)]
    get_client().bulk_upsert(index, docs)


def get_document(index: str, doc_id: str) -> dict | None:
    model_class = _get_model_class(index)
    if not model_class:
        return get_client().get(index, doc_id)
        
    db = SessionLocal()
    try:
        record = db.query(model_class).filter(model_class.stashdb_id == doc_id).first()
        if record and record.raw_json:
            # Return the exact StashDB representation cached in PostgreSQL
            if isinstance(record.raw_json, str):
                return json.loads(record.raw_json)
            return record.raw_json
            
        # Fallback to Typesense if not in DB
        return get_client().get(index, doc_id)
    finally:
        db.close()


def delete_document(index: str, doc_id: str) -> None:
    get_client().delete(index, doc_id)


def search_by_hashes(index: str, hashes: list[str]) -> dict[str, dict]:
    if not hashes:
        return {}
        
    client = get_client()
    docs = client.search_by_hashes(index, hashes)
    
    result: dict[str, dict] = {}
    model_class = _get_model_class(index)
    
    db = SessionLocal()
    try:
        doc_ids = [d.get("stashdb_id") or d.get("id") for d in docs]
        records = []
        if model_class and doc_ids:
            records = db.query(model_class).filter(model_class.stashdb_id.in_(doc_ids)).all()
            
        record_map = {}
        for r in records:
            record_map[r.stashdb_id] = r.raw_json

        for d in docs:
            doc_id = d.get("stashdb_id") or d.get("id")
            full_doc = record_map.get(doc_id, d)
            
            fps = d.get("fingerprints") or []
            for fp in fps:
                # Handle both simple string fingerprints (Typesense) and complex dicts (StashDB JSON)
                val = ""
                if isinstance(fp, dict):
                    val = str(fp.get("hash") or "").lower()
                else:
                    val = str(fp).lower()
                    
                if val and val in [h.lower() for h in hashes]:
                    result[val] = full_doc
                    
        return result
    finally:
        db.close()
