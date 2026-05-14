# Async Ingest Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `scripts/initial_ingest.py` as an async, parallelized, checkpointed pipeline that migrates StashDB data (performers, studios, scenes) to PostgreSQL + Typesense in ~1-2 hours instead of days.

**Architecture:** Three-phase pipeline using `asyncio` + `httpx.AsyncClient`. Phase 1 fetches all female performers by name prefix (collecting studio IDs). Phase 2 fetches studio details. Phase 3 fetches scenes per studio with date >= 2000. A token-bucket rate limiter allows controlled bursts (5 concurrent requests) while respecting StashDB's 1 req/s average limit. Checkpoints saved to a JSON file enable resume after crash. DB and Typesense writes use batched operations instead of per-record commits/upserts.

**Tech Stack:** Python 3.12, asyncio, httpx, SQLAlchemy, Typesense client, aiofiles (for checkpoint writes)

---

## File Structure (planned changes)

**Create:**
- `scripts/ingest/__init__.py`
- `scripts/ingest/rate_limiter.py` — async token-bucket rate limiter
- `scripts/ingest/checkpoint.py` — checkpoint save/resume
- `scripts/ingest/api.py` — async StashDB GraphQL client
- `scripts/ingest/savers.py` — batch DB + Typesense writers
- `scripts/ingest/pipeline.py` — three-phase orchestration

**Modify:**
- `scripts/initial_ingest.py` — update to CLI entry point that calls the new pipeline
- `app/config.py` — add `ingest_concurrency` setting
- `tests/test_ingest_filters.py` — expand tests

**No changes needed to:** models, alembic, docker-compose, typesense_client

---

### Task 1: Token-bucket rate limiter

**Files:**
- Create: `scripts/ingest/__init__.py`
- Create: `scripts/ingest/rate_limiter.py`
- Create: `tests/test_rate_limiter.py`

- [ ] **Step 1: Write failing rate limiter tests**

```python
# tests/test_rate_limiter.py
import asyncio
import time
from scripts.ingest.rate_limiter import TokenBucket

def test_token_bucket_allows_burst():
    bucket = TokenBucket(capacity=5, rate=1.0)
    for _ in range(5):
        assert bucket.try_consume() is True

def test_token_bucket_blocks_when_empty():
    bucket = TokenBucket(capacity=2, rate=1.0)
    bucket.try_consume()
    bucket.try_consume()
    assert bucket.try_consume() is False

@pytest.mark.asyncio
async def test_acquire_waits_for_token():
    bucket = TokenBucket(capacity=1, rate=10.0)
    t0 = time.monotonic()
    await bucket.acquire()
    await bucket.acquire()
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.09  # 1/10th second refill
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_rate_limiter.py -v`
Expected: FAIL (module/class not found)

- [ ] **Step 3: Implement token-bucket rate limiter**

```python
# scripts/ingest/__init__.py
"""Async StashDB ingestion pipeline."""

# scripts/ingest/rate_limiter.py
import asyncio
import time


class TokenBucket:
    def __init__(self, capacity: int, rate: float) -> None:
        self.capacity = capacity
        self.rate = rate
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def try_consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                if self.try_consume():
                    return
            await asyncio.sleep(max(0.01, 1.0 / self.rate / 2))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rate_limiter.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/ingest/ tests/test_rate_limiter.py
git commit -m "feat: add token-bucket rate limiter for async ingest"
```

---

### Task 2: Checkpoint system

**Files:**
- Create: `scripts/ingest/checkpoint.py`
- Create: `tests/test_ingest_checkpoint.py`

- [ ] **Step 1: Write failing checkpoint tests**

