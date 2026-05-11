# VPN Routing for Prowlarr via gluetun + Proton VPN

## Problem

### ISP Blocking + Docker Bypasses Host VPN

1. **Your country blocks adult content sites** at the ISP/network level
2. **Your browser works fine** because Proton VPN on the Windows host routes your traffic through a VPN tunnel
3. **Docker containers bypass the host VPN** entirely — they use their own network stack (WSL2 virtual Ethernet adapter), which connects directly to the ISP without going through Proton VPN
4. **Result**: Prowlarr inside Docker gets `Connection refused` when trying to reach 1337x.to, TorrentGalaxyClone, kickasstorrents.to — even though the same URLs work in your browser

### Why FlareSolverr Alone Doesn't Fix It

FlareSolverr only helps with **Cloudflare challenge pages** (captchas, browser fingerprinting). The error here is `Connection refused` — a raw TCP connection failure — which means the ISP is blocking the connection at the network level before any HTTP/SSL handshake even starts. FlareSolverr cannot bypass an ISP-level block.

```
Host (Proton VPN on)           Docker (no VPN)
┌─────────────────────┐       ┌──────────────────────────┐
│ Browser → 1337x.to   │       │  Prowlarr → ❌ 1337x.to  │
│        ✅ Works      │       │  Connection refused      │
└─────────────────────┘       │  FlareSolverr → ❌       │
                              │  (network-level block)   │
                              └──────────────────────────┘
```

---

## Solution: gluetun VPN Container

### What Is gluetun?

