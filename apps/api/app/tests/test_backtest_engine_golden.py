"""Golden tests: exact numeric assertions against hand-computed series.

These pin the backtest math down to absolute values so that data-layer or
engine refactors cannot silently change results.
"""

import pytest

from app.schemas.backtest import BacktestRunRequest
from app.services.backtest_engine import (
    BacktestFrame,
    calculate_metrics,
    simulate_buy_hold,
    simulate_strategy,
    sortino_ratio,
)
from app.services.market_data import PriceRow, extend_with_synthetic, synthetic_daily_return


def frame(
    day: int,
    qqq: float,
    tqqq: float = 100.0,
    sma200: float = 100.0,
    sma20: float | None = 100.0,
    sma50: float | None = 100.0,
) -> BacktestFrame:
    return BacktestFrame(
        date=f"2024-03-{day:02d}",
        qqq=qqq,
        tqqq=tqqq,
        qld=tqqq,
        spy=qqq,
        sma200=sma200,
        sma20=sma20,
        sma50=sma50,
        high20=None,
    )


def test_buy_hold_exact_total_return_and_drawdown():
    # QQQ: 100 -> 110 (+10%) -> 99 (-10%). Total: 1.1 * 0.9 - 1 = -1%.
    frames = [frame(1, 100), frame(2, 110), frame(3, 99)]
    curve, trades = simulate_buy_hold(frames, 1_000_000, "QQQ")

    assert curve[0].equity == 1_000_000  # day-0 anchor
    assert curve[1].equity == 1_100_000
    assert curve[2].equity == pytest.approx(990_000)

    metrics = calculate_metrics(curve, trades)
    assert metrics.total_return == -1.0
    assert metrics.max_drawdown == -10.0
    assert metrics.final_capital == pytest.approx(990_000)
    assert metrics.win_rate == 50.0


def test_contributions_do_not_change_time_weighted_return():
    # Price rises 10% on the only active day; a contribution lands the same
    # day. TWR must still report exactly +10%.
    frames = [frame(1, 100), frame(2, 110)]
    curve, trades = simulate_buy_hold(
        frames, 1_000_000, "QQQ", monthly_contribution=21_000, cost_ratio=0
    )

    assert curve[1].cash_flow == 1_000.0
    assert curve[1].equity == pytest.approx(1_101_000)

    metrics = calculate_metrics(curve, trades)
    assert metrics.total_return == 10.0


def test_metrics_drawdown_ignores_contribution_cushion():
    # Crash of 50% while contributing heavily: the raw equity curve is
    # cushioned by deposits, but strategy MDD must still be -50%.
    frames = [frame(1, 100), frame(2, 50), frame(3, 50)]
    curve, trades = simulate_buy_hold(
        frames, 1_000_000, "QQQ", monthly_contribution=2_100_000, cost_ratio=0
    )
    metrics = calculate_metrics(curve, trades)
    assert metrics.max_drawdown == -50.0


def test_sortino_uses_downside_deviation_over_all_days():
    returns = [0.02, -0.01, 0.01]
    mean_return = sum(returns) / 3
    downside_deviation = ((0.01**2) / 3) ** 0.5
    expected = round(mean_return / downside_deviation * 252**0.5, 2)
    assert sortino_ratio(returns) == expected


def test_synthetic_extension_matches_hand_calculation():
    base_rows = [
        PriceRow(date="2005-01-03", close=100.0),
        PriceRow(date="2005-01-04", close=110.0),
        PriceRow(date="2005-01-05", close=99.0),
    ]
    real_rows = [
        PriceRow(date="2005-01-05", close=50.0),
        PriceRow(date="2005-01-06", close=51.0),
    ]
    leverage, expense_ratio = 3.0, 0.0095

    merged, synthetic_until = extend_with_synthetic(base_rows, real_rows, leverage, expense_ratio)

    ret_d2 = synthetic_daily_return(0.10, 2005, leverage, expense_ratio)
    ret_d3 = synthetic_daily_return(99 / 110 - 1, 2005, leverage, expense_ratio)
    price_d2 = 50.0 / (1 + ret_d3)
    price_d1 = price_d2 / (1 + ret_d2)

    assert synthetic_until == "2005-01-04"
    assert [row.date for row in merged] == ["2005-01-03", "2005-01-04", "2005-01-05", "2005-01-06"]
    assert merged[0].close == pytest.approx(price_d1)
    assert merged[1].close == pytest.approx(price_d2)
    assert merged[2].close == 50.0  # real anchor untouched
    assert merged[3].close == 51.0


