from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_me_requires_auth():
    # No bearer token → 401 (does not touch Supabase).
    res = client.get("/me")
    assert res.status_code == 401
