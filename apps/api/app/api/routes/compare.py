import httpx
from fastapi import APIRouter, HTTPException

from app.schemas.compare import StrategyCompareRequest, StrategyCompareResponse
from app.services.compare_engine import compare_strategies

router = APIRouter(prefix="/compare", tags=["compare"])


@router.post("/strategies", response_model=StrategyCompareResponse)
async def compare_strategy_route(request: StrategyCompareRequest) -> StrategyCompareResponse:
    try:
        return await compare_strategies(request)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Market data request failed: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