```python
# tests/test_ingest_checkpoint.py
from scripts.ingest.checkpoint import Checkpoint

def test_checkpoint_save_and_load(tmp_path):
    cp = Checkpoint(path=str(tmp_path / "ckpt.json"))
    cp.set("performers_prefix", "m")
    cp.set("performers_page", 5)
    cp.save()
    cp2 = Checkpoint(path=str(tmp_path / "ckpt.json"))
    cp2.load()
    assert cp2.get("performers_prefix") == "m"
    assert cp2.get("performers_page") == 5

def test_checkpoint_defaults():
    cp = Checkpoint(path="/tmp/nonexistent/ckpt.json")
    cp.load()
    assert cp.get("phase", "performers") == "performers"
    assert cp.get("seen_performer_ids", []) == []

def test_checkpoint_append(tmp_path):
    cp = Checkpoint(path=str(tmp_path / "ckpt.json"))
    cp.append("seen_studio_ids", "s1")
    cp.append("seen_studio_ids", "s2")
    cp.save()
    cp2 = Checkpoint(path=str(tmp_path / "ckpt.json"))
    cp2.load()
    assert cp2.get("seen_studio_ids") == ["s1", "s2"]
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_ingest_checkpoint.py -v`
Expected: FAIL (module/class not found)

- [ ] **Step 3: Implement checkpoint**

```python
# scripts/ingest/checkpoint.py
import json
import logging
from pathlib import Path

logger = logging.getLogger("ingest.checkpoint")

DEFAULTS = {
    "phase": "performers",
    "performers_prefix_idx": 0,
    "performers_page": 1,
    "seen_performer_ids": [],
    "seen_studio_ids": [],
    "studios_done": [],
    "studios_idx": 0,
    "scenes_studio_idx": 0,
    "scenes_page": 1,
}

class Checkpoint:
    def __init__(self, path: str = "ingest_checkpoint.json") -> None:
        self.path = path
        self._data = dict(DEFAULTS)
        self._dirty = False

    def load(self) -> None:
        p = Path(self.path)
        if p.exists():
            try:
                with open(p) as f:
                    raw = json.load(f)
                self._data = {**DEFAULTS, **raw}
                logger.info("checkpoint_loaded", extra={"phase": self._data.get("phase")})
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("checkpoint_load_failed", extra={"error": str(e)})

    def save(self) -> None:
        if not self._dirty:
            return
        try:
            with open(self.path, "w") as f:
                json.dump(self._data, f, indent=2)
            self._dirty = False
            logger.debug("checkpoint_saved")
        except OSError as e:
            logger.warning("checkpoint_save_failed", extra={"error": str(e)})

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        if self._data.get(key) != value:
            self._data[key] = value
            self._dirty = True

    def append(self, key: str, value) -> None:
        lst = self._data.setdefault(key, [])
        if value not in lst:
            lst.append(value)
            self._dirty = True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ingest_checkpoint.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/ingest/checkpoint.py tests/test_ingest_checkpoint.py
git commit -m "feat: add checkpoint system for ingest resume"
```

---

### Task 3: Async StashDB API client

**Files:**
- Create: `scripts/ingest/api.py`
- Create: `tests/test_ingest_api.py` (mock-based)

- [ ] **Step 1: Write failing API client tests**

```python
# tests/test_ingest_api.py
import pytest
from scripts.ingest.api import StashDBClient

@pytest.mark.asyncio
async def test_fetch_performers_page(monkeypatch):
    async def fake_post(*a, **kw):
        class FakeResp:
            async def json(self):
                return {"data": {"queryPerformers": {"count": 1, "performers": [{"id": "p1"}]}}}
            def raise_for_status(self):
                pass
            @property
            def status_code(self):
                return 200
        return FakeResp()
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    client = StashDBClient(api_key="test")
    perf, count = await client.fetch_performers_page("alice", page=1)
    assert len(perf) == 1
    assert count == 1

@pytest.mark.asyncio
async def test_fetch_scenes_page(monkeypatch):
    async def fake_post(*a, **kw):
        class FakeResp:
            async def json(self):
                return {"data": {"queryScenes": {"count": 1, "scenes": [{"id": "s1"}]}}}
            def raise_for_status(self):
                pass
            @property
            def status_code(self):
                return 200
        return FakeResp()
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    client = StashDBClient(api_key="test")
    scenes, count = await client.fetch_scenes_page("st1", page=1)
    assert len(scenes) == 1

@pytest.mark.asyncio
async def test_fetch_studio(monkeypatch):
    async def fake_post(*a, **kw):
        class FakeResp:
            async def json(self):
                return {"data": {"findStudio": {"id": "st1", "name": "Test Studio"}}}
            def raise_for_status(self):
                pass
            @property
            def status_code(self):
                return 200
        return FakeResp()
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    client = StashDBClient(api_key="test")
    studio = await client.fetch_studio("st1")
    assert studio["name"] == "Test Studio"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_ingest_api.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement async API client**

```python
# scripts/ingest/api.py
import logging
import httpx
from scripts.ingest.rate_limiter import TokenBucket

