from pydantic import BaseModel, Field


class WalkForwardRequest(BaseModel):
    initial_capital: float = Field(default=10_000_000, gt=0)
    monthly_contribution: float = Field(default=1_000_000, ge=0, le=20_000_000)
    cash_yield: float = Field(default=4.5, ge=0, le=10)
    risk_score: int = Field(default=80, ge=0, le=100)
    is_years: int = Field(default=8, ge=3, le=15)
    oos_years: int = Field(default=3, ge=1, le=8)
    step_years: int = Field(default=3, ge=1, le=8)


class WalkForwardWindow(BaseModel):
    index: int
    is_start: str
    is_end: str
    oos_start: str
    oos_end: str
    selected_label: str
    is_cagr: float
    is_score: int
    oos_cagr: float
    oos_mdd: float
    oos_beat_benchmark: bool
    benchmark_oos_cagr: float
    fixed_oos_cagr: float
    fixed_oos_mdd: float


class WalkForwardReport(BaseModel):
    windows: list[WalkForwardWindow]
    fixed_label: str
    walk_forward_efficiency_pct: float  # aggregate OOS CAGR / IS CAGR of selected
    selection_stability_pct: float  # share of windows won by the modal config
    modal_config: str
    oos_beat_benchmark_pct: float
    adaptive_oos_cagr_median: float
    fixed_oos_cagr_median: float
    adaptive_compound_oos_cagr: float
    adaptive_worst_oos_mdd: float
    fixed_compound_oos_cagr: float
    fixed_worst_oos_mdd: float
    headline: str
    notes: list[str]
