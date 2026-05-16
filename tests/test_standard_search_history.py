from fastapi.testclient import TestClient
from app.main import app
from app.auth.dependencies import get_current_user
from app.database import get_db
from unittest.mock import MagicMock
from app.models import StandardSearchHistory

client = TestClient(app)


def test_history_requires_auth():
    resp = client.get("/api/v1/standard-search/history")
    assert resp.status_code == 403


def test_delete_history_item():
    mock_db = MagicMock()
    mock_user = {"sub": "user-1"}

    # Setup mock item
    mock_item = StandardSearchHistory(id=1, user_id="user-1", query="test")

    # Mock query.filter_by().first()
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_item

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        resp = client.delete("/api/v1/standard-search/history/1")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

        mock_db.delete.assert_called_once_with(mock_item)
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_delete_history_item_not_found():
    mock_db = MagicMock()
    mock_user = {"sub": "user-1"}

    # Mock query.filter_by().first() to return None
    mock_db.query.return_value.filter_by.return_value.first.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        resp = client.delete("/api/v1/standard-search/history/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Item not found"
    finally:
        app.dependency_overrides.clear()


def test_get_history():
    mock_db = MagicMock()
    mock_user = {"sub": "user-1"}

    # Setup mock items
    mock_items = [
        StandardSearchHistory(
            id=1,
            user_id="user-1",
            query="test",
            results=[{"title": "Result 1"}],
            result_count=1,
            status="completed",
        )
    ]

    # Mock query.filter_by().order_by().all()
    mock_query = mock_db.query.return_value.filter_by.return_value.order_by.return_value
    mock_query.all.return_value = mock_items

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        resp = client.get("/api/v1/standard-search/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["query"] == "test"
        assert data[0]["results"] == [{"title": "Result 1"}]
        assert data[0]["result_count"] == 1
    finally:
        app.dependency_overrides.clear()
