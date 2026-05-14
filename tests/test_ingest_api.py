import pytest
from scripts.ingest.api import StashDBClient


class FakeOk:
    def __init__(self, json_data):
        self._json = json_data
    def json(self):
        return self._json
    def raise_for_status(self):
        pass


class FakeError:
    def raise_for_status(self):
        raise Exception("HTTP 500")


@pytest.mark.asyncio
async def test_fetch_performers_page(monkeypatch):
    async def fake_post(*a, **kw):
        return FakeOk({"data": {"queryPerformers": {"count": 1, "performers": [{"id": "p1"}]}}})
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    client = StashDBClient(api_key="test")
    perf, count = await client.fetch_performers_page("alice", page=1)
    assert len(perf) == 1
    assert count == 1


@pytest.mark.asyncio
async def test_fetch_performers_page_error(monkeypatch):
    async def fake_post(*a, **kw):
        return FakeError()
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    client = StashDBClient(api_key="test")
    perf, count = await client.fetch_performers_page("alice", page=1)
    assert perf == []
    assert count == 0


@pytest.mark.asyncio
async def test_fetch_scenes_page(monkeypatch):
    async def fake_post(*a, **kw):
        return FakeOk({"data": {"queryScenes": {"count": 1, "scenes": [{"id": "s1"}]}}})
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    client = StashDBClient(api_key="test")
    scenes, count = await client.fetch_scenes_page("st1", page=1)
    assert len(scenes) == 1


@pytest.mark.asyncio
async def test_fetch_scenes_page_error(monkeypatch):
    async def fake_post(*a, **kw):
        return FakeError()
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    client = StashDBClient(api_key="test")
    scenes, count = await client.fetch_scenes_page("st1", page=1)
    assert scenes == []
    assert count == 0


@pytest.mark.asyncio
async def test_fetch_studio(monkeypatch):
    async def fake_post(*a, **kw):
        return FakeOk({"data": {"findStudio": {"id": "st1", "name": "Test Studio"}}})
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    client = StashDBClient(api_key="test")
    studio = await client.fetch_studio("st1")
    assert studio["name"] == "Test Studio"


@pytest.mark.asyncio
async def test_fetch_studio_error(monkeypatch):
    async def fake_post(*a, **kw):
        return FakeError()
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    client = StashDBClient(api_key="test")
    studio = await client.fetch_studio("st1")
    assert studio is None
