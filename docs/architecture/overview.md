# System Overview

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   DOCKER (single host)                       │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐                       │
│  │ FlareSolverr  │    │  Prowlarr    │                       │
│  │ :8191         │◄──►│ :9696        │                       │
│  │ (CF bypass)   │    │ (indexers)   │                       │
│  └──────────────┘    └──────┬───────┘                       │
│                             │ syncs                         │
│                             ▼                               │
│  ┌────────────────────────────────────┐                     │
│  │            Whisparr                 │                     │
│  │            :6969                    │                     │
│  │  (monitors, grabs, webhook)        │                     │
│  └────────────────┬───────────────────┘                     │
│                   │ On Grab → Webhook                       │
│                   ▼                                         │
│  ┌────────────────────────────────────┐                     │
│  │        Laura Backend (FastAPI)     │                     │
│  │        :8000                       │                     │
│  │  POST /torrents/whisparr-webhook   │                     │
│  │  GET  /torrents/stream/:id         │                     │
│  │  POST /auth/register               │                     │
│  │  POST /auth/login                  │                     │
│  └──────┬──────────────────────┬──────┘                     │
│         │ TorBox API           │ Supabase                   │
│         ▼                      ▼                            │
│  ┌──────────────┐     ┌──────────────────┐                  │
│  │  TorBox Cloud│     │    Supabase      │                  │
│  │  (external)  │     │  (cloud)         │                  │
│  │  torrenting  │     │  auth + DB       │                  │
│  │  + WebDAV    │     └──────────────────┘                  │
│  └──────┬───────┘                                           │
│         │ rclone mount                                      │
│         ▼                                                   │
│  ┌────────────────────────────────────┐                     │
│  │            Stash                    │                     │
│  │            :9999                    │                     │
│  │  GPU-accelerated media library     │                     │
│  │  Scans: /data/torbox (WebDAV)      │                     │
│  │         /data/lauramedia (local)   │                     │
│  └────────────────────────────────────┘                     │
│                                                             │
│  ┌────────────────────────────────────┐                     │
│  │         Frontend (React + Vite)    │                     │
│  │         :5173 (dev)                │                     │
│  │  Public: browse, search, stream    │                     │
│  │  Admin: users, system (Refine)     │                     │
│  └────────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| **FlareSolverr** | 8191 | Cloudflare challenge bypass for indexers |
| **Prowlarr** | 9696 | Indexer management, syncs to Whisparr |
| **Whisparr** | 6969 | Monitor actresses, grab releases, webhook |
| **Stash** | 9999 | Media library with GPU transcoding |
| **Laura Backend** | 8000 | FastAPI — auth, torrents, proxy APIs |
| **Frontend** | 5173 | React SPA — browse, search, admin |

## Network

- All services communicate via Docker bridge network (`laurasuite_default`)
- Ports bound to `127.0.0.1` only (no LAN access)
- Prowlarr + FlareSolverr optionally route through gluetun VPN for blocked indexers
