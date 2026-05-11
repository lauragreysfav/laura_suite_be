# Getting Started

## Browsing the Library

Open the frontend at http://localhost:5173

### Main Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Stats overview, recently added |
| **Scenes** | Browse all scenes, filter by name |
| **Performers** | Browse performers, click for scene list |
| **Studios** | Browse studios, click for scene list |
| **Search** | Search Prowlarr indexers for torrents |
| **Torrents** | TorBox torrent management |
| **Whisparr** | Whisparr monitored movies |
| **Ops** | System health dashboard |

## Searching for Content

1. Go to **Search** page
2. Type your query (e.g. `gal richie`)
3. Select indexer group:
   - **JAV** — Japanese adult video indexers
   - **Western** — Western adult indexers
   - **General** — Public trackers
4. Click Search
5. Results show with magnet links

## Adding a Torrent

1. From Search results, get a magnet link
2. Go to **Torrents** page
3. Paste magnet → click Add
4. TorBox starts downloading (cloud)
5. Once done, files appear in Stash library

## Streaming

1. From Torrents page, click a torrent to see its files
2. Click a file → get stream URL
3. Stream in browser or download

## Admin Panel

Visit `/admin` after logging in:
- **Dashboard** — user count, system status
- **Users** — view registered users and roles
- **System** — backend health status
