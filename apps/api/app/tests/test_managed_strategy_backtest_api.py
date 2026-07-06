from fastapi.testclient import TestClient

from app.api.routes import managed_strategies as managed_routes
from app.main import app
from app.repositories import managed_strategy_repository as repository
from app.schemas.backtest import (
    BacktestMetrics,
    BacktestRunResponse,
    EquityPoint,
    ProjectionScenario,
    RegimePerformance,
)
from app.schemas.managed_strategy import ManagedStrategyCreate
from app.schemas.strategy import MarketSnapshot
from app.tests.test_managed_strategy_contribution import make_plan

client = TestClient(app)


def fake_backtest_response(strategy: str, initial_capital: float) -> BacktestRunResponse:
    metrics = BacktestMetrics(
        final_capital=initial_capital * 1.1,
        total_return=10,
        cagr=8,
        max_drawdown=-12,
        win_rate=55,
        trade_count=3,
        longest_drawdown_days=42,
    )
    curve = [
        EquityPoint(date="2024-01-02", equity=initial_capital, drawdown=0, position="cash"),
        EquityPoint(date="2024-12-31", equity=initial_capital * 1.1, drawdown=-2, position="risk"),
    ]
    return BacktestRunResponse(
        strategy=strategy,  # type: ignore[arg-type]
        strategy_name="테스트 전략",
        moving_average_days=200,
        benchmark_name="QQQ 장기 보유",
        period_start="2024-01-02",
        period_end="2024-12-31",
        equity_curve=curve,
        benchmark_curve=curve,
        metrics=metrics,
        benchmark_metrics=metrics,
        yearly_returns=[],
        regime_performance=[
            RegimePerformance(regime="uptrend", label="상승장", days=100, return_pct=10, win_rate=60, max_drawdown=-5)
        ],
        trades=[],
        projection=[
            ProjectionScenario(name="base", annual_return=8, ending_capital=initial_capital * 1.25, profit=initial_capital * 0.25, note="테스트")
        ],
        interpretation=["테스트 응답"],
    )


def test_managed_strategy_backtest_route_uses_saved_strategy_request(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DATA_PATH", tmp_path / "managed_strategies.json")
    captured = {}

    async def fake_run_backtest(request):
        captured["request"] = request
        return fake_backtest_response(request.strategy, request.initial_capital)

    monkeypatch.setattr(managed_routes, "run_backtest", fake_run_backtest)
    strategy = repository.create_strategy(
        ManagedStrategyCreate(
            plan=make_plan(2_500_000),
            market=MarketSnapshot(
                qqq_close=655,
                qqq_sma200=633.63,
                qqq_sma20=660,
                qqq_sma50=650,
                qqq_high20=670,
                as_of="2026-07-02",
            ),
            total_capital=2_500_000,
            selected_reason="API 백테스트 테스트",
        )
    )

    response = client.post(f"/managed-strategies/{strategy.id}/backtest?projection_years=6&cash_yield=4.1")

    assert response.status_code == 200
    assert response.json()["strategy"] == "tqqq_200ma"
    assert captured["request"].strategy == "tqqq_200ma"
    assert captured["request"].initial_capital == 2_500_000
    assert captured["request"].tqqq_target_ratio == 30
    assert captured["request"].projection_years == 6
    assert captured["request"].cash_yield == 4.1


def test_managed_strategy_backtest_route_returns_404_for_missing_strategy(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DATA_PATH", tmp_path / "managed_strategies.json")

    response = client.post("/managed-strategies/missing/backtest")

    assert response.status_code == 404
