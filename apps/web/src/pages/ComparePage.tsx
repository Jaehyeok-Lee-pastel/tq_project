import { useState } from "react";
import { BarChart3, Bot, FlaskConical, Medal, RefreshCw, ShieldCheck, Trophy } from "lucide-react";

type BacktestStrategy = "qqq_buy_hold" | "tqqq_buy_hold" | "tqqq_200ma" | "qld_200ma" | "tqqq_daily_200ma";
type Verdict = "best_fit" | "high_return" | "defensive" | "too_risky" | "watch";

type StrategyRankItem = {
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
  total_score: number;
  verdict: Verdict;
  reason: string;
};

type Projection = { name: "bear" | "base" | "bull"; ending_capital: number; annual_return: number; profit: number; note: string };
type StrategyCompareResponse = {
  initial_capital: number;
  risk_score: number;
  recommended_strategy: BacktestStrategy;
  summary: string;
  rankings: StrategyRankItem[];
  tqqq_default_comparison?: {
    baseline_label: string;
    custom_label: string;
    final_capital_delta: number;
    cagr_delta: number;
    max_drawdown_delta: number;
    trade_count_delta: number;
    base_projection_delta: number;
    verdict: "custom_better" | "custom_defensive" | "baseline_better" | "similar";
    summary: string;
    philosophy_audit: {
      score: number;
      verdict: "excellent" | "good" | "watch" | "danger";
      summary: string;
      items: { label: string; score: number; status: "ok" | "watch" | "danger"; detail: string }[];
      to_reach_100: string[];
    };
    baseline: { metrics: { final_capital: number; cagr: number; max_drawdown: number; trade_count: number }; projection: Projection[] };
    custom: { metrics: { final_capital: number; cagr: number; max_drawdown: number; trade_count: number }; projection: Projection[] };
  } | null;
  sensitivity?: {
    best_window: number;
    robustness_score: number;
    verdict: string;
    results: { strategy: BacktestStrategy; strategy_name: string; moving_average_days: number; cagr: number; max_drawdown: number; total_score: number }[];
  } | null;
};

type InsightReport = {
  headline: string;
  confidence_level: "low" | "medium" | "high";
  summary: string;
  strongest_evidence: string[];
  main_risks: string[];
  recommended_next_steps: string[];
  ai_used: boolean;
};

