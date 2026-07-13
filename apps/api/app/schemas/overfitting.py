from pydantic import BaseModel, Field


class OverfittingRequest(BaseModel):
    initial_capital: float = Field(default=2_500_000, gt=0)
    initial_tqqq_value: float = Field(default=1_600_000, ge=0)
    initial_one_x_value: float = Field(default=500_000, ge=0)
    initial_cash_value: float = Field(default=400_000, ge=0)
    monthly_contribution: float = Field(default=1_000_000, ge=0, le=20_000_000)
    cash_yield: float = Field(default=4.5, ge=0, le=10)


class OverfittingReport(BaseModel):
    n_trials: int
    correction_trials: int
    sample_days: int
    adopted_label: str
    observed_sharpe: float  # annualized excess-return Sharpe versus QQQ
    deflated_benchmark_sharpe: float  # annualized SR0 (expected best-of-N by luck)
    deflated_sharpe_ratio: float  # DSR probability 0..1
    skew: float
    kurtosis: float
    pbo: float  # probability of backtest overfitting 0..1
    cscv_splits: int
    dsr_verdict: str
    pbo_verdict: str
    headline: str
    notes: list[str]
