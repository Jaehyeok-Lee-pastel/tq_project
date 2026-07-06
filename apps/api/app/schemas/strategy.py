from typing import Literal

from pydantic import BaseModel, Field

RiskProfile = Literal["defensive", "balanced", "aggressive", "very_aggressive"]
MarketRegime = Literal["risk_off", "normal_entry", "reduced_entry", "stretched_entry"]
ScoreLevel = Literal["low", "medium", "high", "very_high"]


class HoldingInput(BaseModel):
    symbol: str
    name: str = ""
    amount: float = Field(ge=0)
    category: str = "other"


class InvestorProfile(BaseModel):
    risk_profile: RiskProfile = "aggressive"
    risk_score: int = Field(default=75, ge=0, le=100)
    target_count: int = Field(default=3, ge=2, le=5)
    allow_tqqq: bool = True
    prefer_200ma: bool = True
    min_cash_ratio: float = Field(default=20, ge=0, le=80)
    max_tqqq_ratio: float = Field(default=50, ge=0, le=80)
    max_semiconductor_ratio: float = Field(default=35, ge=0, le=80)
    max_single_position_ratio: float = Field(default=60, ge=10, le=100)
    goal: str = (
        "2~3개에 집중하되 TQQQ를 포함한 공격형 포트폴리오를 원합니다. "
        "200일선과 분할매수/분할매도 규칙으로 리스크를 관리하고 싶습니다."
    )


class MarketSnapshot(BaseModel):
    qqq_close: float = Field(gt=0)
    qqq_sma200: float = Field(gt=0)
    qqq_sma20: float | None = Field(default=None, gt=0)
    qqq_sma50: float | None = Field(default=None, gt=0)
    qqq_high20: float | None = Field(default=None, gt=0)
    qqq_rsi14: float | None = Field(default=None, ge=0, le=100)
    as_of: str


class StrategyRecommendRequest(BaseModel):
    holdings: list[HoldingInput]
    cash: float = Field(default=0, ge=0)
    profile: InvestorProfile
    market: MarketSnapshot
    use_ai: bool = True


class PortfolioAllocation(BaseModel):
    symbol: str
    name: str
    target_ratio: float
    target_amount: float
    role: str


class TradeAction(BaseModel):
    symbol: str
    action: Literal["buy", "sell", "hold", "wait"]
    amount: float
    reason: str


class SplitStep(BaseModel):
    step: str
    trigger: str
    ratio_of_target: float
    amount: float
    note: str


class RiskMetric(BaseModel):
    label: str
    value: str
    level: ScoreLevel


class ConfidenceBreakdown(BaseModel):
    rule_clarity: int
    market_fit: int
    cash_defense: int
    drawdown_control: int
    overfit_resistance: int
    execution_quality: int
    user_fit: int


class StrategyScores(BaseModel):
    confidence_score: int
    risk_score: int
    fit_score: int
    expected_return_score: int
    execution_difficulty: ScoreLevel
    confidence_breakdown: ConfidenceBreakdown
    confidence_notes: list[str]


class CandidateOpinion(BaseModel):
    symbol: str
    name: str
    stance: Literal["core", "satellite", "defense", "avoid", "watch"]
    reason: str


class StrategyPlan(BaseModel):
    id: str
    title: str
    summary: str
    allocations: list[PortfolioAllocation]
    actions: list[TradeAction]
    buy_plan: list[SplitStep]
    sell_plan: list[SplitStep]
    risk_metrics: list[RiskMetric]
    scores: StrategyScores
    pros: list[str]
    cons: list[str]


class CoachReport(BaseModel):
    headline: str
    diagnosis: str
    recommended_plan_id: str
    why: list[str]
    next_actions: list[str]
    warnings: list[str]
    monitoring_rules: list[str]


class StrategyRecommendResponse(BaseModel):
    total_capital: float
    market_regime: MarketRegime
    qqq_distance_from_200ma: float
    current_diagnosis: list[str]
    candidate_opinions: list[CandidateOpinion] = Field(default_factory=list)
    plans: list[StrategyPlan]
    coach_report: CoachReport
    ai_used: bool
