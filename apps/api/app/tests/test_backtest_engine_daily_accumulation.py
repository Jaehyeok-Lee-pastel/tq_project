from app.schemas.backtest import BacktestRunRequest
from app.services.backtest_engine import BacktestFrame, simulate_strategy


def frame(day: int, qqq: float, tqqq: float, sma200: float = 100) -> BacktestFrame:
    return BacktestFrame(
        date=f"2024-02-{day:02d}",
        qqq=qqq,
        tqqq=tqqq,
        qld=tqqq * 0.8,
        sma200=sma200,
        sma20=qqq,
        sma50=qqq,
        high20=qqq,
    )


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
        ),
    )

    tqqq_buys = [trade for trade in trades if trade.action == "buy" and trade.symbol == "TQQQ"]
    one_x_buys = [trade for trade in trades if trade.action == "buy" and trade.symbol == "QQQM"]

    assert tqqq_buys[0].ratio == 70.0
    assert one_x_buys[0].ratio == 30.0
    assert tqqq_buys[-1].ratio == 45.5
    assert "감속" in tqqq_buys[-1].reason
