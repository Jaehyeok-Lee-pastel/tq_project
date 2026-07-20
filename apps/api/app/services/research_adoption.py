"""Turn a research-lab strategy (ComparePage ranking pick) into a managed strategy.

Builds a plan-lite StrategyPlan so the existing management UI (allocations,
version history, journal) keeps working, while the verbatim rule set lives in
research_config for the today-decision endpoint and simulation tab.
"""

from app.schemas.managed_strategy import AdoptResearchRequest, ManagedStrategyCreate
from app.schemas.strategy import (
    ConfidenceBreakdown,
    PortfolioAllocation,
    RiskMetric,
    SplitStep,
    StrategyPlan,
    StrategyScores,
    TradeAction,
)

STRATEGY_TITLES = {
    "tqqq_daily_200ma": "매일 적립 감속",
    "qld_daily_200ma": "매일 적립 감속",
    "tqqq_200ma": "TQQQ 200일선 분할",
    "qld_200ma": "QLD 200일선 분할",
    "qqq_buy_hold": "QQQ 장기 보유",
    "tqqq_buy_hold": "TQQQ 장기 보유",
}
DEFENSE_TITLES = {
    "cash": "현금 방어",
    "spym_sgov_half": "SPYM+SGOV 반반 방어",
    "hold_one_x": "1x 유지",
}
RISK_SCORE_BY_STRATEGY = {
    "qqq_buy_hold": 45,
    "qld_200ma": 62,
    "tqqq_daily_200ma": 72,
    "qld_daily_200ma": 62,
    "tqqq_200ma": 78,
    "tqqq_buy_hold": 95,
}


