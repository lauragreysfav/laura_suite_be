# Laura Suite — Architecture & Operations Guide

## Overview

Laura Suite is a self-hosted media pipeline for automated adult content discovery, download, and library management. It runs on **Windows via Docker Desktop (WSL2 backend)** with all services containerized except the React frontend (which runs on the host for hot-reload during development).

### Core Principle: Zero Local Storage

All new media is downloaded via **TorBox** (cloud torrenting, ₹250/mo) and served through **TorBox WebDAV**. The local `D:\LauraMedia` holds only previously downloaded content (~49.6 GB organized into Scenes, Clips, Images, GIFs, Favorites). Stash scans both sources transparently.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DOCKER DESKTOP (WSL2)                    │
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │   FlareSolverr    │    │    Prowlarr      │                   │
│  │   :8191           │◄──►│   :9696          │                   │
│  │   (Cloudflare     │    │   (Indexer mgmt) │                   │
│  │    bypass proxy)  │    └────────┬─────────┘                   │
│  └──────────────────┘             │                             │
│                                   │ syncs indexers              │
│                                   ▼                             │
│  ┌──────────────────────────────────────────────────┐           │
│  │                 Whisparr                          │           │
│  │                 :6969                             │           │
│  │   (Monitors actresses, grabs releases via TorBox) │           │
│  └────────────────────┬─────────────────────────────┘           │
│                       │ On Grab → Webhook                       │
│                       ▼                                         │
│  ┌──────────────────────────────────────────────────┐           │
│  │              Laura Backend                        │           │
│  │              :8000                                │           │
│  │   POST /api/v1/torrents/whisparr-webhook          │           │
│  │     → adds magnet to TorBox via API               │           │
│  │   GET  /api/v1/system/status                      │           │
│  │   POST /api/v1/library/scan                       │           │
│  │   POST /api/v1/library/refresh-webdav             │           │
│  └────────────────────┬─────────────────────────────┘           │
│                       │ TorBox API                              │
│                       ▼                                         │
│              ☁️  TorBox Cloud (external)                        │
│                       │ WebDAV                                  │
│                       ▼                                         │
│  ┌──────────────────────────────────────────────────┐           │
│  │              Stash (nerethos/stash)               │           │
│  │              :9999                                │           │
│  │   GPU-accelerated transcoding (NVENC/NVDEC)       │           │
│  │                                                   │           │
│  │   Mounts:                                         │           │
│  │   /data/torbox     ← rclone mount (TorBox WebDAV) │           │
│  │   /data/lauramedia ← D:\LauraMedia (host bind)    │           │
│  │                                                   │           │
│  │   Config: ./config/stash/ → /root/.stash/         │           │
│  │   Cache:  ./stash/cache/     → /cache/            │           │
│  │   Gen:    ./stash/generated/ → /generated/        │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                 │
│  ┌──────────────────────────────────────────────────┐           │
│  │              Frontend (HOST ONLY)                │           │
│  │              :5173                               │           │
│  │   React + Vite + Tailwind CSS                    │           │
│  │   Runs directly on Windows (not in Docker)       │           │
│  │   Hot-reload via `npm run dev`                   │           │
│  └──────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Network Topology

| Service | Internal URL | External URL | Container Name |
|---------|-------------|-------------|----------------|
| FlareSolverr | http://flaresolverr:8191 | http://localhost:8191 | flaresolverr |
| Prowlarr | http://prowlarr:9696 | http://localhost:9696 | prowlarr |
| Whisparr | http://whisparr:6969 | http://localhost:6969 | whisparr |
| Stash | http://stash:9999 | http://localhost:9999 | stash |
| Laura Backend | http://laura-backend:8000 | http://localhost:8000 | laura-backend |

All containers share the `laurasuite_default` bridge network (auto-created by Docker Compose). Services communicate via container names.

---

## Services

### 1. FlareSolverr (`ghcr.io/flaresolverr/flaresolverr:latest`)
- **Purpose**: Bypasses Cloudflare challenge pages for indexers that require it
- **Port**: 8191
- **Proxy**: Configured in Prowlarr as HTTP proxy (id=1) pointing to http://flaresolverr:8191

