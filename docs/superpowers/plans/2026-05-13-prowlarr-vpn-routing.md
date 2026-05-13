# Prowlarr VPN Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Force Prowlarr traffic through Gluetun VPN while keeping host UI access at `localhost:9696` and aligning backend defaults to the VPN-routed endpoint.

**Architecture:** Prowlarr will share Gluetun's network namespace (`network_mode: "service:gluetun"`), so Gluetun becomes the single ingress point for both FlareSolverr and Prowlarr ports. Backend defaults will target `http://gluetun:9696` to avoid hostname assumptions after the namespace shift. Validation combines file-level tests and runtime smoke checks.

**Tech Stack:** Docker Compose, Python 3, FastAPI config (`pydantic-settings`), `unittest`, curl

---

## File Structure and Responsibilities

- `docker-compose.yml` — service networking and published ports (source of truth for VPN routing topology).
- `app/config.py` — backend default service URLs used by runtime settings.
- `.env.example` — documented/default environment values for local setup.
- `tests/test_prowlarr_vpn_routing.py` (new) — regression tests that assert routing and default URL invariants.

### Task 1: Add failing routing regression tests

**Files:**
- Create: `tests/test_prowlarr_vpn_routing.py`
- Test: `tests/test_prowlarr_vpn_routing.py`

- [ ] **Step 1: Write the failing test file**

```python
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestProwlarrVpnRouting(unittest.TestCase):
    def test_gluetun_publishes_prowlarr_port(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("- 127.0.0.1:9696:9696", compose)

    def test_prowlarr_uses_gluetun_network_namespace(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn('network_mode: "service:gluetun"', compose)

    def test_backend_default_prowlarr_url_targets_gluetun(self):
        config_py = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
        self.assertIn('prowlarr_url: str = "http://gluetun:9696"', config_py)

    def test_env_example_default_prowlarr_url_targets_gluetun(self):
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("PROWLARR_URL=http://gluetun:9696", env_example)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify baseline fails**

Run: `python -m unittest discover -s tests -p "test_prowlarr_vpn_routing.py" -v`  
Expected: FAIL on at least one assertion for Gluetun URL and/or Prowlarr namespace routing.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_prowlarr_vpn_routing.py
git commit -m "test: add prowlarr vpn routing regression tests"
```

### Task 2: Route Prowlarr through Gluetun in Compose

**Files:**
- Modify: `docker-compose.yml:34-70`
- Test: `tests/test_prowlarr_vpn_routing.py`

- [ ] **Step 1: Update Gluetun and Prowlarr service blocks**

Apply only these networking changes (leave existing Gluetun environment values unchanged):

```yaml
  gluetun:
    image: qmcgaw/gluetun:latest
    container_name: gluetun
    cap_add:
      - NET_ADMIN
    ports:
      - 127.0.0.1:8191:8191
      - 127.0.0.1:9696:9696
    restart: unless-stopped

  prowlarr:
    image: ghcr.io/hotio/prowlarr:latest
    container_name: prowlarr
    network_mode: "service:gluetun"
    depends_on:
      gluetun:
        condition: service_started
    environment:
      - APP_UID=1000
      - APP_GID=1000
      - TZ=Asia/Kolkata
    volumes:
      - ./config/prowlarr:/config
    restart: unless-stopped
```

- [ ] **Step 2: Validate Compose syntax**

Run: `docker compose config > NUL`  
Expected: command exits successfully with no YAML/compose validation errors.

- [ ] **Step 3: Run regression tests**

Run: `python -m unittest discover -s tests -p "test_prowlarr_vpn_routing.py" -v`  
Expected: Prowlarr network namespace test passes; URL-default tests may still fail.

- [ ] **Step 4: Commit Compose routing change**

```bash
git add docker-compose.yml
git commit -m "infra: route prowlarr through gluetun namespace"
```

### Task 3: Switch backend/default Prowlarr URL to Gluetun endpoint

**Files:**
- Modify: `app/config.py:22-23`
- Modify: `.env.example:20-23`
- Test: `tests/test_prowlarr_vpn_routing.py`

- [ ] **Step 1: Update `app/config.py` default**

Change:

```python
prowlarr_url: str = "http://prowlarr:9696"
```

To:

```python
prowlarr_url: str = "http://gluetun:9696"
```

- [ ] **Step 2: Update `.env.example` default**

Change:

```dotenv
PROWLARR_URL=http://prowlarr:9696
```

To:

```dotenv
PROWLARR_URL=http://gluetun:9696
```

- [ ] **Step 3: Run regression tests to green**

Run: `python -m unittest discover -s tests -p "test_prowlarr_vpn_routing.py" -v`  
Expected: all tests PASS.

- [ ] **Step 4: Commit URL default updates**

```bash
git add app/config.py .env.example tests/test_prowlarr_vpn_routing.py
git commit -m "config: default prowlarr endpoint to gluetun"
```

### Task 4: Runtime smoke verification for routing and access

**Files:**
- Modify: none
- Test: runtime commands only

- [ ] **Step 1: Restart affected services**

Run: `docker compose up -d gluetun prowlarr laura-backend`  
Expected: services report as started/running.

- [ ] **Step 2: Verify host UI access**

Run: `curl http://localhost:9696/api/v1/system/status`  
Expected: HTTP 200 with Prowlarr status JSON.

- [ ] **Step 3: Verify backend-container reachability via Gluetun hostname**

Run: `docker compose exec laura-backend python -c "import httpx; r=httpx.get('http://gluetun:9696/api/v1/system/status', timeout=10); print(r.status_code)"`  
Expected: prints `200`.

- [ ] **Step 4: Confirm clean working tree after smoke checks**

```bash
git status --short
```

Expected: no uncommitted functional changes after verification-only commands.
