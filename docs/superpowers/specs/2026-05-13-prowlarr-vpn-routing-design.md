# Prowlarr VPN Routing Design

**Date:** 2026-05-13  
**Scope:** Laura Suite backend stack (`laura_suite_be`)

## Problem

Prowlarr is currently published directly from its own container (`127.0.0.1:9696:9696`) and is not forced through the VPN namespace. This allows potential non-VPN routing for indexer traffic.

## Goals

1. Force Prowlarr to run through the Gluetun VPN network namespace.
2. Keep host access to Prowlarr UI at `http://localhost:9696`.
3. Make backend default Prowlarr API traffic target the VPN namespace.
4. Preserve existing backend error behavior (visible failures instead of silent bypass).

## Non-Goals

1. Changing Whisparr or other service routing behavior.
2. Refactoring backend Prowlarr service logic beyond endpoint default changes.
3. Introducing a proxy-only or host-firewall-only routing model.

## Current State

1. `docker-compose.yml`:
   - `gluetun` publishes `8191` only.
   - `flaresolverr` uses `network_mode: "service:gluetun"`.
   - `prowlarr` runs separately and publishes `127.0.0.1:9696:9696`.
2. Backend defaults:
   - `app/config.py`: `prowlarr_url = "http://prowlarr:9696"`.
   - `.env.example`: `PROWLARR_URL=http://prowlarr:9696`.

## Chosen Approach

Use **shared network namespace routing**:

1. Move `prowlarr` to `network_mode: "service:gluetun"`.
2. Publish `9696` from `gluetun` (alongside `8191`) to keep host UI access.
3. Switch backend default Prowlarr URL to `http://gluetun:9696`.

This provides the strongest compose-level routing guarantee with low operational complexity.

## Design Details

### 1) Compose topology

1. `prowlarr` no longer manages its own network namespace.
2. `gluetun` remains the only published ingress for VPN-routed services.
3. `prowlarr` host exposure is maintained via `gluetun` port mapping.

### 2) Configuration defaults

1. Update `app/config.py` default from `http://prowlarr:9696` to `http://gluetun:9696`.
2. Update `.env.example` Prowlarr URL to match new default.
3. Existing runtime `.env` values still override defaults when present.

### 3) Data flow

1. Host browser -> `localhost:9696` -> `gluetun` namespace -> Prowlarr UI.
2. Backend container -> `http://gluetun:9696/api/v1/...` -> Prowlarr in VPN namespace.
3. Prowlarr outbound indexer traffic exits through Gluetun.

## Error Handling

1. If Gluetun is unavailable or VPN route fails, backend calls to Prowlarr fail with existing error paths (e.g., propagated HTTP/connection errors to API layer).
2. No silent fallback to non-VPN route is introduced.

## Validation Plan

1. Confirm `http://localhost:9696` loads Prowlarr UI.
2. From backend container, confirm Prowlarr status endpoint responds via `gluetun:9696`.
3. Confirm backend search/indexer endpoints operate with the new default URL.
4. Confirm Prowlarr egress is VPN-routed (no direct host-network bypass).

## Risks and Mitigations

1. **Risk:** Service hostname assumptions break when moving to shared namespace.  
   **Mitigation:** Explicitly switch backend default URL to `gluetun:9696`.
2. **Risk:** Port publishing confusion between `prowlarr` and `gluetun`.  
   **Mitigation:** Ensure only `gluetun` publishes `9696`.

## Implementation Boundaries

Changes are limited to:

1. `docker-compose.yml` (Prowlarr/Gluetun networking and ports)
2. `app/config.py` (default Prowlarr URL)
3. `.env.example` (documented default URL)
