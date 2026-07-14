import { API_BASE_URL as apiBaseUrl } from "../../lib/api";
import { authenticatedFetch } from "../../lib/authApi";
import type {
  FxSnapshot,
  HoldingInput,
  InvestorProfile,
  MarketSnapshot,
  PriceRow,
  QuoteSnapshot,
  StrategyPlan,
  StrategyResponse
} from "./types";

export async function fetchHistory(symbol: string): Promise<PriceRow[]> {
  const response = await fetch(`${apiBaseUrl}/market/history/${symbol}?limit=1200`);
  if (!response.ok) throw new Error(`시장 데이터 API 오류: ${response.status}`);
  return ((await response.json()) as { rows: PriceRow[] }).rows;
}
export async function fetchQuote(symbol: string): Promise<QuoteSnapshot> {
  const response = await fetch(`${apiBaseUrl}/market/quote/${symbol}`);
  if (!response.ok) throw new Error(`시세 API 오류: ${response.status}`);
  return (await response.json()) as QuoteSnapshot;
}
export async function fetchUsdKrw(): Promise<FxSnapshot> {
  const response = await fetch(`${apiBaseUrl}/market/fx/usd-krw`);
  if (!response.ok) throw new Error(`환율 API 오류: ${response.status}`);
  return (await response.json()) as FxSnapshot;
}
export async function requestRecommendation(
  holdings: HoldingInput[],
  cash: number,
  profile: InvestorProfile,
  market: MarketSnapshot,
  useAi: boolean
) {
  const response = await fetch(`${apiBaseUrl}/strategy/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ holdings, cash, profile, market, use_ai: useAi })
  });
  if (!response.ok) throw new Error(`전략 추천 API 오류: ${response.status}`);
  return (await response.json()) as StrategyResponse;
}
export async function adoptManagedStrategy(
  plan: StrategyPlan,
  market: MarketSnapshot,
  totalCapital: number
) {
  const response = await authenticatedFetch(`${apiBaseUrl}/managed-strategies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      plan,
      market,
      total_capital: totalCapital,
      selected_reason: `${plan.title}을 현재 리스크 성향과 QQQ 200일선 기준 운용 전략으로 채택했습니다.`
    })
  });
  if (!response.ok) throw new Error(`전략 채택 API 오류: ${response.status}`);
}
