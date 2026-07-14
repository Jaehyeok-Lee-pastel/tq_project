from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.errors import UserFacingPermissionError
from app.schemas.managed_strategy import ManagedStrategy
from app.services.supabase import get_supabase

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "managed_strategies.json"
SUPABASE_TABLE = "managed_strategies"
LOCAL_ENVS = {"local", "dev", "development", "test"}


class SharedStorageWriteBlocked(UserFacingPermissionError):
    """Raised when a deployed request would write to shared local storage."""


def _use_supabase(user_id: str | None) -> bool:
    return bool(user_id and settings.supabase_url and settings.supabase_service_role_key)


def _shared_file_allowed() -> bool:
    return not settings.is_deployed and settings.app_env.lower() in LOCAL_ENVS


def _ensure_writable(user_id: str | None) -> None:
    if _use_supabase(user_id) or _shared_file_allowed():
        return
    raise SharedStorageWriteBlocked(
        "배포 환경에서는 로그인과 Supabase 설정 없이 전략을 저장할 수 없습니다."
    )


def _load(user_id: str | None = None) -> list[ManagedStrategy]:
    if _use_supabase(user_id):
        response = (
            get_supabase()
            .table(SUPABASE_TABLE)
            .select("data")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return [ManagedStrategy.model_validate(row["data"]) for row in response.data]
    if not _shared_file_allowed():
        return []
    if not DATA_PATH.exists():
        return []
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return [ManagedStrategy.model_validate(item) for item in raw]


def _save(items: list[ManagedStrategy], user_id: str | None = None) -> None:
    _ensure_writable(user_id)
    if _use_supabase(user_id):
        rows = [
            {
                "id": item.id,
                "user_id": user_id,
                "data": item.model_dump(),
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in items
        ]
        if rows:
            get_supabase().table(SUPABASE_TABLE).upsert(rows, on_conflict="id").execute()
        return
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps([item.model_dump() for item in items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_strategies(user_id: str | None = None) -> list[ManagedStrategy]:
    return sorted(_load(user_id), key=lambda item: item.created_at, reverse=True)


def get_strategy(strategy_id: str, user_id: str | None = None) -> ManagedStrategy:
    for strategy in _load(user_id):
        if strategy.id == strategy_id:
            return strategy
    raise KeyError(strategy_id)


def delete_strategy_record(strategy_id: str, user_id: str | None = None) -> list[ManagedStrategy]:
    _ensure_writable(user_id)
    items = _load(user_id)
    remaining = [strategy for strategy in items if strategy.id != strategy_id]
    if len(remaining) == len(items):
        raise KeyError(strategy_id)
    if _use_supabase(user_id):
        get_supabase().table(SUPABASE_TABLE).delete().eq("id", strategy_id).eq(
            "user_id", user_id
        ).execute()
    else:
        _save(remaining, user_id)
    return remaining


# Keep older internal scripts working while application code migrates to the service.
_LEGACY_SERVICE_EXPORTS = {
    "add_journal_entry",
    "advise_adjustment",
    "advise_contribution",
    "advise_philosophy_upgrade",
    "apply_adjustment",
    "apply_contribution",
    "apply_deposit",
    "apply_philosophy_upgrade",
    "build_backtest_request_from_strategy",
    "build_execution_plan",
    "build_guide",
    "create_strategy",
    "delete_journal_entry",
    "delete_strategy",
    "update_strategy",
}


def __getattr__(name: str) -> Any:
    if name not in _LEGACY_SERVICE_EXPORTS:
        raise AttributeError(name)
    from app.services import managed_strategy_service

    return getattr(managed_strategy_service, name)
