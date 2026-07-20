from typing import Literal

from pydantic import BaseModel, Field

BacktestStrategy = Literal[
    "qqq_buy_hold",
    "tqqq_buy_hold",
    "tqqq_200ma",
    "qld_200ma",
    "tqqq_daily_200ma",
]

# What the portfolio holds while QQQ is below the MA200 exit line.
# - cash: everything defensive earns the cash/SGOV yield (final philosophy doc)
# - spym_sgov_half: 50% SPYM (S&P 1x) + 50% SGOV/cash (community-rule variant)
# - hold_one_x: keep the 1x sleeve invested; only TQQQ is defended
DefenseMode = Literal["cash", "spym_sgov_half", "hold_one_x"]


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
    initial_tqqq_value: float = Field(default=0, ge=0, le=1_000_000_000)
    initial_one_x_value: float = Field(default=0, ge=0, le=1_000_000_000)
    initial_cash_value: float = Field(default=0, ge=0, le=1_000_000_000)
    # Rule-robustness experiment knobs. Defaults reproduce the base rules;
    # the compare engine perturbs them to test how curve-fit the rules are.
    disparity_band_scale: float = Field(default=1.0, ge=0.5, le=1.5)
    daily_decel_mid: float = Field(default=0.65, ge=0, le=1)
    daily_decel_high: float = Field(default=0.30, ge=0, le=1)
    # Buy ratio factor beyond +30% disparity (0 = stop new TQQQ, the base rule;
    # 1 = never decelerate). Lets research test "no deceleration at all".
    daily_decel_stop: float = Field(default=0, ge=0, le=1)
    # If > 0: cash left unspent by deceleration is tracked as a carried
    # reserve and redeployed at 1/N per day once disparity returns below +10%
    # (0 = off, the base rule: the reserve waits for a defense-recovery cycle).
    reserve_redeploy_days: int = Field(default=0, ge=0, le=126)
    # If > 0: on a day the disparity falls >= 3%p while still above the MA
    # (a sharp dip, e.g. +15% -> +8%), buy an EXTRA multiple of the daily
    # budget from cash. 0 = off (base rule).
    dip_buy_multiple: float = Field(default=0, ge=0, le=10)
    # Batch-buy cadence (whole-share constraint modeling): each day's buy is
    # earmarked at that day's deceleration ratio, but executed only every N
    # trading days. 1 = daily (idealized fractional buying).
    tqqq_batch_days: int = Field(default=1, ge=1, le=63)
    one_x_batch_days: int = Field(default=1, ge=1, le=63)
    # Salary-day mode: the monthly contribution arrives as a lump on the
    # month's first trading day and the month's 1x allocation is bought
    # upfront that day (TQQQ keeps its daily decelerated cadence).
    one_x_upfront_monthly: bool = True
    ma_exit_band_pct: float = Field(default=0, ge=-5, le=5)
    overheat_trim_distance_pct: float = Field(default=25, ge=10, le=50)
    # None keeps each strategy's historical default: staged -> cash,
    # daily accumulation -> hold_one_x.
    defense_mode: DefenseMode | None = None


class EquityPoint(BaseModel):
    date: str
    equity: float
    drawdown: float
    position: str
    cash_flow: float = 0


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
    data_notes: list[str] = []
