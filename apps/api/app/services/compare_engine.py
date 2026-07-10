from app.schemas.backtest import BacktestRunRequest, BacktestRunResponse
from app.schemas.compare import (
    PhilosophyAudit,
    PhilosophyAuditItem,
    SensitivityItem,
    SensitivitySummary,
    StrategyCompareRequest,
    StrategyCompareResponse,
    StrategyRankItem,
    TqqqDefaultComparison,
)
from app.services.backtest_engine import run_backtest


async def compare_strategies(request: StrategyCompareRequest) -> StrategyCompareResponse:
    backtests: list[BacktestRunResponse] = []
    for strategy in request.strategies:
        backtests.append(
            await run_backtest(
                BacktestRunRequest(
                    strategy=strategy,
                    initial_capital=request.initial_capital,
                    tqqq_target_ratio=request.tqqq_target_ratio,
                    qld_target_ratio=request.qld_target_ratio,
                    one_x_target_ratio=request.one_x_target_ratio,
                    one_x_symbol=request.one_x_symbol,
                    moving_average_days=request.moving_average_days,
                    cash_yield=request.cash_yield,
                    fee_bps=request.fee_bps,
                    slippage_bps=request.slippage_bps,
                    monthly_contribution=request.monthly_contribution,
                    daily_base_tqqq_ratio=request.daily_base_tqqq_ratio,
                    daily_base_one_x_ratio=request.daily_base_one_x_ratio,
                )
            )
        )

    ranked = [score_backtest(result, request.risk_score) for result in backtests]
    ranked.sort(key=lambda item: item.total_score, reverse=True)
    rankings = [
        StrategyRankItem(**{**item.model_dump(), "rank": index + 1})
        for index, item in enumerate(ranked)
    ]
    winner = rankings[0]
    return StrategyCompareResponse(
        initial_capital=request.initial_capital,
        risk_score=request.risk_score,
        recommended_strategy=winner.strategy,
        summary=(
            f"같은 원금 {request.initial_capital:,.0f}원 기준으로 "
            f"{winner.strategy_name}의 종합 점수가 가장 높습니다."
        ),
        rankings=rankings,
        sensitivity=await build_sensitivity(request, winner.strategy),
        tqqq_default_comparison=await build_tqqq_default_comparison(request),
        backtests=backtests,
    )


async def build_sensitivity(
    request: StrategyCompareRequest,
    strategy,
) -> SensitivitySummary:
    windows = [150, 180, 200, 220, 250]
    scored: list[StrategyRankItem] = []
    results: list[SensitivityItem] = []
    for window in windows:
        backtest = await run_backtest(
            BacktestRunRequest(
                strategy=strategy,
                initial_capital=request.initial_capital,
                tqqq_target_ratio=request.tqqq_target_ratio,
                qld_target_ratio=request.qld_target_ratio,
                one_x_target_ratio=request.one_x_target_ratio,
                one_x_symbol=request.one_x_symbol,
                moving_average_days=window,
                cash_yield=request.cash_yield,
                fee_bps=request.fee_bps,
                slippage_bps=request.slippage_bps,
                monthly_contribution=request.monthly_contribution,
                daily_base_tqqq_ratio=request.daily_base_tqqq_ratio,
                daily_base_one_x_ratio=request.daily_base_one_x_ratio,
            )
        )
        item = score_backtest(backtest, request.risk_score)
        scored.append(item)
        results.append(
            SensitivityItem(
                strategy=backtest.strategy,
                strategy_name=backtest.strategy_name,
                moving_average_days=window,
                cagr=backtest.metrics.cagr,
                max_drawdown=backtest.metrics.max_drawdown,
                total_score=item.total_score,
            )
        )
    best = max(results, key=lambda item: item.total_score)
    score_range = max(item.total_score for item in scored) - min(
        item.total_score for item in scored
    )
    robustness_score = round(clamp(100 - score_range * 2.5, 0, 100))
    verdict = (
        "견고함"
        if robustness_score >= 75
        else "보통"
        if robustness_score >= 55
        else "민감함"
    )
    return SensitivitySummary(
        tested_windows=windows,
        best_window=best.moving_average_days,
        robustness_score=robustness_score,
        verdict=verdict,
        results=results,
    )