[gluetun](https://github.com/qdm12/gluetun) is a lightweight Docker container that acts as a VPN client. Other containers can share its network stack, routing all their traffic through the VPN tunnel.

### Architecture After gluetun

```
Host                           Docker
┌──────────────┐              ┌─────────────────────────────────────┐
│ Proton VPN   │              │  gluetun (VPN client)               │
│ (Windows)    │              │  connects to Proton VPN servers     │
│              │              │         ↕                           │
│ Browser ✅   │              │  ┌─────────────────────────────┐    │
│ 1337x.to     │              │  │  Prowlarr (net=service:glue)│    │
└──────────────┘              │  │  :9696 → ✅ 1337x.to         │    │
                              │  └─────────────────────────────┘    │
                              │  ┌─────────────────────────────┐    │
                              │  │ FlareSolverr (net=service:glu)│   │
                              │  │ :8191 → ✅ Cloudflare bypass │    │
                              │  └─────────────────────────────┘    │
                              │                                     │
                              │  Other containers (NOT in VPN)      │
                              │  ┌─────────────────────────────┐    │
                              │  │ Stash :9999                 │    │
                              │  │ Whisparr :6969              │    │
                              │  │ Laura Backend :8000         │    │
                              │  └─────────────────────────────┘    │
                              └─────────────────────────────────────┘
```

**Key points:**
- Only **Prowlarr** and **FlareSolverr** route through gluetun/VPN
- **Stash, Whisparr, Laura Backend** stay on the local network (no VPN needed)
- gluetun exposes Prowlarr (9696) and FlareSolverr (8191) ports so they remain accessible at `localhost`

---

## Prerequisites

- Docker Desktop with WSL2 backend (already configured)
- Proton VPN **Plus** or higher plan (required for port forwarding and P2P)
- A Proton VPN **WireGuard configuration file** **OR** **OpenVPN credentials**

---

## Getting Proton VPN Credentials

### Option A: WireGuard (Recommended — Faster, Lighter)

1. Go to [Proton VPN Dashboard](https://account.protonvpn.com/downloads)
2. Scroll down to **WireGuard configuration**
3. Click **Download config** for any server (e.g., Netherlands #1)
4. Save the `.conf` file to `C:\Users\Grey Area\OneDrive\Documents\LauraSuite\config\protonvpn\wg0.conf`

### Option B: OpenVPN

1. Go to [Proton VPN OpenVPN credentials page](https://account.protonvpn.com/account)
2. Under **OpenVPN / IKEv2 username**, click **Generate** (or copy existing)
3. Note down the **username** and **password** (these are NOT your main Proton account credentials)
4. These go into the gluetun environment variables

---

## docker-compose.yml Configuration

### 1. Add gluetun Service

Insert this block under `services:` in your `docker-compose.yml`:

#### WireGuard Mode

```yaml
gluetun:
  image: qmcgaw/gluetun:latest
  container_name: gluetun
  cap_add:
    - NET_ADMIN
  environment:
    - VPN_SERVICE_PROVIDER=protonvpn
    - VPN_TYPE=wireguard
    - WIREGUARD_PRIVATE_KEY=<your_private_key_from_wg_config>
    - WIREGUARD_ADDRESSES=<your_address_from_wg_config>
    - WIREGUARD_DNS=<your_dns_from_wg_config>
    - SERVER_COUNTRIES=Netherlands
    - TZ=UTC
  volumes:
    - ./config/protonvpn:/config/gluetun
  ports:
    # Prowlarr
    - 9696:9696
    # FlareSolverr
    - 8191:8191
```

**Extracting WireGuard config values:**

Open your downloaded `.conf` file. It looks like this:
```ini
[Interface]
PrivateKey = mABCDEF123456789...=
Address = 10.2.0.2/32
DNS = 10.2.0.1

[Peer]
PublicKey = ...
PresharedKey = ...
Endpoint = 123.45.67.89:51820
AllowedIPs = 0.0.0.0/0
```

Map these to environment variables:
| `.conf` field | Environment variable |
|---|---|
| `[Interface] PrivateKey` | `WIREGUARD_PRIVATE_KEY` |
| `[Interface] Address` | `WIREGUARD_ADDRESSES` (e.g. `10.2.0.2/32`) |
| `[Interface] DNS` | `WIREGUARD_DNS` (e.g. `10.2.0.1`) |

#### OpenVPN Mode

```yaml
gluetun:
  image: qmcgaw/gluetun:latest
  container_name: gluetun
  cap_add:
    - NET_ADMIN
  environment:
    - VPN_SERVICE_PROVIDER=protonvpn
    - VPN_TYPE=openvpn
    - OPENVPN_USER=<your_openvpn_username>
    - OPENVPN_PASSWORD=<your_openvpn_password>
    - SERVER_COUNTRIES=Netherlands
    - TZ=UTC
  ports:
    - 9696:9696
    - 8191:8191
```

### 2. Modify Prowlarr to Use gluetun Network

Change the existing `prowlarr` service:

```yaml
prowlarr:
  image: ghcr.io/hotio/prowlarr:latest
  container_name: prowlarr
  network_mode: service:gluetun    # ← Changed from network: laurasuite_default
  depends_on:
    gluetun:
      condition: service_healthy   # ← Wait for VPN to connect
  environment:
    - APP_UID=1000
    - APP_GID=1000
  volumes:
    - ./config/prowlarr:/config
  restart: unless-stopped
```

**Important changes:**
- Remove the old `networks:` block for prowlarr
- Add `network_mode: service:gluetun`
- Add `depends_on: gluetun: condition: service_healthy`

### 3. Modify FlareSolverr to Use gluetun Network

```yaml
flaresolverr:
  image: ghcr.io/flaresolverr/flaresolverr:latest
  container_name: flaresolverr
  network_mode: service:gluetun    # ← Changed
  depends_on:
    gluetun:
      condition: service_healthy
  environment:
    - LOG_LEVEL=info
    - CAPTCHA_SOLVER=none
  restart: unless-stopped
```

### 4. Handle Inter-Service Communication

Since Prowlarr and FlareSolverr now share gluetun's network (not `laurasuite_default`), they **cannot reach** other services by container name. However:

- **Prowlarr ↔ FlareSolverr**: They share the same network stack via gluetun, so `http://flaresolverr:8191` still works inside Prowlarr
- **Prowlarr → Whisparr**: Add this to the gluetun service to keep them on the same network:

```yaml
gluetun:
  ...
  networks:
    - laurasuite_default
```

This attaches gluetun to your existing network too, so Prowlarr can still reach Whisparr at `http://whisparr:6969`.

### Complete Modified Section for docker-compose.yml

```yaml
services:
  gluetun:
    image: qmcgaw/gluetun:latest
    container_name: gluetun
    cap_add:
      - NET_ADMIN
    environment:
      - VPN_SERVICE_PROVIDER=protonvpn
      - VPN_TYPE=wireguard
      - WIREGUARD_PRIVATE_KEY=your_key_here
      - WIREGUARD_ADDRESSES=your_address_here
      - WIREGUARD_DNS=your_dns_here
      - SERVER_COUNTRIES=Netherlands
      - TZ=UTC
    volumes:
      - ./config/protonvpn:/config/gluetun
    ports:
      - 9696:9696
      - 8191:8191
    networks:
      - laurasuite_default
    healthcheck:
      test: ["CMD", "curl", "-f", "https://ifconfig.me"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    restart: unless-stopped

  prowlarr:
    image: ghcr.io/hotio/prowlarr:latest
    container_name: prowlarr
    network_mode: service:gluetun
    depends_on:
      gluetun:
        condition: service_healthy
    environment:
      - APP_UID=1000
      - APP_GID=1000
    volumes:
      - ./config/prowlarr:/config
    restart: unless-stopped

  flaresolverr:
    image: ghcr.io/flaresolverr/flaresolverr:latest
    container_name: flaresolverr
    network_mode: service:gluetun
    depends_on:
      gluetun:
        condition: service_healthy
    environment:
      - LOG_LEVEL=info
      - CAPTCHA_SOLVER=none
    restart: unless-stopped

  # Other services (whisparr, stash, laura-backend) remain unchanged
```

---

## Environment Variables Reference

### gluetun Common

| Variable | Description | Example |
|----------|-------------|---------|
| `VPN_SERVICE_PROVIDER` | VPN provider name | `protonvpn` |
| `VPN_TYPE` | Protocol to use | `wireguard` or `openvpn` |
| `SERVER_COUNTRIES` | Server location filter | `Netherlands` |
| `SERVER_CITIES` | City filter (optional) | `Amsterdam` |
| `SERVER_HOSTNAMES` | Specific server (optional) | `NL-01` |
| `TZ` | Timezone | `UTC` |

### gluetun WireGuard

| Variable | Source |
|----------|--------|
| `WIREGUARD_PRIVATE_KEY` | From `.conf` `[Interface] PrivateKey` |
| `WIREGUARD_ADDRESSES` | From `.conf` `[Interface] Address` |
| `WIREGUARD_DNS` | From `.conf` `[Interface] DNS` |
| `WIREGUARD_PRESHARED_KEY` | From `.conf` `[Peer] PresharedKey` (optional) |

### gluetun OpenVPN

| Variable | Source |
|----------|--------|
| `OPENVPN_USER` | From Proton VPN OpenVPN credentials page |
| `OPENVPN_PASSWORD` | From Proton VPN OpenVPN credentials page |

---

## How It Works

1. **gluetun starts first** → connects to Proton VPN using your credentials
2. **Health check** runs → confirms VPN connection is active by fetching `ifconfig.me`
3. **Prowlarr and FlareSolverr start** → they share gluetun's network stack (`network_mode: service:gluetun`)
4. **All traffic from Prowlarr/FlareSolverr** exits through the Proton VPN tunnel → appears to come from the VPN server's IP
5. **Blocked sites become reachable** because the ISP sees VPN traffic (TLS tunnel to Proton VPN), not direct connections to adult sites
6. **Prowlarr's API (port 9696) and FlareSolverr's API (port 8191)** are still accessible at `localhost` because gluetun exposes those ports

---

## Verification

### Check VPN Connection Status

```powershell
# Check gluetun logs
docker logs gluetun --tail 20

# Check current VPN IP
docker exec gluetun curl -s ifconfig.me

# Verify it's a Proton VPN IP (not your ISP IP)
```

### Test Site Reachability from Prowlarr

```powershell
# Test 1337x
docker exec prowlarr curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 https://1337x.to

# Should return 200 (not 000)
```

### Verify Prowlarr UI Still Works

Open http://localhost:9696 in your browser — it should load normally.

---

## Adding Blocked Indexers Post-VPN

Once the VPN is confirmed working, add the remaining indexers through Prowlarr UI:

1. Navigate to **Prowlarr → Indexers → Add Indexer**
2. Search and select each indexer:
   - **1337x**
   - **TorrentGalaxyClone**
   - **kickasstorrents.to**
3. Scroll to **Tags** → add tag `sex` (ties to FlareSolverr proxy)
4. Click **Test** → should succeed now
5. Click **Save**

See `adding-indexers.md` for full step-by-step with screenshots of all fields.

---

## Troubleshooting

### gluetun Won't Connect

```powershell
# Check full logs
docker logs gluetun

# Common issues:
# - Wrong WireGuard private key (re-download .conf)
# - Wrong OpenVPN credentials (regenerate from Proton VPN page)
# - Server overloaded (try different SERVER_COUNTRIES)
# - Port 51820 UDP blocked (WireGuard) → try OpenVPN mode instead
```

### Prowlarr Unreachable at localhost:9696

```powershell
# Check gluetun port mapping
docker port gluetun

# Verify no port conflicts with old prowlarr service
netstat -ano | findstr ":9696"
```

### Other Containers Can't Reach Prowlarr

Since Prowlarr now runs on gluetun's network, it's not directly on `laurasuite_default`. To fix:
- Add `networks: [laurasuite_default]` to the gluetun service (shown in the complete example above)
- This gives gluetun a second network interface on your existing Docker network
- Prowlarr inherits this and can be reached at its container name from other services

### VPN DNS Leak

If sites still resolve but Prowlarr can't connect, force DNS through the VPN tunnel:

```yaml
environment:
  - VPN_DNS_OVER_TLS=on  # Encrypt all DNS queries through VPN
```

### Rebuilding After Changes

```powershell
docker compose up -d gluetun prowlarr flaresolverr --force-recreate
```

---

## Security Notes

- Only Prowlarr and FlareSolverr route through the VPN — your media traffic (Stash, Whisparr, backend) stays local
- If using WireGuard, the private key in `WIREGUARD_PRIVATE_KEY` is sensitive — keep it out of version control
- gluetun can be configured to kill the VPN connection if the tunnel drops (`VPN_KILL_SWITCH=on`) to prevent IP leaks
- The `cap_add: NET_ADMIN` permission is required for gluetun to modify network routing — this is normal for VPN containers
