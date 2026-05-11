# Adding CloudFlare-Blocked Indexers via Prowlarr UI

## Overview

Some adult torrent indexers (1337x, TorrentGalaxyClone, kickasstorrents.to) are blocked by **CloudFlare DDoS protection** or **ISP-level blocking**. These cannot be added via the Prowlarr API (which tests connectivity at creation time and fails), and must be added through the **Prowlarr web UI** with specific configurations.

### Current State

| Indexer | Status | How Added |
|---------|--------|-----------|
| Nyaa.si | ✅ Added + synced | API |
| The Pirate Bay | ✅ Added + synced | API |
| sukebei.nyaa.si | ✅ Added + synced | API |
| OneJAV | ✅ Added + synced | API |
| RuTor | ✅ Added + synced (was disabled, now enabled) | API |
| U3C3 | ✅ Added + synced | API |
| TorrentDownload | ✅ Added + synced (was disabled, now enabled) | API |
| xxxtor | ✅ Added + synced | API |
| Free JAV Torrent | ✅ Added + synced | API |
| MyPornClub | ✅ Added + synced | API |
| PornoTorrent | ✅ Added + synced | API |
| PornRips | ✅ Added + synced | API |
| XXXClub | ✅ Added + synced | API |
| **1337x** | ❌ Blocked | Needs Prowlarr UI |
| **TorrentGalaxyClone** | ❌ Blocked | Needs Prowlarr UI |
| **kickasstorrents.to** | ❌ Blocked | Needs Prowlarr UI |

---

## Why API Fails for These Indexers

The Prowlarr API validates indexers at creation time by making a test connection to the site. For CloudFlare-blocked or ISP-blocked sites:

```
POST /api/v1/indexer → Prowlarr tests connection → Connection refused → 400 Bad Request
```

The web UI allows bypassing this validation by:
1. Applying the **FlareSolverr proxy** at creation (via tags)
2. Testing with the proxy active before saving

---

## Prerequisites

Before adding these indexers, ensure:

1. **FlareSolverr is running** — check `docker ps | findstr flaresolverr`
2. **FlareSolverr proxy is configured in Prowlarr** → Settings → Indexers → Indexer Proxies → FlareSolverr (should already exist)
3. **The tag `sex` exists** and is attached to the FlareSolverr proxy (already configured):
   - Tag ID: 1
   - Tag label: `sex`
4. **Prowlarr can reach these sites** — if ISP-blocked, you need VPN routing first (see `vpn-routing.md`)

---

## How FlareSolverr Proxy + Tags Work

### Proxy Configuration

| Setting | Value |
|---------|-------|
| Name | FlareSolverr |
| Implementation | FlareSolverr |
| Host | `http://flaresolverr:8191` |
| Request Timeout | 60 seconds |
| Tags | `sex` |

### Tag Behavior (Important)

