import asyncio

import httpx
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.heatmap import HeatmapReport, HeatmapRequest
from app.schemas.montecarlo import MonteCarloReport, MonteCarloRequest
from app.schemas.overfitting import OverfittingReport, OverfittingRequest
from app.schemas.walkforward import WalkForwardReport, WalkForwardRequest
from app.services.heatmap_engine import run_heatmap
from app.services.market_data import MarketDataError, fetch_provider_history
from app.services.montecarlo_engine import run_montecarlo
from app.services.overfitting_engine import run_overfitting
from app.services.walkforward_engine import run_walkforward

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/montecarlo", response_model=MonteCarloReport)
async def post_montecarlo(request: MonteCarloRequest) -> MonteCarloReport:
    try:
        qqq_rows = await fetch_provider_history("QQQ", settings.market_data_provider.lower())
    except (httpx.HTTPError, MarketDataError) as exc:
        raise HTTPException(status_code=502, detail=f"Market data request failed: {exc}") from exc
    try:
        # CPU-bound; run off the event loop so the server stays responsive.
        return await asyncio.to_thread(run_montecarlo, request, qqq_rows)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/walkforward", response_model=WalkForwardReport)
async def post_walkforward(request: WalkForwardRequest) -> WalkForwardReport:
    try:
        return await run_walkforward(request, settings.market_data_provider.lower())
    except (httpx.HTTPError, MarketDataError) as exc:
        raise HTTPException(status_code=502, detail=f"Market data request failed: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/heatmap", response_model=HeatmapReport)
async def post_heatmap(request: HeatmapRequest) -> HeatmapReport:
    try:
        return await run_heatmap(request, settings.market_data_provider.lower())
    except (httpx.HTTPError, MarketDataError) as exc:
        raise HTTPException(status_code=502, detail=f"Market data request failed: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/overfitting", response_model=OverfittingReport)
async def post_overfitting(request: OverfittingRequest) -> OverfittingReport:
    try:
        return await run_overfitting(request, settings.market_data_provider.lower())
    except (httpx.HTTPError, MarketDataError) as exc:
        raise HTTPException(status_code=502, detail=f"Market data request failed: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