def test_daily_accumulation_conserves_money_with_flat_prices():
    # Above the MA in a deceleration tier, flat prices, zero costs and zero
    # cash yield: total equity must stay exactly at the initial capital.
    # (Regression guard: an earlier version destroyed the decelerated
    # remainder of each day's buy budget.)
    frames = [frame(day, 120.0) for day in range(1, 31)]
    curve, _ = simulate_strategy(
        frames,
        BacktestRunRequest(
            strategy="tqqq_daily_200ma",
            initial_capital=1_000_000,
            monthly_contribution=0,
            fee_bps=0,
            slippage_bps=0,
            cash_yield=0,
        ),
    )
    assert all(point.equity == pytest.approx(1_000_000) for point in curve)


def test_daily_accumulation_redeploys_defensive_cash_after_recovery():
    # Sell everything after 2 days below the MA, then recover: the proceeds
    # must return to the market within the 21-day redeploy window instead of
    # sitting in cash forever.
    frames = (
        [frame(day, 105.0) for day in range(1, 4)]
        + [frame(day, 95.0) for day in range(4, 8)]
        + [frame(day, 105.0) for day in range(8, 31)]
    )
    curve, trades = simulate_strategy(
        frames,
        BacktestRunRequest(
            strategy="tqqq_daily_200ma",
            initial_capital=500_000,
            initial_tqqq_value=500_000,
            initial_one_x_value=0,
            initial_cash_value=0,
            monthly_contribution=0,
            fee_bps=0,
            slippage_bps=0,
            cash_yield=0,
        ),
    )

    sells = [trade for trade in trades if trade.action == "sell"]
    assert sells and "방어 전환" in sells[0].reason
    rebuys = [
        trade
        for trade in trades
        if trade.action == "buy" and trade.date > sells[0].date and trade.symbol == "TQQQ"
    ]
    assert rebuys, "defensive-sale proceeds must be redeployed after MA recovery"
    assert curve[-1].position != "CASH"
    assert curve[-1].equity == pytest.approx(500_000)


def test_reserve_redeploys_when_disparity_normalizes():
    # Phase 1: stretched (+25% -> tier 2), most of the budget goes unspent.
    # Phase 2: disparity normalizes (+5% -> tier 0): with the reserve rule the
    # carried cash re-enters on top of the daily budget; without it, it waits.
    stretched = [frame(day, 125.0, sma200=100.0) for day in range(1, 11)]
    # Phase 2: tier 0, TQQQ rallies 1%/day — extra invested reserve must pay off.
    normalized = [
        frame(day, 105.0, tqqq=100.0 * 1.01 ** (day - 11), sma200=100.0)
        for day in range(11, 26)
    ]
    frames = stretched + normalized
    common = dict(
        strategy="tqqq_daily_200ma",
        initial_capital=1_000_000,
        initial_tqqq_value=1,  # skip the 21-day initial deployment path
        initial_one_x_value=0,
        initial_cash_value=999_999,
        monthly_contribution=1_050_000,  # 50,000/day
        fee_bps=0,
        slippage_bps=0,
        cash_yield=0,
        one_x_symbol="QQQM",
        defense_mode="cash",
    )
    base_curve, _ = simulate_strategy(frames, BacktestRunRequest(**common))
    reserve_curve, _ = simulate_strategy(
        frames, BacktestRunRequest(**common, reserve_redeploy_days=10)
    )

    # The reserve variant put the carried cash into the rally, so it must end
    # ahead; the base rule leaves that cash idle until a defense cycle.
    assert reserve_curve[-1].equity > base_curve[-1].equity


def test_dip_buy_multiple_adds_extra_budget_on_sharp_disparity_drop():
    # Day 11: disparity collapses +15% -> +8% (>=3%p drop, still above MA)
    # then TQQQ rallies. The boosted variant bought extra into the dip, so it
    # must finish ahead of the base rule.
    frames = (
        [frame(day, 115.0, sma200=100.0) for day in range(1, 11)]
        + [
            frame(day, 108.0, tqqq=100.0 * 1.01 ** (day - 11), sma200=100.0)
            for day in range(11, 26)
        ]
    )
    common = dict(
        strategy="tqqq_daily_200ma",
        initial_capital=1_000_000,
        initial_tqqq_value=1,
        initial_one_x_value=0,
        initial_cash_value=999_999,
        monthly_contribution=1_050_000,
        fee_bps=0,
        slippage_bps=0,
        cash_yield=0,
        one_x_symbol="QQQM",
        defense_mode="cash",
    )
    base_curve, _ = simulate_strategy(frames, BacktestRunRequest(**common))
    boosted_curve, _ = simulate_strategy(
        frames, BacktestRunRequest(**common, dip_buy_multiple=4)
    )
    assert boosted_curve[-1].equity > base_curve[-1].equity


