export type BacktestStrategy =
  | "qqq_buy_hold"
  | "tqqq_buy_hold"
  | "tqqq_200ma"
  | "qld_200ma"
  | "tqqq_daily_200ma";

export type Verdict = "best_fit" | "high_return" | "defensive" | "too_risky" | "watch";

export type StrategyRankItem = {
  rank: number;
  strategy: BacktestStrategy;
  strategy_name: string;
  final_capital: number;
  total_return: number;
  cagr: number;
  max_drawdown: number;
  sharpe?: number | null;
  trade_count: number;
  profit_score: number;
  defense_score: number;
  fit_score: number;
  consistency_score: number;
  execution_score: number;
  decisions_per_year: number;
  total_score: number;
  verdict: Verdict;
  reason: string;
};

export type EquityPoint = { date: string; equity: number; drawdown: number; position: string };

export type TradeLogItem = {
  date: string;
  action: "buy" | "sell";
  symbol: string;
  ratio: number;
  reason: string;
};

export type YearlyReturn = { year: number; return_pct: number };

export type RegimePerformance = {
  regime: "uptrend" | "downtrend" | "shock";
  label: string;
  days: number;
  return_pct: number;
  win_rate: number;
  max_drawdown: number;
};

export type BacktestMetrics = {
  final_capital: number;
  total_return: number;
  cagr: number;
  max_drawdown: number;
  sharpe?: number | null;
  sortino?: number | null;
  calmar?: number | null;
  win_rate: number;
  trade_count: number;
  best_year?: number | null;
  worst_year?: number | null;
  longest_drawdown_days: number;
};

export type BacktestResult = {
  strategy: BacktestStrategy;
  strategy_name: string;
  period_start: string;
  period_end: string;
  equity_curve: EquityPoint[];
  benchmark_curve: EquityPoint[];
  metrics: BacktestMetrics;
  benchmark_metrics: BacktestMetrics;
  yearly_returns: YearlyReturn[];
  regime_performance: RegimePerformance[];
  trades: TradeLogItem[];
  interpretation: string[];
  data_notes?: string[];
};

export type RuleVariationItem = {
  label: string;
  cagr: number;
  max_drawdown: number;
  total_score: number;
};

export type RuleRobustnessSummary = {
  strategy: BacktestStrategy;
  strategy_name: string;
  baseline_cagr: number;
  baseline_max_drawdown: number;
  cagr_range: number;
  mdd_range: number;
  robustness_score: number;
  verdict: string;
  note: string;
  results: RuleVariationItem[];
};

export type StrategyCompareResponse = {
  initial_capital: number;
  risk_score: number;
  recommended_strategy: BacktestStrategy;
  summary: string;
  rankings: StrategyRankItem[];
  backtests: BacktestResult[];
  sensitivity?: {
    best_window: number;
    robustness_score: number;
    verdict: string;
    results: {
      strategy: BacktestStrategy;
      strategy_name: string;
      moving_average_days: number;
      cagr: number;
      max_drawdown: number;
      total_score: number;
    }[];
  } | null;
  rule_robustness?: RuleRobustnessSummary | null;
};

export type InsightReport = {
  headline: string;
  confidence_level: "low" | "medium" | "high";
  summary: string;
  strongest_evidence: string[];
  main_risks: string[];
  recommended_next_steps: string[];
  ai_used: boolean;
};

export type CompareConfig = {
  start_date: string;
  end_date: string;
  initial_capital: number;
  initial_tqqq_value: number;
  initial_one_x_value: number;
  initial_cash_value: number;
  risk_score: number;
  tqqq_target_ratio: number;
  qld_target_ratio: number;
  one_x_target_ratio: number;
  one_x_symbol: string;
  cash_yield: number;
  moving_average_days: number;
  include_default_tqqq_comparison: boolean;
  default_tqqq_target_ratio: number;
  monthly_contribution: number;
  daily_base_tqqq_ratio: number;
  daily_base_one_x_ratio: number;
  ma_exit_band_pct: number;
  defense_mode: "" | "cash" | "spym_sgov_half" | "hold_one_x";
  reserve_redeploy_days: number;
  one_x_upfront_monthly: boolean;
};

export type StrategyLabTransfer = {
  source: "strategy_recommendation";
  plan_title: string;
  execution_style: "daily" | "staged";
  fidelity: "exact" | "proxy";
  config: Partial<CompareConfig>;
  selected: BacktestStrategy[];
};

export type Percentiles = {
  p5: number;
  p25: number;
  median: number;
  p75: number;
  p95: number;
  mean: number;
};

export type MonteCarloReport = {
  n_paths: number;
  years: number;
  seed: number;
  regime_summary: {
    regime: string;
    label: string;
    day_share_pct: number;
    ann_return_pct: number;
    ann_vol_pct: number;
  }[];
  cagr: Percentiles;
  max_drawdown: Percentiles;
  final_multiple: Percentiles;
  benchmark_cagr: Percentiles;
  prob_cagr_positive: number;
  prob_beat_benchmark: number;
  prob_mdd_worse_than_60: number;
  prob_mdd_worse_than_70: number;
  sample_paths: { kind: string; points: number[] }[];
  headline: string;
  notes: string[];
};

export type WalkForwardWindow = {
  index: number;
  oos_start: string;
  oos_end: string;
  selected_label: string;
  is_score: number;
  is_cagr: number;
  oos_cagr: number;
  oos_mdd: number;
  oos_beat_benchmark: boolean;
  benchmark_oos_cagr: number;
  fixed_oos_cagr: number;
  fixed_oos_mdd: number;
};

export type WalkForwardReport = {
  windows: WalkForwardWindow[];
  fixed_label: string;
  walk_forward_efficiency_pct: number;
  selection_stability_pct: number;
  modal_config: string;
  oos_beat_benchmark_pct: number;
  adaptive_oos_cagr_median: number;
  fixed_oos_cagr_median: number;
  adaptive_compound_oos_cagr: number;
  adaptive_worst_oos_mdd: number;
  fixed_compound_oos_cagr: number;
  fixed_worst_oos_mdd: number;
  headline: string;
  notes: string[];
};

export type HeatmapCell = {
  ratio: number;
  band: number;
  cagr: number;
  mdd: number;
  score: number;
  is_adopted: boolean;
  is_best: boolean;
};

export type HeatmapReport = {
  ratios: number[];
  bands: number[];
  cells: HeatmapCell[];
  adopted_ratio: number;
  adopted_band: number;
  adopted_score: number;
  adopted_rank: number;
  total_cells: number;
  best_score: number;
  best_label: string;
  neighbor_score_spread: number;
  global_score_spread: number;
  plateau_ratio_pct: number;
  verdict: string;
  headline: string;
  notes: string[];
};

export type OverfittingReport = {
  n_trials: number;
  correction_trials: number;
  sample_days: number;
  adopted_label: string;
  observed_sharpe: number;
  deflated_benchmark_sharpe: number;
  deflated_sharpe_ratio: number;
  skew: number;
  kurtosis: number;
  pbo: number;
  cscv_splits: number;
  dsr_verdict: string;
  pbo_verdict: string;
  headline: string;
  notes: string[];
};
