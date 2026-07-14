from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.schemas.insight import InsightReport, InsightRequest
from app.services.ai_insight import generate_insight

router = APIRouter(prefix="/insights", tags=["insights"])


@router.post("/interpret", response_model=InsightReport)
async def interpret(request: InsightRequest) -> InsightReport:
    return await run_in_threadpool(generate_insight, request)
