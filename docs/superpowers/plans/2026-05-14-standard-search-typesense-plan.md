# Standard Search + PG/Typesense Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Standard Search fixes (auth, NSFW defaults, dynamic categories, history, TorBox magnet reliability) while migrating StashDB cache/search from OpenSearch to PostgreSQL + Typesense with staged cutover.

**Architecture:** PostgreSQL stores full StashDB records (`raw_json`) as the primary cache; Typesense provides search/suggest. Standard Search uses Prowlarr results and enriches via Typesense (with live StashDB fallback). Authentication is required globally for API access.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Typesense (Python client), Supabase auth, React + Vite.

---

## File Structure (planned changes)

**Backend**
- Create: `app/services/typesense_client.py` (Typesense connection + search helpers)
- Create: `app/services/magnet.py` (magnet fallback builder)
- Create: `app/library/common/typesense_schema.py` (Typesense collection schemas)
- Modify: `app/config.py` (Typesense + ingest rate-limit settings)
- Modify: `requirements.txt` (Typesense client)
- Modify: `app/models/__init__.py` (new/extended cache tables + history)
- Create: `alembic/versions/20260514_add_stashdb_cache_and_history.py`
- Modify: `app/library/common/repository.py` (Typesense-backed search)
- Modify: `app/library/common/service.py` (initialize Typesense collections)
- Modify: `scripts/initial_ingest.py` (PG + Typesense ingest, filters, rate limit)
- Modify: `app/library/standard_search/service.py` (PG cache + Typesense; live fallback)
- Modify: `app/library/standard_search/api.py` (WS auth + history updates)
- Modify: `app/auth/dependencies.py` (token verification helper for WS)
- Modify: `app/api/v1/stashdb_search.py` (PG → Typesense → live fallback)
- Modify: `app/api/v1/torrents.py` (magnet fallback on batch add)
- Modify: `app/main.py` (global auth dependency)
- Modify: `docker-compose.yml` (Typesense service; remove OpenSearch)

**Frontend**
- Modify: `src/api/client.ts` (auth headers by default, WS token)
- Modify: `src/App.tsx` + `src/components/ProtectedRoute.tsx` (global route protection)
- Modify: `src/pages/StandardSearch.tsx` (dynamic categories, history panel, blur, details)
- Modify: `src/types/index.ts` (history + enriched scene id)

---

### Task 1: Typesense config + client (with tests)

**Files:**
- Modify: `app/config.py`
- Modify: `requirements.txt`
- Create: `app/services/typesense_client.py`
- Create: `tests/test_typesense_client.py`

- [ ] **Step 1: Write failing tests for Typesense query building**

```python
# tests/test_typesense_client.py
from unittest.mock import MagicMock
from app.services.typesense_client import build_hash_filter, build_search_params

def test_build_hash_filter():
    assert build_hash_filter(["aaa", "bbb"]) == "fingerprints:=[aaa,bbb]"

def test_build_search_params():
    params = build_search_params("alice", ["name", "aliases"], per_page=5, filters="gender:=female")
    assert params["q"] == "alice"
    assert params["query_by"] == "name,aliases"
    assert params["per_page"] == 5
    assert params["filter_by"] == "gender:=female"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_typesense_client.py -v`  
Expected: FAIL (module/function not found).

- [ ] **Step 3: Add Typesense settings**

```python
# app/config.py (Settings)
typesense_host: str = "http://typesense:8108"
typesense_api_key: str = ""
typesense_timeout: int = 5
stashdb_rate_limit_seconds: float = 1.0
```

- [ ] **Step 4: Add Typesense client implementation**

```python
# app/services/typesense_client.py
from typing import Any
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
        self.client = typesense.Client({
            "nodes": [{"host": settings.typesense_host.replace("http://", "").replace("https://", "").split(":")[0],
                       "port": int(settings.typesense_host.split(":")[-1]),
                       "protocol": "http"}],
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

    def search_by_hashes(self, collection: str, hashes: list[str]) -> list[dict]:
        if not hashes:
            return []
        params = {"q": "*", "query_by": "title", "filter_by": build_hash_filter(hashes), "per_page": len(hashes)}
        resp = self.client.collections[collection].documents.search(params)
        return [h["document"] for h in resp.get("hits", [])]
```

- [ ] **Step 5: Add Typesense dependency**