### 2. Prowlarr (`ghcr.io/hotio/prowlarr:latest`)
- **Purpose**: Indexer management — syncs indexers to Whisparr
- **Port**: 9696
- **Config**: `./config/prowlarr/` → `/config`
- **Environment**: `APP_UID=1000`, `APP_GID=1000`
- **Indexers**: 13 added, 9 synced to Whisparr (adult/XXX categories). ~3 more planned behind Cloudflare + VPN.

### 3. Whisparr (`ghcr.io/hotio/whisparr:latest`)
- **Purpose**: Monitors actresses, searches indexers, grabs releases
- **Port**: 6969
- **Config**: `./config/whisparr/` → `/config`
- **Media mount**: `D:\LauraMedia` → `/data/lauramedia`
- **Download client**: TorrentBlackhole (writes `.torrent` files to `./torrents/blackhole/`)
- **Notification**: Webhook to `http://laura-backend:8000/api/v1/torrents/whisparr-webhook` (id=2, "Laura Suite TorBox")

### 4. Stash (custom: `nerethos/stash` + rclone)
- **Purpose**: Media library management, GPU-accelerated transcoding
- **Port**: 9999
- **Custom image**: Built from `./stash/Dockerfile` extending `nerethos/stash:latest`
- **Modifications**: Installs `rclone` + `fuse3`; wrapper entrypoint mounts TorBox WebDAV before starting Stash

#### Volumes
| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `./config/stash/` | `/root/.stash/` | Config, database, blobs, scrapers, plugins |
| `./stash/metadata/` | `/metadata/` | Stash metadata |
| `./stash/cache/` | `/cache/` | Scene/image cache |
| `./stash/generated/` | `/generated/` | Generated previews, sprites, covers |
| `D:\LauraMedia` | `/data/lauramedia` | Local media library |
| *(rclone mount)* | `/data/torbox` | TorBox WebDAV (cloud content) |

#### GPU Passthrough
- **Image**: `nerethos/stash:latest` (includes jellyfin-ffmpeg with NVENC/NVDEC)
- **Docker Desktop**: WSL2 backend supports `--gpus all`
- **Deploy config**:
  ```yaml
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  ```
- **Note**: The official `stashapp/stash:latest` does NOT include NVIDIA drivers — use `nerethos/stash` for GPU transcoding.

### 5. Laura Backend (custom: `./backend/Dockerfile`)
- **Purpose**: REST API bridge between Whisparr, TorBox, and Stash
- **Port**: 8000
- **Stack**: Python 3.12 + FastAPI + SQLAlchemy
- **Config**: `.env` file with TorBox API key, WebDAV creds, Stash URL, DB path
- **Database**: `./data/laura.db` → `/data/laura.db`

#### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/torrents/` | List TorBox torrents |
| POST | `/api/v1/torrents/add` | Add magnet to TorBox |
| DELETE | `/api/v1/torrents/{id}` | Remove torrent from TorBox |
| POST | `/api/v1/torrents/whisparr-webhook` | Whisparr Grab webhook → TorBox |
| GET | `/api/v1/system/status` | Check all service health |
| POST | `/api/v1/library/scan` | Trigger Stash library scan |
| POST | `/api/v1/library/refresh-webdav` | Refresh TorBox WebDAV cache |

### 6. Frontend (HOST ONLY — NOT in Docker)
- **Purpose**: React UI for Laura Suite
- **Tech**: React 19 + Vite 8 + Tailwind CSS 4 + TypeScript 6 + React Router 7
- **Port**: 5173 (`npm run dev`)
- **Runs on**: Host Windows directly (not containerized)
- **Why host-only**: Hot-reload during development requires filesystem watching that doesn't work well in Docker on Windows

---

## TorBox WebDAV Integration (T: drive)

### Problem
Windows network drives (T: mapped via rclone WebDAV) are not accessible inside Docker containers on WSL2. Bind mount `T:\:/data/torbox` creates an empty directory.

### Solution: rclone mount inside Stash container

A custom Dockerfile (`./stash/Dockerfile`) extends `nerethos/stash:latest`:
1. Installs `rclone` and `fuse3` via apt
2. Copies `rclone.conf` (contains TorBox WebDAV credentials) to `/etc/rclone.conf`
3. Copies a wrapper entrypoint `entrypoint.sh` that:
   - Runs `rclone mount torbox: /data/torbox` in background
   - Waits for mount to be ready (up to 15s)
   - Then executes the original Stash entrypoint

