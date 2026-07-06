import httpx
from fastapi import APIRouter, HTTPException

from app.schemas.backtest import BacktestRunRequest, BacktestRunResponse
from app.services.backtest_engine import run_backtest

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestRunResponse)
async def run_backtest_route(request: BacktestRunRequest) -> BacktestRunResponse:
    try:
        return await run_backtest(request)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Market data request failed: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
