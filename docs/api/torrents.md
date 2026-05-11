# Torrents API

All endpoints are under `/api/v1/torrents/`.

## List TorBox Torrents

```http
GET /api/v1/torrents/
```

Response: TorBox API response with all user's torrents.

## Add Magnet

```http
POST /api/v1/torrents/add
Content-Type: application/json

{
    "magnet": "magnet:?xt=urn:btih:...",
    "seed": 1
}
```

## Delete Torrent

```http
DELETE /api/v1/torrents/{torrent_id}
```

## Whisparr Webhook

```http
POST /api/v1/torrents/whisparr-webhook
Content-Type: application/json

{
    "eventType": "Grab",
    "release": {
        "magnetUrl": "magnet:?xt=urn:btih:...",
        "title": "Movie.Title.2026.1080p"
    }
}
```

## List Torrent Files (authenticated)

```http
GET /api/v1/torrents/{torrent_id}/files
Authorization: Bearer <token>
```

Response:
```json
{
    "torrent_id": "12345",
    "files": [
        {"id": "file_1", "name": "video.mp4", "size": 1500000000},
        {"id": "file_2", "name": "subtitles.srt", "size": 50000}
    ]
}
```

## Get Stream URL (authenticated)

```http
GET /api/v1/torrents/stream/{file_id}
Authorization: Bearer <token>
```

Response:
```json
{
    "url": "https://api.torbox.app/v1/api/torrents/files/{file_id}/download?token=...",
    "file_id": "file_1"
}
```

The returned URL is a direct TorBox CDN link — users can stream or download.
