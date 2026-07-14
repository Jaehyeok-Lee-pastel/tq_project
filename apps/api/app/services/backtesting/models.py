from dataclasses import dataclass

TRADING_DAYS_PER_YEAR = 252
TRADING_DAYS_PER_MONTH = 21
REDEPLOY_DAYS = 21


@dataclass(frozen=True, slots=True)
class BacktestFrame:
    date: str
    qqq: float
    tqqq: float
    qld: float
    spy: float
    sma200: float
    sma20: float | None = None
    sma50: float | None = None
    high20: float | None = None


@dataclass(frozen=True)
class MarketDataset:
    frames: list[BacktestFrame]
    tqqq_synthetic_until: str | None
    qld_synthetic_until: str | None


STRATEGY_NAMES = {
    "qqq_buy_hold": "QQQ 장기 보유",
    "tqqq_buy_hold": "TQQQ 장기 보유",
    "tqqq_200ma": "QQQ 200일선 기반 TQQQ 전략",
    "qld_200ma": "QQQ 200일선 기반 QLD 전략",
    "tqqq_daily_200ma": "QQQ 200일선 기반 TQQQ 일일 적립 감속",
}