```text
# requirements.txt
typesense==0.21.0
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_typesense_client.py -v`  
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add app/config.py app/services/typesense_client.py requirements.txt tests/test_typesense_client.py
git commit -m "feat: add typesense client and config"
```

---

### Task 2: Cache models + history models + Alembic migration

**Files:**
- Modify: `app/models/__init__.py`
- Create: `alembic/versions/20260514_add_stashdb_cache_and_history.py`
- Create: `tests/test_models_stashdb_cache.py`

- [ ] **Step 1: Write failing model tests**

```python
# tests/test_models_stashdb_cache.py
from app.models import StashDBPerformerCache, StashDBStudioCache

def test_performer_cache_has_new_fields():
    assert hasattr(StashDBPerformerCache, "gender")
    assert hasattr(StashDBPerformerCache, "birthdate")
    assert hasattr(StashDBPerformerCache, "urls")

def test_studio_cache_has_urls():
    assert hasattr(StashDBStudioCache, "urls")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models_stashdb_cache.py -v`  
Expected: FAIL (attributes missing).

- [ ] **Step 3: Extend models + add new tables**

```python
# app/models/__init__.py
class StashDBPerformerCache(Base):
    __tablename__ = "stashdb_cache_performers"
    id = Column(Integer, primary_key=True)
    stashdb_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    aliases = Column(Text)
    image_url = Column(Text)
    scene_count = Column(Integer, default=0)
    gender = Column(String(50))
    birthdate = Column(String(50))
    urls = Column(JSON)
    raw_json = Column(JSON)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class StashDBStudioCache(Base):
    __tablename__ = "stashdb_cache_studios"
    id = Column(Integer, primary_key=True)
    stashdb_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    image_url = Column(Text)
    scene_count = Column(Integer, default=0)
    parent_studio = Column(String(255))
    urls = Column(JSON)
    raw_json = Column(JSON)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class StashDBSceneCache(Base):
    __tablename__ = "stashdb_cache_scenes"
    id = Column(Integer, primary_key=True)
    stashdb_id = Column(String(255), unique=True, nullable=False)
    title = Column(String(500))
    details = Column(Text)
    release_date = Column(String(20))
    duration = Column(Integer)
    studio_name = Column(String(255))
    studio_id = Column(String(255))
    performer_names = Column(JSON)
    performer_ids = Column(JSON)
    tags = Column(JSON)
    fingerprints = Column(JSON)
    images = Column(JSON)
    raw_json = Column(JSON)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class StandardSearchHistory(Base):
    __tablename__ = "standard_search_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    query = Column(String(500), nullable=False)
    filters = Column(JSON)
    result_count = Column(Integer, default=0)
    status = Column(String(50), default="running")
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Create Alembic migration**

Run: `alembic revision --rev-id 20260514_add_stashdb_cache_and_history -m "add stashdb cache and history"`  
Edit the new file:

```python
# alembic/versions/20260514_add_stashdb_cache_and_history.py
def upgrade():
    op.add_column("stashdb_cache_performers", sa.Column("gender", sa.String(length=50), nullable=True))
    op.add_column("stashdb_cache_performers", sa.Column("birthdate", sa.String(length=50), nullable=True))
    op.add_column("stashdb_cache_performers", sa.Column("urls", sa.JSON(), nullable=True))
    op.add_column("stashdb_cache_studios", sa.Column("urls", sa.JSON(), nullable=True))
    op.create_table(
        "stashdb_cache_scenes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stashdb_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("title", sa.String(length=500)),
        sa.Column("details", sa.Text()),
        sa.Column("release_date", sa.String(length=20)),
        sa.Column("duration", sa.Integer()),
        sa.Column("studio_name", sa.String(length=255)),
        sa.Column("studio_id", sa.String(length=255)),
        sa.Column("performer_names", sa.JSON()),
        sa.Column("performer_ids", sa.JSON()),
        sa.Column("tags", sa.JSON()),
        sa.Column("fingerprints", sa.JSON()),
        sa.Column("images", sa.JSON()),
        sa.Column("raw_json", sa.JSON()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "standard_search_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("filters", sa.JSON()),
        sa.Column("result_count", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(length=50), server_default="running"),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_standard_search_history_user_id", "standard_search_history", ["user_id"])
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_models_stashdb_cache.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/models/__init__.py alembic/versions/20260514_add_stashdb_cache_and_history.py tests/test_models_stashdb_cache.py
git commit -m "feat: add stashdb cache and search history models"
```

---

### Task 3: Replace OpenSearch repository with Typesense

