from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.schemas.strategy import StrategyRecommendRequest, StrategyRecommendResponse
from app.services.ai_coach import generate_coach_report
from app.services.strategy_engine import recommend_strategy

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.post("/recommend", response_model=StrategyRecommendResponse)
async def recommend(request: StrategyRecommendRequest) -> StrategyRecommendResponse:
    response = recommend_strategy(request)
    if not request.use_ai:
        return response

    try:
        report = await run_in_threadpool(generate_coach_report, request, response)
    except Exception:
        return response

    return response.model_copy(update={"coach_report": report, "ai_used": True})
