from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_deployed_managed_strategies_requires_login(monkeypatch):
    monkeypatch.setattr(settings, "railway_project_id", "project-test")
    settings.__dict__.pop("is_deployed", None)
    try:
        response = client.get("/managed-strategies")
        assert response.status_code == 401
    finally:
        settings.__dict__.pop("is_deployed", None)


def test_local_managed_strategies_allows_preview(monkeypatch, tmp_path):
    from app.repositories import managed_strategy_repository as repository

    monkeypatch.setattr(settings, "railway_project_id", "")
    monkeypatch.setattr(settings, "railway_environment_name", "")
    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(repository, "DATA_PATH", tmp_path / "strategies.json")
    settings.__dict__.pop("is_deployed", None)
    try:
        response = client.get("/managed-strategies")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        settings.__dict__.pop("is_deployed", None)