**Files:**
- Modify: `app/library/common/repository.py`
- Modify: `app/library/common/service.py`
- Create: `app/library/common/typesense_schema.py`
- Create: `tests/test_typesense_repository.py`

- [ ] **Step 1: Write failing repository tests**

```python
# tests/test_typesense_repository.py
from unittest.mock import MagicMock
from app.library.common import repository

def test_search_index_calls_typesense(monkeypatch):
    fake = MagicMock()
    fake.search.return_value = [{"title": "x"}]
    monkeypatch.setattr(repository, "get_client", lambda: fake)
    out = repository.search_index("stashdb_scenes", "x", fields=["title^3"])
    assert out == [{"title": "x"}]
    fake.search.assert_called_once()
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_typesense_repository.py -v`  
Expected: FAIL (search not implemented).

- [ ] **Step 3: Add Typesense schemas**

```python
# app/library/common/typesense_schema.py
SCHEMAS = [
    {
        "name": "stashdb_performers",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "name", "type": "string"},
            {"name": "aliases", "type": "string[]", "optional": True},
            {"name": "gender", "type": "string", "optional": True},
            {"name": "birthdate", "type": "string", "optional": True},
            {"name": "scene_count", "type": "int32", "optional": True},
        ],
        "default_sorting_field": "scene_count",
    },
    {
        "name": "stashdb_studios",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "name", "type": "string"},
            {"name": "scene_count", "type": "int32", "optional": True},
        ],
        "default_sorting_field": "scene_count",
    },
    {
        "name": "stashdb_scenes",
        "fields": [
            {"name": "id", "type": "string"},
            {"name": "title", "type": "string"},
            {"name": "details", "type": "string", "optional": True},
            {"name": "release_date", "type": "string", "optional": True},
            {"name": "duration", "type": "int32", "optional": True},
            {"name": "studio_name", "type": "string", "optional": True},
            {"name": "performer_names", "type": "string[]", "optional": True},
            {"name": "tags", "type": "string[]", "optional": True},
            {"name": "fingerprints", "type": "string[]", "optional": True},
            {"name": "images", "type": "string[]", "optional": True},
        ],
    },
]
```

- [ ] **Step 4: Rewrite repository to use Typesense**

```python
# app/library/common/repository.py
from app.services.typesense_client import TypesenseClient

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
    client = get_client()
    return client.search(index, prefix, [field], per_page=size)

def index_document(index: str, doc_id: str, body: dict):
    client = get_client()
    body = {**body, "id": doc_id}
    client.upsert(index, body)

def bulk_index(index: str, documents: list[dict], id_field: str = "stashdb_id"):
    client = get_client()
    docs = [{**d, "id": d.get(id_field)} for d in documents if d.get(id_field)]
    client.bulk_upsert(index, docs)

def get_document(index: str, doc_id: str) -> dict | None:
    return get_client().get(index, doc_id)

def delete_document(index: str, doc_id: str):
    get_client().delete(index, doc_id)

def search_by_hashes(index: str, hashes: list[str]) -> dict[str, dict]:
    docs = get_client().search_by_hashes(index, hashes)
    result: dict[str, dict] = {}
    for d in docs:
        for fp in d.get("fingerprints", []) or []:
            val = str(fp).lower()
            if val in [h.lower() for h in hashes]:
                result[val] = d
    return result
```

- [ ] **Step 5: Update initialize_search**

```python
# app/library/common/service.py
from app.services.typesense_client import TypesenseClient
from app.library.common.typesense_schema import SCHEMAS

def initialize_search():
    TypesenseClient().ensure_collections(SCHEMAS)
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_typesense_repository.py -v`  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/library/common/repository.py app/library/common/service.py app/library/common/typesense_schema.py tests/test_typesense_repository.py
git commit -m "feat: switch search repository to typesense"
```

---

### Task 4: Rewrite initial ingest to PG + Typesense

**Files:**
- Modify: `scripts/initial_ingest.py`
- Create: `tests/test_ingest_filters.py`

- [ ] **Step 1: Write failing filter tests**

```python
# tests/test_ingest_filters.py
from scripts.initial_ingest import should_include_scene

def test_scene_year_filter():
    assert should_include_scene("2000-01-01") is True
    assert should_include_scene("1999-12-31") is False
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_ingest_filters.py -v`  
Expected: FAIL (function missing).

- [ ] **Step 3: Implement PG + Typesense ingest**

```python
# scripts/initial_ingest.py (key changes)
from app.database import SessionLocal
from app.models import StashDBPerformerCache, StashDBStudioCache, StashDBSceneCache
from app.services.typesense_client import TypesenseClient
from app.config import settings

