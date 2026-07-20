from app.schemas.strategy import (
    InvestorProfile,
    MarketSnapshot,
    StrategyRecommendRequest,
)
from app.services.strategy_engine import recommend_strategy


def make_request(execution_style: str) -> StrategyRecommendRequest:
    return StrategyRecommendRequest(
        holdings=[],
        cash=1_000_000,
        profile=InvestorProfile(risk_score=75),
        market=MarketSnapshot(
            qqq_close=700,
            qqq_sma200=650,
            qqq_sma20=690,
            qqq_sma50=675,
            as_of="2026-07-20",
        ),
        execution_style=execution_style,  # type: ignore[arg-type]
        monthly_contribution=1_000_000,
    )


def test_daily_recommendation_uses_daily_execution_copy() -> None:
    response = recommend_strategy(make_request("daily"))

    assert len(response.plans) == 1
    assert response.plans[0].execution_style == "daily"
    assert [step.step for step in response.plans[0].buy_plan] == ["오늘 적립", "월급일 1x 매수"]


def test_staged_recommendation_keeps_staged_execution_copy() -> None:
    response = recommend_strategy(make_request("staged"))

    assert len(response.plans) == 3
    assert response.plans[0].execution_style == "staged"
    assert response.plans[0].buy_plan[0].step == "1차 매수"
