"""Deployed environments must never touch the shared local JSON file."""

import pytest

from app.core.config import settings
from app.repositories import managed_strategy_repository as repo


def test_save_blocked_for_anonymous_on_deployed_env(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    with pytest.raises(repo.SharedStorageWriteBlocked):
        repo._save([], user_id=None)


def test_load_returns_empty_for_anonymous_on_deployed_env(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "app_env", "production")
    data_path = tmp_path / "managed_strategies.json"
    data_path.write_text('[{"bogus": true}]', encoding="utf-8")
    monkeypatch.setattr(repo, "DATA_PATH", data_path)
    assert repo._load(user_id=None) == []


def test_local_env_still_uses_shared_file(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "app_env", "local")
    data_path = tmp_path / "managed_strategies.json"
    monkeypatch.setattr(repo, "DATA_PATH", data_path)
    repo._save([], user_id=None)
    assert data_path.exists()
    assert repo._load(user_id=None) == []