ts = TypesenseClient()

def should_include_scene(release_date: str | None) -> bool:
    return bool(release_date and release_date >= "2000-01-01")

def fetch_studios_by_name(name: str, page: int = 1) -> dict:
    q = """
    query SearchStudios($input: StudioQueryInput!) {
      queryStudios(input: $input) {
        studios { id name scene_count images { url } parent { id name } urls { url type } }
      }
    }
    """
    return graphql(q, {"input": {"names": name, "page": page, "per_page": PER_PAGE}})

def rate_limit():
    time.sleep(settings.stashdb_rate_limit_seconds)

def save_performer(session, p: dict):
    if p.get("gender") != "female":
        return
    cache = StashDBPerformerCache(
        stashdb_id=p["id"],
        name=p.get("name", ""),
        aliases=p.get("aliases"),
        gender=p.get("gender"),
        birthdate=p.get("birth_date"),
        image_url=(p.get("images") or [{}])[0].get("url"),
        scene_count=p.get("scene_count", 0),
        urls=[{"url": u["url"], "type": u["type"]} for u in (p.get("urls") or [])],
        raw_json=p,
    )
    session.merge(cache)
    session.commit()
    ts.upsert("stashdb_performers", {
        "id": p["id"],
        "name": p.get("name", ""),
        "aliases": [a.strip() for a in (p.get("aliases") or "").split(",") if a.strip()],
        "gender": p.get("gender"),
        "birthdate": p.get("birth_date"),
        "scene_count": p.get("scene_count", 0),
    })

def save_studio(session, s: dict):
    imgs = s.get("images") or []
    cache = StashDBStudioCache(
        stashdb_id=s["id"],
        name=s.get("name", ""),
        image_url=imgs[0].get("url") if imgs else None,
        scene_count=s.get("scene_count", 0),
        parent_studio=(s.get("parent") or {}).get("name"),
        urls=[{"url": u["url"], "type": u["type"]} for u in (s.get("urls") or [])],
        raw_json=s,
    )
    session.merge(cache)
    session.commit()
    ts.upsert("stashdb_studios", {
        "id": s["id"],
        "name": s.get("name", ""),
        "scene_count": s.get("scene_count", 0),
    })

def save_scene(session, sc: dict):
    if not should_include_scene(sc.get("release_date")):
        return
    imgs = sc.get("images") or []
    perf = sc.get("performers") or []
    fprints = sc.get("fingerprints") or []
    tags = sc.get("tags") or []
    studio = sc.get("studio") or {}
    cache = StashDBSceneCache(
        stashdb_id=sc["id"],
        title=sc.get("title", ""),
        details=sc.get("details"),
        release_date=sc.get("release_date"),
        duration=sc.get("duration"),
        studio_id=studio.get("id"),
        studio_name=studio.get("name"),
        performer_ids=[p.get("performer", {}).get("id") for p in perf if p.get("performer")],
        performer_names=[p.get("performer", {}).get("name") for p in perf if p.get("performer")],
        fingerprints=[fp.get("hash") for fp in fprints if fp.get("hash")],
        tags=[t.get("name") for t in tags if t.get("name")],
        images=[i.get("url") for i in imgs if i.get("url")],
        raw_json=sc,
    )
    session.merge(cache)
    session.commit()
    ts.upsert("stashdb_scenes", {
        "id": sc["id"],
        "title": sc.get("title", ""),
        "details": sc.get("details"),
        "release_date": sc.get("release_date"),
        "duration": sc.get("duration"),
        "studio_name": studio.get("name"),
        "performer_names": [p.get("performer", {}).get("name") for p in perf if p.get("performer")],
        "tags": [t.get("name") for t in tags if t.get("name")],
        "fingerprints": [fp.get("hash") for fp in fprints if fp.get("hash")],
        "images": [i.get("url") for i in imgs if i.get("url")],
    })

def ingest_performers():
    session = SessionLocal()
    for prefix in NAME_PREFIXES:
        page = 1
        while True:
            data = fetch_performers_by_name(prefix, page)
            performers = (data.get("data") or {}).get("queryPerformers", {}).get("performers", [])
            if not performers:
                break
            for p in performers:
                save_performer(session, p)
            page += 1
            rate_limit()
    session.close()

