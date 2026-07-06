import json
import logging
from functools import lru_cache

from fastapi import HTTPException, status
from openai import OpenAI

from app.core.config import settings
from app.schemas.strategy import CoachReport, StrategyRecommendRequest, StrategyRecommendResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a Korean investment strategy coach specialized in TQQQ, QLD, Nasdaq-100 trend filters,
200-day moving average rules, split-buy plans, split-sell plans, and risk control.

Return only valid JSON. Do not include markdown.
You are not a licensed financial advisor. Never guarantee profit.
Use a practical coaching tone in Korean.

Important rules:
- Do not invent market numbers. Use only the supplied JSON.
- Do not override the deterministic strategy engine's allocations.
- Explain why the recommended plan fits the user's stated goal.
- Emphasize TQQQ risk, 200-day moving average exit rules, and cash as strategic reserve.
- Keep the answer concise enough for a dashboard card.

Return JSON with:
headline, diagnosis, recommended_plan_id, why, next_actions, warnings, monitoring_rules
"""


@lru_cache
def get_openai_client() -> OpenAI:
    if not settings.openai_api_key or settings.openai_api_key == "PASTE_OPENAI_API_KEY_HERE":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY is not configured",
        )
    return OpenAI(
        api_key=settings.openai_api_key,
        max_retries=1,
        timeout=settings.ai_request_timeout_seconds,
    )


def generate_coach_report(
    request: StrategyRecommendRequest,
    response: StrategyRecommendResponse,
) -> CoachReport:
    client = get_openai_client()
    payload = {
        "user_request": request.model_dump(),
        "strategy_engine_result": response.model_dump(exclude={"coach_report", "ai_used"}),
    }
    user_prompt = json.dumps(payload, ensure_ascii=False)

    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=settings.ai_max_output_tokens,
        )
    except Exception as exc:
        logger.exception("AI coach request failed with model=%s", settings.openai_model)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI coach failed: {type(exc).__name__}",
        ) from exc

    content = completion.choices[0].message.content or "{}"
    try:
        return CoachReport.model_validate(json.loads(content))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI coach returned invalid JSON",
        ) from exc
