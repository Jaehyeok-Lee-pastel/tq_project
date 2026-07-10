from typing import Literal

from pydantic import BaseModel, Field

BacktestStrategy = Literal[
    "qqq_buy_hold",
    "tqqq_buy_hold",
    "tqqq_200ma",
    "qld_200ma",
    "tqqq_daily_200ma",
]


class BacktestRunRequest(BaseModel):
    strategy: BacktestStrategy = "tqqq_200ma"
    initial_capital: float = Field(default=2_500_000, gt=0)
    start_date: str | None = None
    end_date: str | None = None
    tqqq_target_ratio: float = Field(default=60, ge=0, le=100)
    qld_target_ratio: float = Field(default=70, ge=0, le=100)
    one_x_target_ratio: float = Field(default=0, ge=0, le=100)
    one_x_symbol: str = "QQQ"
    moving_average_days: int = Field(default=200, ge=50, le=300)
    cash_yield: float = Field(default=3.0, ge=0, le=10)
    fee_bps: float = Field(default=5, ge=0, le=100)
    slippage_bps: float = Field(default=5, ge=0, le=100)
    projection_years: int = Field(default=3, ge=1, le=10)
    monthly_contribution: float = Field(default=0, ge=0, le=20_000_000)
    daily_base_tqqq_ratio: float = Field(default=70, ge=0, le=100)
    daily_base_one_x_ratio: float = Field(default=30, ge=0, le=100)


class EquityPoint(BaseModel):
    date: str
    equity: float
    drawdown: float
    position: str


class TradeLogItem(BaseModel):
    date: str
    action: Literal["buy", "sell"]
    symbol: str
    ratio: float
    reason: str


class BacktestMetrics(BaseModel):
    final_capital: float
    total_return: float
    cagr: float
    max_drawdown: float
    sharpe: float | None = None
    sortino: float | None = None
    calmar: float | None = None
    win_rate: float
    trade_count: int
    best_year: float | None = None
    worst_year: float | None = None
    longest_drawdown_days: int


class YearlyReturn(BaseModel):
    year: int
    return_pct: float


class RegimePerformance(BaseModel):
    regime: Literal["uptrend", "downtrend", "shock"]
    label: str
    days: int
    return_pct: float
    win_rate: float
    max_drawdown: float


class ProjectionScenario(BaseModel):
    name: Literal["bear", "base", "bull"]
    annual_return: float
    ending_capital: float
    profit: float
    note: str


class BacktestRunResponse(BaseModel):
    strategy: BacktestStrategy
    strategy_name: str
    moving_average_days: int
    benchmark_name: str
    period_start: str
    period_end: str
    equity_curve: list[EquityPoint]
    benchmark_curve: list[EquityPoint]
    metrics: BacktestMetrics
    benchmark_metrics: BacktestMetrics
    yearly_returns: list[YearlyReturn]
    regime_performance: list[RegimePerformance]
    trades: list[TradeLogItem]
    projection: list[ProjectionScenario]
    interpretation: list[str]
