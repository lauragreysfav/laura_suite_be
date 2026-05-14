# Standard Search + PG/Typesense Migration Design (2026-05-14)

## Summary
This design delivers Standard Search fixes (auth-gated access, NSFW defaults, dynamic categories, richer results, history, and TorBox magnet reliability) while migrating StashDB caching/search from OpenSearch to a PostgreSQL primary store plus Typesense search index. The cutover is staged to reduce risk and ends with OpenSearch removed.

## Goals
- Require authentication for all API access; unauthenticated users are routed to Login.
- Standard Search defaults to NSFW, with SAFE mode blurring thumbnails.
- Dynamic categories from Prowlarr; result enrichment and detail view for matched scenes.
- Reliable TorBox add flow with fallback magnet construction from infoHash.
- Per-user Standard Search history (query + filters + result count/status) with re-run on click.
- Replace OpenSearch with PostgreSQL + Typesense while preserving all StashDB data in SQL.
- Ingest scope: scenes from year 2000+, all studios, female performers only.

## Non-goals
- Major redesign of non-Standard Search pages.
- RBAC; admin-only auth is sufficient for now.

## Architecture
1. **Ingest pipeline**: StashDB GraphQL → normalize → PG cache tables → Typesense collections (dual-write).
2. **Suggest/search**: Typesense first, live StashDB fallback, then cache into PG + Typesense.
3. **Entity fetch**: PG cache first → Typesense doc retrieve → live StashDB fallback.
4. **Standard Search enrichment**: Prowlarr results → infoHash → Typesense search_by_hashes → enrich results; fallback to live StashDB if missing.

## Data Model
**All StashDB data is preserved** in PostgreSQL via `raw_json` (JSONB) columns.

### PostgreSQL Cache Tables
- `stashdb_cache_performers`:
  - stashdb_id (unique), name, image_url, scene_count, aliases, gender, birthdate, urls(JSON),
    updated_at, raw_json(JSONB)
- `stashdb_cache_studios`:
  - stashdb_id (unique), name, image_url, scene_count, urls(JSON),
    updated_at, raw_json(JSONB)
- `stashdb_cache_scenes` (new):
  - stashdb_id (unique), title, details, release_date, duration, studio_name, studio_id,
    performer_names(JSON), performer_ids(JSON), tags(JSON), fingerprints(JSON), images(JSON),
    updated_at, raw_json(JSONB)

### Typesense Collections
Curated fields for search/suggest; raw_json remains in PG.
- performers: id, name, aliases, gender, birthdate, scene_count
- studios: id, name, scene_count
- scenes: id, title, details, release_date, duration, studio_name, performer_names, tags, fingerprints, images

### Standard Search History
- `standard_search_history`:
  - id, user_id, query, filters(JSON: categories/indexers/xxx_type), result_count,
    status, error, created_at, completed_at

## API & Auth
- **Global auth required** for all API routes (except auth/login callbacks + health).
- **WS auth** for `/api/v1/prowlarr/ws` via Supabase JWT (Authorization header or access_token query param).
- **History API**:
  - `GET /standard-search/history?limit=&offset=` (auth required)
  - History entries created/updated by WS lifecycle (start → complete/fail).

## Frontend (Standard Search)
- Default NSFW **on**; SAFE mode uses `SpoilerBlur` to blur thumbnails.
- Category list loaded dynamically from `/prowlarr/categories/tree`.
- Result cards add **View/Details** action when enriched scene id is available.
- History panel lists recent searches; click to re-run with same filters.
- Add-to-TorBox uses fallback magnets for missing/invalid magnet links.

## Ingest & Migration Plan (Staged Cutover)
1. Add PG cache tables + Alembic migrations.
2. Add Typesense to docker-compose (env-configured key; persistent volume).
3. Implement `typesense_client` service (collections + search/suggest/get/search_by_hashes).
4. Rewrite `library/common/repository.py` to Typesense.
5. Update ingest to write PG + Typesense; **rate-limited** via configurable delay.
   - Scenes: year >= 2000
   - Performers: female only
   - Studios: all
6. Update API query paths to PG/Typesense → live StashDB fallback.
7. Remove OpenSearch services + volumes.

## Error Handling & Observability
- WS errors surface to UI; history marked failed with error.
- Typesense unavailable → live StashDB fallback (with warnings logged); cache on recovery.
- Ingest retries with exponential backoff; checkpoints track progress.

## Testing/Verification
- Unit tests: Typesense client, magnet fallback.
- Integration tests: auth gating, history endpoints, WS auth.
