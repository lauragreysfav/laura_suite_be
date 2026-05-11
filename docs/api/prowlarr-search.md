# Prowlarr Search API

Proxies Prowlarr search. Endpoint under `/api/v1/`.

## Search Indexers

```http
GET /api/v1/prowlarr/search?query=gal+richie&indexer_ids=10,11
```

Parameters:
| Param | Required | Description |
|-------|----------|-------------|
| `query` | Yes | Search terms |
| `indexer_ids` | No | Comma-separated indexer IDs to search |

## List Indexers

```http
GET /api/v1/prowlarr/indexers
```

Returns all configured indexers with their IDs and status.

## Indexer Groups (Frontend)

The frontend groups indexers by name matching:

| Group | Pattern |
|-------|---------|
| **JAV** | `JAV|OneJAV|Free JAV|U3C3|xxxtor|sukebei` |
| **Western** | `MyPornClub|PornoTorrent|PornRips|XXXClub` |
| **General** | `Pirate Bay|1337x|RuTor|TorrentDownload|kickasstorrents` |