type CompareConfig = {
  initial_capital: number;
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
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const allStrategies: { id: BacktestStrategy; label: string }[] = [
  { id: "tqqq_daily_200ma", label: "TQQQ 일일 적립 감속" },
  { id: "tqqq_200ma", label: "TQQQ 200일선 분할" },
  { id: "qld_200ma", label: "QLD 200일선" },
  { id: "qqq_buy_hold", label: "QQQ 장기 보유" },
  { id: "tqqq_buy_hold", label: "TQQQ 장기 보유" },
];

const researchPresets: {
  id: string;
  title: string;
  summary: string;
  selected: BacktestStrategy[];
  config: Partial<CompareConfig>;
}[] = [
  {
    id: "daily_accumulation_7_3",
    title: "월 100만원 · 7:3 일일 적립",
    summary: "QQQ가 200일선 위에 있을 때 TQQQ 70%, QQQM 30%로 매일 적립하고 과열될수록 TQQQ 비중만 감속합니다.",
    selected: ["tqqq_daily_200ma", "tqqq_200ma", "qqq_buy_hold"],
    config: {
      risk_score: 78,
      tqqq_target_ratio: 45,
      qld_target_ratio: 0,
      one_x_target_ratio: 30,
      one_x_symbol: "QQQM",
      moving_average_days: 200,
      cash_yield: 4.5,
      monthly_contribution: 1000000,
      daily_base_tqqq_ratio: 70,
      daily_base_one_x_ratio: 30,
    },
  },
  {
    id: "basic_vs_custom",
    title: "기본형 vs 커스텀형",
    summary: "기본 TQQQ 200일선 전략과 리스크 맞춤 커스텀 전략을 같은 조건에서 비교합니다.",
    selected: ["tqqq_200ma", "qqq_buy_hold"],
    config: { risk_score: 75, tqqq_target_ratio: 45, qld_target_ratio: 0, monthly_contribution: 0, cash_yield: 4.5 },
  },
  {
    id: "qld_buffer",
    title: "QLD 완충형",
    summary: "TQQQ 변동성이 부담될 때 QLD 2배 전략과 QQQ 장기 보유를 비교합니다.",
    selected: ["qld_200ma", "qqq_buy_hold"],
    config: { risk_score: 65, tqqq_target_ratio: 0, qld_target_ratio: 60, monthly_contribution: 0, cash_yield: 4.5 },
  },
];

function formatKrw(value: number) {
  return `${Math.round(value).toLocaleString("ko-KR")}원`;
}

function formatPct(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function verdictLabel(verdict: Verdict) {
  return {
    best_fit: "최적 후보",
    high_return: "고수익형",
    defensive: "방어형",
    too_risky: "위험 과다",
    watch: "관찰",
  }[verdict];
}

async function requestCompare(payload: CompareConfig & { strategies: BacktestStrategy[] }) {
  const response = await fetch(`${apiBaseUrl}/compare/strategies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`전략 비교 API 오류: ${response.status}`);
  return (await response.json()) as StrategyCompareResponse;
}

async function requestInsight(payload: StrategyCompareResponse, useAi: boolean) {
  const response = await fetch(`${apiBaseUrl}/insights/interpret`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ context: "strategy_compare", payload, use_ai: useAi }),
  });
  if (!response.ok) throw new Error(`해석 리포트 API 오류: ${response.status}`);
  return (await response.json()) as InsightReport;
}

export function ComparePage() {
  const [status, setStatus] = useState("개인 연구 전략을 같은 조건으로 비교합니다.");
  const [loading, setLoading] = useState(false);
  const [loadingInsight, setLoadingInsight] = useState(false);
  const [result, setResult] = useState<StrategyCompareResponse | null>(null);
  const [insight, setInsight] = useState<InsightReport | null>(null);
  const [useAiInsight, setUseAiInsight] = useState(true);
  const [config, setConfig] = useState<CompareConfig>({
    initial_capital: 2500000,
    risk_score: 78,
    tqqq_target_ratio: 45,
    qld_target_ratio: 0,
    one_x_target_ratio: 30,
    one_x_symbol: "QQQM",
    cash_yield: 4.5,
    moving_average_days: 200,
    include_default_tqqq_comparison: true,
    default_tqqq_target_ratio: 60,
    monthly_contribution: 1000000,
    daily_base_tqqq_ratio: 70,
    daily_base_one_x_ratio: 30,
  });
  const [selected, setSelected] = useState<BacktestStrategy[]>(["tqqq_daily_200ma", "tqqq_200ma", "qqq_buy_hold"]);
  const winner = result?.rankings[0];

  function toggleStrategy(strategy: BacktestStrategy) {
    setSelected((current) => (current.includes(strategy) ? current.filter((item) => item !== strategy) : [...current, strategy]));
  }

  function applyPreset(preset: (typeof researchPresets)[number]) {
    setConfig((current) => ({ ...current, ...preset.config }));
    setSelected(preset.selected);
    setResult(null);
    setInsight(null);
    setStatus(`${preset.title} 조건을 적용했습니다. 비교 실행을 눌러 검증하세요.`);
  }

  async function runCompare() {
    if (!selected.length) {
      setStatus("비교할 전략을 최소 1개 선택하세요.");
      return;
    }
    setLoading(true);
    setStatus("같은 조건으로 전략 성과를 계산하는 중입니다...");
    try {
      const response = await requestCompare({ ...config, strategies: selected });
      setResult(response);
      setInsight(null);
      setStatus(response.summary);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "전략 비교 실패");
    } finally {
      setLoading(false);
    }
  }

  async function runInsight() {
    if (!result) return;
    setLoadingInsight(true);
    setStatus("전략 비교 결과를 해석하는 중입니다...");
    try {
      const response = await requestInsight(result, useAiInsight);
      setInsight(response);
      setStatus(response.ai_used ? "AI 해석 리포트를 생성했습니다." : "규칙 기반 해석 리포트를 생성했습니다.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "해석 리포트 생성 실패");
    } finally {
      setLoadingInsight(false);
    }
  }

  return (
    <section className="page-grid">
      <div className="hero-panel compare">
        <div>
          <span className="section-label">Personal Research</span>
          <h2>월 적립·이격도 감속 전략을 백테스트합니다</h2>
          <p>{status}</p>
        </div>
        <button className="primary" onClick={runCompare} disabled={loading}>
          <RefreshCw size={17} />
          {loading ? "비교 중" : "전략 비교 실행"}
        </button>
      </div>

      <div className="content-grid">
        <article className="panel span-12 research-lab-card">
          <div className="report-head">
            <h2 className="panel-title">
              <FlaskConical size={18} />
              연구 프리셋
            </h2>
            <p>실전 전략으로 승격하기 전, 개인 연구 가설을 기존 TQQQ 200일선 전략과 비교합니다.</p>
          </div>
          <div className="research-preset-grid">
            {researchPresets.map((preset) => (
              <button key={preset.id} onClick={() => applyPreset(preset)}>
                <strong>{preset.title}</strong>
                <span>{preset.summary}</span>
              </button>
            ))}
          </div>
        </article>

        <article className="panel span-12">
          <h2 className="panel-title">
            <BarChart3 size={18} />
            연구 조건
          </h2>
          <div className="backtest-controls">
            <label>초기 원금<input type="number" value={config.initial_capital} onChange={(event) => setConfig({ ...config, initial_capital: Number(event.target.value) })} /></label>
            <label>월 추가금<input type="number" value={config.monthly_contribution} onChange={(event) => setConfig({ ...config, monthly_contribution: Number(event.target.value) })} /></label>
            <label>리스크 점수<input type="number" min={0} max={100} value={config.risk_score} onChange={(event) => setConfig({ ...config, risk_score: Number(event.target.value) })} /></label>
            <label>일일 TQQQ 기준비중<input type="number" value={config.daily_base_tqqq_ratio} onChange={(event) => setConfig({ ...config, daily_base_tqqq_ratio: Number(event.target.value) })} /></label>
            <label>일일 1x 기준비중<input type="number" value={config.daily_base_one_x_ratio} onChange={(event) => setConfig({ ...config, daily_base_one_x_ratio: Number(event.target.value) })} /></label>
            <label>1x 자산<select value={config.one_x_symbol} onChange={(event) => setConfig({ ...config, one_x_symbol: event.target.value })}><option value="QQQM">QQQM</option><option value="QQQ">QQQ</option><option value="SPYM">SPYM</option></select></label>
            <label>TQQQ 분할 목표<input type="number" value={config.tqqq_target_ratio} onChange={(event) => setConfig({ ...config, tqqq_target_ratio: Number(event.target.value) })} /></label>
            <label>QLD 목표<input type="number" value={config.qld_target_ratio} onChange={(event) => setConfig({ ...config, qld_target_ratio: Number(event.target.value) })} /></label>
            <label>현금/SGOV 기대수익<input type="number" value={config.cash_yield} onChange={(event) => setConfig({ ...config, cash_yield: Number(event.target.value) })} /></label>
            <label>기준 이동평균<input type="number" min={50} max={300} value={config.moving_average_days} onChange={(event) => setConfig({ ...config, moving_average_days: Number(event.target.value) })} /></label>
          </div>
          <div className="strategy-toggle-list">
            {allStrategies.map((strategy) => (
              <button className={selected.includes(strategy.id) ? "selected" : ""} key={strategy.id} onClick={() => toggleStrategy(strategy.id)}>
                {strategy.label}
              </button>
            ))}
          </div>
          <div className="research-rule-strip">
            <span><ShieldCheck size={15} /> QQQ 200일선 위에서만 TQQQ 신규 적립</span>
            <span>+10%, +20%, +30% 이격도 구간마다 TQQQ 일일 매수 감속</span>
            <span>200일선 아래 2거래일이면 TQQQ 방어 전환</span>
            <span>월 추가금은 거래일 단위로 나누어 반영</span>
          </div>
        </article>

        {winner ? (
          <article className="panel span-12 winner-card">
            <div>
              <span className="section-label">Recommended</span>
              <h2><Trophy size={22} />{winner.strategy_name}</h2>
              <p>{winner.reason}</p>
            </div>
            <div className="winner-score"><strong>{winner.total_score}</strong><span>종합 점수</span></div>
          </article>
        ) : null}

        {winner ? (
          <article className="panel span-12">
            <h2 className="panel-title"><ShieldCheck size={18} />판단 근거</h2>
            <div className="confidence-breakdown-grid">
              <Score label="수익성" value={winner.profit_score} />
              <Score label="방어력" value={winner.defense_score} />
              <Score label="성향 적합" value={winner.fit_score} />
              <Score label="일관성" value={winner.consistency_score} />
              <Score label="견고성" value={result?.sensitivity?.robustness_score ?? 0} />
            </div>
          </article>
        ) : null}

        {result ? (
          <article className="panel span-12 insight-card">
            <div className="report-head">
              <h2 className="panel-title"><Bot size={18} />검증 해석 리포트</h2>
              <div className="hero-actions">
                <label className="switch"><input type="checkbox" checked={useAiInsight} onChange={(event) => setUseAiInsight(event.target.checked)} />AI 해석</label>
                <button onClick={runInsight} disabled={loadingInsight}><Bot size={16} />{loadingInsight ? "해석 중" : "리포트 생성"}</button>
              </div>
            </div>
            {insight ? (
              <div className={`insight-report ${insight.confidence_level}`}>
                <span>{insight.ai_used ? "AI" : "Rule"} / {confidenceLabel(insight.confidence_level)}</span>
                <h3>{insight.headline}</h3>
                <p>{insight.summary}</p>
                <div className="report-columns">
                  <ListBlock title="강한 근거" items={insight.strongest_evidence} />
                  <ListBlock title="주요 위험" items={insight.main_risks} />
                  <ListBlock title="다음 행동" items={insight.recommended_next_steps} />
                </div>
              </div>
            ) : <p className="muted">비교 결과를 바탕으로 해석 리포트를 생성할 수 있습니다.</p>}
          </article>
        ) : null}

        {result ? (
          <article className="panel span-12">
            <h2 className="panel-title"><Medal size={18} />전략 순위</h2>
            <div className="ranking-list">
              {result.rankings.map((item) => (
                <div className={`ranking-row ${item.verdict}`} key={item.strategy}>
                  <div className="rank-badge">{item.rank}</div>
                  <div><strong>{item.strategy_name}</strong><small>{item.reason}</small></div>
                  <Score label="종합" value={item.total_score} />
                  <Score label="수익" value={item.profit_score} />
                  <Score label="방어" value={item.defense_score} />
                  <Score label="적합" value={item.fit_score} />
                  <div className="rank-metrics">
                    <span>{formatKrw(item.final_capital)}</span>
                    <span>CAGR {formatPct(item.cagr)}</span>
                    <span>MDD {formatPct(item.max_drawdown)}</span>
                    <span>{verdictLabel(item.verdict)}</span>
                  </div>
                </div>
              ))}
            </div>
          </article>
        ) : null}

        {result?.sensitivity ? (
          <article className="panel span-12">
            <h2 className="panel-title"><BarChart3 size={18} />이동평균 민감도</h2>
            <div className="sensitivity-grid">
              {result.sensitivity.results.map((item) => (
                <div className="sensitivity-card" key={item.moving_average_days}>
                  <span>{item.moving_average_days}일선</span>
                  <strong>{item.total_score}</strong>
                  <small>CAGR {formatPct(item.cagr)} / MDD {formatPct(item.max_drawdown)}</small>
                </div>
              ))}
            </div>
          </article>
        ) : null}
      </div>
    </section>
  );
}

function confidenceLabel(level: InsightReport["confidence_level"]) {
  return { low: "신뢰 낮음", medium: "신뢰 보통", high: "신뢰 높음" }[level];
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="list-block">
      <h3>{title}</h3>
      <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>
    </div>
  );
}

function Score({ label, value }: { label: string; value: number }) {
  return (
    <div className="mini-score">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
