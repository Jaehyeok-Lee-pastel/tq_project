from app.services.supabase import get_supabase, single_or_none


def get_profile_by_id(user_id: str) -> dict | None:
    """Fetch a profile row by user id (None if not found)."""
    res = (
        get_supabase()
        .table("profiles")
        .select("*")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    return single_or_none(res)
