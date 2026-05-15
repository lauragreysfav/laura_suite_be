# Standard Search + OpenSearch Ingestion Design

## Overview
Standard Search provides a unified search experience combining Prowlarr torrent search with StashDB metadata enrichment. A local OpenSearch index caches StashDB data for fast suggest/enrich without hitting the live GraphQL API on every keystroke.

## Architecture

```
Frontend (React)                    Backend (FastAPI)                   External
┌─────────────────┐    WebSocket    ┌──────────────────────┐    ┌──────────────┐
│                 │ ◄─────────────► │ /api/v1/prowlarr/ws  │───►│   Prowlarr   │
│  StandardSearch │     REST        │ /api/v1/prowlarr/*   │    └──────────────┘
│                 │ ◄─────────────► │ /api/v1/stashdb/*    │    ┌──────────────┐
└─────────────────┘                 │                      │───►│  stashdb.org │
                                    │  library/            │    └──────────────┘
                                    │   standard_search/   │    ┌──────────────┐
                                    │   common/            │───►│  OpenSearch  │
                                    └──────────────────────┘    └──────────────┘
```

## Data Flow

### Search Flow
1. User enters query → Prowlarr WebSocket streams results progressively
2. Each result's info_hash is sent to StashDB enrich (local OS first, live fallback)
3. Enrichment data (images, performers, studio) streamed back per-result via WS
4. User selects results → POST /api/v1/torrents/add/batch → TorBox

### Suggest Flow (autocomplete)
1. Local OpenSearch suggest via edge_ngram + prefix query (sub-10ms)
2. If empty → fallback to live stashdb.org GraphQL
3. On live hit → async cache to OpenSearch for future queries

### Initial Ingest
1. `scripts/initial_ingest.py` crawls stashdb.org:
   - Female performers (paginated) → index to `stashdb_performers`
   - Deduplicate studio IDs → fetch each → index to `stashdb_studios`
   - Per studio, scenes with date ≥ 2001 → index to `stashdb_scenes`
2. Runs standalone, not as a Celery task (long-running)
3. Celery Beat every 6h: `prime_suggest_cache` warms common prefixes

## OpenSearch Indices

Three indices with edge_ngram autocomplete analyzers:

| Index | Primary Fields | ID Field |
|-------|---------------|----------|
| `stashdb_performers` | name, aliases, gender, scene_count, image_url | stashdb_id |
| `stashdb_studios` | name, scene_count, parent_studio, image_url | stashdb_id |
| `stashdb_scenes` | title, details, date, studio, performers, fingerprints | stashdb_id |

## Library Package Structure

```
app/library/
├── __init__.py
├── common/
│   ├── __init__.py
│   ├── schema.py          # Index mappings, settings
│   ├── repository.py      # OpenSearch client wrapper
│   └── service.py         # Index lifecycle management
└── standard_search/
    ├── __init__.py
    ├── schema.py           # Pydantic models
    ├── repository.py       # Domain-specific OS queries
    ├── service.py          # Orchestration (local first, live fallback)
    └── api.py              # WebSocket + REST endpoints
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| WS | `/api/v1/prowlarr/ws` | Standard search with Prowlarr streaming |
| GET | `/api/v1/prowlarr/categories/tree` | Newznab category hierarchy |
| GET | `/api/v1/prowlarr/indexers/mapped` | Indexers with JAV/Western classification |
| GET | `/api/v1/stashdb/suggest` | Autocomplete (local OS → live fallback) |
| POST | `/api/v1/torrents/add/batch` | Batch add magnets to TorBox |

## Configuration

Added to `.env`:
```
OPENSEARCH_HOSTS=http://opensearch:9200
```

## Docker Compose

OpenSearch 2.19.1 single-node with security disabled (dev). Health check ensures backend waits for OS readiness.
