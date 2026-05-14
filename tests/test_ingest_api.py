import pytest
from scripts.ingest.api import StashDBClient


@pytest.mark.asyncio
async def test_fetch_performers_page(monkeypatch):
    async def fake_post(*a, **kw):
        class FakeResp:
            def json(self):
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
            def json(self):
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
            def json(self):
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
