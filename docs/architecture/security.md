# Security

## Port Binding

All Docker services bind to `127.0.0.1` only — no LAN or WAN access:

```yaml
ports:
  - "127.0.0.1:9999:9999"  # Stash
  - "127.0.0.1:9696:9696"  # Prowlarr
  - "127.0.0.1:6969:6969"  # Whisparr
  - "127.0.0.1:8000:8000"  # Backend
  - "127.0.0.1:8191:8191"  # FlareSolverr
```

For remote access, use Tailscale or SSH tunneling.

## Authentication

- **Supabase Auth** handles user registration and login
- **JWT tokens** are used for all authenticated API calls
- Passwords are hashed by Supabase (bcrypt)
- Tokens expire after 1 hour (configurable in Supabase)

## Secrets Management

- `.env` files are **gitignored** — never commit secrets
- Use `.env.example` as a template
- Supabase service_role key has admin access — treat it like a root password
- rclone.conf contains WebDAV credentials — keep it out of version control

## VPN for Indexers

Prowlarr and FlareSolverr can route through gluetun VPN for ISP-blocked sites. See [VPN Routing](../ops/vpn-routing.md).

## CORS

The backend only accepts requests from:
- `http://localhost:5173` (dev frontend)
- `http://127.0.0.1:5173` (dev frontend)

In production, update `allow_origins` in `app/main.py`.
