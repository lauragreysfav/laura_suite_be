# Quickstart

## Prerequisites

- Windows with Docker Desktop (WSL2 backend)
- NVIDIA GPU with drivers (optional, for Stash transcoding)
- TorBox account with API key
- Supabase project

## 1. Clone

```powershell
git clone https://github.com/lauragreysfav/laura_suite_be.git
git clone https://github.com/lauragreysfav/laura_suite_fe.git
```

## 2. Configure Environment

```powershell
cd laura_suite_be
cp .env.example .env
```

Edit `.env` with your keys (see [Environment Reference](environment.md)):

| Variable | Where to get it |
|----------|----------------|
| `SUPABASE_URL` | Supabase Dashboard → Project Settings → API |
| `SUPABASE_SERVICE_KEY` | Supabase Dashboard → Project Settings → API (service_role key) |
| `SUPABASE_JWT_SECRET` | Supabase Dashboard → Project Settings → API → JWT Settings |
| `TORBOX_API_KEY` | TorBox Dashboard → API Keys |
| `PROWLARR_API_KEY` | Prowlarr UI → Settings → General |
| `WHISPARR_API_KEY` | Whisparr UI → Settings → General |

## 3. Start Backend Services

```powershell
docker compose up -d
```

This starts: FlareSolverr, Prowlarr, Whisparr, Stash, Laura Backend.

Check status:
```powershell
docker ps
```

## 4. Start Frontend

```powershell
cd laura_suite_fe
npm install
npm run dev
```

Open http://localhost:5173

## 5. Create Admin User

Once Supabase is configured, register via the frontend or API:

```powershell
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your-password"}'
```

## 6. Verify

| Service | URL | Status |
|---------|-----|--------|
| Frontend | http://localhost:5173 | ✅ |
| Backend API | http://localhost:8000 | ✅ |
| Stash | http://localhost:9999 | ✅ |
| Prowlarr | http://localhost:9696 | ✅ |
| Whisparr | http://localhost:6969 | ✅ |
