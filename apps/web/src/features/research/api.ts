import { API_BASE_URL as apiBaseUrl } from "../../lib/api";
import { authenticatedFetch } from "../../lib/authApi";
import type {
  BacktestStrategy,
  CompareConfig,
  HeatmapReport,
  InsightReport,
  MonteCarloReport,
  OverfittingReport,
  StrategyCompareResponse,
  StrategyRankItem,
  WalkForwardReport
} from "./types";

export async function requestCompare(payload: CompareConfig & { strategies: BacktestStrategy[] }) {
  const body = {
    ...payload,
    start_date: payload.start_date || null,
    end_date: payload.end_date || null,
    defense_mode: payload.defense_mode || null
  };
  const response = await fetch(`${apiBaseUrl}/compare/strategies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) throw new Error(`전략 비교 API 오류: ${response.status}`);
  return (await response.json()) as StrategyCompareResponse;
}

export async function requestOverfitting(): Promise<OverfittingReport> {
  const response = await fetch(`${apiBaseUrl}/research/overfitting`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  });
  if (!response.ok) throw new Error(`과최적화 API 오류: ${response.status}`);
  return (await response.json()) as OverfittingReport;
}

export async function requestHeatmap(): Promise<HeatmapReport> {
  const response = await fetch(`${apiBaseUrl}/research/heatmap`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  });
  if (!response.ok) throw new Error(`히트맵 API 오류: ${response.status}`);
  return (await response.json()) as HeatmapReport;
}

export async function requestWalkForward(): Promise<WalkForwardReport> {
  const response = await fetch(`${apiBaseUrl}/research/walkforward`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  });
  if (!response.ok) throw new Error(`워크포워드 API 오류: ${response.status}`);
  return (await response.json()) as WalkForwardReport;
}

export async function requestMonteCarlo(
  config: CompareConfig,
  nPaths: number
): Promise<MonteCarloReport> {
  const body = {
    strategy: "tqqq_daily_200ma",
    daily_base_tqqq_ratio: config.daily_base_tqqq_ratio,
    daily_base_one_x_ratio: config.daily_base_one_x_ratio,
    one_x_symbol: config.one_x_symbol,
    ma_exit_band_pct: config.ma_exit_band_pct,
    defense_mode: config.defense_mode || "cash",
    one_x_upfront_monthly: config.one_x_upfront_monthly,
    monthly_contribution: config.monthly_contribution,
    initial_capital: config.initial_capital,
    initial_tqqq_value: config.initial_tqqq_value,
    initial_qld_value: config.initial_qld_value ?? 0,
    initial_one_x_value: config.initial_one_x_value,
    initial_cash_value: config.initial_cash_value,
    cash_yield: config.cash_yield,
    n_paths: nPaths,
    years: 26
  };
  const response = await fetch(`${apiBaseUrl}/research/montecarlo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) throw new Error(`몬테카를로 API 오류: ${response.status}`);
  return (await response.json()) as MonteCarloReport;
}

export const ADOPTABLE: BacktestStrategy[] = ["tqqq_daily_200ma", "qld_daily_200ma", "tqqq_200ma", "qld_200ma"];

export async function requestAdopt(
  config: CompareConfig,
  item: StrategyRankItem
): Promise<{ id: string }> {
  const historyResponse = await fetch(`${apiBaseUrl}/market/history/QQQ?limit=1200`);
  if (!historyResponse.ok) throw new Error(`QQQ 지표 조회 실패: ${historyResponse.status}`);
  const history = (await historyResponse.json()) as {
    latest: { date: string; close: number };
    sma20?: number | null;
    sma50?: number | null;
    sma200?: number | null;
    high20?: number | null;
  };
  if (!history.sma200) throw new Error("QQQ 200일선 데이터를 계산할 수 없습니다.");
  const defenseMode =
    config.defense_mode || (item.strategy.endsWith("daily_200ma") ? "hold_one_x" : "cash");
  const body = {
    research_config: {
      strategy: item.strategy,
      daily_leveraged_symbol: item.strategy === "qld_daily_200ma" ? "QLD" : "TQQQ",
      daily_base_tqqq_ratio: config.daily_base_tqqq_ratio,
      daily_base_one_x_ratio: config.daily_base_one_x_ratio,
      one_x_symbol: config.one_x_symbol,
      ma_exit_band_pct: config.ma_exit_band_pct,
      defense_mode: defenseMode,
      one_x_upfront_monthly: config.one_x_upfront_monthly,
      monthly_contribution: config.monthly_contribution,
      moving_average_days: config.moving_average_days,
      tqqq_target_ratio: config.tqqq_target_ratio,
      qld_target_ratio: config.qld_target_ratio
    },
    market: {
      qqq_close: history.latest.close,
      qqq_sma200: history.sma200,
      qqq_sma20: history.sma20 ?? null,
      qqq_sma50: history.sma50 ?? null,
      qqq_high20: history.high20 ?? null,
      as_of: history.latest.date
    },
    tqqq_value: config.initial_tqqq_value,
    qld_value: item.strategy === "qld_daily_200ma" ? config.initial_tqqq_value : (config.initial_qld_value ?? 0),
    one_x_value: config.initial_one_x_value,
    cash_value: config.initial_cash_value,
    selected_reason: `개인연구 전략 비교에서 채택 (${item.strategy_name})`,
    source_total_score: item.total_score,
    source_cagr: item.cagr,
    source_max_drawdown: item.max_drawdown
  };
  const response = await authenticatedFetch(`${apiBaseUrl}/managed-strategies/adopt-research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) throw new Error(`전략 채택 실패: ${response.status}`);
  return (await response.json()) as { id: string };
}

export async function requestInsight(payload: StrategyCompareResponse, useAi: boolean) {
  const response = await fetch(`${apiBaseUrl}/insights/interpret`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ context: "daily_accumulation_research", payload, use_ai: useAi })
  });
  if (!response.ok) throw new Error(`해석 리포트 API 오류: ${response.status}`);
  return (await response.json()) as InsightReport;
}
