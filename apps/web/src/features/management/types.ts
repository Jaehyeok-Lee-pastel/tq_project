export type Allocation = {
  symbol: string;
  name: string;
  target_ratio: number;
  target_amount: number;
  role: string;
};
export type SplitStep = {
  step: string;
  trigger: string;
  ratio_of_target: number;
  amount: number;
  note: string;
};
export type ExecutionStep = {
  side: "buy" | "sell";
  step: string;
  symbol: string;
  status: "ready" | "wait" | "blocked" | "done";
  trigger: string;
  trigger_price?: number | null;
  trigger_label?: string;
  current_price?: number | null;
  distance_to_trigger_pct?: number | null;
  amount: number;
  ratio_of_target: number;
  reason: string;
  action_label: string;
};
export type ResearchConfig = {
  strategy: "qqq_buy_hold" | "tqqq_buy_hold" | "tqqq_200ma" | "qld_200ma" | "tqqq_daily_200ma";
  daily_base_tqqq_ratio: number;
  daily_base_one_x_ratio: number;
  one_x_symbol: string;
  ma_exit_band_pct: number;
  defense_mode: "cash" | "spym_sgov_half" | "hold_one_x";
  monthly_contribution: number;
  moving_average_days: number;
  one_x_upfront_monthly?: boolean;
};
export type TodayDecision = {
  as_of: string;
  data_age_days: number;
  qqq_close: number;
  qqq_sma200: number;
  distance_pct: number;
  exit_line: number;
  regime: "above" | "below_unconfirmed" | "defense";
  below_ma_days: number;
  tier: number;
  tier_label: string;
  action:
    | "accumulate"
    | "accumulate_decelerated"
    | "stop_new_tqqq"
    | "hold_below_unconfirmed"
    | "defense_sell"
    | "hold_defense";
  headline: string;
  instructions: string[];
  daily_budget: number;
  tqqq_buy_amount: number;
  one_x_buy_amount: number;
  tqqq_buy_ratio_pct: number;
  one_x_buy_ratio_pct: number;
  redeploy_active: boolean;
  redeploy_day: number;
  defense_mode: "cash" | "spym_sgov_half" | "hold_one_x";
  checklist: string[];
};
export type JournalEntry = {
  id: string;
  created_at: string;
  entry_type:
    | "buy"
    | "sell"
    | "hold"
    | "rebalance"
    | "review"
    | "rule_check"
    | "note"
    | "deposit"
    | "fx"
    | "cash_transfer";
  symbol: string;
  amount: number;
  quantity: number;
  price: number;
  reason: string;
  mood: string;
  note: string;
  qqq_distance_from_200ma: number;
};
export type ManagedStrategy = {
  id: string;
  status: "active" | "paused" | "archived";
  created_at: string;
  updated_at: string;
  version: number;
  selected_reason: string;
  total_capital: number;
  research_config?: ResearchConfig | null;
  market: {
    qqq_close: number;
    qqq_sma200: number;
    qqq_sma20?: number | null;
    qqq_sma50?: number | null;
    qqq_high20?: number | null;
    as_of: string;
  };
  plan: {
    id: string;
    title: string;
    summary: string;
    allocations: Allocation[];
    buy_plan: SplitStep[];
    sell_plan: SplitStep[];
    pros: string[];
    cons: string[];
  };
  journal: JournalEntry[];
  version_history: {
    version: number;
    created_at: string;
    change_type: "created" | "adjustment" | "manual" | "philosophy";
    title: string;
    note: string;
    before_allocations: { symbol: string; ratio: number }[];
    after_allocations: { symbol: string; ratio: number }[];
  }[];
};
export type ManagedGuide = {
  strategy: ManagedStrategy;
  compliance_score: number;
  current_action: string;
  checklist: string[];
  next_review: string;
  issues: { level: "ok" | "watch" | "danger"; title: string; detail: string }[];
  execution_plan: ExecutionStep[];
};
export type AdjustmentAdvice = {
  verdict: "ok" | "watch" | "danger";
  headline: string;
  summary: string;
  current_cash_ratio: number;
  target_cash_ratio: number;
  minimum_cash_ratio: number;
  qqq_distance_from_200ma: number;
  suggested_allocations: {
    symbol: string;
    current_ratio: number;
    suggested_ratio: number;
    delta_ratio: number;
    reason: string;
  }[];
  issues: string[];
  actions: string[];
};
export type ContributionAllocation = {
  symbol: string;
  role: string;
  current_amount: number;
  target_amount_after: number;
  gap_amount: number;
  suggested_amount: number;
  action: "buy" | "wait" | "hold" | "rebalance";
  reason: string;
};
export type ContributionPlanOption = {
  id: string;
  title: string;
  risk_level: "defensive" | "balanced" | "aggressive";
  recommendation_score: number;
  headline: string;
  summary: string;
  contribution_amount: number;
  pay_day: number;
  current_total_capital: number;
  new_total_capital: number;
  qqq_distance_from_200ma: number;
  available_cash_after_deposit: number;
  actions: string[];
  allocations: ContributionAllocation[];
};
export type ContributionAdvice = {
  headline: string;
  summary: string;
  contribution_amount: number;
  pay_day: number;
  current_total_capital: number;
  new_total_capital: number;
  qqq_distance_from_200ma: number;
  available_cash_after_deposit: number;
  actions: string[];
  allocations: ContributionAllocation[];
  recommended_plan_id: string;
  plans: ContributionPlanOption[];
};
export type PhilosophyUpgradeAdvice = {
  verdict: "up_to_date" | "update_recommended" | "major_change";
  headline: string;
  summary: string;
  qqq_distance_from_200ma: number;
  inferred_risk_score: number;
  current_plan_title: string;
  suggested_plan_id: string;
  suggested_plan_title: string;
  suggested_plan_summary: string;
  allocation_diffs: {
    symbol: string;
    current_ratio: number;
    suggested_ratio: number;
    delta_ratio: number;
    reason: string;
  }[];
  changes: string[];
  cautions: string[];
};
export type FxRate = {
  pair: string;
  provider: string;
  rate: number;
  as_of: string;
  freshness: string;
  source_note: string;
};
export type QuoteResponse = {
  symbol: string;
  provider: string;
  price: number;
  as_of: string;
  freshness: string;
  source_note: string;
};
export type PriceRow = { date: string; close: number };
export type HistoryResponse = {
  symbol: string;
  provider: string;
  rows: PriceRow[];
  latest: PriceRow;
  sma20?: number | null;
  sma50?: number | null;
  sma200?: number | null;
  high20?: number | null;
};
export type DataReliabilityItem = {
  symbol: string;
  provider: string;
  latest_date: string;
  age_days: number;
  row_count: number;
  has_sma20: boolean;
  has_sma50: boolean;
  has_sma200: boolean;
  score: number;
  status: "ok" | "watch" | "danger";
  message: string;
};
export type DataReliabilityResponse = {
  provider: string;
  checked_at: string;
  items: DataReliabilityItem[];
};
export type BacktestStrategy = "qqq_buy_hold" | "tqqq_buy_hold" | "tqqq_200ma" | "qld_200ma";
export type ManageTab = "overview" | "journal" | "strategy";
export type UserSettings = {
  targetCashRatio: number;
  monthlyContribution: number;
  payDay: number;
  usdKrwRate: number;
};
