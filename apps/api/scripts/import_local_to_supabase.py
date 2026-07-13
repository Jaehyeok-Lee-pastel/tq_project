"""Safely migrate local managed strategies into one Supabase account.

Required for remote inspection/import:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  TARGET_EMAIL

Optional:
  LOCAL_STRATEGY_JSON   Source JSON path.
  MIGRATION_MODE       "dry-run" (default) or "upsert".
  FORCE_OLDER_SOURCE   "1" to overwrite a newer remote row.

The migration preserves strategy IDs, timestamps, journal entries, and
version history. Before an upsert it writes a local backup of the target
user's current remote rows.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value.rstrip("/") if name == "SUPABASE_URL" else value


def auth_headers(service_role_key: str, **extra: str) -> dict[str, str]:
    return {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        **extra,
    }


def get_user_id(supabase_url: str, service_role_key: str, target_email: str) -> str:
    headers = auth_headers(service_role_key)
    page = 1
    while True:
        response = httpx.get(
            f"{supabase_url}/auth/v1/admin/users",
            params={"page": page, "per_page": 100},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        users = payload.get("users", payload if isinstance(payload, list) else [])
        for user in users:
            if str(user.get("email", "")).lower() == target_email.lower():
                return str(user["id"])
        if not users or len(users) < 100:
            break
        page += 1
    raise SystemExit(f"Could not find Supabase auth user: {target_email}")


def load_source(json_path: Path) -> list[dict[str, Any]]:
    if not json_path.exists():
        raise SystemExit(f"Local strategy JSON not found: {json_path}")
    raw_items = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(raw_items, list):
        raise SystemExit("Local strategy JSON must be a list.")

    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            raise SystemExit(f"Source item {index} is not an object.")
        strategy_id = str(item.get("id") or "").strip()
        if not strategy_id:
            raise SystemExit(f"Source item {index} has no strategy id.")
        if strategy_id in seen_ids:
            raise SystemExit(f"Duplicate strategy id in source: {strategy_id}")
        seen_ids.add(strategy_id)
        rows.append(dict(item))
    return rows


def fetch_remote_rows(
    supabase_url: str, service_role_key: str, user_id: str
) -> list[dict[str, Any]]:
    response = httpx.get(
        f"{supabase_url}/rest/v1/managed_strategies",
        params={"user_id": f"eq.{user_id}", "select": "*", "order": "updated_at.desc"},
        headers=auth_headers(service_role_key),
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []


def parse_time(value: Any) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return datetime.min.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def build_plan(
    source: list[dict[str, Any]], remote: list[dict[str, Any]], force_older: bool
) -> tuple[list[dict[str, Any]], list[str]]:
    remote_by_id = {str(row.get("id")): row for row in remote}
    planned: list[dict[str, Any]] = []
    messages: list[str] = []

    for item in source:
        strategy_id = str(item["id"])
        existing = remote_by_id.get(strategy_id)
        if existing is None:
            planned.append(item)
            messages.append(f"INSERT {strategy_id} version={item.get('version', 1)}")
            continue

        source_updated = parse_time(item.get("updated_at"))
        remote_updated = parse_time(existing.get("updated_at"))
        if source_updated < remote_updated and not force_older:
            messages.append(
                f"SKIP   {strategy_id} remote is newer "
                f"({remote_updated.isoformat()} > {source_updated.isoformat()})"
            )
            continue
        if existing.get("data") == item:
            messages.append(f"SKIP   {strategy_id} already identical")
            continue
        planned.append(item)
        messages.append(f"UPDATE {strategy_id} version={item.get('version', 1)}")

    return planned, messages


def write_backup(remote: list[dict[str, Any]], target_email: str) -> Path:
    root = Path(__file__).resolve().parents[1] / "data" / "migration_backups"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_email = target_email.replace("@", "_at_").replace(".", "_")
    path = root / f"supabase_{safe_email}_{stamp}.json"
    path.write_text(json.dumps(remote, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def upsert_rows(
    supabase_url: str,
    service_role_key: str,
    user_id: str,
    items: list[dict[str, Any]],
) -> int:
    if not items:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "id": str(item["id"]),
            "user_id": user_id,
            "data": item,
            "created_at": item.get("created_at") or now,
            "updated_at": item.get("updated_at") or now,
        }
        for item in items
    ]
    response = httpx.post(
        f"{supabase_url}/rest/v1/managed_strategies",
        params={"on_conflict": "id"},
        headers=auth_headers(
            service_role_key,
            **{
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
        ),
        json=rows,
        timeout=60,
    )
    response.raise_for_status()
    return len(rows)


def main() -> None:
    mode = os.getenv("MIGRATION_MODE", "dry-run").strip().lower()
    if mode not in {"dry-run", "upsert"}:
        raise SystemExit("MIGRATION_MODE must be 'dry-run' or 'upsert'.")

    supabase_url = required_env("SUPABASE_URL")
    service_role_key = required_env("SUPABASE_SERVICE_ROLE_KEY")
    target_email = required_env("TARGET_EMAIL")
    default_path = Path(__file__).resolve().parents[1] / "data" / "managed_strategies.json"
    json_path = Path(os.getenv("LOCAL_STRATEGY_JSON", str(default_path)))
    source = load_source(json_path)
    user_id = get_user_id(supabase_url, service_role_key, target_email)
    remote = fetch_remote_rows(supabase_url, service_role_key, user_id)
    planned, messages = build_plan(
        source, remote, force_older=os.getenv("FORCE_OLDER_SOURCE") == "1"
    )

    print(f"Target: {target_email} ({user_id})")
    print(f"Source: {json_path} ({len(source)} strategies)")
    print(f"Remote: {len(remote)} strategies")
    for message in messages:
        print(message)
    print(f"Planned writes: {len(planned)}")

    if mode == "dry-run":
        print("Dry run only. Set MIGRATION_MODE=upsert to apply the plan.")
        return

    backup = write_backup(remote, target_email)
    count = upsert_rows(supabase_url, service_role_key, user_id, planned)
    print(f"Backup: {backup}")
    print(f"Migrated {count} strategies into {target_email}.")


if __name__ == "__main__":
    main()
