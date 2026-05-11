# Torrent Streaming via TorBox

## How It Works

Laura Suite does NOT store media files locally. Instead, it leverages **TorBox Cloud** as both the downloader and CDN.

```
User searches scene
        │
        ▼
Search Prowlarr indexers → results with magnet links
        │
        ▼
User picks a result
        │
        ▼
POST /api/v1/torrents/add  →  TorBox API creates torrent
        │
        ▼
TorBox downloads + caches the content (cloud)
        │
        ▼
GET /api/v1/torrents/{id}/files  → list downloadable files
        │
        ▼
GET /api/v1/torrents/stream/{file_id}  → TorBox CDN URL
        │
        ▼
User streams or downloads directly from TorBox CDN
```

## Benefits

- **Zero local storage** — TorBox caches everything
- **Instant streaming** — if already cached (check with `GET /api/v1/torrents/`)
- **CDN-speed downloads** — TorBox hosts on fast infrastructure
- **Magnet links** — users can grab the original magnet for offline editing tools

## API Flow

```python
# Frontend usage
const files = await api.getTorrentFiles(torrentId);
const stream = await api.getStreamUrl(files[0].id);
// stream.url = TorBox CDN link → use in <video> or download
```

## TorBox WebDAV

TorBox also provides WebDAV access. Stash mounts this via rclone:

```
rclone mount torbox: /data/torbox
```

Stash scans `/data/torbox` periodically, so downloaded content appears in the library automatically.