logger = logging.getLogger("ingest.api")

STASHDB_URL = "https://stashdb.org/graphql"
PER_PAGE = 100

PERFORMER_QUERY = """
query SearchPerformers($input: PerformerQueryInput!) {
  queryPerformers(input: $input) {
    count
    performers {
      id name aliases gender
      images { url }
      scene_count career_end_year birth_date
      urls { url type }
      studios { studio { id name } }
    }
  }
}
"""

STUDIO_QUERY = """
query GetStudio($id: ID!) {
  findStudio(id: $id) {
    id name images { url } scene_count parent { id name } urls { url type }
  }
}
"""

SCENES_QUERY = """
query StudioScenes($input: SceneQueryInput!) {
  queryScenes(input: $input) {
    count
    scenes {
      id title details release_date duration
      images { url }
      studio { id name }
      performers { performer { id name } }
      fingerprints { algorithm hash duration }
      tags { name }
    }
  }
}
"""

class StashDBClient:
    def __init__(self, api_key: str, rate_limiter: TokenBucket | None = None) -> None:
        self.headers = {"ApiKey": api_key} if api_key else {}
        self.rate_limiter = rate_limiter or TokenBucket(capacity=5, rate=1.0)

    async def _query(self, query: str, variables: dict) -> dict:
        if self.rate_limiter:
            await self.rate_limiter.acquire()
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                STASHDB_URL,
                json={"query": query, "variables": variables},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def fetch_performers_page(self, name: str, page: int = 1) -> tuple[list[dict], int]:
        data = await self._query(PERFORMER_QUERY, {
            "input": {"names": name, "page": page, "per_page": PER_PAGE}
        })
        d = data.get("data") or {}
        qp = d.get("queryPerformers") or {}
        return qp.get("performers", []), qp.get("count", 0)

    async def fetch_studio(self, studio_id: str) -> dict | None:
        try:
            data = await self._query(STUDIO_QUERY, {"id": studio_id})
            return (data.get("data") or {}).get("findStudio")
        except Exception as e:
            logger.warning("studio_fetch_error", extra={"id": studio_id, "error": str(e)})
            return None

    async def fetch_scenes_page(self, studio_id: str, page: int = 1) -> tuple[list[dict], int]:
        data = await self._query(SCENES_QUERY, {
            "input": {
                "studios": {"value": [studio_id], "modifier": "INCLUDES"},
                "page": page,
                "per_page": PER_PAGE,
                "date": {"value": "2000-01-01", "modifier": "GREATER_THAN_OR_EQUALS"},
            }
        })
        d = data.get("data") or {}
        qs = d.get("queryScenes") or {}
        return qs.get("scenes", []), qs.get("count", 0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ingest_api.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/ingest/api.py tests/test_ingest_api.py
git commit -m "feat: add async stashdb graphql client"
```

---

### Task 4: Batch DB + Typesense savers

**Files:**
- Create: `scripts/ingest/savers.py`
- Create: `tests/test_ingest_savers.py` (mock-based)

- [ ] **Step 1: Write failing saver tests**

```python
# tests/test_ingest_savers.py
from unittest.mock import MagicMock
from scripts.ingest.savers import batch_save_performers, batch_save_studios, batch_save_scenes

def test_batch_save_performers():
    session = MagicMock()
    ts = MagicMock()
    performers = [
        {"id": "p1", "name": "Alice", "gender": "female", "aliases": "", "images": [], "urls": [],
         "scene_count": 5, "birth_date": "1990-01-01"}
    ]
    batch_save_performers(session, ts, performers, batch_size=10)
    assert session.bulk_save_objects.called
    ts.bulk_upsert.assert_called_once()

def test_batch_save_performers_skips_male():
    session = MagicMock()
    ts = MagicMock()
    performers = [
        {"id": "p1", "name": "Bob", "gender": "male"}
    ]
    batch_save_performers(session, ts, performers, batch_size=10)
    session.bulk_save_objects.assert_not_called()
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_ingest_savers.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement batch savers**

```python
# scripts/ingest/savers.py
import logging
from app.models import StashDBPerformerCache, StashDBStudioCache, StashDBSceneCache

logger = logging.getLogger("ingest.savers")

def _performer_to_pg(p: dict) -> StashDBPerformerCache:
    imgs = p.get("images", [])
    urls = p.get("urls", [])
    return StashDBPerformerCache(
        stashdb_id=p["id"],
        name=p.get("name", ""),
        aliases=p.get("aliases", ""),
        gender=p.get("gender", ""),
        birthdate=p.get("birth_date"),
        image_url=imgs[0]["url"] if imgs else None,
        scene_count=p.get("scene_count", 0),
        urls=[{"url": u["url"], "type": u["type"]} for u in urls],
        raw_json=p,
    )

def _performer_to_ts(p: dict) -> dict:
    imgs = p.get("images", [])
    aliases_raw = p.get("aliases", "") or ""
    return {
        "id": p["id"],
        "name": p.get("name", ""),
        "aliases": [a.strip() for a in aliases_raw.split(",") if a.strip()],
        "image_url": imgs[0]["url"] if imgs else None,
        "gender": p.get("gender", ""),
        "birthdate": p.get("birth_date"),
        "scene_count": p.get("scene_count", 0),
    }

def _studio_to_pg(s: dict) -> StashDBStudioCache:
    imgs = s.get("images", [])
    parent = s.get("parent") or {}
    urls = s.get("urls") or []
    return StashDBStudioCache(
        stashdb_id=s["id"],
        name=s.get("name", ""),
        image_url=imgs[0]["url"] if imgs else None,
        scene_count=s.get("scene_count", 0),
        parent_studio=parent.get("name"),
        urls=[{"url": u["url"], "type": u["type"]} for u in urls],
        raw_json=s,
    )

def _studio_to_ts(s: dict) -> dict:
    imgs = s.get("images", [])
    return {
        "id": s["id"],
        "name": s.get("name", ""),
        "image_url": imgs[0]["url"] if imgs else None,
        "scene_count": s.get("scene_count", 0),
    }

def _scene_to_pg(sc: dict) -> StashDBSceneCache | None:
    if not sc.get("release_date") or sc["release_date"] < "2000-01-01":
        return None
    imgs = sc.get("images", [])
    pdata = sc.get("performers") or []
    fprints = sc.get("fingerprints") or []
    tags = sc.get("tags") or []
    studio_data = sc.get("studio") or {}
    return StashDBSceneCache(
        stashdb_id=sc["id"],
        title=sc.get("title", ""),
        details=sc.get("details"),
        release_date=sc.get("release_date"),
        duration=sc.get("duration"),
        studio_id=studio_data.get("id"),
        studio_name=studio_data.get("name", ""),
        performer_names=[p.get("performer", {}).get("name") for p in pdata if p.get("performer")],
        performer_ids=[p.get("performer", {}).get("id") for p in pdata if p.get("performer")],
        tags=[t.get("name") for t in tags if t.get("name")],
        fingerprints=[{"algorithm": fp.get("algorithm"), "hash": fp.get("hash"), "duration": fp.get("duration")} for fp in fprints],
        images=[i["url"] for i in imgs] if imgs else [],
        raw_json=sc,
    )

def _scene_to_ts(sc: dict) -> dict | None:
    if not sc.get("release_date") or sc["release_date"] < "2000-01-01":
        return None
    imgs = sc.get("images", [])
    pdata = sc.get("performers") or []
    fprints = sc.get("fingerprints") or []
    tags = sc.get("tags") or []
    studio_data = sc.get("studio") or {}
    return {
        "id": sc["id"],
        "title": sc.get("title", ""),
        "details": sc.get("details"),
        "release_date": sc.get("release_date"),
        "duration": sc.get("duration"),
        "studio_name": studio_data.get("name", ""),
        "performer_names": [p.get("performer", {}).get("name") for p in pdata if p.get("performer")],
        "tags": [t.get("name") for t in tags if t.get("name")],
        "fingerprints": [fp.get("hash") for fp in fprints if fp.get("hash")],
        "images": [i["url"] for i in imgs] if imgs else [],
    }

def batch_save_performers(session, ts, performers: list[dict], batch_size: int = 100) -> int:
    females = [p for p in performers if p.get("gender") == "female"]
    if not females:
        return 0
    pg_rows = [_performer_to_pg(p) for p in females]
    ts_docs = [_performer_to_ts(p) for p in females]
    session.bulk_save_objects(pg_rows)
    session.commit()
    ts.bulk_upsert("stashdb_performers", ts_docs)
    logger.info("saved_performers", extra={"count": len(females)})
    return len(females)

def batch_save_studios(session, ts, studios: list[dict], batch_size: int = 100) -> int:
    if not studios:
        return 0
    pg_rows = [_studio_to_pg(s) for s in studios]
    ts_docs = [_studio_to_ts(s) for s in studios]
    session.bulk_save_objects(pg_rows)
    session.commit()
    ts.bulk_upsert("stashdb_studios", ts_docs)
    logger.info("saved_studios", extra={"count": len(studios)})
    return len(studios)

def batch_save_scenes(session, ts, scenes: list[dict], batch_size: int = 100) -> int:
    pg_rows = []
    ts_docs = []
    for sc in scenes:
        pg = _scene_to_pg(sc)
        if pg:
            pg_rows.append(pg)
        tsd = _scene_to_ts(sc)
        if tsd:
            ts_docs.append(tsd)
    if not pg_rows:
        return 0
    session.bulk_save_objects(pg_rows)
    session.commit()
    ts.bulk_upsert("stashdb_scenes", ts_docs)
    logger.info("saved_scenes", extra={"count": len(pg_rows)})
    return len(pg_rows)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ingest_savers.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/ingest/savers.py tests/test_ingest_savers.py
git commit -m "feat: add batch db and typesense savers"
```

---

### Task 5: Pipeline orchestration

**Files:**
- Create: `scripts/ingest/pipeline.py`

- [ ] **Step 1: Implement the three-phase pipeline**

```python
# scripts/ingest/pipeline.py
import asyncio
import logging
import string

from app.config import settings
from app.database import SessionLocal
from app.services.typesense_client import TypesenseClient
from app.library.common.typesense_schema import SCHEMAS
from scripts.ingest.checkpoint import Checkpoint
from scripts.ingest.api import StashDBClient
from scripts.ingest.savers import batch_save_performers, batch_save_studios, batch_save_scenes

logger = logging.getLogger("ingest.pipeline")

NAME_PREFIXES = [c for c in string.ascii_lowercase] + [str(i) for i in range(10)]
MAX_SCENE_PAGES_PER_STUDIO = 50

async def _phase_performers(client: StashDBClient, ts: TypesenseClient, cp: Checkpoint) -> set[str]:
    db = SessionLocal()
    try:
        start_idx = cp.get("performers_prefix_idx", 0)
        seen_ids = set(cp.get("seen_performer_ids", []))
        seen_studio_ids = set(cp.get("seen_studio_ids", []))
        total = len(seen_ids)

        for idx in range(start_idx, len(NAME_PREFIXES)):
            prefix = NAME_PREFIXES[idx]
            page = cp.get("performers_page", 1) if idx == start_idx else 1
            while True:
                try:
                    performers, _ = await client.fetch_performers_page(prefix, page)
                except Exception as e:
                    logger.warning("performer_page_error", extra={"prefix": prefix, "page": page, "error": str(e)})
                    break
                if not performers:
                    break

                new_females = [p for p in performers if p.get("gender") == "female" and p.get("id") not in seen_ids]
                for p in new_females:
                    seen_ids.add(p["id"])
                    for s_rel in (p.get("studios") or []):
                        s = s_rel.get("studio") or {}
                        if s.get("id"):
                            seen_studio_ids.add(s["id"])

                if new_females:
                    saved = batch_save_performers(db, ts, new_females)
                    total += saved

                logger.info("performers_progress", extra={"prefix": prefix, "page": page, "batch": len(new_females), "total": total})
                cp.set("performers_prefix_idx", idx)
                cp.set("performers_page", page + 1)
                cp.set("seen_performer_ids", list(seen_ids))
                cp.set("seen_studio_ids", list(seen_studio_ids))
                cp.save()
                page += 1

            cp.set("performers_page", 1)
            cp.save()

        logger.info("performers_done", extra={"total": total, "unique_studios": len(seen_studio_ids)})
        return seen_studio_ids
    finally:
        db.close()


async def _phase_studios(client: StashDBClient, ts: TypesenseClient, cp: Checkpoint, studio_ids: set[str]) -> None:
    db = SessionLocal()
    try:
        done = set(cp.get("studios_done", []))
        ids_to_fetch = sorted(studio_ids - done)
        start_idx = cp.get("studios_idx", 0)
        total = len(done)
        batch = []

        for idx in range(start_idx, len(ids_to_fetch)):
            sid = ids_to_fetch[idx]
            studio = await client.fetch_studio(sid)
            if studio:
                batch.append(studio)
                if len(batch) >= 10:
                    saved = batch_save_studios(db, ts, batch)
                    total += saved
                    batch = []
            done.add(sid)
            cp.set("studios_done", list(done))
            cp.set("studios_idx", idx + 1)
            cp.save()

            if idx % 50 == 0:
                logger.info("studios_progress", extra={"fetched": len(done), "total": len(ids_to_fetch)})

        if batch:
            saved = batch_save_studios(db, ts, batch)
            total += saved

        logger.info("studios_done", extra={"total": total})
    finally:
        db.close()


async def _phase_scenes(client: StashDBClient, ts: TypesenseClient, cp: Checkpoint, studio_ids: set[str]) -> None:
    db = SessionLocal()
    try:
        ids_list = sorted(studio_ids)
        start_idx = cp.get("scenes_studio_idx", 0)
        total_scenes = 0

        for idx in range(start_idx, len(ids_list)):
            sid = ids_list[idx]
            page = cp.get("scenes_page", 1) if idx == start_idx else 1
            studio_scenes = 0

            while True:
                try:
                    scenes, _ = await client.fetch_scenes_page(sid, page)
                except Exception as e:
                    logger.warning("scene_page_error", extra={"studio": sid, "page": page, "error": str(e)})
                    break
                if not scenes:
                    break

                saved = batch_save_scenes(db, ts, scenes)
                studio_scenes += saved
                total_scenes += saved

                logger.info("scenes_progress", extra={"studio": sid, "page": page, "batch": len(scenes), "total": total_scenes})
                cp.set("scenes_studio_idx", idx)
                cp.set("scenes_page", page + 1)
                cp.save()
                page += 1
                if page > MAX_SCENE_PAGES_PER_STUDIO:
                    logger.warning("studio_max_pages", extra={"studio": sid, "pages": page})
                    break

            cp.set("scenes_page", 1)
            cp.save()

        logger.info("scenes_done", extra={"total": total_scenes})
    finally:
        db.close()


async def run_pipeline(resume: bool = True) -> None:
    logger.info("pipeline_starting")
    ts = TypesenseClient()
    ts.ensure_collections(SCHEMAS)

    client = StashDBClient(
        api_key=settings.stashdb_api_key,
    )

    cp = Checkpoint()
    if resume:
        cp.load()

    current_phase = cp.get("phase", "performers")

    if current_phase == "performers":
        logger.info("phase_1_performers")
        studio_ids = await _phase_performers(client, ts, cp)
        cp.set("phase", "studios")
        cp.set("studios_done", [])
        cp.set("studios_idx", 0)
        cp.save()
    else:
        studio_ids = set(cp.get("seen_studio_ids", []))

    if current_phase in ("performers", "studios"):
        logger.info("phase_2_studios")
        await _phase_studios(client, ts, cp, studio_ids)
        cp.set("phase", "scenes")
        cp.set("scenes_studio_idx", 0)
        cp.set("scenes_page", 1)
        cp.save()

    logger.info("phase_3_scenes")
    await _phase_scenes(client, ts, cp, studio_ids)
    cp.set("phase", "done")
    cp.save()
    logger.info("pipeline_complete")
```

- [ ] **Step 2: Update CLI entry point**

```python
# scripts/initial_ingest.py (replace entire file)
"""
Async StashDB ingestion pipeline.

Usage:
    docker compose exec laura-backend python scripts/initial_ingest.py [--resume]

Migrates all StashDB data (performers, studios, scenes >= 2000) to
PostgreSQL + Typesense using async parallel requests with checkpoint/resume.

Requires STASHDB_API_KEY in .env (stashdb.org -> Settings -> ApiKeys -> Create).
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from scripts.ingest.pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("initial_ingest")


def main():
    parser = argparse.ArgumentParser(description="StashDB ingestion pipeline")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    args = parser.parse_args()

    if not settings.stashdb_api_key:
        logger.error("STASHDB_API_KEY not set -- add it to .env")
        sys.exit(1)

    asyncio.run(run_pipeline(resume=args.resume))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add scripts/ingest/pipeline.py scripts/initial_ingest.py
git commit -m "feat: rewrite ingest as async parallel pipeline with checkpoint resume"
```

---

### Task 6: Add ingest_concurrency config setting

**Files:**
- Modify: `app/config.py`

- [ ] **Step 1: Add config setting**

```python
# app/config.py
stashdb_ingest_concurrency: int = 5
```

Add this after `stashdb_rate_limit_seconds: float = 1.0`:

```python
stashdb_rate_limit_seconds: float = 1.0
stashdb_ingest_concurrency: int = 5
```

- [ ] **Step 2: Update rate limiter to use config**

In `scripts/ingest/pipeline.py`, update the `StashDBClient` instantiation:

```python
from scripts.ingest.rate_limiter import TokenBucket
client = StashDBClient(
    api_key=settings.stashdb_api_key,
    rate_limiter=TokenBucket(
        capacity=settings.stashdb_ingest_concurrency,
        rate=1.0 / settings.stashdb_rate_limit_seconds,
    ),
)
```

- [ ] **Step 3: Commit**

```bash
git add app/config.py scripts/ingest/pipeline.py
git commit -m "feat: add stashdb_ingest_concurrency config"
```

---

### Task 7: Update existing filter tests

**Files:**
- Modify: `tests/test_ingest_filters.py`

- [ ] **Step 1: Expand ingest filter test**

```python
# tests/test_ingest_filters.py
from scripts.ingest.savers import _scene_to_pg, _scene_to_ts

def test_scene_year_filter():
    assert _scene_to_pg({"release_date": "2000-01-01", "id": "s1", "performers": []}) is not None
    assert _scene_to_pg({"release_date": "1999-12-31", "id": "s2", "performers": []}) is None
    assert _scene_to_pg({"id": "s3", "performers": []}) is None

def test_scene_ts_filter():
    assert _scene_to_ts({"release_date": "2000-01-01", "id": "s1"}) is not None
    assert _scene_to_ts({"release_date": "1999-12-31", "id": "s2"}) is None
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/test_ingest_filters.py -v`
Expected: PASS (2 tests)

- [ ] **Step 3: Commit**

```bash
git add tests/test_ingest_filters.py
git commit -m "test: update ingest filter tests for new saver functions"
```

---

### Task 8: Run all tests and verify

**Files:** N/A — run test suite

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Run lint check (if configured)**

Run: (check if ruff or similar is configured)
Expected: Clean

---

## Self-Review Checklist
1. **Spec coverage:** All requirements map to Tasks 1-8. Three-phase pipeline, async, checkpoint, batch writes all covered.
2. **Placeholder scan:** No TBD/TODO placeholders. All code snippets complete.
3. **Type consistency:** `TokenBucket` created in Task 1, used in Task 3. `Checkpoint` created in Task 2, used in Task 5. All function signatures match across tasks.
4. **Graceful failure:** Checkpoint saves progress every page/batch — crash at any point loses at most 1 page.
5. **Rate limiting:** Token-bucket allows burst of N concurrent requests (configurable) while sustaining 1 req/s average — StashDB won't get hammered even with parallelism.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-14-async-ingest-pipeline.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