async def build_tqqq_default_comparison(
    request: StrategyCompareRequest,
) -> TqqqDefaultComparison | None:
    if not request.include_default_tqqq_comparison:
        return None
    if request.tqqq_target_ratio <= 0:
        return None

    baseline = await run_backtest(
        BacktestRunRequest(
            strategy="tqqq_200ma",
            initial_capital=request.initial_capital,
            tqqq_target_ratio=request.default_tqqq_target_ratio,
            qld_target_ratio=0,
            moving_average_days=200,
            cash_yield=request.cash_yield,
            fee_bps=request.fee_bps,
            slippage_bps=request.slippage_bps,
        )
    )
    custom = await run_backtest(
        BacktestRunRequest(
            strategy="tqqq_200ma",
            initial_capital=request.initial_capital,
            tqqq_target_ratio=request.tqqq_target_ratio,
            qld_target_ratio=0,
            moving_average_days=request.moving_average_days,
            cash_yield=request.cash_yield,
            fee_bps=request.fee_bps,
            slippage_bps=request.slippage_bps,
        )
    )
    final_delta = custom.metrics.final_capital - baseline.metrics.final_capital
    cagr_delta = custom.metrics.cagr - baseline.metrics.cagr
    drawdown_delta = custom.metrics.max_drawdown - baseline.metrics.max_drawdown
    base_projection_delta = projection_ending(custom, "base") - projection_ending(baseline, "base")
    if cagr_delta >= 1 and drawdown_delta >= -5:
        verdict = "custom_better"
        summary = "커스텀형이 기본형 대비 수익성을 높이면서 낙폭 훼손이 제한적입니다."
    elif cagr_delta < 0 and drawdown_delta >= 5:
        verdict = "custom_defensive"
        summary = "커스텀형은 기본형보다 기대 수익은 낮지만 최대낙폭을 줄이는 방어형 조정입니다."
    elif cagr_delta <= -1 and drawdown_delta <= 3:
        verdict = "baseline_better"
        summary = "기본형이 커스텀형보다 과거 수익성과 단순성 측면에서 우세합니다."
    else:
        verdict = "similar"
        summary = "기본형과 커스텀형의 차이가 크지 않아 실행 난이도와 현재 진입 위치가 더 중요합니다."

    philosophy_audit = build_philosophy_audit(
        request=request,
        baseline=baseline,
        custom=custom,
        cagr_delta=cagr_delta,
        drawdown_delta=drawdown_delta,
    )

    return TqqqDefaultComparison(
        baseline_label=f"기본 TQQQ 200일선 {request.default_tqqq_target_ratio:.0f}%",
        custom_label=f"커스텀 TQQQ 200일선 {request.tqqq_target_ratio:.0f}%",
        baseline_target_ratio=request.default_tqqq_target_ratio,
        custom_target_ratio=request.tqqq_target_ratio,
        final_capital_delta=round(final_delta, 2),
        cagr_delta=round(cagr_delta, 2),
        max_drawdown_delta=round(drawdown_delta, 2),
        trade_count_delta=custom.metrics.trade_count - baseline.metrics.trade_count,
        base_projection_delta=round(base_projection_delta, 2),
        verdict=verdict,
        summary=summary,
        philosophy_audit=philosophy_audit,
        baseline=baseline,
        custom=custom,
    )