**Key files**:
- `./stash/Dockerfile` — builds custom Stash image
- `./stash/entrypoint.sh` — wrapper that mounts WebDAV, then starts Stash
- `./config/rclone.conf` — rclone config with obscured TorBox WebDAV password

### Rclone Config (`./config/rclone.conf`)
```ini
[torbox]
type = webdav
url = https://webdav.torbox.app
vendor = other
user = maasifar@gmail.com
pass = <obscured>
```

### Native Windows TorBox Mount (Legacy / Desktop Scripts)
- **`Mount TorBox.bat`** — mounts T: via `rclone mount torbox: T:`
- **`Check TorBox.bat`** — runs `Refresh-TorBox.vbs` to refresh WebDAV
- **`Refresh-TorBox.vbs`** — silent VBS launcher for the refresh script
- **Scheduled task** — refreshes WebDAV every 2 minutes
- **Note**: These are for native Stash usage. Docker Stash handles the mount internally now.

---

## Pipeline: Whisparr → TorBox → Stash

```
Whisparr monitors actress
        │
        ▼
Whisparr grabs release (magnet URL)
        │
        ▼
Whisparr On Grab → Webhook notification
        │
        ▼
Laura Backend POST /api/v1/torrents/whisparr-webhook
        │  ├─ Parses magnetUrl or downloadId from payload
        │  └─ Calls TorBox API to create torrent
        ▼
TorBox Cloud downloads/seeds
        │
        ▼
TorBox WebDAV (auto-syncs, refreshed every 2 min)
        │
        ▼
Stash scans /data/torbox/ (rclone mount)
        │
        ▼
Media available in Stash library
```

---

## Quick Start

### Prerequisites
- Windows with Docker Desktop (WSL2 backend)
- NVIDIA GPU with drivers (optional, for transcoding)
- TorBox account with API key
- Tailscale (optional, for remote access)

### First-time Setup

```powershell
# 1. Clone / navigate to project
cd "C:\Users\Grey Area\OneDrive\Documents\LauraSuite"

# 2. Start all services
docker compose up -d

# 3. Verify all 5 containers are running
docker ps

# 4. Start frontend (host-side, separate terminal)
cd frontend
npm run dev
```

### Starting / Stopping

```powershell
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart a specific service
docker compose restart stash

# Rebuild and restart Stash (after Dockerfile/entrypoint changes)
docker compose up -d stash --build
```

### Accessing Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Stash | http://localhost:9999 | Auth disabled |
| Prowlarr | http://localhost:9696 | API key: `fdd5c4ef67e74e12b5e6c81f2c354527` |
| Whisparr | http://localhost:6969 | API key: `8c74a3dc57954d41ae478d8862a8300d` |
| Laura API | http://localhost:8000 | N/A (internal) |
| Frontend | http://localhost:5173 | N/A (dev) |
| FlareSolverr | http://localhost:8191 | N/A (proxy) |

### Viewing Logs

```powershell
# Follow all logs
docker compose logs -f

# Specific service
docker compose logs stash -f
docker compose logs laura-backend -f

# Check mount status
docker exec stash mountpoint -q /data/torbox && echo "Mounted" || echo "Not mounted"
docker exec stash ls /data/torbox/
```

---

## Directory Structure

