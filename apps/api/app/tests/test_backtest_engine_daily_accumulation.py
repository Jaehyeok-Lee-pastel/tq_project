from app.schemas.backtest import BacktestRunRequest
from app.schemas.managed_strategy import ResearchStrategyConfig
from app.services.backtest_engine import (
    BacktestFrame,
    calculate_metrics,
    calculate_regime_performance,
    simulate_buy_hold,
    simulate_strategy,
)


def frame(day: int, qqq: float, tqqq: float, sma200: float = 100) -> BacktestFrame:
    return BacktestFrame(
        date=f"2024-02-{day:02d}",
        qqq=qqq,
        tqqq=tqqq,
        qld=tqqq * 0.8,
        spy=qqq,
        sma200=sma200,
        sma20=qqq,
        sma50=qqq,
        high20=qqq,
    )


def test_research_daily_defaults_to_payday_one_x_buy() -> None:
    assert ResearchStrategyConfig().one_x_upfront_monthly is True
    assert BacktestRunRequest().one_x_upfront_monthly is True


def test_daily_accumulation_200ma_slows_tqqq_buys_when_stretched():
    frames = [
        frame(1, 105, 100),
        frame(2, 106, 102),
        frame(3, 115, 104),
        frame(4, 116, 106),
    ]

    _, trades = simulate_strategy(
        frames,
        BacktestRunRequest(
            strategy="tqqq_daily_200ma",
            initial_capital=1_000_000,
            monthly_contribution=1_000_000,
            daily_base_tqqq_ratio=70,
            daily_base_one_x_ratio=30,
            one_x_symbol="QQQM",
            cash_yield=4.5,
            one_x_upfront_monthly=False,
        ),
    )

    tqqq_buys = [trade for trade in trades if trade.action == "buy" and trade.symbol == "TQQQ"]
    one_x_buys = [trade for trade in trades if trade.action == "buy" and trade.symbol == "QQQM"]

    assert tqqq_buys[0].ratio == 70.0
    assert one_x_buys[0].ratio == 30.0
    assert tqqq_buys[-1].ratio == 45.5
    assert "감속" in tqqq_buys[-1].reason


def test_daily_accumulation_uses_existing_holdings_as_starting_state():
    frames = [
        frame(1, 105, 100),
        frame(2, 106, 102),
        frame(3, 107, 104),
    ]

    curve, trades = simulate_strategy(
        frames,
        BacktestRunRequest(
            strategy="tqqq_daily_200ma",
            initial_capital=2_500_000,
            initial_tqqq_value=1_600_000,
            initial_one_x_value=500_000,
            initial_cash_value=400_000,
            monthly_contribution=1_000_000,
            daily_base_tqqq_ratio=70,
            daily_base_one_x_ratio=30,
            one_x_symbol="QQQM",
            cash_yield=4.5,
            one_x_upfront_monthly=False,
        ),
    )

    assert curve[0].equity == 2_500_000  # day-0 anchor equals starting holdings
    assert curve[-1].equity > 2_500_000
    assert any(trade.symbol == "TQQQ" and trade.ratio == 70.0 for trade in trades)
    assert any(trade.symbol == "QQQM" and trade.ratio == 30.0 for trade in trades)


def test_buy_hold_strategies_receive_monthly_contributions_for_fair_comparison():
    frames = [
        frame(1, 100, 100),
        frame(2, 101, 103),
        frame(3, 102, 106),
    ]

    without_contribution, _ = simulate_buy_hold(frames, 1_000_000, "QQQ")
    with_contribution, trades = simulate_buy_hold(
        frames,
        1_000_000,
        "QQQ",
        monthly_contribution=1_000_000,
        cost_ratio=0,
    )

    assert with_contribution[-1].equity > without_contribution[-1].equity
    # Contributions are cash flows, not strategy trades: no trade-log spam.
    assert not trades
    assert all(point.cash_flow > 0 for point in with_contribution[1:])


def test_tqqq_buy_hold_receives_monthly_contributions_into_tqqq():
    frames = [
        frame(1, 100, 100),
        frame(2, 101, 103),
        frame(3, 102, 106),
    ]

    curve, trades = simulate_strategy(
        frames,
        BacktestRunRequest(
            strategy="tqqq_buy_hold",
            initial_capital=1_000_000,
            monthly_contribution=1_000_000,
            cash_yield=4.5,
        ),
    )

    assert not trades
    assert all(point.position == "TQQQ" for point in curve)
    assert all(point.cash_flow > 0 for point in curve[1:])


def test_staged_200ma_receives_monthly_contributions_under_current_stage_rules():
    frames = [
        frame(1, 104, 100),
        frame(2, 105, 102),
        frame(3, 104, 103),
        frame(4, 103, 104),
    ]

    without_contribution, _ = simulate_strategy(
        frames,
        BacktestRunRequest(
            strategy="tqqq_200ma",
            initial_capital=1_000_000,
            tqqq_target_ratio=60,
            monthly_contribution=0,
            cash_yield=4.5,
        ),
    )
    with_contribution, trades = simulate_strategy(
        frames,
        BacktestRunRequest(
            strategy="tqqq_200ma",
            initial_capital=1_000_000,
            tqqq_target_ratio=60,
            monthly_contribution=1_000_000,
            cash_yield=4.5,
        ),
    )

    assert with_contribution[-1].equity > without_contribution[-1].equity
    assert any(trade.symbol == "TQQQ" for trade in trades)


def test_monthly_contributions_do_not_inflate_cagr_when_prices_are_flat():
    frames = [
        frame(1, 100, 100),
        frame(2, 100, 100),
        frame(3, 100, 100),
        frame(4, 100, 100),
    ]

    curve, trades = simulate_buy_hold(
        frames,
        1_000_000,
        "QQQ",
        monthly_contribution=1_000_000,
        cost_ratio=0,
    )
    metrics = calculate_metrics(curve, trades)
    regimes = calculate_regime_performance(frames, curve)

    assert metrics.cagr == 0
    assert metrics.total_return == 0
    assert all(item.return_pct == 0 for item in regimes)