From the Prowlarr documentation and source code (PR #2003):

> **"No tags on application = sync all indexers, no matter what other tags the indexers have. App has at least one tag = only if common tag found."**

This means:
- **FlareSolverr proxy** has tag `sex` → only indexers with tag `sex` use FlareSolverr
- **Whisparr app** has **no tags** → it syncs ALL indexers (including those with tag `sex`)
- **Indexers with tag `sex`** → use FlareSolverr AND sync to Whisparr

So adding tag `sex` to these indexers:
- ✅ Routes their requests through FlareSolverr (bypasses Cloudflare)
- ✅ Still syncs to Whisparr (because Whisparr has no tags)

---

## Step-by-Step: Add Indexer via Prowlarr UI

### Step 1: Open Prowlarr in Browser

Navigate to http://localhost:9696

### Step 2: Go to Indexers Page

Click **Indexers** in the main left sidebar (first item under the Search bar — **NOT Settings → Indexers**).

### Step 3: Click Add Indexer

Click the green **+ Add Indexer** button in the top-right corner.

### Step 4: Find and Select Your Indexer

In the search box, type the indexer name:
- `1337x`
- `TorrentGalaxyClone`
- `kickasstorrents.to`

Click on the matching result.

### Step 5: Configure Indexer Settings

#### Required Settings (Same for All Three)

| Field | Value | Notes |
|-------|-------|-------|
| **Enable** | ✅ Checked | Must be enabled to sync |
| **Sync Profile** | Standard | Default is fine |
| **Base Url** | *Leave empty* | Auto-populates from definition |
| **Apps Minimum Seeders** | `1` | Allow grabs with at least 1 seeder |
| **Prefer Magnet URL** | ✅ Checked | TorBox needs magnet links |
| **Indexer Priority** | `25` | Default priority |
| **Tags** | `sex` | Attaches FlareSolverr proxy |

#### Optional / Leave as Default

| Field | Value |
|-------|-------|
| Redirect | Unchecked |
| Query Limit | Empty (unlimited) |
| Grab Limit | Empty (unlimited) |
| Limits Unit | Day |
| Seed Ratio | Empty (download client default) |
| Seed Time | Empty (download client default) |
| Pack Seed Time | Empty (download client default) |

#### Indexer-Specific Fields

**1337x only:**
| Field | Value |
|-------|-------|
| Filter by Uploader | Empty (get all results) |
| Download link | iTorrents.org (default) |
| Download link (fallback) | magnet (default) |
| Disable sorting | Unchecked (only check if searches return zero results) |
| Sort requested from site | created |
| Order requested from site | desc |

**TorrentGalaxyClone only:**
| Field | Value |
|-------|-------|
| Filter by Uploader | Empty |

**kickasstorrents.to only:**
| Field | Value |
|-------|-------|
| (No extra fields beyond standard) | — |

### Step 6: Test the Connection

1. Click **Test** button
2. Wait for the test to complete (may take a few seconds with FlareSolverr)
3. If successful → green checkmark
4. If it fails → see Troubleshooting below

### Step 7: Save

Click **Save**. The indexer appears in your list with a green status indicator.

### Step 8: Verify Sync to Whisparr

1. Go to **Settings → Apps** in Prowlarr
2. Click the **Sync App Indexers** button for Whisparr
3. Open http://localhost:6969 → Settings → Indexers
4. Verify the new indexer appears in Whisparr's indexer list

---

## Expected Behavior After Adding

### What Happens During Sync

1. Prowlarr creates the indexer with tag `sex`
2. FlareSolverr proxy (also tag `sex`) intercepts requests — solves Cloudflare challenges automatically
3. Prowlarr syncs to Whisparr (because Whisparr has no tags → syncs all indexers)
4. Whisparr can now search and grab from these indexers

### What the Tag `sex` Does (and Doesn't Do) When Synced to Whisparr

- Prowlarr **does NOT sync tags to Whisparr** by default — the tag `sex` stays in Prowlarr only
- The setting `Sync Indexer Tags` in the Whisparr app config controls this:
  - **Off** (default) → tags stay in Prowlarr, Whisparr indexers have no tags
  - **On** → tags sync to Whisparr (not recommended unless you use Whisparr tags for filtering)

---

## Troubleshooting

### Test Fails with "Connection refused"

**Cause**: Prowlarr container cannot reach the site — likely ISP block, not a Cloudflare issue.

**Solution**: You need VPN routing. See `vpn-routing.md` to set up gluetun + Proton VPN for Prowlarr.

### Test Fails with "Cloudflare detected" but FlareSolverr is configured

**Cause**: The tag `sex` was not added to the indexer, so FlareSolverr proxy doesn't apply.

**Solution**: Edit the indexer → scroll to Tags → add `sex` → Save → Test again.

### Test Succeeds but Indexer Doesn't Sync to Whisparr

**Cause 1**: Category mismatch — the indexer may not support Whisparr's sync categories (`[6000,6010,...6090]`).

**Solution**:
1. Check Prowlarr → Settings → Apps → Whisparr → Sync Categories
2. Verify the indexer supports at least one of these categories
3. If not, add the category to the sync list or choose a different indexer

**Cause 2**: Sync hasn't been triggered.

**Solution**:
1. Go to Settings → Apps in Prowlarr
2. Click **Sync App Indexers** next to Whisparr
3. Wait 30-60 seconds, then check Whisparr

### Indexer Shows "Enabled" but Whisparr Shows "Disabled"

**Cause**: The indexer in Whisparr was added but is disabled by default.

**Solution**:
1. Open http://localhost:6969 → Settings → Indexers
2. Find the indexer → click **Enable** toggle
3. It will be named like `1337x (Prowlarr)`

### FlareSolverr Errors in Prowlarr Logs

```powershell
# Check FlareSolverr health
curl -s -X POST http://localhost:8191/v1 -H "Content-Type: application/json" -d '{"cmd":"sessions.list"}'

# Expected: {"sessions":[],"status":"ok"}
```

If FlareSolverr returns errors:
1. Restart FlareSolverr: `docker compose restart flaresolverr`
2. Check FlareSolverr logs: `docker logs flaresolverr`
3. Ensure `flaresolverr:8191` is accessible from Prowlarr container

---

## Reference: Current Prowlarr Configuration

### Proxy Config (Settings → Indexers → Indexer Proxies)

| Field | Value |
|-------|-------|
| Name | FlareSolverr |
| Host | `http://flaresolverr:8191` |
| Request Timeout | 60 seconds |
| Tags | `sex` |

### Tags

| ID | Label |
|----|-------|
| 1 | sex |

### App Sync (Settings → Apps → Whisparr)

| Field | Value |
|-------|-------|
| Sync Level | `fullSync` |
| Tags | *(none — syncs all indexers)* |
| Sync Categories | `6000 6010 6020 6030 6040 6045 6050 6070 6080 6090` |
| Prowlarr Server | `http://prowlarr:9696` |
| Whisparr Server | `http://whisparr:6969` |

### Complete Indexer List

| # | Name | Enable | Tag | Syncs to Whisparr |
|---|------|--------|-----|-------------------|
| 1 | Nyaa.si | ✅ | — | ✅ |
| 2 | The Pirate Bay | ✅ | — | ✅ |
| 3 | sukebei.nyaa.si | ✅ | — | ✅ |
| 4 | OneJAV | ✅ | — | ✅ |
| 5 | U3C3 | ✅ | — | ✅ |
| 6 | xxxtor | ✅ | — | ✅ |
| 7 | RuTor | ✅ | — | ✅ |
| 8 | TorrentDownload | ✅ | — | ✅ |
| 9 | Free JAV Torrent | ✅ | — | ✅ |
| 10 | MyPornClub | ✅ | — | ✅ |
| 11 | PornoTorrent | ✅ | — | ✅ |
| 12 | PornRips | ✅ | — | ✅ |
| 13 | XXXClub | ✅ | — | ✅ |
| *14* | *1337x* | *Pending* | *sex* | *Pending* |
| *15* | *TorrentGalaxyClone* | *Pending* | *sex* | *Pending* |
| *16* | *kickasstorrents.to* | *Pending* | *sex* | *Pending* |
