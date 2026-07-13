from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    checks = {
        "supabase": settings.supabase_ready,
        "cors": settings.cors_ready,
        "market_data": settings.market_data_provider.lower() in {"yahoo", "stooq"},
    }
    return {
        "ok": True,
        "service": settings.app_name,
        "env": "production" if settings.is_deployed else settings.app_env,
        "ready": all(checks.values()) if settings.is_deployed else checks["market_data"],
        "checks": checks,
    }