def test_staged_restores_ratio_after_50ma_dip_recovery():
    frames = [
        frame(1, 104, 100),
        frame(2, 105, 102),
        frame(3, 104, 103, sma20=104),
        frame(4, 102.5, 104, sma50=101),
        frame(5, 103, 105, sma50=105),
        frame(6, 106, 105, sma50=104),
        frame(7, 107, 106, sma50=104),
    ]
    _, trades = simulate_strategy(
        frames,
        BacktestRunRequest(
            strategy="tqqq_200ma",
            initial_capital=1_000_000,
            tqqq_target_ratio=60,
            cash_yield=3,
        ),
    )

    sell_trades = [trade for trade in trades if trade.action == "sell"]
    assert sell_trades and sell_trades[0].ratio == 42.0
    recovery_buys = [trade for trade in trades if "복귀" in trade.reason]
    assert recovery_buys and recovery_buys[0].ratio == 60.0


def test_daily_defense_cash_mode_sells_one_x_too():
    # Trigger the MA break by raising the SMA, keeping prices flat so the
    # money-conservation check stays exact.
    frames = (
        [frame(day, 105.0, sma200=100.0) for day in range(1, 4)]
        + [frame(day, 105.0, sma200=110.0) for day in range(4, 9)]
    )
    curve, trades = simulate_strategy(
        frames,
        BacktestRunRequest(
            strategy="tqqq_daily_200ma",
            initial_capital=1_000_000,
            initial_tqqq_value=600_000,
            initial_one_x_value=400_000,
            initial_cash_value=0,
            monthly_contribution=0,
            fee_bps=0,
            slippage_bps=0,
            cash_yield=0,
            one_x_symbol="QQQM",
            defense_mode="cash",
        ),
    )
    sells = {trade.symbol for trade in trades if trade.action == "sell"}
    assert sells == {"TQQQ", "QQQM"}
    assert curve[-1].position == "CASH"
    assert curve[-1].equity == pytest.approx(1_000_000)


def test_daily_defense_half_mode_moves_half_into_spym():
    frames = (
        [frame(day, 105.0, sma200=100.0) for day in range(1, 4)]
        + [frame(day, 105.0, sma200=110.0) for day in range(4, 9)]
    )
    curve, trades = simulate_strategy(
        frames,
        BacktestRunRequest(
            strategy="tqqq_daily_200ma",
            initial_capital=1_000_000,
            initial_tqqq_value=600_000,
            initial_one_x_value=400_000,
            initial_cash_value=0,
            monthly_contribution=0,
            fee_bps=0,
            slippage_bps=0,
            cash_yield=0,
            one_x_symbol="QQQM",
            defense_mode="spym_sgov_half",
        ),
    )
    spym_buys = [trade for trade in trades if trade.action == "buy" and trade.symbol == "SPYM"]
    assert spym_buys and spym_buys[0].ratio == 50
    assert curve[-1].position == "SPYM+SGOV"
    # Flat prices, zero costs: money is conserved through the conversion.
    assert curve[-1].equity == pytest.approx(1_000_000)


def test_staged_half_defense_earns_spy_return_below_ma():
    # Below the MA200 the whole time; SPY rallies while cash yield is zero.
    frames = [
        BacktestFrame(
            date=f"2024-04-{day:02d}",
            qqq=90.0,
            tqqq=100.0,
            qld=100.0,
            spy=100.0 * (1.01 ** (day - 1)),
            sma200=100.0,
            sma20=100.0,
            sma50=100.0,
            high20=None,
        )
        for day in range(1, 11)
    ]
    request_common = dict(
        strategy="tqqq_200ma",
        initial_capital=1_000_000,
        tqqq_target_ratio=60,
        fee_bps=0,
        slippage_bps=0,
        cash_yield=0,
    )
    cash_curve, _ = simulate_strategy(frames, BacktestRunRequest(**request_common, defense_mode="cash"))
    half_curve, _ = simulate_strategy(
        frames, BacktestRunRequest(**request_common, defense_mode="spym_sgov_half")
    )
    assert cash_curve[-1].equity == pytest.approx(1_000_000)
    # The staged engine is ratio-based, so the 50/50 defense is a daily
    # rebalanced blend: (1 + 0.5 x 1%)^9.
    assert half_curve[-1].equity == pytest.approx(1_000_000 * 1.005**9)
    assert half_curve[-1].position == "SPYM+SGOV"


def test_staged_enters_reduced_when_disparity_is_high_at_start():
    frames = [frame(1, 120, 100), frame(2, 121, 101)]
    _, trades = simulate_strategy(
        frames,
        BacktestRunRequest(
            strategy="tqqq_200ma",
            initial_capital=1_000_000,
            tqqq_target_ratio=60,
            cash_yield=3,
        ),
    )

    assert len(trades) == 1
    assert trades[0].ratio == 9.0
    assert "이격 과다" in trades[0].reason
