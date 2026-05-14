import urllib.parse
import typesense
from app.config import settings


def build_search_params(q: str, query_by: list[str], per_page: int = 20, filters: str | None = None) -> dict:
    params = {"q": q, "query_by": ",".join(query_by), "per_page": per_page}
    if filters:
        params["filter_by"] = filters
    return params


def build_hash_filter(hashes: list[str]) -> str:
    return f"fingerprints:=[{','.join(hashes)}]"


class TypesenseClient:
    def __init__(self) -> None:
        parsed = urllib.parse.urlparse(settings.typesense_host)
        host = parsed.hostname or "typesense"
        port = parsed.port or 8108
        protocol = parsed.scheme or "http"
        self.client = typesense.Client({
            "nodes": [{"host": host, "port": port, "protocol": protocol}],
            "api_key": settings.typesense_api_key,
            "connection_timeout_seconds": settings.typesense_timeout,
        })

    def ensure_collections(self, schemas: list[dict]) -> None:
        existing = {c["name"] for c in self.client.collections.retrieve()}
        for schema in schemas:
            if schema["name"] not in existing:
                self.client.collections.create(schema)

    def upsert(self, collection: str, doc: dict) -> None:
        self.client.collections[collection].documents.upsert(doc)

    def bulk_upsert(self, collection: str, docs: list[dict]) -> None:
        if docs:
            self.client.collections[collection].documents.import_(docs, {"action": "upsert"})

    def search(self, collection: str, q: str, query_by: list[str], per_page: int = 20, filters: str | None = None) -> list[dict]:
        params = build_search_params(q, query_by, per_page, filters)
        resp = self.client.collections[collection].documents.search(params)
        return [h["document"] for h in resp.get("hits", [])]

    def get(self, collection: str, doc_id: str) -> dict | None:
        try:
            return self.client.collections[collection].documents[doc_id].retrieve()
        except typesense.exceptions.ObjectNotFound:
            return None

    def delete(self, collection: str, doc_id: str) -> None:
        try:
            self.client.collections[collection].documents[doc_id].delete()
        except typesense.exceptions.ObjectNotFound:
            pass

    def search_by_hashes(self, collection: str, hashes: list[str], query_by: list[str] | None = None) -> list[dict]:
        if not hashes:
            return []
        qb = query_by or ["title"]
        params = {"q": "*", "query_by": ",".join(qb), "filter_by": build_hash_filter(hashes), "per_page": len(hashes)}
        resp = self.client.collections[collection].documents.search(params)
        return [h["document"] for h in resp.get("hits", [])]
