import { useEffect, useMemo, useState } from "react";
import {
  Bot,
  BrainCircuit,
  CheckCircle2,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Target,
  Trash2,
} from "lucide-react";
import { supabase } from "../lib/supabase";

type PriceRow = { date: string; close: number };
type ScoreLevel = "low" | "medium" | "high" | "very_high";
type HoldingInput = { symbol: string; name: string; amount: number; category: string };
type InvestorProfile = {
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
type MarketSnapshot = {
  qqq_close: number;
  qqq_sma200: number;
  qqq_sma20?: number | null;
  qqq_sma50?: number | null;
  qqq_high20?: number | null;
  qqq_rsi14?: number | null;
  as_of: string;
};
type Allocation = { symbol: string; name: string; target_ratio: number; target_amount: number; role: string };
type TradeAction = { symbol: string; action: "buy" | "sell" | "hold" | "wait"; amount: number; reason: string };
type SplitStep = { step: string; trigger: string; ratio_of_target: number; amount: number; note: string };
type RiskMetric = { label: string; value: string; level: ScoreLevel };
type StrategyScores = {
  confidence_score: number;
  risk_score: number;
  fit_score: number;
  expected_return_score: number;
  execution_difficulty: ScoreLevel;
  confidence_notes: string[];
};
type CandidateOpinion = {
  symbol: string;
  name: string;
  stance: "core" | "satellite" | "defense" | "avoid" | "watch";
  reason: string;
};
type StrategyPlan = {
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
type StrategyResponse = {
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
type CandidateAsset = { symbol: string; name: string; category: string; role: string };

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const candidateAssets: CandidateAsset[] = [
  { symbol: "TQQQ", name: "ProShares UltraPro QQQ", category: "nasdaq_leverage", role: "공격 엔진" },
  { symbol: "QLD", name: "ProShares Ultra QQQ", category: "nasdaq_leverage", role: "완충형 레버리지" },
  { symbol: "QQQ", name: "Invesco QQQ Trust", category: "nasdaq", role: "나스닥 기준 자산" },
  { symbol: "SMH", name: "VanEck Semiconductor ETF", category: "semiconductor", role: "미국 반도체 위성" },
  { symbol: "SOXX", name: "iShares Semiconductor ETF", category: "semiconductor", role: "반도체 위성" },
  { symbol: "ACE K반도체TOP2", name: "ACE K반도체TOP2", category: "semiconductor", role: "한국 반도체 집중" },
  { symbol: "VOO", name: "Vanguard S&P 500 ETF", category: "broad_market", role: "광범위 지수 완충" },
  { symbol: "SGOV", name: "iShares 0-3 Month Treasury Bond ETF", category: "cash_like", role: "현금성 대기" },
  { symbol: "BIL", name: "SPDR Bloomberg 1-3 Month T-Bill ETF", category: "cash_like", role: "분할매수 대기" },
  { symbol: "SHY", name: "iShares 1-3 Year Treasury Bond ETF", category: "short_bond", role: "단기채 완충" },
  { symbol: "IEF", name: "iShares 7-10 Year Treasury Bond ETF", category: "intermediate_bond", role: "중기채 완충" },
  { symbol: "TLT", name: "iShares 20+ Year Treasury Bond ETF", category: "long_bond", role: "장기채 위성" },
];

const defaultHoldings: HoldingInput[] = [];
const exampleQuickInput = "QLD 150만원, ACE K반도체TOP2 100만원";
const defaultProfile: InvestorProfile = {
  risk_profile: "aggressive",
  risk_score: 75,
  target_count: 3,
  allow_tqqq: true,
  prefer_200ma: true,
  min_cash_ratio: 20,
  max_tqqq_ratio: 50,
  max_semiconductor_ratio: 15,
  max_single_position_ratio: 60,
  goal: "작은 시드에서 2~3개에 집중하되 TQQQ를 포함한 공격형 전략을 원합니다.",
};

function formatKrw(value: number) {
  return `${Math.round(value).toLocaleString("ko-KR")}원`;
}
function formatUsd(value: number) {
  return `$${value.toFixed(2)}`;
}
function formatPct(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}
function sma(rows: PriceRow[], length: number) {
  if (rows.length < length) return null;
  return rows.slice(-length).reduce((sum, row) => sum + row.close, 0) / length;
}
function rollingHigh(rows: PriceRow[], length: number) {
  if (rows.length < length) return null;
  return Math.max(...rows.slice(-length).map((row) => row.close));
}
function riskBand(score: number) {
  if (score <= 20) return "방어형";
  if (score <= 40) return "안정 성장형";
  if (score <= 60) return "균형형";
  if (score <= 80) return "공격형";
  return "초공격형";
}
function riskProfileKind(score: number): InvestorProfile["risk_profile"] {
  if (score <= 30) return "defensive";
  if (score <= 60) return "balanced";
  if (score <= 82) return "aggressive";
  return "very_aggressive";
}
function recommendedProfile(score: number): Pick<
  InvestorProfile,
  "risk_profile" | "target_count" | "min_cash_ratio" | "max_tqqq_ratio" | "max_semiconductor_ratio" | "max_single_position_ratio"
> {
  if (score <= 30) {
    return {
      risk_profile: "defensive",
      target_count: 4,
      min_cash_ratio: 40,
      max_tqqq_ratio: 0,
      max_semiconductor_ratio: 0,
      max_single_position_ratio: 45,
    };
  }
  if (score <= 55) {
    return {
      risk_profile: "balanced",
      target_count: 3,
      min_cash_ratio: 30,
      max_tqqq_ratio: 12,
      max_semiconductor_ratio: 6,
      max_single_position_ratio: 50,
    };
  }
  if (score <= 75) {
    return {
      risk_profile: "aggressive",
      target_count: 3,
      min_cash_ratio: 22,
      max_tqqq_ratio: 28,
      max_semiconductor_ratio: 10,
      max_single_position_ratio: 55,
    };
  }
  if (score <= 90) {
    return {
      risk_profile: "very_aggressive",
      target_count: 3,
      min_cash_ratio: 16,
      max_tqqq_ratio: 40,
      max_semiconductor_ratio: 15,
      max_single_position_ratio: 60,
    };
  }
  return {
    risk_profile: "very_aggressive",
    target_count: 2,
    min_cash_ratio: 12,
    max_tqqq_ratio: 45,
    max_semiconductor_ratio: 18,
    max_single_position_ratio: 65,
  };
}
function profileRecommendationText(score: number) {
  if (score <= 30) return "TQQQ는 보류하고 SGOV/BIL/VOO 중심으로 방어력을 먼저 둡니다.";
  if (score <= 55) return "소량 TQQQ만 허용하고 QQQ/SPYM/현금성 자산으로 변동성을 낮춥니다.";
  if (score <= 75) return "TQQQ를 분할 진입하되 현금성 대기자금과 SPYM 완충을 함께 둡니다.";
  if (score <= 90) return "TQQQ를 공격적으로 쓰되 QQQ 신호, SPYM, 현금성 자산을 필수 안전장치로 둡니다.";
  return "초공격형이지만 TQQQ 상한과 최소 현금은 남겨 급락 시 재진입 여력을 보존합니다.";
}
function normalizeSymbol(rawSymbol: string) {
  const compact = rawSymbol.trim().toUpperCase().replace(/\s+/g, "");
  const aliases: Record<string, string> = {
    ACEK반도체TOP2: "ACE K반도체TOP2",
    K반도체TOP2: "ACE K반도체TOP2",
    SOLTOP2: "ACE K반도체TOP2",
    현금: "CASH",
    단기채: "SGOV",
    중기채: "IEF",
    장기채: "TLT",
  };
  return aliases[compact] ?? rawSymbol.trim().toUpperCase();
}
function findCandidate(rawSymbol: string) {
  const normalized = normalizeSymbol(rawSymbol);
  return candidateAssets.find((asset) => asset.symbol.toUpperCase() === normalized.toUpperCase());
}
function parseAmount(text: string) {
  const trimmed = text.replace(/,/g, "").trim();
  const value = Number(trimmed.match(/[\d.]+/)?.[0] ?? 0);
  if (!value) return 0;
  if (trimmed.includes("만원")) return value * 10000;
  if (trimmed.includes("천원")) return value * 1000;
  return value;
}
function parseQuickHoldings(text: string) {
  return text
    .split(/[,;\n]+/)
    .map((chunk) => chunk.trim())
    .filter(Boolean)
    .map((chunk) => {
      const amountText = chunk.match(/[\d,.]+\s*(만원|천원|원)?/)?.[0] ?? "";
      const symbolText = chunk.replace(amountText, "").trim();
      const candidate = findCandidate(symbolText);
      const symbol = candidate?.symbol ?? normalizeSymbol(symbolText);
      return { symbol, name: candidate?.name ?? symbol, amount: parseAmount(amountText), category: candidate?.category ?? "other" };
    })
    .filter((holding) => holding.symbol && holding.amount > 0);
}
async function fetchHistory(symbol: string): Promise<PriceRow[]> {
  const response = await fetch(`${apiBaseUrl}/market/history/${symbol}?limit=1200`);
  if (!response.ok) throw new Error(`시장 데이터 API 오류: ${response.status}`);
  return ((await response.json()) as { rows: PriceRow[] }).rows;
}
async function requestRecommendation(
  holdings: HoldingInput[],
  cash: number,
  profile: InvestorProfile,
  market: MarketSnapshot,
  useAi: boolean,
) {
  const response = await fetch(`${apiBaseUrl}/strategy/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ holdings, cash, profile, market, use_ai: useAi }),
  });
  if (!response.ok) throw new Error(`전략 추천 API 오류: ${response.status}`);
  return (await response.json()) as StrategyResponse;
}
async function adoptManagedStrategy(plan: StrategyPlan, market: MarketSnapshot, totalCapital: number) {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  const response = await fetch(`${apiBaseUrl}/managed-strategies`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({
      plan,
      market,
      total_capital: totalCapital,
      selected_reason: `${plan.title}을 현재 리스크 성향과 QQQ 200일선 기준 운용 전략으로 채택했습니다.`,
    }),
  });
  if (!response.ok) throw new Error(`전략 채택 API 오류: ${response.status}`);
}
function actionLabel(action: TradeAction["action"]) {
  return { buy: "매수", sell: "매도", hold: "유지", wait: "대기" }[action];
}
function stanceLabel(stance: CandidateOpinion["stance"]) {
  return { core: "핵심", satellite: "위성", defense: "방어", avoid: "제외", watch: "관찰" }[stance];
}

export function StrategyPage() {
  const [holdings, setHoldings] = useState<HoldingInput[]>(defaultHoldings);
  const [quickInput, setQuickInput] = useState("");
  const [cash, setCash] = useState(0);
  const [profile, setProfile] = useState<InvestorProfile>(defaultProfile);
  const [market, setMarket] = useState<MarketSnapshot>({ qqq_close: 736.4, qqq_sma200: 633.63, qqq_sma20: 720.18, qqq_sma50: 706.22, qqq_high20: 736.4, as_of: "2026-06-30" });
  const [recommendation, setRecommendation] = useState<StrategyResponse | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [useAi, setUseAi] = useState(true);
  const [loading, setLoading] = useState<"market" | "strategy" | "adopt" | "">("");
  const [status, setStatus] = useState("포트폴리오와 리스크 점수를 입력한 뒤 전략을 추천받으세요.");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showCandidates, setShowCandidates] = useState(false);

  const totalCapital = useMemo(() => cash + holdings.reduce((sum, holding) => sum + holding.amount, 0), [cash, holdings]);
  const selectedPlan = recommendation?.plans.find((plan) => plan.id === selectedPlanId) ?? recommendation?.plans[0];
  const recommendedRiskProfile = useMemo(() => recommendedProfile(profile.risk_score), [profile.risk_score]);

  useEffect(() => {
    if (recommendation?.plans[0]) setSelectedPlanId(recommendation.plans[0].id);
  }, [recommendation]);

  function applyQuickInput() {
    const parsed = parseQuickHoldings(quickInput);
    if (!parsed.length) {
      setStatus("예: QLD 150만원, ACE K반도체TOP2 100만원");
      return;
    }
    setHoldings(parsed);
    setStatus(`${parsed.length}개 보유 종목을 반영했습니다.`);
  }
  function updateHolding(index: number, patch: Partial<HoldingInput>) {
    setHoldings((current) => current.map((holding, idx) => (idx === index ? { ...holding, ...patch } : holding)));
  }
  function addHolding(candidate?: CandidateAsset) {
    setHoldings((current) => [...current, { symbol: candidate?.symbol ?? "", name: candidate?.name ?? "", amount: 0, category: candidate?.category ?? "other" }]);
  }
  function applyRecommendedProfile() {
    const recommended = recommendedProfile(profile.risk_score);
    setProfile((current) => ({
      ...current,
      ...recommended,
      risk_score: current.risk_score,
      risk_profile: riskProfileKind(current.risk_score),
      allow_tqqq: current.risk_score >= 45,
      prefer_200ma: true,
    }));
    setStatus(`리스크 ${profile.risk_score}점 기준 권장값을 적용했습니다. ${profileRecommendationText(profile.risk_score)}`);
  }
  async function loadMarket() {
    setLoading("market");
    setStatus("QQQ 시장 지표를 갱신하는 중입니다...");
    try {
      const rows = await fetchHistory("QQQ");
      const latest = rows[rows.length - 1];
      const nextSma200 = sma(rows, 200);
      const nextSma20 = sma(rows, 20);
      const nextSma50 = sma(rows, 50);
      const nextHigh20 = rollingHigh(rows, 20);
      if (!nextSma200) throw new Error("200일선 계산 데이터가 부족합니다.");
      setMarket({ qqq_close: latest.close, qqq_sma200: nextSma200, qqq_sma20: nextSma20, qqq_sma50: nextSma50, qqq_high20: nextHigh20, as_of: latest.date });
      setStatus(`시장 지표 갱신 완료: ${latest.date}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "시장 지표 갱신 실패");
    } finally {
      setLoading("");
    }
  }
  async function runStrategy() {
    setLoading("strategy");
    setStatus("전략 추천을 계산하는 중입니다...");
    try {
      const result = await requestRecommendation(holdings, cash, profile, market, useAi);
      setRecommendation(result);
      setStatus(result.ai_used ? "AI 코치 리포트를 생성했습니다." : "규칙 기반 리포트를 생성했습니다.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "전략 추천 실패");
    } finally {
      setLoading("");
    }
  }

  async function adoptPlan(plan: StrategyPlan) {
    setLoading("adopt");
    setStatus(`${plan.title}을 내 전략으로 저장하는 중입니다...`);
    try {
      await adoptManagedStrategy(plan, market, totalCapital);
      setStatus("전략을 저장했습니다. 상단의 전략 관리 메뉴에서 운용 가이드와 기록장을 확인하세요.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "전략 저장에 실패했습니다.");
    } finally {
      setLoading("");
    }
  }

  return (
    <section className="page-grid">
      <div className="hero-panel">
        <div>
          <span className="section-label">Strategy Studio</span>
          <h2>현재 포트폴리오를 기준으로 다음 비중을 설계합니다.</h2>
          <p>{status}</p>
        </div>
        <div className="hero-actions">
          <button onClick={loadMarket} disabled={loading === "market"}>
            <RefreshCw size={17} />
            {loading === "market" ? "갱신 중" : "시장 지표 갱신"}
          </button>
          <button className="primary" onClick={runStrategy} disabled={loading === "strategy"}>
            <Bot size={17} />
            {loading === "strategy" ? "추천 중" : "전략 추천"}
          </button>
        </div>
      </div>

      <div className="metric-grid">
        <Metric label="총 자산" value={formatKrw(totalCapital)} note="보유금액 + 현금" />
        <Metric label="리스크 허용도" value={`${profile.risk_score}`} note={riskBand(profile.risk_score)} />
        <Metric label="QQQ 200일선 대비" value={formatPct((market.qqq_close / market.qqq_sma200 - 1) * 100)} note={market.as_of} />
        <Metric label="QQQ / 200일선" value={formatUsd(market.qqq_close)} note={formatUsd(market.qqq_sma200)} />
      </div>

      <div className="content-grid">
        <article className="panel span-12 data-quality-card">
          <h2 className="panel-title">데이터 신뢰도</h2>
          <div className="risk-strip">
            <div className="risk-pill low">
              <span>최근 가격일</span>
              <strong>{market.as_of}</strong>
            </div>
            <div className="risk-pill low">
              <span>200일선 계산</span>
              <strong>{market.qqq_sma200 > 0 ? "가능" : "불가"}</strong>
            </div>
            <div className="risk-pill medium">
              <span>시세 출처</span>
              <strong>API 프록시</strong>
            </div>
            <div className="risk-pill medium">
              <span>검증 방식</span>
              <strong>백테스트 + 모의</strong>
            </div>
          </div>
        </article>

        <article className="panel span-7">
          <PanelTitle icon={<Target size={18} />} title="포트폴리오 입력" />
          <div className="quick-input">
            <label>
              빠른 입력
              <textarea
                value={quickInput}
                onChange={(event) => setQuickInput(event.target.value)}
                placeholder="보유 종목과 금액을 입력하세요"
              />
              <small className="input-example">예: {exampleQuickInput}</small>
            </label>
            <button onClick={applyQuickInput}>
              <Plus size={16} />
              반영
            </button>
          </div>
          <div className="holdings-list">
            {holdings.map((holding, index) => (
              <div className="holding-row" key={`${holding.symbol}-${index}`}>
                <input value={holding.symbol} onChange={(event) => updateHolding(index, { symbol: event.target.value })} placeholder="심볼" />
                <input value={holding.name} onChange={(event) => updateHolding(index, { name: event.target.value })} placeholder="이름" />
                <input type="number" value={holding.amount} onChange={(event) => updateHolding(index, { amount: Number(event.target.value) })} />
                <select value={holding.category} onChange={(event) => updateHolding(index, { category: event.target.value })}>
                  <option value="nasdaq_leverage">나스닥 레버리지</option>
                  <option value="semiconductor">반도체</option>
                  <option value="broad_market">광범위 지수</option>
                  <option value="cash_like">현금성</option>
                  <option value="other">기타</option>
                </select>
                <button onClick={() => setHoldings((current) => current.filter((_, idx) => idx !== index))} aria-label="삭제">
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
          <div className="inline-actions">
            <button onClick={() => addHolding()}>
              <Plus size={16} />
              보유 추가
            </button>
            <label>
              현금
              <input type="number" value={cash} onChange={(event) => setCash(Number(event.target.value))} />
            </label>
          </div>
        </article>

        <article className="panel span-5">
          <PanelTitle icon={<SlidersHorizontal size={18} />} title="리스크 설정" />
          <div className="risk-slider-box">
            <div className="risk-slider-head">
              <strong>{profile.risk_score} / 100</strong>
              <span>{riskBand(profile.risk_score)}</span>
            </div>
            <input type="range" min={0} max={100} value={profile.risk_score} onChange={(event) => setProfile({ ...profile, risk_score: Number(event.target.value) })} />
          </div>
          <div className="recommendation-box">
            <div>
              <span className="section-label">권장 세팅</span>
              <p>{profileRecommendationText(profile.risk_score)}</p>
            </div>
            <div className="recommendation-values">
              <span>종목 {recommendedRiskProfile.target_count}개</span>
              <span>현금 {recommendedRiskProfile.min_cash_ratio}%+</span>
              <span>TQQQ {recommendedRiskProfile.max_tqqq_ratio}%↓</span>
              <span>위성 {recommendedRiskProfile.max_semiconductor_ratio}%↓</span>
            </div>
            <button className="primary" onClick={applyRecommendedProfile}>
              <CheckCircle2 size={16} />
              권장값 적용
            </button>
          </div>
          <div className="advanced-summary">
            <button type="button" onClick={() => setShowAdvanced((current) => !current)}>
              {showAdvanced ? "고급 설정 숨기기" : "고급 설정 열기"}
            </button>
            <small>목표 종목수, 최소 현금, 최대 TQQQ 비중, AI 코치 사용 여부는 고급 설정에서 조정합니다.</small>
          </div>
          {showAdvanced ? (
            <div className="profile-grid">
              <label>목표 종목 수<input type="number" value={profile.target_count} onChange={(event) => setProfile({ ...profile, target_count: Number(event.target.value) })} /></label>
              <label>최소 현금 %<input type="number" value={profile.min_cash_ratio} onChange={(event) => setProfile({ ...profile, min_cash_ratio: Number(event.target.value) })} /></label>
              <label>최대 TQQQ %<input type="number" value={profile.max_tqqq_ratio} onChange={(event) => setProfile({ ...profile, max_tqqq_ratio: Number(event.target.value) })} /></label>
              <label>최대 비핵심 위성 %<input type="number" value={profile.max_semiconductor_ratio} onChange={(event) => setProfile({ ...profile, max_semiconductor_ratio: Number(event.target.value) })} /></label>
              <label>단일 종목 최대 %
                <input type="number" value={profile.max_single_position_ratio} onChange={(event) => setProfile({ ...profile, max_single_position_ratio: Number(event.target.value) })} />
              </label>
              <label className="switch advanced-switch">
                <input type="checkbox" checked={useAi} onChange={(event) => setUseAi(event.target.checked)} />
                AI 코치 보조 사용
              </label>
            </div>
          ) : null}
        </article>

        <article className="panel span-12 optional-panel">
          <div className="panel-headline">
            <PanelTitle icon={<Search size={18} />} title="후보군 추가" />
            <button type="button" onClick={() => setShowCandidates((current) => !current)}>
              {showCandidates ? "후보군 접기" : "후보군 열기"}
            </button>
          </div>
          <p className="muted">
            처음에는 현재 보유 종목과 리스크만 입력해도 됩니다. 검증된 ETF 후보를 직접 추가하고 싶을 때만 열어 사용하세요.
          </p>
          {showCandidates ? (
            <div className="candidate-list compact">
              {candidateAssets.map((asset) => (
                <button className="candidate-chip" key={asset.symbol} onClick={() => addHolding(asset)}>
                  <strong>{asset.symbol}</strong>
                  <span>{asset.role}</span>
                </button>
              ))}
            </div>
          ) : null}
        </article>

        {recommendation && (
          <article className="panel span-12 coach-report">
            <span className="section-label">Coach Report</span>
            <h2>{recommendation.coach_report.headline}</h2>
            <p>{recommendation.coach_report.diagnosis}</p>
            <div className="report-columns">
              <ListBlock title="추천 이유" items={recommendation.coach_report.why} />
              <ListBlock title="다음 액션" items={recommendation.coach_report.next_actions} />
              <ListBlock title="모니터링" items={recommendation.coach_report.monitoring_rules} />
              <ListBlock title="주의" items={recommendation.coach_report.warnings} tone="warn" />
            </div>
          </article>
        )}

        {recommendation?.candidate_opinions?.length ? (
          <article className="panel span-12">
            <PanelTitle icon={<BrainCircuit size={18} />} title="후보군 판단" />
            <div className="opinion-grid">
              {recommendation.candidate_opinions.map((opinion) => (
                <div className={`opinion-card ${opinion.stance}`} key={opinion.symbol}>
                  <span>{stanceLabel(opinion.stance)}</span>
                  <strong>{opinion.symbol}</strong>
                  <small>{opinion.reason}</small>
                </div>
              ))}
            </div>
          </article>
        ) : null}

        {recommendation && (
          <article className="panel span-12">
            <PanelTitle icon={<CheckCircle2 size={18} />} title="추천 포트폴리오" />
            <div className="plan-tabs">
              {recommendation.plans.map((plan) => (
                <button key={plan.id} className={plan.id === selectedPlan?.id ? "selected" : ""} onClick={() => setSelectedPlanId(plan.id)}>
                  {plan.title}
                </button>
              ))}
            </div>
            {selectedPlan ? <PlanDetail plan={selectedPlan} onAdopt={adoptPlan} adopting={loading === "adopt"} /> : null}
          </article>
        )}
      </div>
    </section>
  );
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return <article className="metric panel"><span>{label}</span><strong>{value}</strong><small>{note}</small></article>;
}
function PanelTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return <h2 className="panel-title">{icon}{title}</h2>;
}
function ListBlock({ title, items, tone }: { title: string; items: string[]; tone?: "warn" }) {
  return <div className={`list-block ${tone ?? ""}`}><h3>{title}</h3><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></div>;
}
function PlanDetail({ plan, onAdopt, adopting }: { plan: StrategyPlan; onAdopt: (plan: StrategyPlan) => void; adopting: boolean }) {
  return (
    <div className="plan-detail">
      <p>{plan.summary}</p>
      <button className="primary" onClick={() => onAdopt(plan)} disabled={adopting}>
        {adopting ? "전략 저장 중..." : "이 전략 채택하기"}
      </button>
      <div className="score-grid">
        <MetricCard label="신뢰도" value={`${plan.scores.confidence_score}`} note="규칙/방어/시장 적합성" />
        <MetricCard label="위험도" value={`${plan.scores.risk_score}`} note="레버리지와 집중도" />
        <MetricCard label="적합도" value={`${plan.scores.fit_score}`} note="리스크 허용치와 거리" />
        <MetricCard label="수익 탄력" value={`${plan.scores.expected_return_score}`} note="상승장 반응도" />
      </div>
      <div className="plan-section-grid">
        <DataTable title="목표 비중" rows={plan.allocations.map((item) => [item.symbol, `${item.target_ratio.toFixed(1)}%`, formatKrw(item.target_amount)])} />
        <DataTable title="조정 액션" rows={plan.actions.map((item) => [item.symbol, actionLabel(item.action), item.amount ? formatKrw(item.amount) : item.reason])} />
      </div>
      <div className="risk-strip">
        {plan.risk_metrics.map((metric) => <div className={`risk-pill ${metric.level}`} key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong></div>)}
      </div>
    </div>
  );
}
function MetricCard({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="score-card"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>;
}
function DataTable({ title, rows }: { title: string; rows: string[][] }) {
  return <div><h3>{title}</h3><table><tbody>{rows.map((row) => <tr key={row.join("-")}>{row.map((cell) => <td key={cell}>{cell}</td>)}</tr>)}</tbody></table></div>;
}
