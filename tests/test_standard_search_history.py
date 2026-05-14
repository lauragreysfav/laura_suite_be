from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_history_requires_auth():
    resp = client.get("/api/v1/standard-search/history")
    assert resp.status_code == 403
