from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert "service" in body
    assert "ready" in body
    assert set(body["checks"]) == {"supabase", "cors", "market_data"}
