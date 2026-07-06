from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.backtest import BacktestRunResponse, BacktestStrategy


class StrategyCompareRequest(BaseModel):
    initial_capital: float = Field(default=2_500_000, gt=0)
    risk_score: int = Field(default=75, ge=0, le=100)
    strategies: list[BacktestStrategy] = Field(
        default_factory=lambda: [
            "tqqq_200ma",
            "qld_200ma",
            "qqq_buy_hold",
            "tqqq_buy_hold",
        ],
        min_length=1,
        max_length=8,
    )
    tqqq_target_ratio: float = Field(default=60, ge=0, le=100)
    qld_target_ratio: float = Field(default=70, ge=0, le=100)
    moving_average_days: int = Field(default=200, ge=50, le=300)
    cash_yield: float = Field(default=3.0, ge=0, le=10)
    fee_bps: float = Field(default=5, ge=0, le=100)
    slippage_bps: float = Field(default=5, ge=0, le=100)
    include_default_tqqq_comparison: bool = True
    default_tqqq_target_ratio: float = Field(default=60, ge=0, le=100)


class StrategyRankItem(BaseModel):
    rank: int
    strategy: BacktestStrategy
    strategy_name: str
    final_capital: float
    total_return: float
    cagr: float
    max_drawdown: float
    sharpe: float | None = None
    trade_count: int
    profit_score: int
    defense_score: int
    fit_score: int
    consistency_score: int
    total_score: int
    verdict: Literal["best_fit", "high_return", "defensive", "too_risky", "watch"]
    reason: str


class SensitivityItem(BaseModel):
    strategy: BacktestStrategy
    strategy_name: str
    moving_average_days: int
    cagr: float
    max_drawdown: float
    total_score: int


class SensitivitySummary(BaseModel):
    tested_windows: list[int]
    best_window: int
    robustness_score: int
    verdict: str
    results: list[SensitivityItem]


class PhilosophyAuditItem(BaseModel):
    label: str
    score: int
    status: Literal["ok", "watch", "danger"]
    detail: str


class PhilosophyAudit(BaseModel):
    score: int
    verdict: Literal["excellent", "good", "watch", "danger"]
    summary: str
    items: list[PhilosophyAuditItem]
    to_reach_100: list[str]


class TqqqDefaultComparison(BaseModel):
    baseline_label: str
    custom_label: str
    baseline_target_ratio: float
    custom_target_ratio: float
    final_capital_delta: float
    cagr_delta: float
    max_drawdown_delta: float
    trade_count_delta: int
    base_projection_delta: float
    verdict: Literal["custom_better", "custom_defensive", "baseline_better", "similar"]
    summary: str
    philosophy_audit: PhilosophyAudit
    baseline: BacktestRunResponse
    custom: BacktestRunResponse


class StrategyCompareResponse(BaseModel):
    initial_capital: float
    risk_score: int
    recommended_strategy: BacktestStrategy
    summary: str
    rankings: list[StrategyRankItem]
    sensitivity: SensitivitySummary | None = None
    tqqq_default_comparison: TqqqDefaultComparison | None = None
    backtests: list[BacktestRunResponse]