def ingest_studios():
    session = SessionLocal()
    for prefix in NAME_PREFIXES:
        page = 1
        while True:
            data = fetch_studios_by_name(prefix, page)
            studios = (data.get("data") or {}).get("queryStudios", {}).get("studios", [])
            if not studios:
                break
            for s in studios:
                save_studio(session, s)
            page += 1
            rate_limit()
    session.close()

def ingest_scenes():
    session = SessionLocal()
    for prefix in NAME_PREFIXES:
        page = 1
        while True:
            data = fetch_performers_by_name(prefix, page)
            performers = (data.get("data") or {}).get("queryPerformers", {}).get("performers", [])
            if not performers:
                break
            for p in performers:
                for s_rel in (p.get("studios") or []):
                    studio = s_rel.get("studio") or {}
                    sid = studio.get("id")
                    if not sid:
                        continue
                    spage = 1
                    while True:
                        sdata = fetch_scenes_by_studio(sid, spage)
                        scenes = (sdata.get("data") or {}).get("queryScenes", {}).get("scenes", [])
                        if not scenes:
                            break
                        for sc in scenes:
                            save_scene(session, sc)
                        spage += 1
                        rate_limit()
            page += 1
            rate_limit()
    session.close()

def main():
    require_api_key()
    ingest_performers()
    ingest_studios()
    ingest_scenes()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_ingest_filters.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/initial_ingest.py tests/test_ingest_filters.py
git commit -m "feat: rewrite initial ingest to pg + typesense"
```

---

### Task 5: Update StashDB search endpoints for PG + Typesense

**Files:**
- Modify: `app/api/v1/stashdb_search.py`
- Modify: `app/library/standard_search/service.py`
- Create: `tests/test_stashdb_search_fallback.py`

- [ ] **Step 1: Write failing fallback test**

```python
# tests/test_stashdb_search_fallback.py
from app.api.v1 import stashdb_search

def test_entity_fallback_order():
    calls = []
    stashdb_search._try_pg = lambda *a, **k: calls.append("pg") or None
    stashdb_search._try_typesense = lambda *a, **k: calls.append("ts") or None
    stashdb_search._try_live = lambda *a, **k: calls.append("live") or {"id": "x"}
    res = stashdb_search._resolve_entity("scene", "x", None)
    assert res["id"] == "x"
    assert calls == ["pg", "ts", "live"]
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_stashdb_search_fallback.py -v`  
Expected: FAIL (test needs implementation).

- [ ] **Step 3: Update stashdb_search to use PG/Typesense first**

```python
# app/api/v1/stashdb_search.py
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import StashDBPerformerCache, StashDBStudioCache, StashDBSceneCache
from app.services.typesense_client import TypesenseClient

def _try_pg(entity_type: str, id: str, db: Session) -> dict | None:
    if entity_type == "performer":
        row = db.query(StashDBPerformerCache).filter_by(stashdb_id=id).first()
        return row.raw_json if row else None
    if entity_type == "studio":
        row = db.query(StashDBStudioCache).filter_by(stashdb_id=id).first()
        return row.raw_json if row else None
    row = db.query(StashDBSceneCache).filter_by(stashdb_id=id).first()
    return row.raw_json if row else None

def _try_typesense(entity_type: str, id: str) -> dict | None:
    collection = {"performer": "stashdb_performers", "studio": "stashdb_studios", "scene": "stashdb_scenes"}[entity_type]
    return TypesenseClient().get(collection, id)

def _try_live(entity_type: str, id: str) -> dict | None:
    return _try_stashdb_live(entity_type, id)

def _resolve_entity(entity_type: str, id: str, db: Session | None) -> dict | None:
    return (_try_pg(entity_type, id, db) if db else None) or _try_typesense(entity_type, id) or _try_live(entity_type, id)

