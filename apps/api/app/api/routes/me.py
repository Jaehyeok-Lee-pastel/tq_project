from fastapi import APIRouter

from app.api.deps import CurrentUserDep
from app.repositories.profile_repository import get_profile_by_id
from app.schemas.me import MeResponse

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeResponse)
async def read_me(current_user: CurrentUserDep) -> MeResponse:
    """Example protected route — requires a valid Supabase bearer token.

    Demonstrates the full path: deps (auth) → repository (Supabase) → schema.
    """
    profile = get_profile_by_id(current_user.user_id) or {}
    return MeResponse(
        user_id=current_user.user_id,
        email=profile.get("email") or current_user.email,
        display_name=profile.get("display_name"),
    )
