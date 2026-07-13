from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    backtest,
    compare,
    health,
    insights,
    managed_strategies,
    market,
    me,
    research,
    strategy,
)
from app.core.config import settings
from app.core.errors import register_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(market.router)
    app.include_router(strategy.router)
    app.include_router(backtest.router)
    app.include_router(compare.router)
    app.include_router(research.router)
    app.include_router(insights.router)
    app.include_router(managed_strategies.router)
    app.include_router(me.router)  # example protected route (GET /me)

    return app


app = create_app()
