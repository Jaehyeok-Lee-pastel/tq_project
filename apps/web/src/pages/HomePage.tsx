import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Bot,
  Calculator,
  FlaskConical,
  HandCoins,
  LineChart,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Target,
  Trash2,
  TrendingUp,
} from "lucide-react";

type PriceRow = { date: string; close: number };
type ScoreLevel = "low" | "medium" | "high" | "very_high";

type HoldingInput = {
  symbol: string;
  name: string;
  amount: number;
  category: string;
};

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

type Allocation = {
  symbol: string;
  name: string;
  target_ratio: number;
  target_amount: number;
  role: string;
};

type TradeAction = {
  symbol: string;
  action: "buy" | "sell" | "hold" | "wait";
  amount: number;
  reason: string;
};

type SplitStep = {
  step: string;
  trigger: string;
  ratio_of_target: number;
  amount: number;
  note: string;
};

type RiskMetric = {
  label: string;
  value: string;
  level: ScoreLevel;
};

type ConfidenceBreakdown = {
  rule_clarity: number;
  market_fit: number;
  cash_defense: number;
  drawdown_control: number;
  overfit_resistance: number;
  execution_quality: number;
  user_fit: number;
};

type StrategyScores = {
  confidence_score: number;
  risk_score: number;
  fit_score: number;
  expected_return_score: number;
  execution_difficulty: ScoreLevel;
  confidence_breakdown: ConfidenceBreakdown;
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

type CoachReport = {
  headline: string;
  diagnosis: string;
  recommended_plan_id: string;
  why: string[];
  next_actions: string[];
  warnings: string[];
  monitoring_rules: string[];
};

type StrategyResponse = {
  total_capital: number;
  market_regime: string;
  qqq_distance_from_200ma: number;
  current_diagnosis: string[];
  candidate_opinions: CandidateOpinion[];
  plans: StrategyPlan[];
  coach_report: CoachReport;
  ai_used: boolean;
};

type BacktestStrategy = "qqq_buy_hold" | "tqqq_buy_hold" | "tqqq_200ma" | "qld_200ma";

type BacktestMetrics = {
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

type EquityPoint = {
  date: string;
  equity: number;
  drawdown: number;
  position: string;
};

type ProjectionScenario = {
  name: "bear" | "base" | "bull";
  annual_return: number;
  ending_capital: number;
  profit: number;
  note: string;
};

type BacktestResponse = {
  strategy: BacktestStrategy;
  strategy_name: string;
  benchmark_name: string;
  period_start: string;
  period_end: string;
  equity_curve: EquityPoint[];
  benchmark_curve: EquityPoint[];
  metrics: BacktestMetrics;
  benchmark_metrics: BacktestMetrics;
  yearly_returns: { year: number; return_pct: number }[];
  trades: { date: string; action: "buy" | "sell"; symbol: string; ratio: number; reason: string }[];
  projection: ProjectionScenario[];
  interpretation: string[];
};

type PaperPosition = {
  id: string;
  symbol: string;
  name: string;
  amount: number;
  entryPrice: number;
  currentPrice: number;
  buyDate: string;
};

type CandidateAsset = {
  symbol: string;
  name: string;
  category: string;
  role: string;
};

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
];

const defaultHoldings: HoldingInput[] = [];
const exampleQuickInput = "QLD 150만원, ACE K반도체TOP2 100만원, 현금 50만원";

const defaultProfile: InvestorProfile = {
  risk_profile: "aggressive",
  risk_score: 75,
  target_count: 3,
  allow_tqqq: true,
  prefer_200ma: true,
  min_cash_ratio: 20,
  max_tqqq_ratio: 50,
  max_semiconductor_ratio: 35,
  max_single_position_ratio: 60,
  goal: "작은 시드에서 2~3개에 집중하되, TQQQ를 포함한 공격형 전략을 200일선과 분할매수/분할매도로 관리하고 싶습니다.",
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
  const slice = rows.slice(-length);
  return slice.reduce((sum, row) => sum + row.close, 0) / length;
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

function findCandidate(rawSymbol: string) {
  const normalized = normalizeSymbol(rawSymbol);
  return candidateAssets.find((asset) => asset.symbol.toUpperCase() === normalized.toUpperCase());
}

function normalizeSymbol(rawSymbol: string) {
  const compact = rawSymbol.trim().toUpperCase().replace(/\s+/g, "");
  const aliases: Record<string, string> = {
    ACEK반도체TOP2: "ACE K반도체TOP2",
    "ACEK반도체": "ACE K반도체TOP2",
    K반도체TOP2: "ACE K반도체TOP2",
    SOLTOP2: "ACE K반도체TOP2",
    SOL반도체: "ACE K반도체TOP2",
  };
  return aliases[compact] ?? rawSymbol.trim().toUpperCase();
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
  const chunks = text
    .split(/[,;\n]+/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);

  return chunks
    .map((chunk) => {
      const amountText = chunk.match(/[\d,.]+\s*(만원|천원|원)?/)?.[0] ?? "";
      const symbolText = chunk.replace(amountText, "").trim();
      const candidate = findCandidate(symbolText);
      const symbol = candidate?.symbol ?? normalizeSymbol(symbolText);
      return {
        symbol,
        name: candidate?.name ?? symbol,
        amount: parseAmount(amountText),
        category: candidate?.category ?? "other",
      };
    })
    .filter((holding) => holding.symbol && holding.amount > 0);
}

function isCashInputSymbol(symbol: string) {
  const compact = symbol.trim().toUpperCase().replace(/\s+/g, "");
  return ["CASH", "현금", "예수금", "원화", "KRW"].includes(compact);
}

async function fetchHistory(symbol: string): Promise<PriceRow[]> {
  const response = await fetch(`${apiBaseUrl}/market/history/${symbol}?limit=1200`);
  if (!response.ok) throw new Error(`시장 데이터 API 오류: ${response.status}`);
  const payload = (await response.json()) as { rows: PriceRow[] };
  return payload.rows;
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

async function requestBacktest(payload: {
  strategy: BacktestStrategy;
  initial_capital: number;
  tqqq_target_ratio: number;
  qld_target_ratio: number;
  projection_years: number;
  cash_yield: number;
}) {
  const response = await fetch(`${apiBaseUrl}/backtest/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`백테스트 API 오류: ${response.status}`);
  return (await response.json()) as BacktestResponse;
}

function loadPaperPositions() {
  try {
    const raw = localStorage.getItem("tqcoach.paperPositions");
    return raw ? (JSON.parse(raw) as PaperPosition[]) : [];
  } catch {
    return [];
  }
}

function regimeLabel(regime: string) {
  const labels: Record<string, string> = {
    risk_off: "방어",
    normal_entry: "정상 진입",
    reduced_entry: "비중 축소",
    stretched_entry: "분할 진입",
  };
  return labels[regime] ?? regime;
}

function actionLabel(action: TradeAction["action"]) {
  return { buy: "매수", sell: "매도", hold: "유지", wait: "대기" }[action];
}

function difficultyLabel(level: ScoreLevel) {
  return { low: "낮음", medium: "중간", high: "높음", very_high: "매우 높음" }[level];
}

function stanceLabel(stance: CandidateOpinion["stance"]) {
  return { core: "핵심", satellite: "위성", defense: "방어", avoid: "제외", watch: "관찰" }[stance];
}

export function HomePage() {
  const [holdings, setHoldings] = useState<HoldingInput[]>(defaultHoldings);
  const [quickInput, setQuickInput] = useState("");
  const [searchText, setSearchText] = useState("");
  const [cash, setCash] = useState(0);
  const [profile, setProfile] = useState<InvestorProfile>(defaultProfile);
  const [market, setMarket] = useState<MarketSnapshot>({
    qqq_close: 736.4,
    qqq_sma200: 633.63,
    qqq_sma20: 720.18,
    qqq_sma50: 706.22,
    qqq_high20: 736.4,
    as_of: "2026-06-30",
  });
  const [recommendation, setRecommendation] = useState<StrategyResponse | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [loadingMarket, setLoadingMarket] = useState(false);
  const [loadingStrategy, setLoadingStrategy] = useState(false);
  const [loadingBacktest, setLoadingBacktest] = useState(false);
  const [useAi, setUseAi] = useState(true);
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null);
  const [paperPositions, setPaperPositions] = useState<PaperPosition[]>(loadPaperPositions);
  const [paperDraft, setPaperDraft] = useState({ symbol: "TQQQ", amount: 500000 });
  const [backtestConfig, setBacktestConfig] = useState({
    strategy: "tqqq_200ma" as BacktestStrategy,
    initial_capital: 2500000,
    tqqq_target_ratio: 60,
    qld_target_ratio: 70,
    projection_years: 3,
    cash_yield: 3,
  });
  const [status, setStatus] = useState("보유 종목을 빠르게 입력하거나 후보군에서 선택한 뒤 전략 추천을 실행하세요.");

  const totalCapital = useMemo(
    () => cash + holdings.reduce((sum, holding) => sum + holding.amount, 0),
    [cash, holdings],
  );
  const setupChecks = [
    { label: "보유 종목 또는 현금 입력", done: totalCapital > 0 },
    { label: "리스크 점수 확인", done: profile.risk_score >= 0 },
    { label: "QQQ 지표 기준일 확인", done: Boolean(market.as_of) },
  ];
  const selectedPlan = recommendation?.plans.find((plan) => plan.id === selectedPlanId) ?? recommendation?.plans[0];
  const filteredCandidates = candidateAssets.filter((asset) => {
    const keyword = searchText.toLowerCase();
    return `${asset.symbol} ${asset.name} ${asset.role}`.toLowerCase().includes(keyword);
  });

  useEffect(() => {
    if (recommendation?.plans[0]) setSelectedPlanId(recommendation.plans[0].id);
  }, [recommendation]);

  useEffect(() => {
    localStorage.setItem("tqcoach.paperPositions", JSON.stringify(paperPositions));
  }, [paperPositions]);

  function updateHolding(index: number, patch: Partial<HoldingInput>) {
    setHoldings((current) => current.map((holding, idx) => (idx === index ? { ...holding, ...patch } : holding)));
  }

  function addHolding(candidate?: CandidateAsset) {
    setHoldings((current) => [
      ...current,
      {
        symbol: candidate?.symbol ?? "",
        name: candidate?.name ?? "",
        amount: 0,
        category: candidate?.category ?? "other",
      },
    ]);
  }

  function removeHolding(index: number) {
    setHoldings((current) => current.filter((_, idx) => idx !== index));
  }

  function applyQuickInput() {
    const parsed = parseQuickHoldings(quickInput);
    if (!parsed.length) {
      setStatus("빠른 입력에서 종목과 금액을 찾지 못했습니다. 예: QLD 150만원, ACE K반도체TOP2 100만원");
      return;
    }
    const cashAmount = parsed
      .filter((holding) => isCashInputSymbol(holding.symbol))
      .reduce((sum, holding) => sum + holding.amount, 0);
    const assetHoldings = parsed.filter((holding) => !isCashInputSymbol(holding.symbol));
    setHoldings(assetHoldings);
    if (cashAmount > 0) setCash(cashAmount);
    setStatus(`${assetHoldings.length}개 보유 종목${cashAmount > 0 ? `과 현금 ${formatKrw(cashAmount)}` : ""}을 빠른 입력에서 불러왔습니다.`);
  }

  function applyExampleInput() {
    setQuickInput(exampleQuickInput);
    setStatus("예시를 입력창에 불러왔습니다. 금액과 종목을 본인 상황에 맞게 바꾼 뒤 입력 반영을 누르세요.");
  }

  function hydrateHoldingSymbol(index: number, symbol: string) {
    const candidate = findCandidate(symbol);
    updateHolding(index, {
      symbol: candidate?.symbol ?? symbol,
      name: candidate?.name ?? "",
      category: candidate?.category ?? "other",
    });
  }

  async function loadMarket() {
    setLoadingMarket(true);
    setStatus("QQQ 시장 지표를 불러오는 중입니다...");
    try {
      const rows = await fetchHistory("QQQ");
      const latest = rows[rows.length - 1];
      const nextSma200 = sma(rows, 200);
      const nextSma20 = sma(rows, 20);
      const nextSma50 = sma(rows, 50);
      const nextHigh20 = rollingHigh(rows, 20);
      if (!nextSma200) throw new Error("200일선 계산에 필요한 데이터가 부족합니다.");
      setMarket({ qqq_close: latest.close, qqq_sma200: nextSma200, qqq_sma20: nextSma20, qqq_sma50: nextSma50, qqq_high20: nextHigh20, as_of: latest.date });
      setStatus(`시장 지표 갱신 완료: ${latest.date}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "시장 지표를 불러오지 못했습니다.");
    } finally {
      setLoadingMarket(false);
    }
  }

  async function runStrategy() {
    if (totalCapital <= 0) {
      setStatus("먼저 보유 종목이나 현금을 입력해야 전략을 추천할 수 있습니다.");
      return;
    }
    setLoadingStrategy(true);
    setStatus("검증 후보군, 리스크 허용도, 시장 지표를 바탕으로 전략을 계산하는 중입니다...");
    try {
      const result = await requestRecommendation(holdings, cash, profile, market, useAi);
      setRecommendation(result);
      setStatus(result.ai_used ? "전략 엔진과 AI 코치 리포트를 생성했습니다." : "전략 엔진 리포트를 생성했습니다.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "전략 추천에 실패했습니다.");
    } finally {
      setLoadingStrategy(false);
    }
  }

  async function runBacktest() {
    setLoadingBacktest(true);
    setStatus("과거 백테스트와 미래 모의 시나리오를 계산하는 중입니다...");
    try {
      const result = await requestBacktest(backtestConfig);
      setBacktest(result);
      setStatus(`${result.strategy_name} 백테스트를 계산했습니다.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "백테스트 계산에 실패했습니다.");
    } finally {
      setLoadingBacktest(false);
    }
  }

  async function getLatestPrice(symbol: string) {
    const rows = await fetchHistory(symbol);
    return rows[rows.length - 1].close;
  }

  async function addPaperPosition() {
    const candidate = findCandidate(paperDraft.symbol);
    const symbol = candidate?.symbol ?? paperDraft.symbol.toUpperCase();
    setStatus(`${symbol} 현재가를 불러와 모의 보유에 추가하는 중입니다...`);
    try {
      const latestPrice = await getLatestPrice(symbol);
      const position: PaperPosition = {
        id: `${symbol}-${Date.now()}`,
        symbol,
        name: candidate?.name ?? symbol,
        amount: paperDraft.amount,
        entryPrice: latestPrice,
        currentPrice: latestPrice,
        buyDate: new Date().toISOString().slice(0, 10),
      };
      setPaperPositions((current) => [...current, position]);
      setStatus(`${symbol}을 실제 매수한 것처럼 모의 보유에 기록했습니다.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "모의 보유 추가에 실패했습니다.");
    }
  }

  async function refreshPaperPositions() {
    setStatus("모의 보유 종목의 현재가를 갱신하는 중입니다...");
    try {
      const symbols = Array.from(new Set(paperPositions.map((position) => position.symbol)));
      const pricePairs = await Promise.all(symbols.map(async (symbol) => [symbol, await getLatestPrice(symbol)] as const));
      const priceMap = Object.fromEntries(pricePairs);
      setPaperPositions((current) =>
        current.map((position) => ({ ...position, currentPrice: priceMap[position.symbol] ?? position.currentPrice })),
      );
      setStatus("모의 보유 평가금액을 현재가 기준으로 갱신했습니다.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "모의 보유 갱신에 실패했습니다.");
    }
  }

  function removePaperPosition(id: string) {
    setPaperPositions((current) => current.filter((position) => position.id !== id));
  }

  return (
    <section className="coach-dashboard">
      <div className="toolbar panel">
        <button className="primary" onClick={loadMarket} disabled={loadingMarket}>
          <RefreshCw size={17} />
          {loadingMarket ? "갱신 중" : "시장 지표 갱신"}
        </button>
        <button className="primary" onClick={runStrategy} disabled={loadingStrategy}>
          <Bot size={17} />
          {loadingStrategy ? "추천 중" : "전략 추천"}
        </button>
        <label className="switch">
          <input type="checkbox" checked={useAi} onChange={(event) => setUseAi(event.target.checked)} />
          AI 코치 사용
        </label>
        <p>{status}</p>
      </div>

      {!recommendation && (
        <article className="panel onboarding-card">
          <div>
            <span className="section-label">Start Here</span>
            <h2>현재 보유와 성향만 넣으면 TQQQ 200일선 기준으로 판단합니다.</h2>
            <p>처음 화면은 추천을 받기 위한 입력에 집중합니다. 백테스트와 모의운용은 전략 추천 이후에 이어서 확인할 수 있습니다.</p>
          </div>
          <div className="onboarding-steps">
            {setupChecks.map((item, index) => (
              <span className={item.done ? "done" : ""} key={item.label}>
                <strong>{index + 1}</strong>
                {item.label}
              </span>
            ))}
          </div>
        </article>
      )}

      <div className="metric-grid">
        <article className="metric panel">
          <span>총 자산</span>
          <strong>{formatKrw(totalCapital)}</strong>
          <small>보유금액 + 현금</small>
        </article>
        <article className="metric panel">
          <span>리스크 허용도</span>
          <strong>{profile.risk_score}</strong>
          <small>{riskBand(profile.risk_score)}</small>
        </article>
        <article className="metric panel">
          <span>QQQ 200일선 대비</span>
          <strong>{formatPct((market.qqq_close / market.qqq_sma200 - 1) * 100)}</strong>
          <small>{recommendation ? regimeLabel(recommendation.market_regime) : market.as_of}</small>
        </article>
        <article className="metric panel">
          <span>QQQ 종가 / 200일선</span>
          <strong>{formatUsd(market.qqq_close)}</strong>
          <small>{formatUsd(market.qqq_sma200)}</small>
        </article>
      </div>

      <div className="coach-grid">
        <article className="panel setup-card">
          <h2>
            <Target size={19} />
            현재 포트폴리오
          </h2>
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
              입력 반영
            </button>
          </div>
          <div className="holdings-list">
            {holdings.length ? holdings.map((holding, index) => (
              <div className="holding-row" key={`${holding.symbol}-${index}`}>
                <input
                  list="candidate-symbols"
                  value={holding.symbol}
                  onBlur={(event) => hydrateHoldingSymbol(index, event.target.value)}
                  onChange={(event) => updateHolding(index, { symbol: event.target.value })}
                  placeholder="심볼"
                />
                <input value={holding.name} onChange={(event) => updateHolding(index, { name: event.target.value })} placeholder="이름" />
                <input type="number" value={holding.amount} onChange={(event) => updateHolding(index, { amount: Number(event.target.value) })} />
                <select value={holding.category} onChange={(event) => updateHolding(index, { category: event.target.value })}>
                  <option value="nasdaq_leverage">나스닥 레버리지</option>
                  <option value="nasdaq">나스닥</option>
                  <option value="semiconductor">반도체</option>
                  <option value="broad_market">광범위 지수</option>
                  <option value="cash_like">현금성</option>
                  <option value="other">기타</option>
                </select>
                <button aria-label="보유 삭제" onClick={() => removeHolding(index)}>
                  <Trash2 size={16} />
                </button>
              </div>
            )) : (
              <div className="empty-input-state">
                <Target size={22} />
                <strong>아직 입력된 보유 종목이 없습니다.</strong>
                <span>빠른 입력을 사용하거나 보유 추가 버튼으로 직접 입력하세요. 예시는 자동 적용되지 않습니다.</span>
              </div>
            )}
          </div>
          <datalist id="candidate-symbols">
            {candidateAssets.map((asset) => (
              <option key={asset.symbol} value={asset.symbol}>
                {asset.name}
              </option>
            ))}
          </datalist>
          <div className="inline-actions">
            <button onClick={() => addHolding()}>
              <Plus size={16} />
              보유 추가
            </button>
            <button onClick={applyExampleInput}>
              예시 불러오기
            </button>
            <label>
              현금
              <input type="number" value={cash} onChange={(event) => setCash(Number(event.target.value))} placeholder="예: 500000" />
            </label>
          </div>
        </article>

        <article className="panel setup-card candidate-helper">
          <h2>
            <Search size={19} />
            검증 후보군
          </h2>
          <details>
            <summary>검증된 후보군에서 종목 추가</summary>
            <input value={searchText} onChange={(event) => setSearchText(event.target.value)} placeholder="TQQQ, 반도체, 현금성..." />
            <div className="candidate-list">
              {filteredCandidates.map((asset) => (
                <button className="candidate-chip" key={asset.symbol} onClick={() => addHolding(asset)}>
                  <strong>{asset.symbol}</strong>
                  <span>{asset.role}</span>
                </button>
              ))}
            </div>
          </details>
        </article>

        <article className="panel setup-card">
          <h2>
            <SlidersHorizontal size={19} />
            리스크와 방향성
          </h2>
          <div className="risk-slider-box">
            <div className="risk-slider-head">
              <strong>{profile.risk_score} / 100</strong>
              <span>{riskBand(profile.risk_score)}</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={profile.risk_score}
              onChange={(event) => setProfile({ ...profile, risk_score: Number(event.target.value) })}
            />
          </div>
          <div className="profile-grid">
            <label>
              목표 종목 수
              <input type="number" min={2} max={5} value={profile.target_count} onChange={(event) => setProfile({ ...profile, target_count: Number(event.target.value) })} />
            </label>
            <label>
              방어/대기 최소 비중
              <input type="number" value={profile.min_cash_ratio} onChange={(event) => setProfile({ ...profile, min_cash_ratio: Number(event.target.value) })} />
            </label>
            <label>
              최대 TQQQ 비중
              <input type="number" value={profile.max_tqqq_ratio} onChange={(event) => setProfile({ ...profile, max_tqqq_ratio: Number(event.target.value) })} />
            </label>
            <label>
              최대 반도체 비중
              <input type="number" value={profile.max_semiconductor_ratio} onChange={(event) => setProfile({ ...profile, max_semiconductor_ratio: Number(event.target.value) })} />
            </label>
            <label className="wide">
              투자 목표
              <textarea value={profile.goal} onChange={(event) => setProfile({ ...profile, goal: event.target.value })} />
            </label>
          </div>
        </article>

        {recommendation && (
          <article className="panel coach-report">
            <div className="report-head">
              <div>
                <span className="section-label">{recommendation.ai_used ? "AI 코치 리포트" : "규칙 기반 코치 리포트"}</span>
                <h2>{recommendation.coach_report.headline}</h2>
              </div>
              <span className="pill">{regimeLabel(recommendation.market_regime)}</span>
            </div>
            <p>{recommendation.coach_report.diagnosis}</p>
            <div className="report-columns">
              <ListBlock title="추천 이유" items={recommendation.coach_report.why} />
              <ListBlock title="다음 액션" items={recommendation.coach_report.next_actions} />
              <ListBlock title="모니터링 규칙" items={recommendation.coach_report.monitoring_rules} />
              <ListBlock title="주의" items={recommendation.coach_report.warnings} tone="warn" />
            </div>
          </article>
        )}

        {recommendation?.candidate_opinions?.length ? (
          <article className="panel universe-card">
            <h2>후보군 판단</h2>
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
          <article className="panel plans-card">
            <h2>
              <Calculator size={19} />
              추천 포트폴리오 3안
            </h2>
            <div className="plan-tabs">
              {recommendation.plans.map((plan) => (
                <button key={plan.id} className={plan.id === selectedPlan?.id ? "selected" : ""} onClick={() => setSelectedPlanId(plan.id)}>
                  {plan.title}
                </button>
              ))}
            </div>
            {selectedPlan && <PlanDetail plan={selectedPlan} />}
          </article>
        )}

        {recommendation ? (
        <article className="panel backtest-card">
          <div className="report-head">
            <h2>
              <FlaskConical size={19} />
              백테스트와 모의 수익
            </h2>
            <button className="primary" onClick={runBacktest} disabled={loadingBacktest}>
              <LineChart size={17} />
              {loadingBacktest ? "계산 중" : "백테스트 실행"}
            </button>
          </div>
          <div className="backtest-controls">
            <label>
              전략
              <select
                value={backtestConfig.strategy}
                onChange={(event) =>
                  setBacktestConfig({ ...backtestConfig, strategy: event.target.value as BacktestStrategy })
                }
              >
                <option value="tqqq_200ma">QQQ 200일선 기반 TQQQ 전략</option>
                <option value="qld_200ma">QQQ 200일선 기반 QLD 전략</option>
                <option value="qqq_buy_hold">QQQ 장기 보유</option>
                <option value="tqqq_buy_hold">TQQQ 장기 보유</option>
              </select>
            </label>
            <label>
              초기 금액
              <input
                type="number"
                value={backtestConfig.initial_capital}
                onChange={(event) =>
                  setBacktestConfig({ ...backtestConfig, initial_capital: Number(event.target.value) })
                }
              />
            </label>
            <label>
              TQQQ 목표 비중
              <input
                type="number"
                value={backtestConfig.tqqq_target_ratio}
                onChange={(event) =>
                  setBacktestConfig({ ...backtestConfig, tqqq_target_ratio: Number(event.target.value) })
                }
              />
            </label>
            <label>
              QLD 목표 비중
              <input
                type="number"
                value={backtestConfig.qld_target_ratio}
                onChange={(event) =>
                  setBacktestConfig({ ...backtestConfig, qld_target_ratio: Number(event.target.value) })
                }
              />
            </label>
            <label>
              모의 기간
              <input
                type="number"
                min={1}
                max={10}
                value={backtestConfig.projection_years}
                onChange={(event) =>
                  setBacktestConfig({ ...backtestConfig, projection_years: Number(event.target.value) })
                }
              />
            </label>
            <label>
              현금 수익률
              <input
                type="number"
                value={backtestConfig.cash_yield}
                onChange={(event) => setBacktestConfig({ ...backtestConfig, cash_yield: Number(event.target.value) })}
              />
            </label>
          </div>
          {backtest ? <BacktestResult result={backtest} /> : <p className="muted">전략별 과거 성과와 앞으로의 보수/기준/낙관 시나리오를 함께 확인합니다.</p>}
        </article>
        ) : null}

        {recommendation ? (
        <article className="panel paper-card">
          <div className="report-head">
            <h2>
              <HandCoins size={19} />
              실시간 모의 보유
            </h2>
            <button onClick={refreshPaperPositions} disabled={!paperPositions.length}>
              <RefreshCw size={17} />
              현재가 갱신
            </button>
          </div>
          <div className="paper-controls">
            <label>
              종목
              <input
                list="candidate-symbols"
                value={paperDraft.symbol}
                onChange={(event) => setPaperDraft({ ...paperDraft, symbol: event.target.value })}
              />
            </label>
            <label>
              모의 매수 금액
              <input
                type="number"
                value={paperDraft.amount}
                onChange={(event) => setPaperDraft({ ...paperDraft, amount: Number(event.target.value) })}
              />
            </label>
            <button className="primary" onClick={addPaperPosition}>
              <Plus size={16} />
              모의 매수
            </button>
          </div>
          <PaperPortfolio positions={paperPositions} onRemove={removePaperPosition} />
        </article>
        ) : null}

        {!recommendation && (
          <article className="panel empty-state">
            <LineChart size={34} />
            <h2>전략 추천을 실행하면 후보군 기반 교체 판단까지 표시합니다.</h2>
            <p>현재 보유 종목을 고집하지 않고 검증 후보군 안에서 유지, 축소, 교체, 대기를 계산합니다.</p>
          </article>
        )}
      </div>
    </section>
  );
}

function PaperPortfolio({
  positions,
  onRemove,
}: {
  positions: PaperPosition[];
  onRemove: (id: string) => void;
}) {
  if (!positions.length) {
    return <p className="muted">전략을 실제로 샀다고 가정하고 보유 금액과 손익률을 추적합니다.</p>;
  }
  const totalInvested = positions.reduce((sum, position) => sum + position.amount, 0);
  const totalValue = positions.reduce((sum, position) => sum + paperValue(position), 0);
  const totalReturn = totalValue / totalInvested - 1;

  return (
    <div className="paper-result">
      <div className="score-grid">
        <MetricCard label="모의 투자금" value={formatKrw(totalInvested)} note={`${positions.length}개 보유`} />
        <MetricCard label="현재 평가금액" value={formatKrw(totalValue)} note="현재가 기준" />
        <MetricCard label="평가손익" value={formatKrw(totalValue - totalInvested)} note={formatPct(totalReturn * 100)} />
        <MetricCard label="가격 기준" value="ETF 현재가" note="환율 변동은 제외" />
      </div>
      <table>
        <thead>
          <tr>
            <th>종목</th>
            <th>매수가</th>
            <th>현재가</th>
            <th>손익률</th>
            <th>평가금액</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {positions.map((position) => {
            const returnPct = position.currentPrice / position.entryPrice - 1;
            return (
              <tr key={position.id}>
                <td>
                  <strong>{position.symbol}</strong>
                  <small>{position.buyDate} 모의 매수</small>
                </td>
                <td>{formatUsd(position.entryPrice)}</td>
                <td>{formatUsd(position.currentPrice)}</td>
                <td>{formatPct(returnPct * 100)}</td>
                <td>{formatKrw(paperValue(position))}</td>
                <td>
                  <button aria-label="모의 보유 삭제" onClick={() => onRemove(position.id)}>
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function paperValue(position: PaperPosition) {
  return position.amount * (position.currentPrice / position.entryPrice);
}

function BacktestResult({ result }: { result: BacktestResponse }) {
  const latest = result.equity_curve[result.equity_curve.length - 1];
  const first = result.equity_curve[0];
  const chartPoints = result.equity_curve.map((point) => {
    const x = ((new Date(point.date).getTime() - new Date(first.date).getTime()) /
      (new Date(latest.date).getTime() - new Date(first.date).getTime())) *
      100;
    const minEquity = Math.min(...result.equity_curve.map((item) => item.equity));
    const maxEquity = Math.max(...result.equity_curve.map((item) => item.equity));
    const y = 100 - ((point.equity - minEquity) / Math.max(maxEquity - minEquity, 1)) * 100;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });

  return (
    <div className="backtest-result">
      <div className="score-grid">
        <MetricCard label="최종 금액" value={formatKrw(result.metrics.final_capital)} note={`${result.period_start} ~ ${result.period_end}`} />
        <MetricCard label="총수익률" value={formatPct(result.metrics.total_return)} note={`QQQ ${formatPct(result.benchmark_metrics.total_return)}`} />
        <MetricCard label="CAGR" value={formatPct(result.metrics.cagr)} note={`Calmar ${result.metrics.calmar ?? "-"}`} />
        <MetricCard label="MDD" value={formatPct(result.metrics.max_drawdown)} note={`최장 손실 ${result.metrics.longest_drawdown_days}일`} />
        <MetricCard label="거래 횟수" value={`${result.metrics.trade_count}회`} note={`승률 ${result.metrics.win_rate.toFixed(1)}%`} />
      </div>
      <div className="equity-chart" aria-label="백테스트 수익 곡선">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none">
          <polyline points={chartPoints.join(" ")} />
        </svg>
      </div>
      <div className="projection-grid">
        {result.projection.map((scenario) => (
          <div className={`projection-card ${scenario.name}`} key={scenario.name}>
            <span>{scenarioLabel(scenario.name)}</span>
            <strong>{formatKrw(scenario.ending_capital)}</strong>
            <small>
              예상 손익 {formatKrw(scenario.profit)} / 연 {formatPct(scenario.annual_return)}
            </small>
            <p>{scenario.note}</p>
          </div>
        ))}
      </div>
      <div className="report-columns">
        <ListBlock title="해석" items={result.interpretation} />
        <ListBlock title="최근 거래 로그" items={result.trades.slice(-6).map((trade) => `${trade.date} ${actionLabel(trade.action)} ${trade.symbol} ${trade.ratio}%: ${trade.reason}`)} />
      </div>
    </div>
  );
}

function MetricCard({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="score-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}

function scenarioLabel(name: ProjectionScenario["name"]) {
  return { bear: "보수", base: "기준", bull: "낙관" }[name];
}

function ListBlock({ title, items, tone }: { title: string; items: string[]; tone?: "warn" }) {
  return (
    <div className={`list-block ${tone ?? ""}`}>
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function PlanDetail({ plan }: { plan: StrategyPlan }) {
  return (
    <div className="plan-detail">
      <p>{plan.summary}</p>
      <ScoreCards scores={plan.scores} />
      <div className="plan-section-grid">
        <div>
          <h3>목표 비중</h3>
          <table>
            <thead>
              <tr>
                <th>자산</th>
                <th>비중</th>
                <th>금액</th>
              </tr>
            </thead>
            <tbody>
              {plan.allocations.map((allocation) => (
                <tr key={allocation.symbol}>
                  <td>
                    <strong>{allocation.symbol}</strong>
                    <small>{allocation.role}</small>
                  </td>
                  <td>{allocation.target_ratio.toFixed(1)}%</td>
                  <td>{formatKrw(allocation.target_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <h3>현재 해야 할 조정</h3>
          <table>
            <tbody>
              {plan.actions.map((action) => (
                <tr key={`${action.symbol}-${action.action}-${action.amount}`}>
                  <td>
                    <strong>{action.symbol}</strong>
                    <small>{action.reason}</small>
                  </td>
                  <td>{actionLabel(action.action)}</td>
                  <td>{action.amount ? formatKrw(action.amount) : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="split-grid">
        <SplitPlan title="분할매수 코칭" icon={<TrendingUp size={18} />} steps={plan.buy_plan} />
        <SplitPlan title="분할매도 코칭" icon={<ShieldCheck size={18} />} steps={plan.sell_plan} />
      </div>
      <div className="risk-strip">
        {plan.risk_metrics.map((metric) => (
          <div className={`risk-pill ${metric.level}`} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </div>
        ))}
      </div>
      <div className="pros-cons">
        <ListBlock title="신뢰도 근거" items={plan.scores.confidence_notes} />
        <ListBlock title="약점" items={plan.cons} tone="warn" />
      </div>
    </div>
  );
}

function ScoreCards({ scores }: { scores: StrategyScores }) {
  const items = [
    ["전략 신뢰도", scores.confidence_score, "규칙/방어력/시장 적합성"],
    ["전략 위험도", scores.risk_score, "레버리지와 집중도"],
    ["사용자 적합도", scores.fit_score, "리스크 허용도와의 거리"],
    ["수익 탄력", scores.expected_return_score, "상승장 반응도"],
  ] as const;
  return (
    <div className="score-grid">
      {items.map(([label, value, note]) => (
        <div className="score-card" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
          <small>{note}</small>
        </div>
      ))}
      <div className="score-card">
        <span>실전 난이도</span>
        <strong>{difficultyLabel(scores.execution_difficulty)}</strong>
        <small>규칙을 실제로 지키는 난이도</small>
      </div>
    </div>
  );
}

function SplitPlan({ title, icon, steps }: { title: string; icon: ReactNode; steps: SplitStep[] }) {
  return (
    <div className="split-card">
      <h3>
        {icon}
        {title}
      </h3>
      {steps.map((step) => (
        <div className="split-step" key={`${title}-${step.step}`}>
          <div>
            <strong>{step.step}</strong>
            <p>{step.trigger}</p>
            <small>{step.note}</small>
          </div>
          <span>{step.amount ? formatKrw(step.amount) : "대기"}</span>
        </div>
      ))}
    </div>
  );
}
