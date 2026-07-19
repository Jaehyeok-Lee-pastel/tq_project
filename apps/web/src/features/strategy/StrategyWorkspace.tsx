import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bot,
  CheckCircle2,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Target,
  Trash2
} from "lucide-react";
import type {
  PriceRow,
  HoldingInput,
  InvestorProfile,
  MarketSnapshot,
  QuoteSnapshot,
  FxSnapshot,
  Allocation,
  TradeAction,
  CandidateOpinion,
  StrategyPlan,
  StrategyResponse,
  CandidateAsset,
  ResearchStrategyConfig
} from "./types";

const AUTO_MARKET_REFRESH_MS = 30 * 60 * 1000;

const candidateAssets: CandidateAsset[] = [
  {
    symbol: "TQQQ",
    name: "ProShares UltraPro QQQ",
    category: "nasdaq_leverage",
    role: "공격 엔진"
  },
  {
    symbol: "QLD",
    name: "ProShares Ultra QQQ",
    category: "nasdaq_leverage",
    role: "완충형 레버리지"
  },
  { symbol: "QQQ", name: "Invesco QQQ Trust", category: "nasdaq", role: "나스닥 기준 자산" },
  { symbol: "QQQM", name: "Invesco NASDAQ 100 ETF", category: "nasdaq", role: "저비용 나스닥 1x" },
  {
    symbol: "SPYM",
    name: "SPDR Portfolio S&P 500 ETF",
    category: "broad_market",
    role: "저비용 S&P 500 코어"
  },
  {
    symbol: "SMH",
    name: "VanEck Semiconductor ETF",
    category: "semiconductor",
    role: "미국 반도체 위성"
  },
  {
    symbol: "SOXX",
    name: "iShares Semiconductor ETF",
    category: "semiconductor",
    role: "반도체 위성"
  },
  {
    symbol: "ACE K반도체TOP2",
    name: "ACE K반도체TOP2",
    category: "semiconductor",
    role: "한국 반도체 집중"
  },
  {
    symbol: "VOO",
    name: "Vanguard S&P 500 ETF",
    category: "broad_market",
    role: "광범위 지수 완충"
  },
  {
    symbol: "SGOV",
    name: "iShares 0-3 Month Treasury Bond ETF",
    category: "cash_like",
    role: "현금성 대기"
  },
  {
    symbol: "BIL",
    name: "SPDR Bloomberg 1-3 Month T-Bill ETF",
    category: "cash_like",
    role: "분할매수 대기"
  }
];

const defaultHoldings: HoldingInput[] = [];
const exampleQuickInput = "QLD 150만원, ACE K반도체TOP2 100만원";
const userSettingsKey = "tqcoach.userSettings";

type CashflowSettings = { monthlyContribution: number; payDay: number };

function loadCashflowSettings(): CashflowSettings {
  try {
    const saved = JSON.parse(localStorage.getItem(userSettingsKey) ?? "{}") as Partial<CashflowSettings>;
    return {
      monthlyContribution: Number(saved.monthlyContribution) || 1_000_000,
      payDay: Math.min(31, Math.max(1, Number(saved.payDay) || 10))
    };
  } catch {
    return { monthlyContribution: 1_000_000, payDay: 10 };
  }
}
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
  goal: "작은 시드에서 2~3개에 집중하되 TQQQ를 포함한 공격형 전략을 원합니다."
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
function recommendedProfile(
  score: number
): Pick<
  InvestorProfile,
  | "risk_profile"
  | "target_count"
  | "min_cash_ratio"
  | "max_tqqq_ratio"
  | "max_semiconductor_ratio"
  | "max_single_position_ratio"
