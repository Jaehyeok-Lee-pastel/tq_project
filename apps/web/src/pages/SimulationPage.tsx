import { useEffect, useState } from "react";
import { ArrowLeft, FlaskConical, HandCoins, LineChart, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

type PriceRow = { date: string; close: number };
type QuoteResponse = {
  symbol: string;
  provider: string;
  price: number;
  as_of: string;
  freshness: string;
  source_note: string;
};
type BacktestStrategy = "qqq_buy_hold" | "tqqq_buy_hold" | "tqqq_200ma" | "qld_200ma";
type EquityPoint = { date: string; equity: number; drawdown: number; position: string };
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
  longest_drawdown_days: number;
};
type ProjectionScenario = {
  name: "bear" | "base" | "bull";
  annual_return: number;
  ending_capital: number;
  profit: number;
  note: string;
};
type RegimePerformance = {
  regime: "uptrend" | "downtrend" | "shock";
  label: string;
  days: number;
  return_pct: number;
  win_rate: number;
  max_drawdown: number;
};
type BacktestResponse = {
  strategy: BacktestStrategy;
  strategy_name: string;
  moving_average_days?: number;
  benchmark_name: string;
  period_start: string;
  period_end: string;
  equity_curve: EquityPoint[];
  benchmark_curve: EquityPoint[];
  metrics: BacktestMetrics;
  benchmark_metrics: BacktestMetrics;
  yearly_returns: { year: number; return_pct: number }[];
  regime_performance: RegimePerformance[];
  trades: { date: string; action: "buy" | "sell"; symbol: string; ratio: number; reason: string }[];
  projection: ProjectionScenario[];
  interpretation: string[];
};
type PaperPosition = {
  id: string;
  symbol: string;
  amount: number;
  entryPrice: number;
  currentPrice: number;
  buyDate: string;
};
type PaperStrategy = {
  id: string;
  strategy: BacktestStrategy;
  name: string;
  amount: number;
  startDate: string;
  startSymbol: string;
  startPrice: number;
  currentPrice: number;
  targetRatio: number;
};
type ManagedTestDraft = {
  source: "managed_strategy";
  strategy_id: string;
  version: number;
  title: string;
  summary: string;
  initial_capital: number;
  strategy: BacktestStrategy;
  tqqq_target_ratio: number;
  qld_target_ratio: number;
  cash_yield: number;
  projection_years: number;
  allocations: {
    symbol: string;
    role: string;
    target_ratio: number;
    target_amount: number;
  }[];
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const paperKey = "tqcoach.paperPositions";
const strategyPaperKey = "tqcoach.paperStrategies";
const managedTestDraftKey = "tqcoach.managedTestDraft";
const symbols = ["TQQQ", "QLD", "QQQ", "SMH", "SOXX", "VOO", "SGOV"];
const strategyNames: Record<BacktestStrategy, string> = {
  qqq_buy_hold: "QQQ 장기 보유",
  tqqq_buy_hold: "TQQQ 장기 보유",
  tqqq_200ma: "QQQ 200일선 기반 TQQQ",
  qld_200ma: "QQQ 200일선 기반 QLD",
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
function actionLabel(action: "buy" | "sell") {
  return action === "buy" ? "매수" : "매도";
}
function scenarioLabel(name: ProjectionScenario["name"]) {
  return { bear: "보수", base: "기준", bull: "낙관" }[name];
}
function allocationRatio(draft: ManagedTestDraft, predicate: (symbol: string) => boolean) {
  return draft.allocations
    .filter((allocation) => predicate(allocation.symbol.toUpperCase()))
    .reduce((sum, allocation) => sum + allocation.target_ratio, 0);
}
function managedEngineLabel(draft: ManagedTestDraft) {
  if (draft.strategy === "tqqq_200ma") return "QQQ 200일선 기반 TQQQ";
  if (draft.strategy === "qld_200ma") return "QQQ 200일선 기반 QLD";
  if (draft.strategy === "qqq_buy_hold") return "QQQ 장기 보유";
  return "TQQQ 장기 보유";
}
function loadPaperPositions() {
  try {
    const raw = localStorage.getItem(paperKey);
    return raw ? (JSON.parse(raw) as PaperPosition[]) : [];
  } catch {
    return [];
  }
}
function loadPaperStrategies() {
  try {
    const raw = localStorage.getItem(strategyPaperKey);
    return raw ? (JSON.parse(raw) as PaperStrategy[]) : [];
  } catch {
    return [];
  }
}
function loadManagedTestDraft() {
  try {
    const raw = localStorage.getItem(managedTestDraftKey);
    return raw ? (JSON.parse(raw) as ManagedTestDraft) : null;
  } catch {
    return null;
  }
}
async function fetchHistory(symbol: string): Promise<PriceRow[]> {
  const response = await fetch(`${apiBaseUrl}/market/history/${symbol}?limit=1200`);
  if (!response.ok) throw new Error(`시장 데이터 API 오류: ${response.status}`);
  return ((await response.json()) as { rows: PriceRow[] }).rows;
}
async function fetchQuote(symbol: string): Promise<QuoteResponse> {
  const response = await fetch(`${apiBaseUrl}/market/quote/${symbol}`);
  if (!response.ok) throw new Error(`실시간/장중 시세 API 오류: ${response.status}`);
  return (await response.json()) as QuoteResponse;
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
async function requestManagedBacktest(strategyId: string, payload: { projection_years: number; cash_yield: number }) {
  const params = new URLSearchParams({
    projection_years: String(payload.projection_years),
    cash_yield: String(payload.cash_yield),
  });
  const response = await fetch(`${apiBaseUrl}/managed-strategies/${strategyId}/backtest?${params.toString()}`, {
    method: "POST",
  });
  if (!response.ok) throw new Error(`저장 전략 백테스트 API 오류: ${response.status}`);
  return (await response.json()) as BacktestResponse;
}

export function SimulationPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("백테스트와 미래 시나리오를 통해 전략의 기대값과 위험을 검증합니다.");
  const [loading, setLoading] = useState<"backtest" | "paper" | "">("");
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null);
  const [paperPositions, setPaperPositions] = useState<PaperPosition[]>(loadPaperPositions);
  const [paperStrategies, setPaperStrategies] = useState<PaperStrategy[]>(loadPaperStrategies);
  const [managedDraft, setManagedDraft] = useState<ManagedTestDraft | null>(loadManagedTestDraft);
  const [paperDraft, setPaperDraft] = useState({ symbol: "TQQQ", amount: 500000 });
  const [strategyDraft, setStrategyDraft] = useState({
    strategy: "tqqq_200ma" as BacktestStrategy,
    amount: 2500000,
  });
  const [paperRefreshInfo, setPaperRefreshInfo] = useState({
    lastCheckedAt: "",
    changedCount: 0,
    unchangedCount: 0,
    failedSymbols: [] as string[],
    sourceNote: "",
    message: "아직 현재가 갱신을 실행하지 않았습니다.",
  });
  const [config, setConfig] = useState({
    strategy: "tqqq_200ma" as BacktestStrategy,
    initial_capital: 2500000,
    tqqq_target_ratio: 60,
    qld_target_ratio: 70,
    projection_years: 3,
    cash_yield: 3,
  });

  useEffect(() => {
    localStorage.setItem(paperKey, JSON.stringify(paperPositions));
  }, [paperPositions]);
  useEffect(() => {
    localStorage.setItem(strategyPaperKey, JSON.stringify(paperStrategies));
  }, [paperStrategies]);
  useEffect(() => {
    if (!managedDraft) return;
    setConfig((current) => ({
      ...current,
      strategy: managedDraft.strategy,
      initial_capital: Math.round(managedDraft.initial_capital),
      tqqq_target_ratio: Number(managedDraft.tqqq_target_ratio.toFixed(1)),
      qld_target_ratio: Number(managedDraft.qld_target_ratio.toFixed(1)),
      projection_years: managedDraft.projection_years,
      cash_yield: managedDraft.cash_yield,
    }));
    setStrategyDraft({
      strategy: managedDraft.strategy,
      amount: Math.round(managedDraft.initial_capital),
    });
    if (window.location.search.includes("source=managed")) {
      setStatus(`${managedDraft.title} v${managedDraft.version} 전략을 테스트랩으로 불러왔습니다. 백테스트를 실행해 과거 성과와 미래 시나리오를 확인하세요.`);
    }
  }, [managedDraft]);

  async function runBacktest() {
    setLoading("backtest");
    setStatus("과거 백테스트를 계산하는 중입니다...");
    try {
      const result = await requestBacktest(config);
      setBacktest(result);
      setStatus(`${result.strategy_name} 백테스트를 계산했습니다.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "백테스트 실패");
    } finally {
      setLoading("");
    }
  }
  async function runManagedBacktest() {
    if (!managedDraft) return;
    setLoading("backtest");
    setStatus(`${managedDraft.title} v${managedDraft.version} 저장 전략 기준으로 백테스트를 계산하는 중입니다...`);
    try {
      const result = await requestManagedBacktest(managedDraft.strategy_id, {
        projection_years: config.projection_years,
        cash_yield: config.cash_yield,
      });
      setBacktest(result);
      setStatus(`${managedDraft.title} v${managedDraft.version} 저장 전략 백테스트를 계산했습니다.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "저장 전략 백테스트 실패");
    } finally {
      setLoading("");
    }
  }
  async function getLatestPrice(symbol: string) {
    const quote = await fetchQuote(symbol);
    return quote.price;
  }
  async function addPaperPosition() {
    const symbol = paperDraft.symbol.toUpperCase();
    setLoading("paper");
    setStatus(`${symbol} 현재가를 불러오는 중입니다...`);
    try {
      const latestPrice = await getLatestPrice(symbol);
      setPaperPositions((current) => [
        ...current,
        { id: `${symbol}-${Date.now()}`, symbol, amount: paperDraft.amount, entryPrice: latestPrice, currentPrice: latestPrice, buyDate: new Date().toISOString().slice(0, 10) },
      ]);
      setStatus(`${symbol} 모의 매수를 기록했습니다.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "모의 매수 실패");
    } finally {
      setLoading("");
    }
  }
  function targetSymbolForStrategy(strategy: BacktestStrategy) {
    if (strategy === "qld_200ma") return "QLD";
    if (strategy === "qqq_buy_hold") return "QQQ";
    return "TQQQ";
  }
  function targetRatioForStrategy(strategy: BacktestStrategy) {
    if (strategy === "tqqq_200ma") return config.tqqq_target_ratio / 100;
    if (strategy === "qld_200ma") return config.qld_target_ratio / 100;
    return 1;
  }
  async function addPaperStrategy() {
    const symbol = targetSymbolForStrategy(strategyDraft.strategy);
    setLoading("paper");
    setStatus(`${strategyNames[strategyDraft.strategy]} 전략을 모의 시작하는 중입니다...`);
    try {
      const latestPrice = await getLatestPrice(symbol);
      setPaperStrategies((current) => [
        ...current,
        {
          id: `${strategyDraft.strategy}-${Date.now()}`,
          strategy: strategyDraft.strategy,
          name: strategyNames[strategyDraft.strategy],
          amount: strategyDraft.amount,
          startDate: new Date().toISOString().slice(0, 10),
          startSymbol: symbol,
          startPrice: latestPrice,
          currentPrice: latestPrice,
          targetRatio: targetRatioForStrategy(strategyDraft.strategy),
        },
      ]);
      setStatus(`${strategyNames[strategyDraft.strategy]} 전략 모의 운용을 시작했습니다.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "전략 모의 시작 실패");
    } finally {
      setLoading("");
    }
  }
  function clearManagedDraft() {
    localStorage.removeItem(managedTestDraftKey);
    setManagedDraft(null);
    setStatus("관리전략 연결을 해제했습니다. 수동 조건으로 테스트할 수 있습니다.");
  }
  async function refreshPaperPositions() {
    const trackedSymbols = [
      ...paperPositions.map((position) => position.symbol),
      ...paperStrategies.map((strategy) => strategy.startSymbol),
    ];
    if (!trackedSymbols.length) {
      setPaperRefreshInfo({
        lastCheckedAt: new Date().toLocaleString("ko-KR"),
        changedCount: 0,
        unchangedCount: 0,
        failedSymbols: [],
        sourceNote: "",
        message: "갱신할 모의 보유 또는 모의 전략이 없습니다.",
      });
      return;
    }
    setLoading("paper");
    setStatus("모의 보유 현재가를 갱신하는 중입니다...");
    try {
      const uniqueSymbols = Array.from(new Set(trackedSymbols));
      const settled = await Promise.allSettled(
        uniqueSymbols.map(async (symbol) => [symbol, await fetchQuote(symbol)] as const),
      );
      const pricePairs = settled
        .filter((item): item is PromiseFulfilledResult<readonly [string, QuoteResponse]> => item.status === "fulfilled")
        .map((item) => [item.value[0], item.value[1].price] as const);
      const sourceNotes = settled
        .filter((item): item is PromiseFulfilledResult<readonly [string, QuoteResponse]> => item.status === "fulfilled")
        .map((item) => `${item.value[0]} ${item.value[1].freshness} ${item.value[1].as_of}`);
      const failedSymbols = uniqueSymbols.filter((symbol) => !pricePairs.some(([item]) => item === symbol));
      const priceMap = Object.fromEntries(pricePairs);
      let changedCount = 0;
      let unchangedCount = 0;
      paperPositions.forEach((position) => {
        const nextPrice = priceMap[position.symbol];
        if (nextPrice == null) return;
        if (nextPrice !== position.currentPrice) changedCount += 1;
        else unchangedCount += 1;
      });
      paperStrategies.forEach((strategy) => {
        const nextPrice = priceMap[strategy.startSymbol];
        if (nextPrice == null) return;
        if (nextPrice !== strategy.currentPrice) changedCount += 1;
        else unchangedCount += 1;
      });
      setPaperPositions((current) => current.map((position) => ({ ...position, currentPrice: priceMap[position.symbol] ?? position.currentPrice })));
      setPaperStrategies((current) =>
        current.map((strategy) => ({
          ...strategy,
          currentPrice: priceMap[strategy.startSymbol] ?? strategy.currentPrice,
        })),
      );
      const lastCheckedAt = new Date().toLocaleString("ko-KR");
      const message =
        changedCount > 0
          ? `${changedCount}개 항목의 가격이 바뀌었습니다.`
          : "요청은 성공했지만 가격 변동은 없습니다. 현재 데이터는 1일봉 종가 기준이라 장중에는 그대로일 수 있습니다.";
      setPaperRefreshInfo({
        lastCheckedAt,
        changedCount,
        unchangedCount,
        failedSymbols,
        sourceNote: sourceNotes.join(" · "),
        message,
      });
      setStatus(failedSymbols.length ? `일부 종목 갱신 실패: ${failedSymbols.join(", ")}` : message);
    } catch (error) {
      setPaperRefreshInfo({
        lastCheckedAt: new Date().toLocaleString("ko-KR"),
        changedCount: 0,
        unchangedCount: 0,
        failedSymbols: trackedSymbols,
        sourceNote: "",
        message: error instanceof Error ? error.message : "현재가 갱신 실패",
      });
      setStatus(error instanceof Error ? error.message : "현재가 갱신 실패");
    } finally {
      setLoading("");
    }
  }

  return (
    <section className="page-grid">
      <div className="hero-panel lab">
        <div>
          <span className="section-label">Test Lab</span>
          <h2>백테스트와 미래 시나리오로 전략을 검증합니다</h2>
          <p>{status}</p>
        </div>
        <button className="primary" onClick={runBacktest} disabled={loading === "backtest"}>
          <FlaskConical size={17} />
          {loading === "backtest" ? "계산 중" : "백테스트 실행"}
        </button>
      </div>

      <div className="content-grid">
        {managedDraft ? (
          <article className="panel span-12 managed-test-card">
            <div className="managed-test-top">
              <div>
                <span className="section-label">Managed Strategy</span>
                <h2>{managedDraft.title} v{managedDraft.version}</h2>
                <p>{managedDraft.summary}</p>
              </div>
              <div className="hero-actions">
                <button className="primary" onClick={runBacktest} disabled={loading === "backtest"}>
                  <FlaskConical size={16} />
                  화면 조건 백테스트
                </button>
                <button onClick={runManagedBacktest} disabled={loading === "backtest"}>
                  <FlaskConical size={16} />
                  저장 전략 기준
                </button>
                <button onClick={() => navigate("/manage")}>
                  <ArrowLeft size={16} />
                  관리로 돌아가기
                </button>
                <button onClick={clearManagedDraft}>연결 해제</button>
              </div>
            </div>
            <div className="managed-metric-strip">
              <span>
                <small>동일 원금</small>
                <strong>{formatKrw(managedDraft.initial_capital)}</strong>
              </span>
              <span>
                <small>검증 엔진</small>
                <strong>{managedEngineLabel(managedDraft)}</strong>
              </span>
              <span>
                <small>레버리지 노출</small>
                <strong>{allocationRatio(managedDraft, (symbol) => ["TQQQ", "QLD"].includes(symbol)).toFixed(1)}%</strong>
              </span>
              <span>
                <small>현금/대기 자산</small>
                <strong>{allocationRatio(managedDraft, (symbol) => ["CASH", "SGOV", "BIL"].includes(symbol)).toFixed(1)}%</strong>
              </span>
            </div>
            <div className="validation-steps">
              <span className="active">1 저장 전략 불러옴</span>
              <span>2 동일 원금 백테스트</span>
              <span>3 미래 시나리오 확인</span>
              <span>4 결과 비교</span>
            </div>
            <div className="managed-allocation-grid">
              {managedDraft.allocations.map((allocation) => (
                <div key={allocation.symbol}>
                  <strong>{allocation.symbol}</strong>
                  <span>{allocation.target_ratio.toFixed(1)}%</span>
                  <small>{allocation.role} · {formatKrw(allocation.target_amount)}</small>
                </div>
              ))}
            </div>
            <p className="managed-test-note">
              저장 전략의 원금과 목표 비중을 그대로 가져왔습니다. 백테스트는 QQQ 200일선 기반 TQQQ/QLD 핵심 엔진을 검증하고, SPYM/QQQM/SGOV/CASH 같은 보조 자산은 전략 해석의 기준 정보로 유지합니다.
            </p>
          </article>
        ) : null}

        <article className="panel span-12">
          <PanelTitle icon={<FlaskConical size={18} />} title="백테스트" />
          <div className="backtest-controls">
            <label>전략<select value={config.strategy} onChange={(event) => setConfig({ ...config, strategy: event.target.value as BacktestStrategy })}><option value="tqqq_200ma">분할형 QQQ 200일선 기반 TQQQ</option><option value="qld_200ma">분할형 QQQ 200일선 기반 QLD</option><option value="qqq_buy_hold">QQQ 장기 보유</option><option value="tqqq_buy_hold">TQQQ 장기 보유</option></select></label>
            <label>초기 금액<input type="number" value={config.initial_capital} onChange={(event) => setConfig({ ...config, initial_capital: Number(event.target.value) })} /></label>
            <label>TQQQ 비중<input type="number" value={config.tqqq_target_ratio} onChange={(event) => setConfig({ ...config, tqqq_target_ratio: Number(event.target.value) })} /></label>
            <label>QLD 비중<input type="number" value={config.qld_target_ratio} onChange={(event) => setConfig({ ...config, qld_target_ratio: Number(event.target.value) })} /></label>
            <label>현금 수익률<input type="number" value={config.cash_yield} onChange={(event) => setConfig({ ...config, cash_yield: Number(event.target.value) })} /></label>
            <label>표시 기간<input type="number" value={config.projection_years} onChange={(event) => setConfig({ ...config, projection_years: Number(event.target.value) })} /></label>
          </div>
          {backtest ? <BacktestResult result={backtest} /> : <p className="muted">백테스트 실행 시 수익 곡선, CAGR, MDD, 거래 로그가 표시됩니다. TQQQ/QLD 200일선 전략은 1차/2차/3차 분할매수와 방어 매도 규칙을 반영합니다.</p>}
        </article>

        {/* 실시간 모의 보유와 전략 단위 모의 운용은 추후 머신러닝/실시간 운용 고도화 단계에서 복원할 수 있도록 내부 로직만 보존하고 사용자 화면에서는 숨깁니다. */}
      </div>
    </section>
  );
}

function BacktestResult({ result }: { result: BacktestResponse }) {
  const points = buildChartPoints(result.equity_curve);
  return (
    <div className="backtest-result">
      <div className="score-grid">
        <MetricCard label="최종 금액" value={formatKrw(result.metrics.final_capital)} note={`${result.period_start} ~ ${result.period_end}`} />
        <MetricCard label="총수익률" value={formatPct(result.metrics.total_return)} note={`QQQ ${formatPct(result.benchmark_metrics.total_return)}`} />
        <MetricCard label="CAGR" value={formatPct(result.metrics.cagr)} note={`Sharpe ${result.metrics.sharpe ?? "-"}`} />
        <MetricCard label="MDD" value={formatPct(result.metrics.max_drawdown)} note={`최장 ${result.metrics.longest_drawdown_days}일`} />
      </div>
      {result.strategy === "tqqq_200ma" || result.strategy === "qld_200ma" ? (
        <div className="refresh-status changed">
          <strong>분할형 200일선 엔진</strong>
          <small>
            1차 30%, 2차 65%, 3차 100%까지 단계적으로 진입하고, QQQ 50일선 이탈·200일선 이탈·200일선 대비 +25% 구간에서 방어/수익회수 매도를 반영합니다.
          </small>
        </div>
      ) : null}
      <div className="equity-chart"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><polyline points={points} /></svg></div>
      <div className="projection-grid">
        {result.projection.map((scenario) => <div className={`projection-card ${scenario.name}`} key={scenario.name}><span>{scenarioLabel(scenario.name)}</span><strong>{formatKrw(scenario.ending_capital)}</strong><small>{formatPct(scenario.annual_return)} / 손익 {formatKrw(scenario.profit)}</small><p>{scenario.note}</p></div>)}
      </div>
      <div className="regime-grid">
        {result.regime_performance.map((item) => (
          <div className={`regime-card ${item.regime}`} key={item.regime}>
            <span>{item.label}</span>
            <strong>{formatPct(item.return_pct)}</strong>
            <small>{item.days}일 / 승률 {item.win_rate.toFixed(1)}% / MDD {formatPct(item.max_drawdown)}</small>
          </div>
        ))}
      </div>
      <div className="report-columns">
        <ListBlock title="해석" items={result.interpretation} />
        <ListBlock title="최근 거래" items={result.trades.slice(-6).map((trade) => `${trade.date} ${actionLabel(trade.action)} ${trade.symbol} ${trade.ratio}%`)} />
      </div>
    </div>
  );
}
function RefreshStatus({
  info,
}: {
  info: {
    lastCheckedAt: string;
    changedCount: number;
    unchangedCount: number;
    failedSymbols: string[];
    sourceNote: string;
    message: string;
  };
}) {
  return (
    <div className={`refresh-status ${info.failedSymbols.length ? "failed" : info.changedCount > 0 ? "changed" : ""}`}>
      <strong>{info.message}</strong>
      <small>
        {info.lastCheckedAt ? `마지막 확인: ${info.lastCheckedAt}` : "마지막 확인: 없음"} · 변경{" "}
        {info.changedCount}개 · 동일 {info.unchangedCount}개
        {info.failedSymbols.length ? ` · 실패: ${info.failedSymbols.join(", ")}` : ""}
      </small>
      {info.sourceNote ? <small>데이터: {info.sourceNote}</small> : null}
    </div>
  );
}
function PaperPortfolio({ positions, onRemove }: { positions: PaperPosition[]; onRemove: (id: string) => void }) {
  if (!positions.length) return <p className="muted">종목과 금액을 넣고 모의 매수를 누르면 실제 보유처럼 평가손익을 추적합니다.</p>;
  const totalInvested = positions.reduce((sum, item) => sum + item.amount, 0);
  const totalValue = positions.reduce((sum, item) => sum + paperValue(item), 0);
  return (
    <div className="paper-result">
      <div className="score-grid">
        <MetricCard label="모의 투자금" value={formatKrw(totalInvested)} note={`${positions.length}개 보유`} />
        <MetricCard label="평가금액" value={formatKrw(totalValue)} note="현재가 기준" />
        <MetricCard label="평가손익" value={formatKrw(totalValue - totalInvested)} note={formatPct((totalValue / totalInvested - 1) * 100)} />
        <MetricCard label="기준" value="ETF 가격" note="환율 변동 제외" />
      </div>
      <table><tbody>{positions.map((position) => <tr key={position.id}><td><strong>{position.symbol}</strong><small>{position.buyDate}</small></td><td>{formatUsd(position.entryPrice)}</td><td>{formatUsd(position.currentPrice)}</td><td>{formatPct((position.currentPrice / position.entryPrice - 1) * 100)}</td><td>{formatKrw(paperValue(position))}</td><td><button onClick={() => onRemove(position.id)}><Trash2 size={16} /></button></td></tr>)}</tbody></table>
    </div>
  );
}
function PaperStrategyPortfolio({ strategies, onRemove }: { strategies: PaperStrategy[]; onRemove: (id: string) => void }) {
  if (!strategies.length) return <p className="muted">같은 원금으로 전략 자체를 모의 시작하면 시간이 지나며 어떤 전략이 더 잘 버티는지 비교할 수 있습니다.</p>;
  const totalInvested = strategies.reduce((sum, item) => sum + item.amount, 0);
  const totalValue = strategies.reduce((sum, item) => sum + paperStrategyValue(item), 0);
  const watchCount = strategies.filter((strategy) => Math.abs(paperStrategyDrift(strategy)) >= 5).length;
  return (
    <div className="paper-result">
      <div className="score-grid">
        <MetricCard label="전략 원금" value={formatKrw(totalInvested)} note={`${strategies.length}개 전략`} />
        <MetricCard label="전략 평가금액" value={formatKrw(totalValue)} note="현재가 기준" />
        <MetricCard label="전략 손익" value={formatKrw(totalValue - totalInvested)} note={formatPct((totalValue / totalInvested - 1) * 100)} />
        <MetricCard label="이탈 점검" value={`${watchCount}개`} note="목표비중 5%p 이상" />
      </div>
      <table>
        <tbody>
          {strategies.map((strategy) => {
            const currentWeight = paperStrategyRiskWeight(strategy);
            const drift = paperStrategyDrift(strategy);
            const action = paperStrategyActionLabel(strategy);
            return (
              <tr key={strategy.id}>
                <td>
                  <strong>{strategy.name}</strong>
                  <small>{strategy.startDate} 시작 / {strategy.startSymbol} 목표 {Math.round(strategy.targetRatio * 100)}%</small>
                </td>
                <td>{formatUsd(strategy.startPrice)}</td>
                <td>{formatUsd(strategy.currentPrice)}</td>
                <td>{formatPct((paperStrategyValue(strategy) / strategy.amount - 1) * 100)}</td>
                <td>
                  <strong>{currentWeight.toFixed(1)}%</strong>
                  <small>목표 대비 {drift >= 0 ? "+" : ""}{drift.toFixed(1)}%p</small>
                </td>
                <td>
                  <span className={`paper-action ${action.level}`}>{action.label}</span>
                  <small>{action.note}</small>
                </td>
                <td>{formatKrw(paperStrategyValue(strategy))}</td>
                <td><button onClick={() => onRemove(strategy.id)}><Trash2 size={16} /></button></td>
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
function paperStrategyValue(strategy: PaperStrategy) {
  const riskyReturn = strategy.currentPrice / strategy.startPrice;
  return strategy.amount * (strategy.targetRatio * riskyReturn + (1 - strategy.targetRatio));
}
function paperStrategyRiskWeight(strategy: PaperStrategy) {
  const riskyValue = strategy.amount * strategy.targetRatio * (strategy.currentPrice / strategy.startPrice);
  return (riskyValue / paperStrategyValue(strategy)) * 100;
}
function paperStrategyDrift(strategy: PaperStrategy) {
  return paperStrategyRiskWeight(strategy) - strategy.targetRatio * 100;
}
function paperStrategyActionLabel(strategy: PaperStrategy) {
  const drift = paperStrategyDrift(strategy);
  const gain = (paperStrategyValue(strategy) / strategy.amount - 1) * 100;
  if (drift >= 8) {
    return { level: "danger", label: "비중 과다", note: "일부 수익 회수 또는 대기자산 전환 검토" };
  }
  if (drift <= -8) {
    return { level: "watch", label: "비중 부족", note: "매수 조건 충족 시 추가 집행 후보" };
  }
  if (gain <= -8) {
    return { level: "watch", label: "손실 점검", note: "200일선/매도 규칙을 먼저 확인" };
  }
  return { level: "ok", label: "유지", note: "목표비중 허용 범위" };
}
function buildChartPoints(curve: EquityPoint[]) {
  if (curve.length < 2) return "";
  const firstTime = new Date(curve[0].date).getTime();
  const lastTime = new Date(curve[curve.length - 1].date).getTime();
  const minEquity = Math.min(...curve.map((item) => item.equity));
  const maxEquity = Math.max(...curve.map((item) => item.equity));
  return curve.map((point) => {
    const x = ((new Date(point.date).getTime() - firstTime) / Math.max(lastTime - firstTime, 1)) * 100;
    const y = 100 - ((point.equity - minEquity) / Math.max(maxEquity - minEquity, 1)) * 100;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");
}
function PanelTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return <h2 className="panel-title">{icon}{title}</h2>;
}
function MetricCard({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="score-card"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>;
}
function ListBlock({ title, items }: { title: string; items: string[] }) {
  return <div className="list-block"><h3>{title}</h3><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></div>;
}
