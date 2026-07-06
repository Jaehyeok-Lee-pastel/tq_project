from functools import lru_cache

from fastapi import HTTPException, status
from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_supabase() -> Client:
    """Server-side Supabase client (service role — bypasses RLS).

    The ONLY place a Supabase client is created on the backend. Always verify
    tenant/ownership in the service layer because RLS is bypassed here.
    """
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase server credentials are not configured",
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def single_or_none(response) -> dict | None:
    """Return the first row of a Supabase response, or None."""
    data = response.data
    if isinstance(data, list):
        return data[0] if data else None
    return data
