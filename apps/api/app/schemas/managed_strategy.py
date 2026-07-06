from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.strategy import MarketSnapshot, StrategyPlan

ManagedStrategyStatus = Literal["active", "paused", "archived"]
JournalEntryType = Literal[
    "buy",
    "sell",
    "hold",
    "rebalance",
    "review",
    "rule_check",
    "note",
    "deposit",
    "fx",
    "cash_transfer",
]
JournalMood = Literal["calm", "confident", "anxious", "greedy", "fearful", "neutral"]
ExecutionSide = Literal["buy", "sell"]
ExecutionStatus = Literal["ready", "wait", "blocked", "done"]


class ManagedStrategyCreate(BaseModel):
    plan: StrategyPlan
    market: MarketSnapshot
    total_capital: float = Field(ge=0)
    selected_reason: str = ""


class ManagedStrategyUpdate(BaseModel):
    status: ManagedStrategyStatus | None = None
    selected_reason: str | None = None
    market: MarketSnapshot | None = None


class StrategyJournalCreate(BaseModel):
    entry_type: JournalEntryType = "note"
    symbol: str = ""
    amount: float = Field(default=0, ge=0)
    quantity: float = Field(default=0, ge=0)
    price: float = Field(default=0, ge=0)
    reason: str = ""
    mood: JournalMood = "neutral"
    note: str = ""


class StrategyJournalEntry(StrategyJournalCreate):
    id: str
    created_at: str
    qqq_close: float
    qqq_sma200: float
    qqq_distance_from_200ma: float


class StrategyVersionAllocation(BaseModel):
    symbol: str
    ratio: float


class StrategyVersionEntry(BaseModel):
    version: int
    created_at: str
    change_type: Literal["created", "adjustment", "manual", "philosophy"]
    title: str
    note: str = ""
    before_allocations: list[StrategyVersionAllocation] = Field(default_factory=list)
    after_allocations: list[StrategyVersionAllocation] = Field(default_factory=list)


class ManagedStrategy(ManagedStrategyCreate):
    id: str
    status: ManagedStrategyStatus = "active"
    created_at: str
    updated_at: str
    version: int = 1
    journal: list[StrategyJournalEntry] = Field(default_factory=list)
    version_history: list[StrategyVersionEntry] = Field(default_factory=list)


class ComplianceIssue(BaseModel):
    level: Literal["ok", "watch", "danger"]
    title: str
    detail: str


class SplitExecutionStep(BaseModel):
    side: ExecutionSide
    step: str
    symbol: str
    status: ExecutionStatus
    trigger: str
    trigger_price: float | None = None
    trigger_label: str = ""
    current_price: float | None = None
    distance_to_trigger_pct: float | None = None
    amount: float
    ratio_of_target: float
    reason: str
    action_label: str


class ManagedStrategyGuide(BaseModel):
    strategy: ManagedStrategy
    compliance_score: int
    current_action: str
    checklist: list[str]
    issues: list[ComplianceIssue]
    execution_plan: list[SplitExecutionStep]
    next_review: str


class StrategyAdjustmentRequest(BaseModel):
    target_cash_ratio: float = Field(ge=0, le=80)
    note: str = ""


class StrategyAdjustmentAllocation(BaseModel):
    symbol: str
    current_ratio: float
    suggested_ratio: float
    delta_ratio: float
    reason: str


class StrategyAdjustmentAdvice(BaseModel):
    verdict: Literal["ok", "watch", "danger"]
    headline: str
    summary: str
    current_cash_ratio: float
    target_cash_ratio: float
    minimum_cash_ratio: float
    qqq_distance_from_200ma: float
    suggested_allocations: list[StrategyAdjustmentAllocation]
    issues: list[str]
    actions: list[str]


class StrategyAdjustmentApplyRequest(StrategyAdjustmentRequest):
    accepted_headline: str = ""


class ContributionPlanRequest(BaseModel):
    contribution_amount: float = Field(default=1_000_000, ge=0)
    pay_day: int = Field(default=10, ge=1, le=31)
    note: str = ""


class ContributionAllocationAdvice(BaseModel):
    symbol: str
    role: str
    current_amount: float
    target_amount_after: float
    gap_amount: float
    suggested_amount: float
    action: Literal["buy", "wait", "hold", "rebalance"]
    reason: str


class ContributionPlanOption(BaseModel):
    id: str = "balanced"
    title: str = ""
    risk_level: Literal["defensive", "balanced", "aggressive"] = "balanced"
    recommendation_score: int = Field(default=80, ge=0, le=100)
    headline: str
    summary: str
    contribution_amount: float
    pay_day: int
    current_total_capital: float
    new_total_capital: float
    qqq_distance_from_200ma: float
    available_cash_after_deposit: float
    actions: list[str]
    allocations: list[ContributionAllocationAdvice]


class ContributionPlanAdvice(BaseModel):
    headline: str
    summary: str
    contribution_amount: float
    pay_day: int
    current_total_capital: float
    new_total_capital: float
    qqq_distance_from_200ma: float
    available_cash_after_deposit: float
    actions: list[str]
    allocations: list[ContributionAllocationAdvice]
    recommended_plan_id: str = "balanced"
    plans: list[ContributionPlanOption] = Field(default_factory=list)


class ContributionPlanApplyRequest(ContributionPlanRequest):
    accepted_headline: str = ""
    selected_plan_id: str = "balanced"


class PhilosophyAllocationDiff(BaseModel):
    symbol: str
    current_ratio: float
    suggested_ratio: float
    delta_ratio: float
    reason: str


class PhilosophyUpgradeAdvice(BaseModel):
    verdict: Literal["up_to_date", "update_recommended", "major_change"]
    headline: str
    summary: str
    qqq_distance_from_200ma: float
    inferred_risk_score: int
    current_plan_title: str
    suggested_plan_id: str
    suggested_plan_title: str
    suggested_plan_summary: str
    allocation_diffs: list[PhilosophyAllocationDiff]
    changes: list[str]
    cautions: list[str]


class PhilosophyUpgradeApplyRequest(BaseModel):
    accepted_headline: str = ""
