from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.backtest import BacktestStrategy, DefenseMode
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


class ResearchStrategyConfig(BaseModel):
    """The exact rule set validated in the research lab (ComparePage).

    Stored verbatim on the managed strategy so the daily decision endpoint
    and the simulation tab run the SAME rules the backtest validated.
    """

    strategy: BacktestStrategy = "tqqq_daily_200ma"
    daily_base_tqqq_ratio: float = Field(default=70, ge=0, le=100)
    daily_base_one_x_ratio: float = Field(default=30, ge=0, le=100)
    one_x_symbol: str = "QQQM"
    ma_exit_band_pct: float = Field(default=2, ge=-5, le=5)
    defense_mode: DefenseMode = "cash"
    monthly_contribution: float = Field(default=0, ge=0, le=20_000_000)
    moving_average_days: int = Field(default=200, ge=50, le=300)
    tqqq_target_ratio: float = Field(default=45, ge=0, le=100)
    qld_target_ratio: float = Field(default=60, ge=0, le=100)
    # Buy the month's 1x allocation as a lump on payday (fractional order in
    # the Toss app); TQQQ keeps the daily decelerated cadence. Validated in
    # research study 20.
    one_x_upfront_monthly: bool = True
    preset_id: str | None = None
    preset_version: str | None = None

    @model_validator(mode="after")
    def validate_daily_allocation(self) -> "ResearchStrategyConfig":
        if self.strategy != "tqqq_daily_200ma":
            return self
        total_ratio = self.daily_base_tqqq_ratio + self.daily_base_one_x_ratio
        if abs(total_ratio - 100) > 0.01:
            raise ValueError("일일 적립 규칙의 TQQQ와 1x 비중 합계는 100이어야 합니다.")
        return self


class AdoptResearchRequest(BaseModel):
    research_config: ResearchStrategyConfig
    market: MarketSnapshot
    tqqq_value: float = Field(default=0, ge=0)
    one_x_value: float = Field(default=0, ge=0)
    cash_value: float = Field(default=0, ge=0)
    selected_reason: str = ""
    source_total_score: int | None = None
    source_cagr: float | None = None
    source_max_drawdown: float | None = None


TodayRegime = Literal["above", "below_unconfirmed", "defense"]
TodayAction = Literal[
    "accumulate",
    "accumulate_decelerated",
    "stop_new_tqqq",
    "hold_below_unconfirmed",
    "defense_sell",
    "hold_defense",
]


class TodayDecision(BaseModel):
    as_of: str
    data_age_days: int
    qqq_close: float
    qqq_sma200: float
    distance_pct: float
    exit_line: float
    regime: TodayRegime
    below_ma_days: int
    tier: int
    tier_label: str
    action: TodayAction
    headline: str
    instructions: list[str]
    daily_budget: float
    tqqq_buy_amount: float
    one_x_buy_amount: float
    tqqq_buy_ratio_pct: float
    one_x_buy_ratio_pct: float
    redeploy_active: bool
    redeploy_day: int
    defense_mode: DefenseMode
    checklist: list[str]


class DepositRequest(BaseModel):
    """A salary-day cash deposit into the strategy (research strategies).

    The rules decide how the money deploys (daily split, deceleration); the
    deposit only grows the cash sleeve and leaves an auditable record.
    """

    amount: float = Field(gt=0, le=100_000_000)
    note: str = ""


class ManagedStrategyCreate(BaseModel):
    plan: StrategyPlan
    market: MarketSnapshot
    total_capital: float = Field(ge=0)
    selected_reason: str = ""
    research_config: ResearchStrategyConfig | None = None


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