> {
  if (score <= 30) {
    return {
      risk_profile: "defensive",
      target_count: 4,
      min_cash_ratio: 40,
      max_tqqq_ratio: 0,
      max_semiconductor_ratio: 0,
      max_single_position_ratio: 45
    };
  }
  if (score <= 55) {
    return {
      risk_profile: "balanced",
      target_count: 3,
      min_cash_ratio: 30,
      max_tqqq_ratio: 12,
      max_semiconductor_ratio: 6,
      max_single_position_ratio: 50
    };
  }
  if (score <= 75) {
    return {
      risk_profile: "aggressive",
      target_count: 3,
      min_cash_ratio: 22,
      max_tqqq_ratio: 28,
      max_semiconductor_ratio: 10,
      max_single_position_ratio: 55
    };
  }
  if (score <= 90) {
    return {
      risk_profile: "very_aggressive",
      target_count: 3,
      min_cash_ratio: 16,
      max_tqqq_ratio: 40,
      max_semiconductor_ratio: 15,
      max_single_position_ratio: 60
    };
  }
  return {
    risk_profile: "very_aggressive",
    target_count: 2,
    min_cash_ratio: 12,
    max_tqqq_ratio: 75,
    max_semiconductor_ratio: 18,
    max_single_position_ratio: 65
  };
}
function profileRecommendationText(score: number) {
  if (score <= 30) return "TQQQ는 보류하고 SGOV/BIL/VOO 중심으로 방어력을 먼저 둡니다.";
  if (score <= 55) return "소량 TQQQ만 허용하고 QQQM/SPYM 1x 완충으로 참여와 방어를 함께 둡니다.";
  if (score <= 75)
    return "TQQQ는 조건부 분할 집행하고, 미집행분은 QQQM/SPYM 완충으로 시장 참여를 유지합니다.";
  if (score <= 90)
    return "TQQQ를 공격적으로 쓰되 QQQ 이격도 상한, 1x 완충, SGOV/CASH 역할을 함께 둡니다.";
  return "초공격형은 TQQQ 상한을 높게 열어두되, 실제 매수는 QQQ 이격도·분할 규칙·경고를 통과한 금액만 집행합니다.";
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
    장기채: "TLT"
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
      return {
        symbol,
        name: candidate?.name ?? symbol,
        amount: parseAmount(amountText),
        category: candidate?.category ?? "other"
      };
    })
    .filter((holding) => holding.symbol && holding.amount > 0);
}
import {
  adoptResearchStrategy,
  adoptManagedStrategy,
  fetchHistory,
  fetchQuote,
  fetchUsdKrw,
  requestRecommendation
} from "./api";

const RESEARCH_PRESET_ID = "daily_70_30_early_defense_cash_v1";
const RESEARCH_PRESET_VERSION = "2026-07";
function actionLabel(action: TradeAction["action"]) {
  return { buy: "매수", sell: "매도", hold: "유지", wait: "대기" }[action];
}
function stanceLabel(stance: CandidateOpinion["stance"]) {
  return { core: "핵심", satellite: "위성", defense: "방어", avoid: "제외", watch: "관찰" }[stance];
}