```
LauraSuite/
├── docker-compose.yml          # Main Compose file (all services)
├── backend/                    # FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env                    # 🔒 API keys (not committed)
│   ├── app/
│   │   ├── config.py           # Pydantic settings (reads .env)
│   │   ├── main.py             # FastAPI app factory
│   │   ├── api/v1/
│   │   │   ├── system.py       # /system/status
│   │   │   ├── torrents.py     # /torrents/*, /torrents/whisparr-webhook
│   │   │   └── library.py      # /library/scan, /library/refresh-webdav
│   │   ├── services/
│   │   │   ├── torbox.py       # TorBox API client
│   │   │   └── stash.py        # Stash GraphQL client
│   │   └── models/             # SQLAlchemy models (future)
│   └── docs/                   # 📚 Documentation
│       ├── architecture.md     # This document
│       ├── vpn-routing.md      # Proton VPN via gluetun for Prowlarr
│       └── adding-indexers.md  # Adding CloudFlare-blocked indexers
├── frontend/                   # React + Vite (host-side)
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   └── public/
├── config/
│   ├── prowlarr/              # Prowlarr config (Docker volume)
│   ├── whisparr/              # Whisparr config (Docker volume)
│   ├── stash/                 # Stash config (Docker volume)
│   │   ├── config.yml         # Stash configuration (Docker paths)
│   │   ├── custom.css         # Modern Dark theme CSS
│   │   ├── stash-go.sqlite    # Stash database
│   │   ├── blobs/
│   │   ├── scrapers/
│   │   └── plugins/
│   └── rclone.conf            # TorBox WebDAV rclone config
├── stash/                     # Custom Stash Docker build context
│   ├── Dockerfile              # Extends nerethos/stash + rclone
│   ├── entrypoint.sh           # Mounts WebDAV, then starts Stash
│   ├── rclone.conf             # Copied to /etc/rclone.conf in image
│   ├── metadata/
│   ├── cache/
│   └── generated/
├── data/                      # Laura Backend data (Docker volume)
│   └── laura.db
├── torrents/
│   └── blackhole/             # Whisparr TorrentBlackhole output
└── scripts/
    └── whisparr-grab.ps1      # Legacy (replaced by Webhook)
```

---

## Environment Variables (`.env`)

Located at `./backend/.env`:

| Variable | Value | Purpose |
|----------|-------|---------|
| `TORBOX_API_KEY` | `dd52f451-...` | TorBox API authentication |
| `TORBOX_WEBDAV_USER` | `maasifar@gmail.com` | WebDAV username |
| `TORBOX_WEBDAV_PASS` | `Asifar632@` | WebDAV password |
| `TORBOX_WEBDAV_URL` | `https://webdav.torbox.app` | WebDAV endpoint |
| `STASH_URL` | `http://stash:9999` | Stash internal URL |
| `STASH_API_KEY` | *(empty)* | Stash auth (disabled) |
| `DATABASE_PATH` | `/data/laura.db` | Laura Backend DB path |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Development

### Backend
```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

### Hot-reload notes
- Frontend runs on host (port 5173) with live HMR
- Backend runs in Docker by default; for development, run locally with `uvicorn --reload`
- When running backend locally, update `.env` `STASH_URL=http://localhost:9999`

---

## Maintenance

### Docker Desktop
- Ensure WSL2 backend is selected in Docker Desktop Settings → General
- Network drives (T:) are NOT accessible via WSL2 bind mounts — use the rclone mount inside Stash instead

### Database Backups
```powershell
# Stash database
copy ".\config\stash\stash-go.sqlite" ".\config\stash\stash-go.sqlite.bak"

# Laura database
copy ".\data\laura.db" ".\data\laura.db.bak"
```

### Updating Images
```powershell
docker compose pull
docker compose up -d --build
```

### Troubleshooting

**Stash won't start — "config file not found"**
- Ensure `./config/stash/config.yml` exists (copied from `~/.stash/`)
- Check volume mount: `docker logs stash`

**WebDAV mount not showing files**
```powershell
docker exec stash rclone ls torbox: --config /etc/rclone.conf
docker exec stash mountpoint -q /data/torbox
docker exec stash ls /data/torbox/
```

**Port conflicts on startup**
Check for native services still running:
```powershell
netstat -ano | findstr ":9999 :9696 :6969 :8000"
```
Kill any stale `stash-win.exe` or `uvicorn` processes.

**GPU not detected in Stash**
- Verify NVIDIA drivers installed on Windows host
- Check `docker exec stash nvidia-smi`
- Stash logs show: `[InitHWSupport] Hardware codec initialization...`

---

## Desktop Scripts (for reference)

- **`Laura Suite.bat`** → `docker compose up -d` (starts all Docker services)
- **`Mount TorBox.bat`** → Native Windows rclone T: mount (for using native Stash)
- **`Check TorBox.bat`** → Runs `D:\LauraMedia\Refresh-TorBox.vbs` (triggers WebDAV refresh via scheduled task)

The native scripts are legacy — Docker Stash mounts WebDAV internally.

---

## Tailscale Remote Access

Tailscale is installed on this machine. All services are accessible from any Tailscale-connected device at:
- `http://<tailscale-ip>:9999` (Stash)
- `http://<tailscale-ip>:9696` (Prowlarr)
- `http://<tailscale-ip>:6969` (Whisparr)