def build_philosophy_audit(
    request: StrategyCompareRequest,
    baseline: BacktestRunResponse,
    custom: BacktestRunResponse,
    cagr_delta: float,
    drawdown_delta: float,
) -> PhilosophyAudit:
    ma_deviation = abs(request.moving_average_days - 200)
    rule_purity = round(clamp(100 - ma_deviation * 0.8, 0, 100))
    leverage_discipline = round(
        clamp(100 - max(request.tqqq_target_ratio - 60, 0) * 1.8 - max(20 - request.tqqq_target_ratio, 0) * 0.5, 0, 100)
    )
    default_comparison = 100
    trade_delta = custom.metrics.trade_count - baseline.metrics.trade_count
    overfit_resistance = round(
        clamp(100 - ma_deviation * 0.6 - max(trade_delta, 0) * 2.5 - max(cagr_delta, 0) * max(-drawdown_delta, 0) * 0.25, 0, 100)
    )
    drawdown_guard = round(clamp(82 + drawdown_delta * 1.8, 0, 100))
    execution_simplicity = round(clamp(100 - max(custom.metrics.trade_count - baseline.metrics.trade_count, 0) * 3, 0, 100))

    items = [
        audit_item("200일선 순도", rule_purity, f"현재 이동평균 기준은 {request.moving_average_days}일입니다. 200일에 가까울수록 기본 철학과 맞습니다."),
        audit_item("레버리지 절제", leverage_discipline, f"TQQQ 목표 비중 {request.tqqq_target_ratio:.0f}%입니다. 기본형보다 과도하게 높이면 감점합니다."),
        audit_item("기본형 직접 비교", default_comparison, "순정 TQQQ 200일선과 같은 원금으로 비교해 커스텀의 이유를 확인합니다."),
        audit_item("과최적화 저항", overfit_resistance, "이동평균 변경, 거래 증가, 수익 개선 대비 낙폭 악화를 함께 감점합니다."),
        audit_item("낙폭 방어", drawdown_guard, f"기본형 대비 최대낙폭 차이는 {drawdown_delta:+.2f}%p입니다. 낙폭이 줄면 가점합니다."),
        audit_item("실행 단순성", execution_simplicity, f"기본형 대비 거래 횟수 차이는 {trade_delta:+d}회입니다. 거래가 늘수록 실행 피로도를 감점합니다."),
    ]
    score = round(
        rule_purity * 0.22
        + leverage_discipline * 0.17
        + default_comparison * 0.16
        + overfit_resistance * 0.18
        + drawdown_guard * 0.17
        + execution_simplicity * 0.10
    )
    if score >= 92:
        verdict = "excellent"
        summary = "기본 TQQQ 200일선 철학과 매우 잘 맞습니다. 커스텀을 늘리기보다 기록과 실행 준수율을 유지하는 단계입니다."
    elif score >= 82:
        verdict = "good"
        summary = "기본 철학은 잘 유지되고 있습니다. 100점에 가까워지려면 규칙 수를 더 줄이고 기본형 대비 이유를 계속 검증해야 합니다."
    elif score >= 68:
        verdict = "watch"
        summary = "전략은 사용할 수 있지만 커스텀 근거가 약한 부분이 있습니다. 수익률보다 단순성, 낙폭, 실행 가능성을 먼저 보강하세요."
    else:
        verdict = "danger"
        summary = "기본 200일선 매매법보다 커스텀 영향이 커 보입니다. 순정 규칙으로 되돌려 비교한 뒤 필요한 조정만 다시 추가하세요."

    return PhilosophyAudit(
        score=score,
        verdict=verdict,  # type: ignore[arg-type]
        summary=summary,
        items=items,
        to_reach_100=build_100_point_guidance(items, request),
    )


def audit_item(label: str, score: int, detail: str) -> PhilosophyAuditItem:
    status = "ok" if score >= 90 else "watch" if score >= 75 else "danger"
    return PhilosophyAuditItem(label=label, score=score, status=status, detail=detail)  # type: ignore[arg-type]


def build_100_point_guidance(items: list[PhilosophyAuditItem], request: StrategyCompareRequest) -> list[str]:
    guidance: list[str] = []
    if request.moving_average_days != 200:
        guidance.append("이동평균 기준을 200일로 고정해 순정 TQQQ 200일선과의 비교 순도를 높이세요.")
    if request.tqqq_target_ratio > 60:
        guidance.append("TQQQ 목표 비중을 60% 이하로 낮추고, 초과 위험은 현금/SGOV 또는 QQQ/VOO 같은 비레버리지 자산으로 분산하세요.")
    if request.tqqq_target_ratio <= 0:
        guidance.append("TQQQ 200일선 전략 검증이라면 TQQQ 목표 비중을 0보다 크게 설정해야 철학 정렬도를 평가할 수 있습니다.")
    low_items = [item for item in items if item.score < 90]
    for item in low_items[:3]:
        guidance.append(f"{item.label} 점수를 90점 이상으로 올리세요. {item.detail}")
    guidance.append("새 매수 조건을 추가하기 전에는 기본형 대비 CAGR, MDD, 거래 횟수, 민감도 점수가 모두 개선되는지 확인하세요.")
    guidance.append("100점은 공격성을 의미하지 않습니다. 규칙이 단순하고, 같은 원금 비교가 가능하며, 실행 기록으로 검증될수록 가까워집니다.")
    return list(dict.fromkeys(guidance))[:6]


