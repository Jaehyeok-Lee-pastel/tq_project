from pydantic import BaseModel, Field

from app.schemas.backtest import DefenseMode


class MonteCarloRequest(BaseModel):
    # Strategy under test (defaults = the adopted best-practice config).
    strategy: str = "tqqq_daily_200ma"
    daily_base_tqqq_ratio: float = Field(default=80, ge=0, le=100)
    daily_base_one_x_ratio: float = Field(default=20, ge=0, le=100)
    one_x_symbol: str = "QQQM"
    ma_exit_band_pct: float = Field(default=2, ge=-5, le=5)
    defense_mode: DefenseMode = "cash"
    one_x_upfront_monthly: bool = True
    monthly_contribution: float = Field(default=1_000_000, ge=0, le=20_000_000)
    tqqq_target_ratio: float = Field(default=45, ge=0, le=100)
    qld_target_ratio: float = Field(default=60, ge=0, le=100)
    one_x_target_ratio: float = Field(default=0, ge=0, le=100)
    moving_average_days: int = Field(default=200, ge=50, le=300)
    initial_capital: float = Field(default=2_500_000, gt=0)
    initial_tqqq_value: float = Field(default=1_600_000, ge=0)
    initial_one_x_value: float = Field(default=500_000, ge=0)
    initial_cash_value: float = Field(default=400_000, ge=0)
    cash_yield: float = Field(default=4.5, ge=0, le=10)
    # Monte Carlo controls.
    n_paths: int = Field(default=200, ge=50, le=1500)
    years: int = Field(default=26, ge=5, le=40)
    seed: int = Field(default=20260713, ge=0, le=2_000_000_000)


class Percentiles(BaseModel):
    p5: float
    p25: float
    median: float
    p75: float
    p95: float
    mean: float


class RegimeSummaryItem(BaseModel):
    regime: str
    label: str
    day_share_pct: float
    ann_return_pct: float
    ann_vol_pct: float


class SamplePath(BaseModel):
    kind: str  # "median" | "p5" | "p95"
    points: list[float]


class MonteCarloReport(BaseModel):
    n_paths: int
    years: int
    seed: int
    strategy: str
    regime_summary: list[RegimeSummaryItem]
    cagr: Percentiles
    max_drawdown: Percentiles
    final_multiple: Percentiles  # final / total invested
    benchmark_cagr: Percentiles
    prob_cagr_positive: float
    prob_beat_benchmark: float
    prob_mdd_worse_than_60: float
    prob_mdd_worse_than_70: float
    sample_paths: list[SamplePath]
    headline: str
    notes: list[str]
