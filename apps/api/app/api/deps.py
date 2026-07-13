from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.auth import CurrentUser, verify_token
from app.core.config import settings


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )

    token = authorization.removeprefix("Bearer ").strip()
    payload = verify_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        )

    return CurrentUser(user_id=user_id, email=payload.get("email"))


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


async def get_optional_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser | None:
    if not authorization:
        return None
    return await get_current_user(authorization)


OptionalCurrentUserDep = Annotated[CurrentUser | None, Depends(get_optional_current_user)]


async def get_managed_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser | None:
    """Require login for managed data in every deployed environment.

    Anonymous access remains available only for an explicitly local developer
    session where the JSON repository is intentionally used as a preview.
    """
    if authorization:
        return await get_current_user(authorization)
    if not settings.is_deployed:
        return None
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Login is required for managed strategy data",
    )


ManagedUserDep = Annotated[CurrentUser | None, Depends(get_managed_user)]
