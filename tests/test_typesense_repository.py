from unittest.mock import MagicMock
from app.library.common import repository


def test_search_index_calls_typesense(monkeypatch):
    monkeypatch.setattr(repository, "SessionLocal", MagicMock)
    fake = MagicMock()
    fake.search.return_value = [{"title": "x"}]
    repository._client = fake
    out = repository.search_index("stashdb_scenes", "x", fields=["title^3"])
    repository._client = None
    assert out == [{"title": "x"}]


def test_suggest_index_returns_list():
    fake = MagicMock()
    fake.search.return_value = [{"id": "1", "name": "alice"}]
    repository._client = fake
    out = repository.suggest_index("stashdb_performers", "ali", field="name", size=5)
    repository._client = None
    assert len(out) == 1


def test_get_document_returns_none_on_miss(monkeypatch):
    class FakeSession:
        def query(self, model):
            q = MagicMock()
            q.filter.return_value.first.return_value = None
            return q
        def close(self):
            pass
    monkeypatch.setattr(repository, "SessionLocal", lambda: FakeSession())
    from app.services.typesense_client import TypesenseClient
    fake = MagicMock(spec=TypesenseClient)
    fake.get.return_value = None
    repository._client = fake
    out = repository.get_document("stashdb_performers", "nope")
    repository._client = None
    assert out is None


def test_search_by_hashes_returns_matched(monkeypatch):
    monkeypatch.setattr(repository, "SessionLocal", MagicMock)
    from app.services.typesense_client import TypesenseClient
    fake = MagicMock(spec=TypesenseClient)
    fake.search_by_hashes.return_value = [
        {"id": "s1", "fingerprints": ["abc", "def"]}
    ]
    repository._client = fake
    out = repository.search_by_hashes("stashdb_scenes", ["abc"])
    repository._client = None
    assert "abc" in out


def test_index_document_includes_id():
    fake = MagicMock()
    repository._client = fake
    repository.index_document("stashdb_performers", "p1", {"name": "alice"})
    repository._client = None
    fake.upsert.assert_called_once_with("stashdb_performers", {"id": "p1", "name": "alice"})


def test_bulk_index_skips_missing_id():
    fake = MagicMock()
    repository._client = fake
    repository.bulk_index("stashdb_scenes", [{"title": "no id"}])
    repository._client = None
    fake.bulk_upsert.assert_called_once_with("stashdb_scenes", [])
