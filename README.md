# Laura Suite Backend

FastAPI backend for Laura Suite — bridges Whisparr, TorBox, and Stash.

## How to Start Everything

### 1. Start Docker Services (Backend Stack)

```powershell
cd "C:\Users\Grey Area\OneDrive\Documents\LauraSuite"
docker compose up -d
```

This starts all 5 containers: FlareSolverr, Prowlarr, Whisparr, Stash, and the backend itself.

### 2. Start Frontend (Host-side, separate terminal)

```powershell
cd "C:\Users\Grey Area\OneDrive\Documents\LauraSuite\frontend"
npm run dev
```

Frontend runs on host (not in Docker) for hot-reload during development.

### 3. Quick Start Scripts

Existing scripts in `scripts/`:

| Script | Description |
|--------|-------------|
| `start-all.ps1` | Starts backend + frontend |
| `start-backend.ps1` | Starts backend on host (dev mode) |
| `start-frontend.ps1` | Starts Vite frontend dev server |

Scripts use `D:\LauraSuite\` path — update if running from OneDrive path.

## Access Services

| Service | URL |
|---------|-----|
| Stash | http://localhost:9999 |
| Prowlarr | http://localhost:9696 |
| Whisparr | http://localhost:6969 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Frontend | http://localhost:5173 |
| FlareSolverr | http://localhost:8191 |

## rclone / TorBox WebDAV

Stash container has rclone built in (custom Dockerfile in `stash/`). On startup it auto-mounts TorBox WebDAV to `/data/torbox` — no manual steps needed.

## Directory Structure

```
backend/
├── README.md
├── Dockerfile
├── requirements.txt
├── .env               # API keys (do not commit)
├── app/
│   ├── main.py        # FastAPI entry point
│   ├── config.py      # Settings from .env
│   ├── api/v1/        # Route handlers
│   │   ├── system.py
│   │   ├── torrents.py
│   │   ├── library.py
│   │   ├── whisparr.py
│   │   └── prowlarr.py
│   ├── services/      # Business logic
│   │   ├── torbox.py
│   │   ├── stash.py
│   │   └── prowlarr.py
│   └── models/
└── docs/              # Documentation
    ├── architecture.md
    ├── vpn-routing.md
    └── adding-indexers.md
```
