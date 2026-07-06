from app.services.backtest_engine import BacktestFrame, simulate_strategy
from app.schemas.backtest import BacktestRunRequest


def frame(
    day: int,
    qqq: float,
    tqqq: float,
    sma200: float = 100,
    sma20: float | None = 100,
    sma50: float | None = 100,
    high20: float | None = 108,
) -> BacktestFrame:
    return BacktestFrame(
        date=f"2024-01-{day:02d}",
        qqq=qqq,
        tqqq=tqqq,
        qld=tqqq * 0.8,
        sma200=sma200,
        sma20=sma20,
        sma50=sma50,
        high20=high20,
    )


def test_staged_200ma_strategy_buys_in_three_steps():
    frames = [
        frame(1, 104, 100),
        frame(2, 105, 102),
        frame(3, 104, 103, sma20=104),
        frame(4, 102.5, 104, sma50=101),
        frame(5, 103, 105),
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

    buy_trades = [trade for trade in trades if trade.action == "buy"]
    assert [trade.ratio for trade in buy_trades[:3]] == [18.0, 39.0, 60.0]
    assert "1차 매수" in buy_trades[0].reason
    assert "2차 매수" in buy_trades[1].reason
    assert "3차 매수" in buy_trades[2].reason


def test_staged_200ma_strategy_does_not_third_buy_too_close_to_50ma():
    frames = [
        frame(1, 104, 100),
        frame(2, 105, 102),
        frame(3, 104, 103, sma20=104, sma50=103),
        frame(4, 102, 104, sma50=101),
        frame(5, 103, 105),
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

    buy_trades = [trade for trade in trades if trade.action == "buy"]
    assert [trade.ratio for trade in buy_trades] == [18.0, 39.0]


def test_staged_200ma_strategy_reduces_first_buy_when_qqq_is_stretched():
    frames = [
        frame(1, 110, 100),
        frame(2, 111, 102),
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

    assert len(trades) == 1
    assert trades[0].action == "buy"
    assert trades[0].ratio == 9.0
    assert "1차 축소 매수" in trades[0].reason


def test_staged_200ma_strategy_waits_on_minor_50ma_break():
    frames = [
        frame(1, 104, 100),
        frame(2, 105, 102),
        frame(3, 104, 103, sma20=104),
        frame(4, 102.5, 104, sma50=101),
        frame(5, 100.5, 103, sma50=101),
        frame(6, 100, 102, sma50=101),
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
    assert not sell_trades


def test_staged_200ma_strategy_reduces_risk_on_confirmed_50ma_break():
    frames = [
        frame(1, 104, 100),
        frame(2, 105, 102),
        frame(3, 104, 103, sma20=104),
        frame(4, 102.5, 104, sma50=101),
        frame(5, 99.9, 101, sma200=95, sma50=101),
        frame(6, 100, 102, sma50=101),
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
    assert sell_trades
    assert sell_trades[0].ratio == 42.0
    assert "-1% 이하" in sell_trades[0].reason


def test_staged_200ma_strategy_sells_when_qqq_breaks_200ma():
    frames = [
        frame(1, 104, 100),
        frame(2, 105, 102),
        frame(3, 104, 103, sma20=104),
        frame(4, 99, 96),
        frame(5, 98, 94),
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
    assert sell_trades
    assert sell_trades[-1].ratio == 0
    assert "방어 전환" in sell_trades[-1].reason