export function StrategyWorkspace() {
  const navigate = useNavigate();
  const [holdings, setHoldings] = useState<HoldingInput[]>(defaultHoldings);
  const [quickInput, setQuickInput] = useState("");
  const [cash, setCash] = useState(0);
  const [cashflow, setCashflow] = useState<CashflowSettings>(loadCashflowSettings);
  const [setupStep, setSetupStep] = useState<1 | 2>(1);
  const [profile, setProfile] = useState<InvestorProfile>(defaultProfile);
  const [market, setMarket] = useState<MarketSnapshot>({
    qqq_close: 736.4,
    qqq_sma200: 633.63,
    qqq_sma20: 720.18,
    qqq_sma50: 706.22,
    qqq_high20: 736.4,
    as_of: "2026-06-30"
  });
  const [quotes, setQuotes] = useState<Record<string, QuoteSnapshot>>({});
  const [usdKrw, setUsdKrw] = useState<FxSnapshot | null>(null);
  const [recommendation, setRecommendation] = useState<StrategyResponse | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [useAi, setUseAi] = useState(true);
  const [loading, setLoading] = useState<"market" | "strategy" | "adopt" | "">("");
  const [status, setStatus] = useState("포트폴리오와 리스크 점수를 입력한 뒤 전략을 추천받으세요.");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showCandidates, setShowCandidates] = useState(false);
  const [useResearchPreset, setUseResearchPreset] = useState(false);
  const marketRefreshInFlight = useRef(false);
  const cashInputRef = useRef<HTMLInputElement>(null);
  const riskInputRef = useRef<HTMLElement>(null);

  const totalCapital = useMemo(
    () => cash + holdings.reduce((sum, holding) => sum + holding.amount, 0),
    [cash, holdings]
  );
  const selectedPlan =
    recommendation?.plans.find((plan) => plan.id === selectedPlanId) ?? recommendation?.plans[0];
  const recommendedRiskProfile = useMemo(
    () => recommendedProfile(profile.risk_score),
    [profile.risk_score]
  );
  const onboardingStep = recommendation ? 3 : setupStep;
  const presetCompatible = holdings.every((holding) => ["TQQQ", "QQQM"].includes(holding.symbol.toUpperCase()));

  useEffect(() => {
    if (recommendation?.plans[0]) setSelectedPlanId(recommendation.plans[0].id);
  }, [recommendation]);

  useEffect(() => {
    try {
      const current = JSON.parse(localStorage.getItem(userSettingsKey) ?? "{}") as Record<string, unknown>;
      localStorage.setItem(userSettingsKey, JSON.stringify({ ...current, ...cashflow }));
    } catch {
      // Local preferences are optional and must not block strategy setup.
    }
  }, [cashflow]);

  function applyQuickInput() {
    const parsed = parseQuickHoldings(quickInput);
    if (!parsed.length) {
      setStatus("예: QLD 150만원, ACE K반도체TOP2 100만원");
      return;
    }
    setHoldings(parsed);
    setStatus(`${parsed.length}개 보유 종목을 반영했습니다.`);
  }
  function loadExamplePortfolio() {
    setHoldings(parseQuickHoldings(exampleQuickInput));
    setQuickInput(exampleQuickInput);
    setStatus("예시 포트폴리오를 불러왔습니다. 내 보유금액에 맞게 수정할 수 있습니다.");
  }
  function startWithCashOnly() {
    setQuickInput("");
    setHoldings([]);
    setStatus("현금만으로 시작합니다. 아래 현금과 월 추가금만 입력하세요.");
    window.setTimeout(() => cashInputRef.current?.focus(), 0);
  }
  function advanceToRisk() {
    if (totalCapital <= 0) {
      setStatus("보유금액 또는 현금을 입력한 뒤 다음 단계로 갈 수 있습니다.");
      return;
    }
    setSetupStep(2);
    window.setTimeout(
      () => {
        riskInputRef.current?.focus({ preventScroll: true });
        riskInputRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      },
      0
    );
  }
  function updateHolding(index: number, patch: Partial<HoldingInput>) {
    setHoldings((current) =>
      current.map((holding, idx) => (idx === index ? { ...holding, ...patch } : holding))
    );
  }
  function addHolding(candidate?: CandidateAsset) {
    setHoldings((current) => [
      ...current,
      {
        symbol: candidate?.symbol ?? "",
        name: candidate?.name ?? "",
        amount: 0,
        category: candidate?.category ?? "other"
      }
    ]);
  }
  function applyRecommendedProfile() {
    const recommended = recommendedProfile(profile.risk_score);
    setProfile((current) => ({
      ...current,
      ...recommended,
      risk_score: current.risk_score,
      risk_profile: riskProfileKind(current.risk_score),
      allow_tqqq: current.risk_score >= 45,
      prefer_200ma: true
    }));
    setStatus(
      `리스크 ${profile.risk_score}점 기준 권장값을 적용했습니다. ${profileRecommendationText(profile.risk_score)}`
    );
  }
  const loadMarket = useCallback(async (options?: { silent?: boolean }) => {
    if (marketRefreshInFlight.current) return;
    marketRefreshInFlight.current = true;
    const silent = Boolean(options?.silent);
    if (!silent) {
      setLoading("market");
      setStatus("QQQ 시장 지표를 갱신하는 중입니다...");
    }
    try {
      const rows = await fetchHistory("QQQ");
      const latest = rows[rows.length - 1];
      const nextSma200 = sma(rows, 200);
      const nextSma20 = sma(rows, 20);
      const nextSma50 = sma(rows, 50);
      const nextHigh20 = rollingHigh(rows, 20);
      if (!nextSma200) throw new Error("200일선 계산 데이터가 부족합니다.");
      setMarket({
        qqq_close: latest.close,
        qqq_sma200: nextSma200,
        qqq_sma20: nextSma20,
        qqq_sma50: nextSma50,
        qqq_high20: nextHigh20,
        as_of: latest.date
      });
      const quoteSymbols = ["QQQ", "QQQM", "TQQQ", "QLD", "SGOV", "BIL"];
      const quoteResults = await Promise.allSettled(
        quoteSymbols.map((symbol) => fetchQuote(symbol))
      );
      const nextQuotes: Record<string, QuoteSnapshot> = {};
      quoteResults.forEach((result) => {
        if (result.status === "fulfilled") nextQuotes[result.value.symbol] = result.value;
      });
      if (Object.keys(nextQuotes).length) setQuotes(nextQuotes);
      const fxResult = await Promise.allSettled([fetchUsdKrw()]);
      if (fxResult[0]?.status === "fulfilled") setUsdKrw(fxResult[0].value);
      const refreshedAt = new Date().toLocaleTimeString("ko-KR", {
        hour: "2-digit",
        minute: "2-digit"
      });
      setStatus(`${silent ? "자동 " : ""}시장 지표 갱신 완료: ${latest.date} · ${refreshedAt}`);
    } catch (error) {
      if (!silent) setStatus(error instanceof Error ? error.message : "시장 지표 갱신 실패");
    } finally {
      marketRefreshInFlight.current = false;
      if (!silent) setLoading("");
    }
  }, []);

  useEffect(() => {
    void loadMarket({ silent: true });
    const timer = window.setInterval(() => {
      void loadMarket({ silent: true });
    }, AUTO_MARKET_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [loadMarket]);
  async function runStrategy() {
    if (totalCapital <= 0) {
      setStatus("현재 보유금액 또는 현금을 먼저 입력하세요. 현금만 있어도 시작할 수 있습니다.");
      return;
    }
    setLoading("strategy");
    setStatus("전략 추천을 계산하는 중입니다...");
    try {
      const result = await requestRecommendation(holdings, cash, profile, market, useAi);
      setRecommendation(result);
      setStatus(
        result.ai_used ? "AI 코치 리포트를 생성했습니다." : "규칙 기반 리포트를 생성했습니다."
      );
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
      if (useResearchPreset) {
        if (!presetCompatible) {
          throw new Error("연구 기반 일일 적립 규칙은 현재 TQQQ·QQQM·현금 보유 상태에서만 바로 채택할 수 있습니다.");
        }
        const researchConfig: ResearchStrategyConfig = {
          strategy: "tqqq_daily_200ma",
          daily_base_tqqq_ratio: 70,
          daily_base_one_x_ratio: 30,
          one_x_symbol: "QQQM",
          ma_exit_band_pct: 2,
          defense_mode: "cash",
          monthly_contribution: cashflow.monthlyContribution,
          moving_average_days: 200,
          one_x_upfront_monthly: false,
          preset_id: RESEARCH_PRESET_ID,
          preset_version: RESEARCH_PRESET_VERSION
        };
        const tqqqValue = holdings
          .filter((holding) => holding.symbol.toUpperCase() === "TQQQ")
          .reduce((sum, holding) => sum + holding.amount, 0);
        const oneXValue = holdings
          .filter((holding) => holding.symbol.toUpperCase() === "QQQM")
          .reduce((sum, holding) => sum + holding.amount, 0);
        await adoptResearchStrategy(researchConfig, market, tqqqValue, oneXValue, cash);
      } else {
        await adoptManagedStrategy(plan, market, totalCapital);
      }
      setStatus(
        "전략을 저장했습니다. 상단의 전략 관리 메뉴에서 운용 가이드와 기록장을 확인하세요."
      );
      navigate("/manage");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "전략 저장에 실패했습니다.");
    } finally {
      setLoading("");
    }
  }

  return (
    <section className="page-grid strategy-workspace">
      {!recommendation ? (
        <article className="strategy-onboarding" aria-label="전략 수립 진행 단계">
          <div>
            <span className="section-label">전략 수립 · {onboardingStep}/3</span>
            <strong>지금은 {onboardingStep === 1 ? "보유 자산과 현금" : onboardingStep === 2 ? "지킬 수 있는 위험 수준" : "추천 전략 비교"}을 확인합니다.</strong>
          </div>
          <ol>
            <li className={onboardingStep === 1 ? "active" : ""}>
              <span>1</span>
              <div><strong>현재 자금</strong><small>보유 종목과 현금</small></div>
            </li>
            <li className={onboardingStep === 2 ? "active" : ""}>
              <span>2</span>
              <div><strong>위험 성향</strong><small>지킬 수 있는 수준</small></div>
            </li>
            <li className={onboardingStep === 3 ? "active" : ""}>
              <span>3</span>
              <div><strong>비교 후 채택</strong><small>하나의 규칙으로 관리</small></div>
            </li>
          </ol>
        </article>
      ) : null}
      <div className="hero-panel strategy-hero">
        <div>
          <span className="section-label">내 투자 규칙 만들기</span>
          <h2>보유 자산과 위험 한도를 하나의 운용 규칙으로 만듭니다.</h2>
          <p>{status}</p>
          {!recommendation ? (
            <div className="onboarding-market-note">
              <span>QQQ 기준일 {market.as_of}</span>
              <span>200일선 {formatUsd(market.qqq_sma200)}</span>
              <span>과거 검증은 미래 수익을 보장하지 않습니다.</span>
            </div>
          ) : null}
        </div>
        <div className="hero-actions">
          <button onClick={() => loadMarket()} disabled={loading === "market"}>
            <RefreshCw size={17} />
            {loading === "market" ? "갱신 중" : "시장 지표 갱신"}
          </button>
          <button
            className="primary"
            onClick={runStrategy}
            disabled={loading === "strategy" || setupStep === 1}
            title={setupStep === 1 ? "보유금액 또는 현금 입력 후 위험 성향을 정하세요." : undefined}
          >
            <Bot size={17} />
            {loading === "strategy" ? "추천 중" : "전략 추천"}
          </button>
        </div>
      </div>

      {totalCapital > 0 || recommendation ? <div className="metric-grid">
        <Metric label="총 자산" value={formatKrw(totalCapital)} note="보유금액 + 현금" />
        <Metric
          label="리스크 허용도"
          value={`${profile.risk_score}`}
          note={riskBand(profile.risk_score)}
        />
        <Metric
          label="QQQ 200일선 대비"
          value={formatPct((market.qqq_close / market.qqq_sma200 - 1) * 100)}
          note={market.as_of}
        />
        <Metric
          label="QQQ / 200일선"
          value={formatUsd(market.qqq_close)}
          note={formatUsd(market.qqq_sma200)}
        />
      </div> : null}

      {recommendation && selectedPlan ? (
        <DecisionSummary
          recommendation={recommendation}
          plan={selectedPlan}
          quotes={quotes}
          usdKrw={usdKrw}
          onAdopt={adoptPlan}
          adopting={loading === "adopt"}
          researchPresetActive={useResearchPreset}
        />
      ) : null}

      <div className={`content-grid strategy-builder-grid ${recommendation ? "has-recommendation" : ""}`}>
        {recommendation ? <article className="panel span-12 data-quality-card strategy-trust-panel">
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
        </article> : null}

        <article
          id="portfolio-input"
          className={`panel span-7 strategy-input-panel ${setupStep === 1 ? "onboarding-active-panel" : "onboarding-complete-panel"}`}
        >
          <PanelTitle icon={<Target size={18} />} title="포트폴리오 입력" />
          {setupStep === 2 && !recommendation ? (
            <div className="strategy-input-summary">
              <div>
                <span>입력 완료</span>
                <strong>총 자산 {formatKrw(totalCapital)} · 월 추가금 {formatKrw(cashflow.monthlyContribution)}</strong>
              </div>
              <button type="button" onClick={() => setSetupStep(1)}>
                입력 수정
              </button>
            </div>
          ) : null}
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
            <button type="button" onClick={loadExamplePortfolio}>
              예시 불러오기
            </button>
            <button onClick={applyQuickInput}>
              <Plus size={16} />
              반영
            </button>
          </div>
          <div className="holdings-list">
            {holdings.map((holding, index) => (
              <div className="holding-row" key={`${holding.symbol}-${index}`}>
                <input
                  value={holding.symbol}
                  onChange={(event) => updateHolding(index, { symbol: event.target.value })}
                  placeholder="심볼"
                />
                <input
                  value={holding.name}
                  onChange={(event) => updateHolding(index, { name: event.target.value })}
                  placeholder="이름"
                />
                <input
                  type="number"
                  value={holding.amount}
                  onChange={(event) => updateHolding(index, { amount: Number(event.target.value) })}
                />
                <select
                  value={holding.category}
                  onChange={(event) => updateHolding(index, { category: event.target.value })}
                >
                  <option value="nasdaq_leverage">나스닥 레버리지</option>
                  <option value="semiconductor">반도체</option>
                  <option value="broad_market">광범위 지수</option>
                  <option value="cash_like">현금성</option>
                  <option value="other">기타</option>
                </select>
                <button
                  onClick={() =>
                    setHoldings((current) => current.filter((_, idx) => idx !== index))
                  }
                  aria-label="삭제"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
          <div className="inline-actions">
            <button type="button" onClick={startWithCashOnly}>
              현금만으로 시작
            </button>
            <button onClick={() => addHolding()}>
              <Plus size={16} />
              보유 추가
            </button>
            <label>
              현금
              <input
                ref={cashInputRef}
                type="number"
                value={cash}
                onChange={(event) => setCash(Number(event.target.value))}
              />
            </label>
            <label>
              월 추가금
              <input
                type="number"
                min={0}
                step={100000}
                value={cashflow.monthlyContribution}
                onChange={(event) =>
                  setCashflow((current) => ({
                    ...current,
                    monthlyContribution: Math.max(0, Number(event.target.value))
                  }))
                }
              />
            </label>
            <label>
              월급일
              <input
                type="number"
                min={1}
                max={31}
                value={cashflow.payDay}
                onChange={(event) =>
                  setCashflow((current) => ({
                    ...current,
                    payDay: Math.min(31, Math.max(1, Number(event.target.value)))
                  }))
                }
              />
            </label>
          </div>
          <p className="onboarding-cashflow-note">
            월 추가금은 전략 채택 뒤 오늘 판단 화면의 월급일 코치에 그대로 연결됩니다.
          </p>
          {setupStep === 1 ? (
            <div className="onboarding-next-action">
              <button className="primary" type="button" onClick={advanceToRisk}>
                다음: 위험 성향 정하기
              </button>
              <small>보유금액 또는 현금을 입력하면 다음 단계로 이동합니다.</small>
            </div>
          ) : null}
        </article>

        {setupStep === 1 ? (
          <aside className="panel strategy-onboarding-preview" aria-label="전략 수립 결과 미리보기">
            <span className="section-label">입력 후 받게 될 결과</span>
            <h3>내 운용 규칙의 초안을 확인합니다.</h3>
            <p>
              보유 자산과 현금을 입력하면, 감당할 수 있는 위험 수준에 맞춰 실행 가능한
              투자 비중과 관리 기준을 제안합니다.
            </p>
            <ol>
              <li><span>01</span><div><strong>권장 투자 비중</strong><small>자산별 역할과 최대 비중</small></div></li>
              <li><span>02</span><div><strong>위험 관리 기준</strong><small>현금 비중과 손실 방어 원칙</small></div></li>
              <li><span>03</span><div><strong>오늘의 실행 가이드</strong><small>다음 납입일과 행동 기준</small></div></li>
            </ol>
            <div className="strategy-preview-note">
              <strong>첫 단계에서는 보유 자산만 입력하세요.</strong>
              <span>추천은 아직 실행되지 않으며, 다음 단계에서 위험 성향을 함께 확인합니다.</span>
            </div>
          </aside>
        ) : null}

        {setupStep === 2 ? <article ref={riskInputRef} id="risk-input" tabIndex={-1} className="panel span-5 strategy-risk-panel">
          <PanelTitle icon={<SlidersHorizontal size={18} />} title="리스크 설정" />
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
              onChange={(event) =>
                setProfile({ ...profile, risk_score: Number(event.target.value) })
              }
            />
          </div>
          <section className={`research-preset-choice ${useResearchPreset ? "selected" : ""}`} aria-labelledby="research-preset-title">
            <div>
              <span className="section-label">연구 기반 운용 규칙</span>
              <h3 id="research-preset-title">7:3 · 조기방어 2% · 현금 방어</h3>
              <p>1999년 이후 동일 조건 비교에서 종합 83점으로 상위권에 오른 규칙입니다. 미래 성과를 보장하지 않습니다.</p>
            </div>
            <ul>
              <li>월 추가금은 TQQQ 70% · QQQM 30%로 일일 집행</li>
              <li>QQQ 200일선 +2% 아래 2거래일 확인 시 현금·SGOV 방어</li>
            </ul>
            <button
              type="button"
              className={useResearchPreset ? "primary" : ""}
              onClick={() => setUseResearchPreset((current) => !current)}
              disabled={!presetCompatible}
            >
              {useResearchPreset ? "연구 규칙 적용됨" : "이 규칙 적용"}
            </button>
            {!presetCompatible ? <small>현재는 TQQQ·QQQM·현금 보유 상태에서만 이 규칙을 바로 채택할 수 있습니다.</small> : null}
          </section>
          <p className="risk-disclosure">
            레버리지 ETF는 짧은 기간에도 큰 손실이 발생할 수 있습니다. 추천은 과거 데이터와 규칙 기반의
            교육용 판단 보조이며, 수익이나 손실 한계를 보장하지 않습니다.
          </p>
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
            <small>
              목표 종목수, 최소 현금, 최대 TQQQ 비중, AI 코치 사용 여부를 조정하되 최종 추천은 QQQ
              이격도 상한을 우선합니다.
            </small>
          </div>
          {showAdvanced ? (
            <div className="profile-grid">
              <label>
                목표 종목 수
                <input
                  type="number"
                  value={profile.target_count}
                  onChange={(event) =>
                    setProfile({ ...profile, target_count: Number(event.target.value) })
                  }
                />
              </label>
              <label>
                최소 현금 %
                <input
                  type="number"
                  value={profile.min_cash_ratio}
                  onChange={(event) =>
                    setProfile({ ...profile, min_cash_ratio: Number(event.target.value) })
                  }
                />
              </label>
              <label>
                최대 TQQQ %
                <input
                  type="number"
                  value={profile.max_tqqq_ratio}
                  onChange={(event) =>
                    setProfile({ ...profile, max_tqqq_ratio: Number(event.target.value) })
                  }
                />
              </label>
              <label>
                최대 비핵심 위성 %
                <input
                  type="number"
                  value={profile.max_semiconductor_ratio}
                  onChange={(event) =>
                    setProfile({ ...profile, max_semiconductor_ratio: Number(event.target.value) })
                  }
                />
              </label>
              <label>
                단일 종목 최대 %
                <input
                  type="number"
                  value={profile.max_single_position_ratio}
                  onChange={(event) =>
                    setProfile({
                      ...profile,
                      max_single_position_ratio: Number(event.target.value)
                    })
                  }
                />
              </label>
              <label className="switch advanced-switch">
                <input
                  type="checkbox"
                  checked={useAi}
                  onChange={(event) => setUseAi(event.target.checked)}
                />
                AI 코치 보조 사용
              </label>
            </div>
          ) : null}
          <div className="onboarding-next-action">
            <button className="primary" type="button" onClick={runStrategy} disabled={loading === "strategy"}>
              <Bot size={16} /> {loading === "strategy" ? "전략 비교 중..." : "전략 3개 비교"}
            </button>
            <small>추천 결과에서 목표 비중, 약한 상황, 검증 기준을 비교할 수 있습니다.</small>
          </div>
        </article> : null}

        {setupStep === 2 || recommendation ? <details className="panel span-12 optional-panel strategy-candidates-panel">
          <summary>상세 근거와 후보군</summary>
          <div className="panel-headline">
            <PanelTitle icon={<Search size={18} />} title="후보군 추가" />
            <button type="button" onClick={() => setShowCandidates((current) => !current)}>
              {showCandidates ? "후보군 접기" : "후보군 열기"}
            </button>
          </div>
          <p className="muted">
            처음에는 현재 보유 종목과 리스크만 입력해도 됩니다. 검증된 ETF 후보를 직접 추가하고 싶을
            때만 열어 사용하세요.
          </p>
          {showCandidates ? (
            <div className="candidate-list compact">
              {candidateAssets.map((asset) => (
                <button
                  className="candidate-chip"
                  key={asset.symbol}
                  onClick={() => addHolding(asset)}
                >
                  <strong>{asset.symbol}</strong>
                  <span>{asset.role}</span>
                </button>
              ))}
            </div>
          ) : null}
        </details> : null}

        {recommendation && (
          <article className="panel span-12 coach-report">
            <span className="section-label">Coach Report</span>
            <h2>{recommendation.coach_report.headline}</h2>
            <p>{recommendation.coach_report.diagnosis}</p>
            <div className="report-columns">
              <ListBlock title="추천 이유" items={recommendation.coach_report.why} />
              <ListBlock title="다음 액션" items={recommendation.coach_report.next_actions} />
              <details className="secondary-details"><summary>모니터링과 주의사항</summary><div className="report-columns"><ListBlock title="모니터링" items={recommendation.coach_report.monitoring_rules} /><ListBlock title="주의" items={recommendation.coach_report.warnings} tone="warn" /></div></details>
            </div>
          </article>
        )}

        {recommendation?.candidate_opinions?.length ? (
          <details className="panel span-12 strategy-evidence-panel optional-panel">
            <summary>후보군 판단과 상세 근거</summary>
            <div className="opinion-grid">
              {recommendation.candidate_opinions.map((opinion) => (
                <div className={`opinion-card ${opinion.stance}`} key={opinion.symbol}>
                  <span>{stanceLabel(opinion.stance)}</span>
                  <strong>{opinion.symbol}</strong>
                  <small>{opinion.reason}</small>
                </div>
              ))}
            </div>
          </details>
        ) : null}

        {recommendation && (
          <article className="panel span-12 recommendation-plan-panel">
            <PanelTitle icon={<CheckCircle2 size={18} />} title="추천 포트폴리오" />
            <div className="plan-tabs">
              {recommendation.plans.map((plan) => (
                <button
                  key={plan.id}
                  className={plan.id === selectedPlan?.id ? "selected" : ""}
                  onClick={() => setSelectedPlanId(plan.id)}
                >
                  {plan.title}
                </button>
              ))}
            </div>
            {selectedPlan ? (
              <PlanDetail plan={selectedPlan} onAdopt={adoptPlan} adopting={loading === "adopt"} />
            ) : null}
          </article>
        )}
      </div>
    </section>
  );
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <article className="metric panel">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}
function PanelTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <h2 className="panel-title">
      {icon}
      {title}
    </h2>
  );
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
function DecisionSummary({
  recommendation,
  plan,
  quotes,
  usdKrw,
  onAdopt,
  adopting,
  researchPresetActive
}: {
  recommendation: StrategyResponse;
  plan: StrategyPlan;
  quotes: Record<string, QuoteSnapshot>;
  usdKrw: FxSnapshot | null;
  onAdopt: (plan: StrategyPlan) => void;
  adopting: boolean;
  researchPresetActive: boolean;
}) {
  const topAllocations = [...plan.allocations]
    .sort((a, b) => b.target_ratio - a.target_ratio)
    .slice(0, 3);
  const leverageMetric = plan.risk_metrics.find(
    (metric) => metric.label.includes("레버리지") || metric.label.includes("실효")
  );
  const capMetric = plan.risk_metrics.find((metric) => metric.label.includes("상한"));
  const primaryAction = recommendation.coach_report.next_actions[0] ?? plan.summary;
  const primaryWarning = recommendation.coach_report.warnings[0];
  const executableAllocations = topAllocations
    .map((allocation) => {
      const quote = quotes[allocation.symbol];
      if (!quote || !usdKrw?.rate) return null;
      const krwPerShare = quote.price * usdKrw.rate;
      const shares = allocation.target_amount / krwPerShare;
      return { allocation, quote, shares, krwPerShare };
    })
    .filter(Boolean) as Array<{
    allocation: Allocation;
    quote: QuoteSnapshot;
    shares: number;
    krwPerShare: number;
  }>;
  const qqqAllocation = plan.allocations.find((allocation) => allocation.symbol === "QQQ");
  const qqqShareHint =
    qqqAllocation &&
    quotes.QQQ &&
    quotes.QQQM &&
    usdKrw?.rate &&
    qqqAllocation.target_amount < quotes.QQQ.price * usdKrw.rate
      ? "QQQ 목표금액이 1주 가격보다 작습니다. 같은 Nasdaq-100 1x 역할은 QQQM으로 우선 검토하세요."
      : "주문 전 현재가, 환율, 예상 체결가를 다시 입력해 실제 매수 수량을 확인하세요.";
  return (
    <article className="decision-summary panel">
      <div className="decision-main">
        <span className="section-label">오늘의 판단</span>
        <h2>{recommendation.coach_report.headline}</h2>
        <p>{primaryAction}</p>
        {researchPresetActive ? (
          <p className="decision-preset-note">채택하면 연구 기반의 7:3 일일 적립·조기 방어 규칙으로 저장됩니다.</p>
        ) : null}
        <div className="decision-actions">
          <button className="primary" onClick={() => onAdopt(plan)} disabled={adopting}>
            {adopting ? "저장 중" : "이 전략 채택"}
          </button>
          <span>
            {recommendation.market_regime} · QQQ 200일선 대비{" "}
            {formatPct(recommendation.qqq_distance_from_200ma)}
          </span>
        </div>
        <details className="decision-evidence">
          <summary>채택 전 확인</summary>
          <div>
            <section>
              <strong>왜 이 전략인가</strong>
              <p>{recommendation.coach_report.why[0] ?? plan.pros[0] ?? plan.summary}</p>
            </section>
            <section>
              <strong>약한 상황</strong>
              <p>{plan.cons[0] ?? primaryWarning ?? "과거 결과는 미래 수익을 보장하지 않습니다."}</p>
            </section>
            <section>
              <strong>검증 기준</strong>
              <p>QQQ 200일선, 목표 비중, 실행 규칙을 기준으로 관리합니다.</p>
            </section>
          </div>
        </details>
      </div>
      <div className="decision-stack">
        <div className="decision-card accent">
          <span>추천안</span>
          <strong>{plan.title}</strong>
          <small>{plan.summary}</small>
        </div>
        <div className="decision-card">
          <span>핵심 비중</span>
          <div className="allocation-pills">
            {topAllocations.map((allocation) => (
              <em key={allocation.symbol}>
                {allocation.symbol} {allocation.target_ratio.toFixed(1)}%
              </em>
            ))}
          </div>
        </div>
        <div className="decision-card">
          <span>위험 확인</span>
          <strong>
            {capMetric
              ? `${capMetric.label} ${capMetric.value}`
              : leverageMetric
                ? `${leverageMetric.label} ${leverageMetric.value}`
                : `${plan.scores.risk_score}점`}
          </strong>
          <small>{primaryWarning}</small>
        </div>
        <div className="decision-card execution">
          <span>매수 가능 수량</span>
          {executableAllocations.length ? (
            <div className="execution-pills">
              {executableAllocations.map(({ allocation, shares }) => (
                <em key={allocation.symbol}>
                  {allocation.symbol} 약 {shares.toFixed(shares >= 10 ? 1 : 2)}주
                </em>
              ))}
            </div>
          ) : (
            <strong>시세 갱신 후 표시</strong>
          )}
          <small>{qqqShareHint}</small>
        </div>
      </div>
    </article>
  );
}
function PlanDetail({
  plan,
  onAdopt,
  adopting
}: {
  plan: StrategyPlan;
  onAdopt: (plan: StrategyPlan) => void;
  adopting: boolean;
}) {
  return (
    <div className="plan-detail">
      <p>{plan.summary}</p>
      <button className="primary" onClick={() => onAdopt(plan)} disabled={adopting}>
        {adopting ? "전략 저장 중..." : "이 전략 채택하기"}
      </button>
      <div className="score-grid">
        <MetricCard
          label="신뢰도"
          value={`${plan.scores.confidence_score}`}
          note="규칙/방어/시장 적합성"
        />
        <MetricCard label="위험도" value={`${plan.scores.risk_score}`} note="레버리지와 집중도" />
        <MetricCard label="적합도" value={`${plan.scores.fit_score}`} note="리스크 허용치와 거리" />
        <MetricCard
          label="수익 탄력"
          value={`${plan.scores.expected_return_score}`}
          note="상승장 반응도"
        />
      </div>
      <div className="plan-section-grid">
        <DataTable
          title="목표 비중"
          rows={plan.allocations.map((item) => [
            item.symbol,
            `${item.target_ratio.toFixed(1)}%`,
            formatKrw(item.target_amount)
          ])}
        />
        <DataTable
          title="조정 액션"
          rows={plan.actions.map((item) => [
            item.symbol,
            actionLabel(item.action),
            item.amount ? formatKrw(item.amount) : item.reason
          ])}
        />
      </div>
      <div className="plan-section-grid">
        <DataTable
          title="TQQQ 집행 원칙"
          rows={plan.buy_plan.map((item) => [item.step, `${item.ratio_of_target}%`, item.note])}
        />
        <DataTable
          title="방어/회수 원칙"
          rows={plan.sell_plan.map((item) => [item.step, `${item.ratio_of_target}%`, item.trigger])}
        />
      </div>
      <div className="risk-strip">
        {plan.risk_metrics.map((metric) => (
          <div className={`risk-pill ${metric.level}`} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </div>
        ))}
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
function DataTable({ title, rows }: { title: string; rows: string[][] }) {
  return (
    <div>
      <h3>{title}</h3>
      <table>
        <tbody>
          {rows.map((row) => (
            <tr key={row.join("-")}>
              {row.map((cell) => (
                <td key={cell}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
