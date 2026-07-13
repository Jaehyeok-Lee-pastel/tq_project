"""Scoring must stay meaningful on full-history (26y) backtests.

The old absolute formulas saturated: every strategy hit profit=100 and
defense~0 once the 2000-2002 crash was included, so rankings were decided by
the hardcoded risk priors alone. These tests pin the benchmark-relative
behavior.
"""

from app.schemas.backtest import BacktestMetrics, BacktestRunResponse, TradeLogItem
from app.services.compare_engine import score_backtest


def make_trades(buys: int, sells: int) -> list[TradeLogItem]:
    items = [
        TradeLogItem(date="2010-01-04", action="buy", symbol="TQQQ", ratio=30, reason="buy")
        for _ in range(buys)
    ]
    items += [
        TradeLogItem(date="2010-06-04", action="sell", symbol="TQQQ", ratio=0, reason="sell")
        for _ in range(sells)
    ]
    return items


def make_metrics(cagr: float, max_drawdown: float, trade_count: int = 400) -> BacktestMetrics:
    return BacktestMetrics(
        final_capital=1_000_000,
        total_return=1_500.0,  # 26-year cumulative; must NOT saturate scores
        cagr=cagr,
        max_drawdown=max_drawdown,
        sharpe=0.58,
        sortino=0.8,
        calmar=0.2,
        win_rate=54.0,
        trade_count=trade_count,
        best_year=80.0,
        worst_year=-60.0,
        longest_drawdown_days=900,
    )


def make_result(
    strategy: str,
    cagr: float,
    mdd: float,
    trade_count: int = 400,
    trades: list[TradeLogItem] | None = None,
) -> BacktestRunResponse:
    return BacktestRunResponse(
        strategy=strategy,  # type: ignore[arg-type]
        strategy_name=strategy,
        moving_average_days=200,
        benchmark_name="QQQ 장기 보유",
        period_start="1999-12-22",
        period_end="2026-07-09",
        equity_curve=[],
        benchmark_curve=[],
        metrics=make_metrics(cagr, mdd, trade_count),
        benchmark_metrics=make_metrics(8.9, -83.0, 0),
        yearly_returns=[],
        regime_performance=[],
        trades=trades or [],
        projection=[],
        interpretation=[],
    )


def test_scores_do_not_saturate_on_full_history():
    item = score_backtest(make_result("tqqq_200ma", cagr=12.4, mdd=-66.0), user_risk_score=78)
    assert 0 < item.profit_score < 100
    assert 0 < item.defense_score < 100


def test_benchmark_itself_scores_neutral_profit():
    item = score_backtest(make_result("qqq_buy_hold", cagr=8.9, mdd=-83.0, trade_count=0), 78)
    assert item.profit_score == 50


def test_defense_discriminates_shallower_drawdowns():
    deep = score_backtest(make_result("tqqq_buy_hold", cagr=-2.0, mdd=-99.9, trade_count=0), 78)
    mid = score_backtest(make_result("tqqq_200ma", cagr=12.4, mdd=-66.0), 78)
    shallow = score_backtest(make_result("qld_200ma", cagr=11.4, mdd=-62.0), 78)
    assert deep.defense_score < mid.defense_score < shallow.defense_score


def test_cagr_edge_beats_equal_risk_alternative():
    better = score_backtest(make_result("tqqq_200ma", cagr=12.4, mdd=-66.0), 78)
    worse = score_backtest(make_result("tqqq_daily_200ma", cagr=11.5, mdd=-66.0), 78)
    assert better.profit_score > worse.profit_score


def test_reason_mentions_benchmark_edge():
    item = score_backtest(make_result("tqqq_200ma", cagr=12.4, mdd=-66.0), 78)
    assert "QQQ 장기 보유 대비" in item.reason


def test_execution_counts_only_real_decisions():
    # Staged: every logged transition is a manual decision (~15.8/yr here).
    staged = score_backtest(
        make_result("tqqq_200ma", cagr=11.6, mdd=-54.4, trades=make_trades(buys=250, sells=170)),
        78,
    )
    # Daily accumulation: scheduled buys are mechanical; only sells count.
    daily = score_backtest(
        make_result("tqqq_daily_200ma", cagr=11.5, mdd=-66.0, trades=make_trades(buys=860, sells=64)),
        78,
    )
    hold = score_backtest(
        make_result("qqq_buy_hold", cagr=8.9, mdd=-83.0, trade_count=0),
        78,
    )

    assert hold.execution_score == 100
    assert daily.execution_score > staged.execution_score
    assert daily.decisions_per_year < 3
    assert staged.decisions_per_year > 10
    assert "시그널 대응 규율" in staged.reason
