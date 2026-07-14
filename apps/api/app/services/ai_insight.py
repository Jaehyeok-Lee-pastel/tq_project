import json
import logging
from functools import lru_cache

from fastapi import HTTPException, status
from openai import OpenAI

from app.core.config import settings
from app.schemas.insight import InsightReport, InsightRequest

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a Korean investment strategy validation coach.
Your job is to interpret already-computed backtest and strategy comparison results.

Return only valid JSON. Do not include markdown.
Never invent numbers. Use only supplied JSON.
Do not guarantee profits or provide personalized financial advice.
Focus on trust, robustness, risk, drawdown, and execution difficulty.

Return JSON with:
headline, confidence_level, summary, strongest_evidence, main_risks, recommended_next_steps
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


def generate_insight(request: InsightRequest) -> InsightReport:
    if not request.use_ai:
        return build_rule_based_insight(request)
    try:
        return generate_ai_insight(request)
    except Exception:
        logger.exception("AI insight failed; falling back to rule-based insight")
        return build_rule_based_insight(request)


def generate_ai_insight(request: InsightRequest) -> InsightReport:
    client = get_openai_client()
    user_prompt = json.dumps(request.model_dump(), ensure_ascii=False)
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        max_completion_tokens=settings.ai_max_output_tokens,
    )
    content = completion.choices[0].message.content or "{}"
    report = InsightReport.model_validate(json.loads(content))
    return report.model_copy(update={"ai_used": True})


def build_rule_based_insight(request: InsightRequest) -> InsightReport:
    payload = request.payload
    rankings = payload.get("rankings") or []
    sensitivity = payload.get("sensitivity") or {}
    if not rankings:
        return InsightReport(
            headline="비교 결과가 아직 부족합니다.",
            confidence_level="low",
            summary="전략 랭킹 데이터가 없어 해석 리포트를 만들 수 없습니다.",
            recommended_next_steps=["전략 비교를 먼저 실행하세요."],
        )

    winner = rankings[0]
    worst_mdd = min((item.get("max_drawdown", 0) for item in rankings), default=0)
    robustness_score = sensitivity.get("robustness_score")
    confidence = "high" if robustness_score and robustness_score >= 75 else "medium"
    if winner.get("verdict") == "too_risky" or worst_mdd <= -70:
        confidence = "low"

    evidence = [
        (
            f"1위 전략은 {winner.get('strategy_name')}이며 "
            f"종합 점수는 {winner.get('total_score')}점입니다."
        ),
        f"CAGR {winner.get('cagr')}%, MDD {winner.get('max_drawdown')}%로 계산되었습니다.",
    ]
    if robustness_score is not None:
        evidence.append(
            f"이동평균 민감도 견고성은 {robustness_score}점, "
            f"판정은 {sensitivity.get('verdict')}입니다."
        )

    risks = [
        "백테스트는 과거 검증이며 미래 수익을 보장하지 않습니다.",
        "TQQQ 계열 전략은 급락장과 횡보장에서 손실 회복이 오래 걸릴 수 있습니다.",
    ]
    if winner.get("max_drawdown", 0) <= -50:
        risks.append("1위 전략도 과거 최대낙폭이 큰 편이라 실제 운용 난이도가 높습니다.")

    steps = [
        "1위 전략을 바로 확정하지 말고 개인연구의 상세 백테스트와 거래 로그를 확인하세요.",
        "150/180/200/220/250일선 결과가 크게 갈리면 비중을 낮추세요.",
        "QQQ가 장기선 위인지, 현재 과열 구간인지 매수 전 다시 확인하세요.",
    ]

    return InsightReport(
        headline=f"{winner.get('strategy_name')}이 현재 조건의 우선 후보입니다.",
        confidence_level=confidence,
        summary=(
            "동일 원금 기준 비교에서는 수익성, 방어력, 리스크 적합도, 견고성을 "
            "함께 보는 방식이 가장 중요합니다."
        ),
        strongest_evidence=evidence,
        main_risks=risks,
        recommended_next_steps=steps,
    )