def projection_ending(result: BacktestRunResponse, scenario: str) -> float:
    for item in result.projection:
        if item.name == scenario:
            return item.ending_capital
    return 0


def score_backtest(result: BacktestRunResponse, user_risk_score: int) -> StrategyRankItem:
    metrics = result.metrics
    profit_score = round(clamp(metrics.cagr * 2.1 + metrics.total_return * 0.12, 0, 100))
    defense_score = round(clamp(100 + metrics.max_drawdown * 1.4, 0, 100))
    strategy_risk = estimate_strategy_risk(result)
    fit_score = round(clamp(100 - abs(strategy_risk - user_risk_score), 0, 100))
    consistency_score = round(
        clamp(
            (metrics.sharpe or 0) * 18
            + metrics.win_rate * 0.35
            - min(metrics.trade_count, 80) * 0.15,
            0,
            100,
        )
    )
    total_score = round(
        profit_score * 0.32
        + defense_score * 0.26
        + fit_score * 0.28
        + consistency_score * 0.14
    )
    verdict = verdict_for(strategy_risk, user_risk_score, profit_score, defense_score, total_score)
    return StrategyRankItem(
        rank=0,
        strategy=result.strategy,
        strategy_name=result.strategy_name,
        final_capital=metrics.final_capital,
        total_return=metrics.total_return,
        cagr=metrics.cagr,
        max_drawdown=metrics.max_drawdown,
        sharpe=metrics.sharpe,
        trade_count=metrics.trade_count,
        profit_score=profit_score,
        defense_score=defense_score,
        fit_score=fit_score,
        consistency_score=consistency_score,
        total_score=total_score,
        verdict=verdict,
        reason=reason_for(result, strategy_risk, user_risk_score),
    )


def estimate_strategy_risk(result: BacktestRunResponse) -> int:
    base = {
        "qqq_buy_hold": 45,
        "qld_200ma": 62,
        "tqqq_daily_200ma": 72,
        "tqqq_200ma": 78,
        "tqqq_buy_hold": 95,
    }.get(result.strategy, 60)
    drawdown_penalty = min(abs(result.metrics.max_drawdown) * 0.25, 18)
    return round(clamp(base + drawdown_penalty, 0, 100))


def verdict_for(
    strategy_risk: int,
    user_risk_score: int,
    profit_score: int,
    defense_score: int,
    total_score: int,
) -> str:
    if strategy_risk - user_risk_score >= 18:
        return "too_risky"
    if total_score >= 75:
        return "best_fit"
    if profit_score >= 75 and defense_score < 45:
        return "high_return"
    if defense_score >= 75:
        return "defensive"
    return "watch"


def reason_for(result: BacktestRunResponse, strategy_risk: int, user_risk_score: int) -> str:
    risk_gap = strategy_risk - user_risk_score
    if risk_gap >= 18:
        return "수익 탄력은 있어도 사용자의 리스크 허용도보다 전략 위험도가 높습니다."
    if result.metrics.max_drawdown <= -60:
        return "최대낙폭이 커서 실제 운용 시 버티는 난이도가 높습니다."
    if result.metrics.cagr > result.benchmark_metrics.cagr and result.metrics.max_drawdown > -45:
        return "QQQ 대비 수익성과 방어력의 균형이 좋습니다."
    if result.metrics.trade_count > 40:
        return "매매 횟수가 많아 횡보장에서 실행 피로도가 생길 수 있습니다."
    return "동일 원금 비교에서 수익, 낙폭, 리스크 적합도를 함께 평가했습니다."


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
