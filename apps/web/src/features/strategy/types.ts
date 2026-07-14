export type PriceRow = { date: string; close: number };

export type ScoreLevel = "low" | "medium" | "high" | "very_high";

export type HoldingInput = { symbol: string; name: string; amount: number; category: string };

export type InvestorProfile = {
  risk_profile: "defensive" | "balanced" | "aggressive" | "very_aggressive";
  risk_score: number;
  target_count: number;
  allow_tqqq: boolean;
  prefer_200ma: boolean;
  min_cash_ratio: number;
  max_tqqq_ratio: number;
  max_semiconductor_ratio: number;
  max_single_position_ratio: number;
  goal: string;
};

export type MarketSnapshot = {
  qqq_close: number;
  qqq_sma200: number;
  qqq_sma20?: number | null;
  qqq_sma50?: number | null;
  qqq_high20?: number | null;
  qqq_rsi14?: number | null;
  as_of: string;
};

export type QuoteSnapshot = { symbol: string; price: number; as_of: string; freshness: string };

export type FxSnapshot = { rate: number; as_of: string; freshness: string };

export type Allocation = {
  symbol: string;
  name: string;
  target_ratio: number;
  target_amount: number;
  role: string;
};

export type TradeAction = {
  symbol: string;
  action: "buy" | "sell" | "hold" | "wait";
  amount: number;
  reason: string;
};

export type SplitStep = {
  step: string;
  trigger: string;
  ratio_of_target: number;
  amount: number;
  note: string;
};

export type RiskMetric = { label: string; value: string; level: ScoreLevel };

export type StrategyScores = {
  confidence_score: number;
  risk_score: number;
  fit_score: number;
  expected_return_score: number;
  execution_difficulty: ScoreLevel;
  confidence_notes: string[];
};

export type CandidateOpinion = {
  symbol: string;
  name: string;
  stance: "core" | "satellite" | "defense" | "avoid" | "watch";
  reason: string;
};

export type StrategyPlan = {
  id: string;
  title: string;
  summary: string;
  allocations: Allocation[];
  actions: TradeAction[];
  buy_plan: SplitStep[];
  sell_plan: SplitStep[];
  risk_metrics: RiskMetric[];
  scores: StrategyScores;
  pros: string[];
  cons: string[];
};

export type StrategyResponse = {
  total_capital: number;
  market_regime: string;
  qqq_distance_from_200ma: number;
  current_diagnosis: string[];
  candidate_opinions: CandidateOpinion[];
  plans: StrategyPlan[];
  coach_report: {
    headline: string;
    diagnosis: string;
    recommended_plan_id: string;
    why: string[];
    next_actions: string[];
    warnings: string[];
    monitoring_rules: string[];
  };
  ai_used: boolean;
};

export type CandidateAsset = { symbol: string; name: string; category: string; role: string };
