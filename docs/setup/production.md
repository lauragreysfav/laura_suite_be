# Production Deployment

## Build Frontend

```powershell
cd laura_suite_fe
npm run build
```

Output goes to `dist/`. Serve these static files with Nginx or the backend.

## Docker Compose Production

```powershell
cd laura_suite_be
docker compose up -d --build
```

Override for production (`docker-compose.prod.yml`):

```yaml
services:
  laura-backend:
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      - LOG_LEVEL=WARNING

  # Add Nginx for frontend
  nginx:
    image: nginx:alpine
    ports:
      - "127.0.0.1:80:80"
    volumes:
      - ../laura_suite_fe/dist:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
```

## Domain + SSL

Use a reverse proxy (Caddy, Nginx, or Traefik) with Let's Encrypt:

- `https://api.laura-suite.app` → `127.0.0.1:8000`
- `https://laura-suite.app` → static files or `127.0.0.1:5173`

## Backup

```powershell
# Stash DB
copy "config/stash/stash-go.sqlite" "backups/stash-$(Get-Date -Format yyyyMMdd).sqlite"

# Supabase (via Dashboard → Database → Backup)
# Laura backend DB
copy "data/laura.db" "backups/laura-$(Get-Date -Format yyyyMMdd).db"
```

## Monitoring

- Frontend: Operations Dashboard at `/operations`
- Backend: `GET /api/v1/system/status`
- Docker: `docker stats`, `docker compose logs -f`
