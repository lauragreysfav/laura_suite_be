# Library API

Proxies Stash GraphQL API. All endpoints under `/api/v1/`.

## Get Stats

```http
GET /api/v1/stash/stats
```

Returns scene, performer, studio counts.

## Get Scenes

```http
GET /api/v1/stash/scenes?q=&page=1&per_page=40&sort=date&direction=desc
GET /api/v1/stash/scenes/{id}
```

## Get Performers

```http
GET /api/v1/stash/performers?q=&page=1&per_page=40
GET /api/v1/stash/performers/{id}
```

## Get Studios

```http
GET /api/v1/stash/studios?q=&page=1&per_page=40
GET /api/v1/stash/studios/{id}
```

## Scan Library

```http
POST /api/v1/library/scan
```

Triggers Stash library scan.

## Refresh WebDAV

```http
POST /api/v1/library/refresh-webdav
```

Refreshes TorBox WebDAV cache.
