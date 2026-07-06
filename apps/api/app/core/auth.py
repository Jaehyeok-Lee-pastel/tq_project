from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings
from app.services.supabase import get_supabase


class CurrentUser:
    def __init__(self, user_id: str, email: str | None = None):
        self.user_id = user_id
        self.email = email


def verify_token(token: str) -> dict:
    """Verify a Supabase JWT and return its payload ({sub, email}).

    Prefers local HS256 verification with SUPABASE_JWT_SECRET; falls back to
    asking Supabase auth to resolve the token. Raises 401 on failure.
    """
    if settings.supabase_jwt_secret:
        try:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"require": ["exp", "sub"]},
            )
        except JWTError:
            pass

    try:
        auth_response = get_supabase().auth.get_user(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token"
        ) from exc

    auth_user = getattr(auth_response, "user", None)
    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token"
        )
    return {"sub": auth_user.id, "email": auth_user.email}
