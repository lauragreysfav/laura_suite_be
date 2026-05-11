# Environment Variables

## Backend (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service_role key |
| `SUPABASE_JWT_SECRET` | Yes | JWT secret for token verification |
| `TORBOX_API_KEY` | Yes | TorBox API authentication |
| `TORBOX_WEBDAV_USER` | Yes | WebDAV username (TorBox email) |
| `TORBOX_WEBDAV_PASS` | Yes | WebDAV password |
| `TORBOX_WEBDAV_URL` | No | Default: `https://webdav.torbox.app` |
| `STASH_URL` | No | Default: `http://stash:9999` |
| `STASH_API_KEY` | No | Stash API key (optional) |
| `WHISPARR_URL` | No | Default: `http://whisparr:6969` |
| `WHISPARR_API_KEY` | Yes | Whisparr API key |
| `PROWLARR_URL` | No | Default: `http://prowlarr:9696` |
| `PROWLARR_API_KEY` | Yes | Prowlarr API key |
| `DATABASE_PATH` | No | Default: `/data/laura.db` |
| `LOG_LEVEL` | No | Default: `INFO` |
| `SECRET_KEY` | No | Additional secret for app |

## Frontend (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_SUPABASE_URL` | Yes | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | Supabase anon/public key |
| `VITE_API_URL` | No | Backend URL (default: `http://localhost:8000`) |