def build_research_adoption(payload: AdoptResearchRequest) -> ManagedStrategyCreate:
    config = payload.research_config
    leveraged_symbol = config.daily_leveraged_symbol
    leveraged_value = payload.tqqq_value if leveraged_symbol == "TQQQ" else payload.qld_value
    total = leveraged_value + payload.one_x_value + payload.cash_value
    if total <= 0:
        raise ValueError("채택하려면 현재 보유 금액(TQQQ/1x/현금 합계)이 0보다 커야 합니다.")

    title = (
        f"{STRATEGY_TITLES.get(config.strategy, config.strategy)} "
        f"{config.daily_base_tqqq_ratio:.0f}:{config.daily_base_one_x_ratio:.0f}"
        f" · 밴드 {config.ma_exit_band_pct:+.0f}% · {DEFENSE_TITLES[config.defense_mode]}"
        if config.strategy in {"tqqq_daily_200ma", "qld_daily_200ma"}
        else (
            f"{STRATEGY_TITLES.get(config.strategy, config.strategy)}"
            f" · 밴드 {config.ma_exit_band_pct:+.0f}% · {DEFENSE_TITLES[config.defense_mode]}"
        )
    )

    evidence = ""
    if payload.source_total_score is not None:
        evidence = (
            f"개인연구 전수 비교 종합 {payload.source_total_score}점"
            + (
                f" (CAGR {payload.source_cagr:+.2f}%, MDD {payload.source_max_drawdown:.2f}%)"
                if payload.source_cagr is not None and payload.source_max_drawdown is not None
                else ""
            )
        )

    allocations = [
        PortfolioAllocation(
            symbol=leveraged_symbol,
            name="ProShares UltraPro QQQ" if leveraged_symbol == "TQQQ" else "ProShares Ultra QQQ",
            target_ratio=round(leveraged_value / total * 100, 1),
            target_amount=round(leveraged_value, 2),
            role="레버리지 성장 엔진",
        ),
        PortfolioAllocation(
            symbol=config.one_x_symbol,
            name=f"{config.one_x_symbol} (1x 완충)",
            target_ratio=round(payload.one_x_value / total * 100, 1),
            target_amount=round(payload.one_x_value, 2),
            role="1x 완충 코어",
        ),
        PortfolioAllocation(
            symbol="CASH",
            name="현금",
            target_ratio=round(payload.cash_value / total * 100, 1),
            target_amount=round(payload.cash_value, 2),
            role="방어·집행 대기",
        ),
    ]

    band_line = f"QQQ 200일선 x (1 {config.ma_exit_band_pct:+.1f}%)"
    daily_amount = config.monthly_contribution / 21 if config.monthly_contribution else 0
    buy_plan = [
        SplitStep(
            step="매일 적립",
            trigger=f"QQQ 종가가 {band_line} 위",
            ratio_of_target=config.daily_base_tqqq_ratio,
            amount=round(daily_amount, 0),
            note=(
                f"월 적립을 21거래일로 나눠 {leveraged_symbol} {config.daily_base_tqqq_ratio:.0f}% / "
                f"{config.one_x_symbol} {config.daily_base_one_x_ratio:.0f}% 매수. "
                "이격 +10/20/30%에서 감속(x0.65/x0.30/중지)."
            ),
        ),
        SplitStep(
            step="방어 후 재투입",
            trigger="기준선 회복 후 21거래일",
            ratio_of_target=100,
            amount=0,
            note="방어 현금을 21거래일 분할로 같은 비율 재매수.",
        ),
    ]
    sell_plan = [
        SplitStep(
            step="방어 전환",
            trigger=f"QQQ 종가가 {band_line} 아래 2일 연속",
            ratio_of_target=100,
            amount=0,
            note=DEFENSE_TITLES[config.defense_mode]
            + {
                "cash": ": TQQQ와 1x 전량 매도 후 현금 100%.",
                "spym_sgov_half": ": 전량 매도 후 SPYM 50% + SGOV/현금 50%.",
                "hold_one_x": ": TQQQ만 전량 매도, 1x는 계속 보유.",
            }[config.defense_mode],
        ),
    ]

    base_confidence = payload.source_total_score or 75
    scores = StrategyScores(
        confidence_score=base_confidence,
        risk_score=RISK_SCORE_BY_STRATEGY.get(config.strategy, 70),
        fit_score=base_confidence,
        expected_return_score=base_confidence,
            execution_difficulty="low" if config.strategy in {"tqqq_daily_200ma", "qld_daily_200ma"} else "medium",
        confidence_breakdown=ConfidenceBreakdown(
            rule_clarity=90,
            market_fit=base_confidence,
            cash_defense=85 if config.defense_mode != "hold_one_x" else 60,
            drawdown_control=75,
            overfit_resistance=85,
            execution_quality=90 if config.strategy in {"tqqq_daily_200ma", "qld_daily_200ma"} else 65,
            user_fit=base_confidence,
        ),
        confidence_notes=[
            "개인연구(1999~ 전 구간 백테스트 + 규칙 강건성 검증)에서 채택한 전략입니다.",
            evidence or "백테스트 근거는 개인연구 탭에서 재확인할 수 있습니다.",
        ],
    )

    plan = StrategyPlan(
        id=f"research_{config.strategy}",
        title=title,
        summary=(
            "개인연구 랩에서 검증한 규칙 그대로 운용합니다. 오늘의 판단 탭이 이 규칙으로 "
            "매일 실행 지시를 계산합니다."
        ),
        allocations=allocations,
        actions=[
            TradeAction(
                symbol=leveraged_symbol,
                action="hold",
                amount=leveraged_value,
                reason="현재 보유분에서 출발 — 오늘의 판단 지시에 따라 관리",
            )
        ],
        buy_plan=buy_plan,
        sell_plan=sell_plan,
        risk_metrics=[
            RiskMetric(
                label="백테스트 MDD",
                value=(
                    f"{payload.source_max_drawdown:.1f}%"
                    if payload.source_max_drawdown is not None
                    else "개인연구 참조"
                ),
                level="high",
            ),
        ],
        scores=scores,
        pros=[
            "백테스트로 검증된 규칙을 그대로 실행",
            "판단이 필요한 행동이 드물어 실행 규율을 지키기 쉬움"
            if config.strategy in {"tqqq_daily_200ma", "qld_daily_200ma"}
            else "낙폭 방어력이 검증된 분할 규칙",
        ],
        cons=[
            "전 구간 기준 -55% 안팎의 낙폭 구간을 견뎌야 함",
            "과거 데이터 기반 규칙으로 미래 수익을 보장하지 않음",
        ],
    )

    return ManagedStrategyCreate(
        plan=plan,
        market=payload.market,
        total_capital=total,
        selected_reason=payload.selected_reason or evidence,
        research_config=config,
    )
