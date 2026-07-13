from app.schemas.strategy import StrategyRecommendRequest, StrategyRecommendResponse
from app.services.strategy_allocation import classify_market
from app.services.strategy_report import (
    build_candidate_opinions,
    build_plans,
    build_rule_based_report,
    diagnose_current_portfolio,
    normalize_holdings,
)


def recommend_strategy(request: StrategyRecommendRequest) -> StrategyRecommendResponse:
    holdings = normalize_holdings(request.holdings)
    total = request.cash + sum(holding.amount for holding in holdings)
    if total <= 0:
        total = 1

    distance = (request.market.qqq_close / request.market.qqq_sma200 - 1) * 100
    regime = classify_market(distance)
    diagnosis = diagnose_current_portfolio(holdings, request.cash, total, distance)
    opinions = build_candidate_opinions(request, regime)
    plans = build_plans(request, holdings, total, distance, regime)
    plans.sort(key=lambda plan: plan.scores.fit_score, reverse=True)
    coach_report = build_rule_based_report(
        plans[0],
        diagnosis,
        regime,
        distance,
        request.profile.risk_score,
    )

    return StrategyRecommendResponse(
        total_capital=total,
        market_regime=regime,
        qqq_distance_from_200ma=round(distance, 2),
        current_diagnosis=diagnosis,
        candidate_opinions=opinions,
        plans=plans,
        coach_report=coach_report,
        ai_used=False,
    )
