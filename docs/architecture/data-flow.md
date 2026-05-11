# Data Flow

## Whisparr → TorBox → Stash Pipeline

```
Whisparr monitors actress
    │  (RSS feeds from indexers)
    ▼
Whisparr finds matching release
    │  (grabs magnet URL)
    ▼
Whisparr On Grab → Webhook
    │  POST http://laura-backend:8000/api/v1/torrents/whisparr-webhook
    ▼
Laura Backend parses payload
    │  extracts magnetUrl or downloadId
    ▼
Laura Backend calls TorBox API
    │  POST https://api.torbox.app/v1/api/torrents/createtorrent
    ▼
TorBox downloads + seeds (cloud)
    │  (no local download needed)
    ▼
TorBox WebDAV syncs files
    │  rclone mount: /data/torbox
    ▼
Stash scans /data/torbox
    │  (scheduled scan or manual trigger)
    ▼
Media appears in Stash library
    │
    ▼
Users browse, search, stream via Frontend
```

## User Search Flow

```
User types query in Frontend
    │
    ▼
GET /api/v1/prowlarr/search?query=...
    │  proxy → Prowlarr API → indexers
    ▼
Results returned with magnet links
    │
    ▼
User clicks → POST /api/v1/torrents/add
    │  TorBox creates torrent
    ▼
User gets stream link → GET /api/v1/torrents/stream/{file_id}
    │  TorBox CDN URL
    ▼
Stream in browser or download
```

## Auth Flow

```
User visits laura-suite.app
    │  no session → redirect to /login
    ▼
Login form → POST /api/v1/auth/login
    │  Backend calls Supabase Auth
    ▼
Returns JWT token
    │  stored in Supabase session
    ▼
All subsequent API calls include:
    Authorization: Bearer <token>
    │
    ▼
Backend verifies JWT with Supabase
    │  if valid → return data
    │  if expired → 401 → redirect to login
```
