"""Import local managed strategy JSON into a Supabase user account.

Required environment variables:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  TARGET_EMAIL

Optional:
  LOCAL_STRATEGY_JSON
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value.rstrip("/") if name == "SUPABASE_URL" else value


def get_user_id(supabase_url: str, service_role_key: str, target_email: str) -> str:
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }
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
                return user["id"]
        if not users or len(users) < 100:
            break
        page += 1
    raise SystemExit(f"Could not find Supabase auth user: {target_email}")


def import_rows(supabase_url: str, service_role_key: str, user_id: str, json_path: Path) -> int:
    if not json_path.exists():
        raise SystemExit(f"Local strategy JSON not found: {json_path}")

    raw_items = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(raw_items, list):
        raise SystemExit("Local strategy JSON must be a list.")

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        data = dict(item)
        data["id"] = uuid4().hex
        data["created_at"] = now
        data["updated_at"] = now
        reason = str(data.get("selected_reason") or "").strip()
        data["selected_reason"] = (
            f"{reason} / 로그인 후 기존 로컬 데이터를 가져왔습니다."
            if reason
            else "로그인 후 기존 로컬 데이터를 가져왔습니다."
        )
        rows.append(
            {
                "id": data["id"],
                "user_id": user_id,
                "data": data,
                "created_at": now,
                "updated_at": now,
            }
        )

    if not rows:
        return 0

    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    response = httpx.post(
        f"{supabase_url}/rest/v1/managed_strategies",
        params={"on_conflict": "id"},
        headers=headers,
        json=rows,
        timeout=60,
    )
    response.raise_for_status()
    return len(rows)


def main() -> None:
    supabase_url = required_env("SUPABASE_URL")
    service_role_key = required_env("SUPABASE_SERVICE_ROLE_KEY")
    target_email = required_env("TARGET_EMAIL")
    default_path = Path(__file__).resolve().parents[1] / "data" / "managed_strategies.json"
    json_path = Path(os.getenv("LOCAL_STRATEGY_JSON", str(default_path)))

    user_id = get_user_id(supabase_url, service_role_key, target_email)
    count = import_rows(supabase_url, service_role_key, user_id, json_path)
    print(f"Imported {count} strategies into {target_email} ({user_id}).")


if __name__ == "__main__":
    main()