@router.get("/entity")
def get_entity(type: str = Query(..., regex="^(performer|studio|scene)$"), id: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    result = _resolve_entity(type, id, db)
    if result:
        return result
    raise HTTPException(status_code=404, detail=f"{type} {id} not found")
```

- [ ] **Step 4: Update standard_search service to cache live results**

```python
# app/library/standard_search/service.py
from app.database import SessionLocal
from app.models import StashDBSceneCache
from app.services.typesense_client import TypesenseClient

def enrich_by_hashes(info_hashes: list[str]) -> dict[str, dict]:
    local = local_repo.enrich_by_hashes(info_hashes)
    missing = [h for h in info_hashes if h not in local]
    if missing:
        live = stashdb_live.enrich_by_hashes(missing)
        if live:
            db = SessionLocal()
            ts = TypesenseClient()
            for h, data in live.items():
                local[h] = data
                db.merge(StashDBSceneCache(
                    stashdb_id=data.get("id"),
                    title=data.get("title"),
                    details=data.get("details"),
                    release_date=data.get("release_date"),
                    duration=(data.get("file") or {}).get("duration"),
                    studio_name=(data.get("studio") or {}).get("name"),
                    performer_names=[p.get("name") for p in data.get("performers", [])],
                    tags=[t.get("name") for t in data.get("tags", [])],
                    images=[(data.get("paths") or {}).get("screenshot")] if (data.get("paths") or {}).get("screenshot") else [],
                    raw_json=data,
                ))
                ts.upsert("stashdb_scenes", {
                    "id": data.get("id"),
                    "title": data.get("title", ""),
                    "details": data.get("details"),
                    "release_date": data.get("release_date"),
                    "duration": (data.get("file") or {}).get("duration"),
                    "studio_name": (data.get("studio") or {}).get("name"),
                    "performer_names": [p.get("name") for p in data.get("performers", [])],
                    "tags": [t.get("name") for t in data.get("tags", [])],
                    "images": [(data.get("paths") or {}).get("screenshot")] if (data.get("paths") or {}).get("screenshot") else [],
                })
            db.commit()
            db.close()
    return local
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_stashdb_search_fallback.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/api/v1/stashdb_search.py app/library/standard_search/service.py tests/test_stashdb_search_fallback.py
git commit -m "feat: use pg + typesense for stashdb search and cache"
```

---

### Task 6: Standard Search history + WS auth + history updates

**Files:**
- Modify: `app/library/standard_search/api.py`
- Create: `app/api/v1/standard_search_history.py`
- Modify: `app/auth/dependencies.py`
- Create: `tests/test_standard_search_history.py`

- [ ] **Step 1: Write failing history API test**

```python
# tests/test_standard_search_history.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_history_requires_auth():
    resp = client.get("/api/v1/standard-search/history")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_standard_search_history.py -v`  
Expected: FAIL (route missing).

- [ ] **Step 3: Add history API**

```python
# app/api/v1/standard_search_history.py
from fastapi import Query
@router.get("/standard-search/history")
def history(limit: int | None = Query(None, ge=1), user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(StandardSearchHistory).filter_by(user_id=user["sub"]).order_by(StandardSearchHistory.id.desc())
    rows = q.limit(limit).all() if limit else q.all()
    return [
        {
            "id": h.id,
            "query": h.query,
            "filters": h.filters,
            "result_count": h.result_count,
            "status": h.status,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in rows
    ]
```

- [ ] **Step 4: Enforce WS auth + write history rows**

```python
# app/auth/dependencies.py
def verify_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=["HS256"],
        audience="authenticated",
    )
    return payload

# app/library/standard_search/api.py
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import StandardSearchHistory
token = websocket.query_params.get("access_token") or ""
if not token:
    await websocket.close(code=4401)
    return
try:
    user = verify_token(token)
except Exception:
    await websocket.close(code=4401)
    return

db = SessionLocal()
history = StandardSearchHistory(
    user_id=user["sub"],
    query=query,
    filters={"categories": categories, "indexers": indexer_ids, "xxx_type": xxx_type},
)
db.add(history)
db.commit()
db.refresh(history)
# on complete:
history.status = "completed"
history.result_count = len(processed)
history.completed_at = datetime.now(timezone.utc)
db.commit()
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_standard_search_history.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/library/standard_search/api.py app/api/v1/standard_search_history.py tests/test_standard_search_history.py
git commit -m "feat: add standard search history and ws auth"
```

---

### Task 7: Magnet fallback + batch add reliability

**Files:**
- Create: `app/services/magnet.py`
- Modify: `app/api/v1/torrents.py`
- Create: `tests/test_magnet_fallback.py`

- [ ] **Step 1: Write failing magnet tests**

```python
# tests/test_magnet_fallback.py
from app.services.magnet import build_magnet

def test_build_magnet():
    m = build_magnet("ABC123", "Title")
    assert m.startswith("magnet:?xt=urn:btih:ABC123")
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_magnet_fallback.py -v`  
Expected: FAIL (module missing).

- [ ] **Step 3: Implement magnet fallback and use in batch add**

```python
# app/services/magnet.py
import urllib.parse

def build_magnet(info_hash: str, title: str = "") -> str:
    dn = urllib.parse.quote(title) if title else ""
    return f"magnet:?xt=urn:btih:{info_hash}&dn={dn}" if dn else f"magnet:?xt=urn:btih:{info_hash}"
```

```python
# app/api/v1/torrents.py (batch add)
from app.services.magnet import build_magnet

class BatchAddMagnetItem(BaseModel):
    magnet: str | None = None
    info_hash: str | None = None
    title: str | None = None

class BatchAddMagnetRequest(BaseModel):
    items: list[BatchAddMagnetItem]
    seed: int = 1

@router.post("/add/batch")
def add_torrents_batch(body: BatchAddMagnetRequest):
    results = []
    for item in body.items:
        magnet = item.magnet or ""
        if (not magnet or not magnet.startswith("magnet:?xt=urn:btih:")) and item.info_hash:
            magnet = build_magnet(item.info_hash, item.title or "")
        try:
            data = torbox.create_torrent(magnet, body.seed)
            results.append({"magnet": magnet[:60], "status": "ok", "data": data})
        except Exception as e:
            results.append({"magnet": magnet[:60], "status": "error", "error": str(e)})
    return {"results": results}
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_magnet_fallback.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/magnet.py app/api/v1/torrents.py tests/test_magnet_fallback.py
git commit -m "feat: add magnet fallback for torbox batch add"
```

---

### Task 8: Global auth gating (backend + frontend)

**Files:**
- Modify: `app/main.py`
- Modify: `src/App.tsx`
- Modify: `src/components/ProtectedRoute.tsx`
- Modify: `src/api/client.ts`

- [ ] **Step 1: Add auth dependency to all API routers**

```python
# app/main.py
from fastapi import Depends
from app.auth.dependencies import get_current_user
secure_routers = [
    torrents.router,
    system.router,
    library.router,
    stash.router,
    whisparr.router,
    prowlarr.router,
    search.router,
    trackers.router,
    watch.router,
    email.router,
    recommender.router,
    stats.router,
    metrics.router,
    lib_std_search.router,
    stashdb_search.router,
]
for r in secure_routers:
    app.include_router(r, prefix="/api/v1", dependencies=[Depends(get_current_user)])
app.include_router(auth.router, prefix="/api/v1")
```

- [ ] **Step 2: Protect all frontend routes**

```tsx
// src/App.tsx
<Route path="*" element={
  <ProtectedRoute>
    <Layout>
      <AnimatedRoutes />
    </Layout>
  </ProtectedRoute>
} />
```

- [ ] **Step 3: Always send auth headers for API calls**

```ts
// src/api/client.ts
async function get<T>(path: string): Promise<T> {
  const headers = await authHeaders();
  const r = await fetchWithTimeout(`${BASE}${path}`, { headers });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (body) headers['Content-Type'] = 'application/json';
  Object.assign(headers, await authHeaders());
  const r = await fetchWithTimeout(`${BASE}${path}`, {
    method: 'POST',
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

// connectStandardSearch
const token = await getToken();
const ws = new WebSocket(`${protocol}//${host}/api/v1/prowlarr/ws?access_token=${encodeURIComponent(token || '')}`);
```

- [ ] **Step 4: Commit**

```bash
git add app/main.py src/App.tsx src/components/ProtectedRoute.tsx src/api/client.ts
git commit -m "feat: require auth globally for api and ui"
```

---

### Task 9: Standard Search UI upgrades

**Files:**
- Modify: `src/pages/StandardSearch.tsx`
- Modify: `src/api/client.ts`
- Modify: `src/types/index.ts`

- [ ] **Step 1: Add history API bindings and types**

```ts
// src/types/index.ts
export interface StandardSearchHistoryItem {
  id: number;
  query: string;
  filters: { categories?: number[]; indexers?: number[]; xxx_type?: string };
  result_count: number;
  status: string;
  created_at: string;
}

export interface EnrichedResult {
  id?: string;
  title: string;
  images: string[];
  performers: string[];
  studio: string | null;
}
```

```ts
// src/api/client.ts
getStandardSearchHistory: () => get<StandardSearchHistoryItem[]>('/standard-search/history'),
```

- [ ] **Step 2: Dynamic categories + history panel + details**

```tsx
// src/pages/StandardSearch.tsx (add state + effects)
const [categoryTree, setCategoryTree] = useState<CategoryTreeItem[]>([]);
const [history, setHistory] = useState<StandardSearchHistoryItem[]>([]);

useEffect(() => {
  api.getCategoryTree().then(d => Array.isArray(d) && setCategoryTree(d));
  api.getStandardSearchHistory().then(setHistory).catch(() => setHistory([]));
}, []);

const topCategories = categoryTree.filter(c => c.id < 7000);
const xxxCategory = categoryTree.find(c => c.id >= 6000 && c.id < 7000);
const xxxSubcats = xxxCategory?.subCategories || [];

const applyHistory = (h: StandardSearchHistoryItem) => {
  setQuery(h.query);
  setSelectedCategories(h.filters.categories || []);
  setSelectedIndexers(h.filters.indexers || []);
  setXxxType((h.filters.xxx_type as XxxType) || 'both');
  doSearch();
};

// categories render
<div className="flex flex-wrap gap-2 mb-3">
  <button onClick={() => setSelectedCategories([])} className={selectedCategories.length === 0 ? 'bg-accent text-black' : 'border-zinc-700 text-zinc-400'}>
    All
  </button>
  {topCategories.map(c => (
    <button key={c.id} onClick={() => toggleCategory(c.id)} className={selectedCategories.includes(c.id) ? 'bg-accent/20 text-accent' : 'border-zinc-700 text-zinc-400'}>
      {c.name}
    </button>
  ))}
</div>
{isXxxSelected && (
  <div className="flex flex-wrap gap-1.5">
    {xxxSubcats.map(sc => (
      <button key={sc.id} onClick={() => toggleCategory(sc.id)} className={selectedCategories.includes(sc.id) ? 'bg-accent/20 text-accent' : 'border-zinc-700 text-zinc-500'}>
        {sc.name}
      </button>
    ))}
  </div>
)}

// history panel
<div className="glass rounded-xl p-4">
  <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-3">History</h3>
  <div className="space-y-2 max-h-48 overflow-y-auto">
    {history.map(h => (
      <button key={h.id} onClick={() => applyHistory(h)} className="w-full text-left text-xs text-zinc-300 hover:text-white">
        {h.query} <span className="text-zinc-500">({h.result_count})</span>
      </button>
    ))}
  </div>
</div>

// details action in result card
{r.enriched?.id && (
  <button onClick={() => openPanel('scene', r.enriched!.id!)} className="text-xs text-accent">
    View
  </button>
)}

// addToTorBox payload
const items = results.filter(r => selected.has(r.guid)).map(r => ({
  magnet: r.magnetUrl || null,
  info_hash: r.infoHash || null,
  title: r.title || '',
}));
await fetch('/api/v1/torrents/add/batch', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items, seed: 1 }) });
```

- [ ] **Step 3: Blur thumbnails in SAFE mode**

```tsx
// wrap image
<SpoilerBlur>
  <img src={r.enriched?.images?.[0]} alt="" className="w-full h-full object-cover" />
</SpoilerBlur>
```

- [ ] **Step 4: Commit**

```bash
git add src/pages/StandardSearch.tsx src/api/client.ts src/types/index.ts
git commit -m "feat: standard search history, dynamic categories, blur"
```

---

### Task 10: Docker compose Typesense + remove OpenSearch

**Files:**
- Modify: `docker-compose.yml`
- Modify: `requirements.txt`
- Modify: `app/library/common/schema.py`

- [ ] **Step 1: Add Typesense service and volumes**

```yaml
typesense:
  image: typesense/typesense:27.0
  ports:
    - 127.0.0.1:8108:8108
  environment:
    - TYPESENSE_API_KEY=${TYPESENSE_API_KEY}
    - TYPESENSE_DATA_DIR=/data
  volumes:
    - typesense_data:/data
```

- [ ] **Step 2: Remove OpenSearch services/volumes**

- [ ] **Step 3: Drop OpenSearch dependency and schema mappings**

```text
# requirements.txt
# remove: opensearch-py (or opensearchpy)
```

```python
# app/library/common/schema.py
STASHDB_INDEX_PERFORMERS = "stashdb_performers"
STASHDB_INDEX_STUDIOS = "stashdb_studios"
STASHDB_INDEX_SCENES = "stashdb_scenes"
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml requirements.txt app/library/common/schema.py
git commit -m "feat: add typesense and remove opensearch"
```

---

## Self-Review Checklist
1. **Spec coverage:** All spec requirements map to Tasks 1–10.
2. **Placeholder scan:** No TBD/TODO placeholders remain; code snippets included.
3. **Type consistency:** Typesense schemas and cache models align with API usage.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-14-standard-search-typesense-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration  
**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints  

**Which approach?**
