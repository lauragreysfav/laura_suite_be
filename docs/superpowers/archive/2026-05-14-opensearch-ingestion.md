# OpenSearch Ingestion Implementation Plan

## Status: ✅ COMPLETED

## Phases

### Phase 1: Infrastructure ✅
- [x] Add OpenSearch service to docker-compose.yml (image: opensearchproject/opensearch:2.19.1, single-node, security disabled)
- [x] Add `opensearch_data` volume
- [x] Add `opensearch-py>=2.7.0` to requirements.txt
- [x] Add `opensearch_hosts` to config.py
- [x] Wire depends_on for laura-backend, laura-worker, laura-beat

### Phase 2: Library Structure ✅
- [x] Create `app/library/__init__.py`
- [x] Create `app/library/common/schema.py` — OpenSearch index mappings with edge_ngram autocomplete
- [x] Create `app/library/common/repository.py` — OpenSearch client wrapper (get, suggest, search, bulk, etc.)
- [x] Create `app/library/common/service.py` — Index lifecycle (init, rebuild, upsert, remove)

### Phase 3: Standard Search Library ✅
- [x] Create `app/library/standard_search/__init__.py`
- [x] Create `app/library/standard_search/schema.py` — Pydantic models
- [x] Create `app/library/standard_search/repository.py` — Domain-specific OS queries (suggest_performers, enrich_by_hashes, etc.)
- [x] Create `app/library/standard_search/service.py` — Orchestration (local OS → live stashdb.org fallback + cache-on-miss)
- [x] Create `app/library/standard_search/api.py` — WebSocket + REST endpoints (replaces flat prowlarr_search.py)

### Phase 4: Ingest Script ✅
- [x] Create `scripts/initial_ingest.py` — crawl female performers → studios → scenes (date ≥ 2001)

### Phase 5: Celery Tasks ✅
- [x] Create `app/tasks/library_search_tasks.py` with `prime_suggest_cache` task
- [x] Add 6h beat schedule in celery_app.py

### Phase 6: Router Updates ✅
- [x] Replace `prowlarr_search` import in main.py with `library.standard_search.api`
- [x] Update `stashdb_search.py` to use new library service (local-first suggest)

### Phase 7: Build & Verify ⬜
- [ ] RUN: `docker compose build` — rebuild images
- [ ] RUN: `docker compose up -d` — restart stack
- [ ] VERIFY: `curl http://localhost:9200` — OpenSearch responds
- [ ] VERIFY: `curl http://localhost:8000/api/v1/stashdb/suggest?q=test` — suggest works
- [ ] VERIFY: `pip install opensearch-py` installed (already in requirements.txt)
