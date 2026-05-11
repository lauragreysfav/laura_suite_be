# Troubleshooting

## Stash Won't Start — YAML Error

```
config initialization error: yaml: line N: mapping values are not allowed in this context
```

**Fix**: Check `config/stash/config.yml` for indentation errors. The `scan:` block should look like:

```yaml
taskDefaults:
    scan:
        rescan: false
        scanGenerateClipPreviews: true
        ...
```

All 8 keys (`rescan`, `scanGenerate*`) must be **siblings** at the same indentation under `scan:`.

## Port Conflicts

```powershell
netstat -ano | findstr ":9999 :9696 :6969 :8000"
```

Kill any stale processes. All Laura Suite services run in Docker — stop any native installations.

## Stash Not Responding

```powershell
docker logs stash --tail 20
docker exec stash curl -s http://localhost:9999/graphql -X POST -d '{"query":"{systemStatus{status}}"}'
```

## WebDAV Mount Empty

```powershell
docker exec stash rclone ls torbox: --config /etc/rclone.conf
docker exec stash mountpoint -q /data/torbox && echo "Mounted" || echo "Not mounted"
```

## Prowlarr Indexers Blocked

Error: `Connection refused` for adult indexers.

**Cause**: ISP blocks the site. Docker bypasses host VPN.

**Fix**: Set up gluetun VPN (see [VPN Routing](vpn-routing.md)).

## Backend Can't Reach Prowlarr/Whisparr

Ensure all containers are on the same Docker network:

```powershell
docker compose up -d
docker network inspect laurasuite_default
```

## Frontend Auth Issues

- Check `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are set in `laura_suite_fe/.env`
- Verify Supabase project is active
- Check browser console for CORS errors

## Database Issues

Supabase tables not found:

```sql
-- Run in Supabase SQL Editor
select * from information_schema.tables where table_schema = 'public';
```

Missing `profiles` table? Run the SQL from [Supabase Setup](../setup/supabase-setup.md).
