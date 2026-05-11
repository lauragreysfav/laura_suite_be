# Laura Suite

Self-hosted adult content pipeline — automated discovery, cloud torrenting, and media library management.

## Architecture

- [System Overview](architecture/overview.md) — full system diagram, services, network topology
- [Data Flow](architecture/data-flow.md) — Whisparr → TorBox → Stash pipeline
- [Database](architecture/database.md) — Supabase schema, auth, and data model
- [Security](architecture/security.md) — JWT auth, port binding, secrets management

## Setup

- [Quickstart](setup/quickstart.md) — from `git clone` to running system
- [Supabase Setup](setup/supabase-setup.md) — create project, configure auth, get API keys
- [Environment Variables](setup/environment.md) — .env reference
- [Production Deployment](setup/production.md) — domain, SSL, docker compose prod

## API Reference

- [Authentication](api/auth.md) — register, login, JWT usage
- [Library](api/library.md) — scenes, performers, studios
- [Torrents](api/torrents.md) — search, add, stream links
- [Prowlarr Search](api/prowlarr-search.md) — indexer search proxy

## Features

- [Torrent Streaming](features/torrent-streaming.md) — TorBox CDN streaming links
- [Indexer Guide](features/indexer-guide.md) — adding indexers, proxy tags, Cloudflare bypass

## Operations

- [VPN Routing](ops/vpn-routing.md) — gluetun + Proton VPN for blocked indexers
- [Troubleshooting](ops/troubleshooting.md) — common issues and fixes

## User Guide

- [Getting Started](user-guide/getting-started.md) — browsing, searching, downloading
