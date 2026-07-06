import { useState } from "react";
import { BarChart3, Bot, FlaskConical, Medal, RefreshCw, ShieldCheck, Trophy } from "lucide-react";

type BacktestStrategy = "qqq_buy_hold" | "tqqq_buy_hold" | "tqqq_200ma" | "qld_200ma";
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
type StrategyCompareResponse = {
  initial_capital: number;
  risk_score: number;
  recommended_strategy: BacktestStrategy;
  summary: string;
  rankings: StrategyRankItem[];
  tqqq_default_comparison?: {
    baseline_label: string;
    custom_label: string;
    baseline_target_ratio: number;
    custom_target_ratio: number;
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
    baseline: {
      metrics: { final_capital: number; cagr: number; max_drawdown: number; trade_count: number };
      projection: { name: "bear" | "base" | "bull"; ending_capital: number; annual_return: number; profit: number; note: string }[];
    };
    custom: {
      metrics: { final_capital: number; cagr: number; max_drawdown: number; trade_count: number };
      projection: { name: "bear" | "base" | "bull"; ending_capital: number; annual_return: number; profit: number; note: string }[];
    };
  } | null;
  sensitivity?: {
    tested_windows: number[];
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

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const allStrategies: { id: BacktestStrategy; label: string }[] = [
  { id: "tqqq_200ma", label: "QQQ 200일선 기반 TQQQ" },
  { id: "qld_200ma", label: "QQQ 200일선 기반 QLD" },
  { id: "qqq_buy_hold", label: "QQQ 장기 보유" },
  { id: "tqqq_buy_hold", label: "TQQQ 장기 보유" },
];
const researchPresets = [
  {
    id: "default_vs_custom",
    title: "기본형 vs 커스텀형",
    summary: "기본 TQQQ 200일선 60%와 현재 리스크 맞춤 커스텀 비중을 같은 원금으로 직접 비교합니다.",
    selected: ["tqqq_200ma", "qqq_buy_hold"] as BacktestStrategy[],
    config: { risk_score: 75, tqqq_target_ratio: 45, qld_target_ratio: 0, moving_average_days: 200, cash_yield: 4.5 },
  },
  {
    id: "tqqq_core",
    title: "TQQQ 200일선 공격형",
    summary: "TQQQ를 핵심 엔진으로 쓰되 목표 비중을 45%로 제한하고 SGOV/현금 대기를 전제로 봅니다.",
    selected: ["tqqq_200ma", "qqq_buy_hold"] as BacktestStrategy[],
    config: { risk_score: 78, tqqq_target_ratio: 45, qld_target_ratio: 0, moving_average_days: 200, cash_yield: 4.5 },
  },
  {
    id: "qld_buffer",
    title: "QLD 완충형",
    summary: "TQQQ 변동성이 부담될 때 QLD 2배 레버리지로 대체해 지속 가능성을 비교합니다.",
    selected: ["qld_200ma", "qqq_buy_hold"] as BacktestStrategy[],
    config: { risk_score: 65, tqqq_target_ratio: 0, qld_target_ratio: 60, moving_average_days: 200, cash_yield: 4.5 },
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

async function requestCompare(payload: {
  initial_capital: number;
  risk_score: number;
  strategies: BacktestStrategy[];
  tqqq_target_ratio: number;
  qld_target_ratio: number;
  cash_yield: number;
  moving_average_days: number;
  include_default_tqqq_comparison?: boolean;
  default_tqqq_target_ratio?: number;
}) {
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
  const [status, setStatus] = useState("같은 원금으로 여러 전략을 동시에 비교합니다.");
  const [loading, setLoading] = useState(false);
  const [loadingInsight, setLoadingInsight] = useState(false);
  const [result, setResult] = useState<StrategyCompareResponse | null>(null);
  const [insight, setInsight] = useState<InsightReport | null>(null);
  const [useAiInsight, setUseAiInsight] = useState(true);
  const [config, setConfig] = useState({
    initial_capital: 2500000,
    risk_score: 75,
    tqqq_target_ratio: 60,
    qld_target_ratio: 70,
    cash_yield: 3,
    moving_average_days: 200,
    include_default_tqqq_comparison: true,
    default_tqqq_target_ratio: 60,
  });
  const [selected, setSelected] = useState<BacktestStrategy[]>(allStrategies.map((item) => item.id));

  function toggleStrategy(strategy: BacktestStrategy) {
    setSelected((current) =>
      current.includes(strategy)
        ? current.filter((item) => item !== strategy)
        : [...current, strategy],
    );
  }

  async function runCompare() {
    if (!selected.length) {
      setStatus("비교할 전략을 최소 1개 선택하세요.");
      return;
    }
    setLoading(true);
    setStatus("동일 원금 기준 전략 랭킹을 계산하는 중입니다...");
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

  function applyPreset(preset: (typeof researchPresets)[number]) {
    setConfig((current) => ({ ...current, ...preset.config }));
    setSelected(preset.selected);
    setResult(null);
    setInsight(null);
    setStatus(`${preset.title} 조건을 적용했습니다. 전략 비교 실행을 눌러 같은 원금 기준으로 검증하세요.`);
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

  const winner = result?.rankings[0];

  return (
    <section className="page-grid">
      <div className="hero-panel compare">
        <div>
          <span className="section-label">Strategy Lab</span>
          <h2>QQQ/QLD/TQQQ 전략을 같은 원금으로 연구합니다.</h2>
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
              실험 프리셋
            </h2>
            <p>프리셋은 입력값을 바꾸는 도구입니다. 실제 판단은 아래 백테스트 결과와 민감도 검증으로 확인합니다.</p>
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
            <label>동일 원금<input type="number" value={config.initial_capital} onChange={(event) => setConfig({ ...config, initial_capital: Number(event.target.value) })} /></label>
            <label>리스크 점수<input type="number" min={0} max={100} value={config.risk_score} onChange={(event) => setConfig({ ...config, risk_score: Number(event.target.value) })} /></label>
            <label>TQQQ 목표 비중<input type="number" value={config.tqqq_target_ratio} onChange={(event) => setConfig({ ...config, tqqq_target_ratio: Number(event.target.value) })} /></label>
            <label>기본형 TQQQ 비중<input type="number" value={config.default_tqqq_target_ratio} onChange={(event) => setConfig({ ...config, default_tqqq_target_ratio: Number(event.target.value) })} /></label>
            <label>QLD 목표 비중<input type="number" value={config.qld_target_ratio} onChange={(event) => setConfig({ ...config, qld_target_ratio: Number(event.target.value) })} /></label>
            <label>현금 수익률<input type="number" value={config.cash_yield} onChange={(event) => setConfig({ ...config, cash_yield: Number(event.target.value) })} /></label>
            <label>기준 이동평균<input type="number" min={50} max={300} value={config.moving_average_days} onChange={(event) => setConfig({ ...config, moving_average_days: Number(event.target.value) })} /></label>
            <label>기본 비교<select value={config.include_default_tqqq_comparison ? "on" : "off"} onChange={(event) => setConfig({ ...config, include_default_tqqq_comparison: event.target.value === "on" })}><option value="on">사용</option><option value="off">끄기</option></select></label>
          </div>
          <div className="strategy-toggle-list">
            {allStrategies.map((strategy) => (
              <button
                className={selected.includes(strategy.id) ? "selected" : ""}
                key={strategy.id}
                onClick={() => toggleStrategy(strategy.id)}
              >
                {strategy.label}
              </button>
            ))}
          </div>
          <div className="research-rule-strip">
            <span>
              <ShieldCheck size={15} />
              QQQ 기준 200일선을 기본 신호로 사용
            </span>
            <span>TQQQ와 QLD는 보통 동시 핵심 보유보다 대체 비교</span>
            <span>SGOV/현금 수익률은 대기자산 가정으로 반영</span>
            <span>분할비율·이격도 규칙 백테스트 확장은 다음 단계</span>
          </div>
        </article>

        {result?.tqqq_default_comparison ? (
          <article className="panel span-12 winner-card subtle">
            <div>
              <span className="section-label">Default vs Custom</span>
              <h2>
                <ShieldCheck size={22} />
                기본 TQQQ 200일선과 커스텀 전략 비교
              </h2>
              <p>{result.tqqq_default_comparison.summary}</p>
              <div className="research-rule-strip">
                <span>{result.tqqq_default_comparison.baseline_label}</span>
                <span>{result.tqqq_default_comparison.custom_label}</span>
                <span>현재 리스크 {result.risk_score}점 기준</span>
              </div>
            </div>
            <div className="confidence-breakdown-grid">
              <Score label="최종자산 차이" value={Math.round(result.tqqq_default_comparison.final_capital_delta / 10000)} />
              <Score label="CAGR 차이" value={Math.round(result.tqqq_default_comparison.cagr_delta)} />
              <Score label="MDD 차이" value={Math.round(result.tqqq_default_comparison.max_drawdown_delta)} />
              <Score label="기준 예상차" value={Math.round(result.tqqq_default_comparison.base_projection_delta / 10000)} />
            </div>
            <div className={`insight-report ${result.tqqq_default_comparison.philosophy_audit.verdict === "excellent" || result.tqqq_default_comparison.philosophy_audit.verdict === "good" ? "high" : result.tqqq_default_comparison.philosophy_audit.verdict === "watch" ? "medium" : "low"}`}>
              <span>TQQQ 200 철학 정렬도 / {result.tqqq_default_comparison.philosophy_audit.score}점</span>
              <h3>{result.tqqq_default_comparison.philosophy_audit.summary}</h3>
              <div className="confidence-breakdown-grid">
                {result.tqqq_default_comparison.philosophy_audit.items.map((item) => (
                  <Score key={item.label} label={item.label} value={item.score} />
                ))}
              </div>
              <ListBlock title="100점에 가까워지는 방법" items={result.tqqq_default_comparison.philosophy_audit.to_reach_100} />
            </div>
            <div className="ranking-list compact">
              <ComparisonRow
                label={result.tqqq_default_comparison.baseline_label}
                metrics={result.tqqq_default_comparison.baseline.metrics}
                projection={result.tqqq_default_comparison.baseline.projection}
              />
              <ComparisonRow
                label={result.tqqq_default_comparison.custom_label}
                metrics={result.tqqq_default_comparison.custom.metrics}
                projection={result.tqqq_default_comparison.custom.projection}
              />
            </div>
          </article>
        ) : null}

        {winner ? (
          <article className="panel span-12 winner-card">
            <div>
              <span className="section-label">Recommended</span>
              <h2>
                <Trophy size={22} />
                {winner.strategy_name}
              </h2>
              <p>{winner.reason}</p>
            </div>
            <div className="winner-score">
              <strong>{winner.total_score}</strong>
              <span>종합 점수</span>
            </div>
          </article>
        ) : null}

        {winner ? (
          <article className="panel span-12">
            <h2 className="panel-title">
              <ShieldCheck size={18} />
              신뢰도 분해
            </h2>
            <div className="confidence-breakdown-grid">
              <Score label="수익성" value={winner.profit_score} />
              <Score label="방어력" value={winner.defense_score} />
              <Score label="성향 적합" value={winner.fit_score} />
              <Score label="일관성" value={winner.consistency_score} />
              <Score label="견고성" value={result?.sensitivity?.robustness_score ?? 0} />
            </div>
            <div className="confidence-note-grid">
              <span>수익성은 CAGR과 총수익률을 봅니다.</span>
              <span>방어력은 최대낙폭을 중심으로 봅니다.</span>
              <span>성향 적합은 사용자의 리스크 점수와 전략 위험의 거리입니다.</span>
              <span>견고성은 150/180/200/220/250일선 민감도 차이를 봅니다.</span>
            </div>
          </article>
        ) : null}

        {result ? (
          <article className="panel span-12 insight-card">
            <div className="report-head">
              <h2 className="panel-title">
                <Bot size={18} />
                검증 해석 리포트
              </h2>
              <div className="hero-actions">
                <label className="switch">
                  <input type="checkbox" checked={useAiInsight} onChange={(event) => setUseAiInsight(event.target.checked)} />
                  AI 해석
                </label>
                <button onClick={runInsight} disabled={loadingInsight}>
                  <Bot size={16} />
                  {loadingInsight ? "해석 중" : "리포트 생성"}
                </button>
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
            ) : (
              <p className="muted">전략 랭킹과 민감도 결과를 바탕으로 신뢰도 중심 해석을 생성합니다.</p>
            )}
          </article>
        ) : null}

        {result ? (
          <article className="panel span-12">
            <h2 className="panel-title">
              <Medal size={18} />
              전략 랭킹
            </h2>
            <div className="ranking-list">
              {result.rankings.map((item) => (
                <div className={`ranking-row ${item.verdict}`} key={item.strategy}>
                  <div className="rank-badge">{item.rank}</div>
                  <div>
                    <strong>{item.strategy_name}</strong>
                    <small>{item.reason}</small>
                  </div>
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
            <h2 className="panel-title">
              <BarChart3 size={18} />
              이동평균 민감도 검증
            </h2>
            <div className="winner-card subtle">
              <div>
                <span className="section-label">Robustness</span>
                <h2>{result.sensitivity.verdict}</h2>
                <p>
                  150/180/200/220/250일선을 비교했습니다. 가장 높은 점수는{" "}
                  {result.sensitivity.best_window}일선에서 나왔습니다.
                </p>
              </div>
              <div className="winner-score">
                <strong>{result.sensitivity.robustness_score}</strong>
                <span>견고성</span>
              </div>
            </div>
            <div className="sensitivity-grid">
              {result.sensitivity.results.map((item) => (
                <div className="sensitivity-card" key={item.moving_average_days}>
                  <span>{item.moving_average_days}일선</span>
                  <strong>{item.total_score}</strong>
                  <small>
                    CAGR {formatPct(item.cagr)} / MDD {formatPct(item.max_drawdown)}
                  </small>
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
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function baseProjection(
  projection: { name: "bear" | "base" | "bull"; ending_capital: number; annual_return: number; profit: number; note: string }[],
) {
  return projection.find((item) => item.name === "base");
}

function ComparisonRow({
  label,
  metrics,
  projection,
}: {
  label: string;
  metrics: { final_capital: number; cagr: number; max_drawdown: number; trade_count: number };
  projection: { name: "bear" | "base" | "bull"; ending_capital: number; annual_return: number; profit: number; note: string }[];
}) {
  const base = baseProjection(projection);
  return (
    <div className="ranking-row watch">
      <div className="rank-badge">TQ</div>
      <div>
        <strong>{label}</strong>
        <small>최종 {formatKrw(metrics.final_capital)} · 기준 예상 {base ? formatKrw(base.ending_capital) : "-"}</small>
      </div>
      <div className="rank-metrics">
        <span>CAGR {formatPct(metrics.cagr)}</span>
        <span>MDD {formatPct(metrics.max_drawdown)}</span>
        <span>거래 {metrics.trade_count}회</span>
        {base ? <span>미래 기준 {formatPct(base.annual_return)}</span> : null}
      </div>
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
