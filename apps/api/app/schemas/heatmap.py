from pydantic import BaseModel, Field


class HeatmapRequest(BaseModel):
    initial_capital: float = Field(default=2_500_000, gt=0)
    initial_tqqq_value: float = Field(default=1_600_000, ge=0)
    initial_one_x_value: float = Field(default=500_000, ge=0)
    initial_cash_value: float = Field(default=400_000, ge=0)
    monthly_contribution: float = Field(default=1_000_000, ge=0, le=20_000_000)
    cash_yield: float = Field(default=4.5, ge=0, le=10)
    risk_score: int = Field(default=80, ge=0, le=100)
    defense_mode: str = "cash"


class HeatmapCell(BaseModel):
    ratio: int
    band: float
    cagr: float
    mdd: float
    score: int
    is_adopted: bool
    is_best: bool


class HeatmapReport(BaseModel):
    ratios: list[int]
    bands: list[float]
    cells: list[HeatmapCell]
    adopted_ratio: int
    adopted_band: float
    adopted_score: int
    adopted_rank: int
    total_cells: int
    best_score: int
    best_label: str
    neighbor_score_spread: int  # max-min score among adopted +/- 1 neighborhood
    global_score_spread: int
    plateau_ratio_pct: float  # % of cells within 5 score pts of the best
    verdict: str
    headline: str
    notes: list[str]
