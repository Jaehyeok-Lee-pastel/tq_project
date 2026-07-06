import asyncio

from app.schemas.backtest import (
    BacktestMetrics,
    BacktestRunResponse,
    EquityPoint,
    ProjectionScenario,
)
from app.schemas.compare import StrategyCompareRequest
from app.services import compare_engine


def fake_backtest_response(strategy: str, initial_capital: float, target_ratio: float) -> BacktestRunResponse:
    metrics = BacktestMetrics(
        final_capital=initial_capital * (1.25 if target_ratio <= 60 else 1.35),
        total_return=25 if target_ratio <= 60 else 35,
        cagr=9 if target_ratio <= 60 else 11,
        max_drawdown=-32 if target_ratio <= 60 else -46,
        win_rate=54,
        trade_count=8 if target_ratio <= 60 else 14,
        longest_drawdown_days=120,
    )
    curve = [
        EquityPoint(date="2020-01-02", equity=initial_capital, drawdown=0, position="CASH"),
        EquityPoint(date="2024-12-31", equity=metrics.final_capital, drawdown=metrics.max_drawdown, position="TQQQ"),
    ]
    return BacktestRunResponse(
        strategy=strategy,  # type: ignore[arg-type]
        strategy_name="TQQQ 200일선 테스트",
        moving_average_days=200,
        benchmark_name="QQQ 장기 보유",
        period_start="2020-01-02",
        period_end="2024-12-31",
        equity_curve=curve,
        benchmark_curve=curve,
        metrics=metrics,
        benchmark_metrics=metrics,
        yearly_returns=[],
        regime_performance=[],
        trades=[],
        projection=[
            ProjectionScenario(
                name="base",
                annual_return=metrics.cagr,
                ending_capital=initial_capital * 1.4,
                profit=initial_capital * 0.4,
                note="테스트",
            )
        ],
        interpretation=["테스트"],
    )


def test_tqqq_default_comparison_contains_philosophy_audit(monkeypatch):
    async def fake_run_backtest(request):
        return fake_backtest_response(request.strategy, request.initial_capital, request.tqqq_target_ratio)

    monkeypatch.setattr(compare_engine, "run_backtest", fake_run_backtest)

    result = asyncio.run(
        compare_engine.compare_strategies(
            StrategyCompareRequest(
                initial_capital=2_500_000,
                strategies=["tqqq_200ma"],
                tqqq_target_ratio=45,
                moving_average_days=200,
                include_default_tqqq_comparison=True,
            )
        )
    )

    audit = result.tqqq_default_comparison.philosophy_audit
    assert audit.score >= 80
    assert audit.items
    assert audit.to_reach_100
    assert any(item.label == "200일선 순도" for item in audit.items)
    assert any("100점" in item for item in audit.to_reach_100)
