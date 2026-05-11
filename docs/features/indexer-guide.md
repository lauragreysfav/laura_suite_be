# Indexer Guide

## Current Indexers

| # | Name | Status | Proxy |
|---|------|--------|-------|
| 1 | Nyaa.si | ✅ | — |
| 2 | The Pirate Bay | ✅ | — |
| 3 | sukebei.nyaa.si | ✅ | — |
| 4 | OneJAV | ✅ | — |
| 5 | RuTor | ✅ | — |
| 6 | U3C3 | ✅ | — |
| 7 | TorrentDownload | ✅ | — |
| 8 | xxxtor | ✅ | — |
| 9 | MyPornClub | ✅ | — |
| 10 | Free JAV Torrent | ✅ | — |
| 11 | PornoTorrent | ✅ | — |
| 12 | PornRips | ✅ | — |
| 13 | XXXClub | ✅ | sex |
| *14* | *1337x* | *blocked* | *needs VPN* |
| *15* | *TorrentGalaxyClone* | *blocked* | *needs VPN* |
| *16* | *kickasstorrents.to* | *blocked* | *needs VPN* |

## Adding Blocked Indexers

Indexers blocked by ISP or Cloudflare need special handling:

1. **FlareSolverr proxy** — for Cloudflare challenges. Tag: `sex`
2. **gluetun VPN** — for ISP-level blocks. Routes Prowlarr + FlareSolverr through VPN.

See [VPN Routing](../ops/vpn-routing.md).

## Adding via Prowlarr UI

```powershell
# Open Prowlarr
start http://localhost:9696

# Click Indexers → Add Indexer
# Search for name
# Configure:
#   - Tags: sex (for Cloudflare indexers)
#   - Priority: 25
#   - Prefer Magnet URL: ✅
# Click Test → Save
```

## Tag Behavior

- **No tags on Whisparr app** = syncs all indexers
- **FlareSolverr proxy has tag `sex`** = only indexers with tag `sex` use the proxy
- **Indexer has tag `sex`** = routes through FlareSolverr + syncs to Whisparr
