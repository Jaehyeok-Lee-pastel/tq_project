import { memo, useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  BarChart3,
  Bot,
  FlaskConical,
  LineChart,
  Medal,
  RefreshCw,
  ShieldCheck,
  Trophy
} from "lucide-react";
import type {
  BacktestStrategy,
  Verdict,
  StrategyRankItem,
  EquityPoint,
  BacktestResult,
  StrategyCompareResponse,
  InsightReport,
  CompareConfig,
  MonteCarloReport,
  WalkForwardReport,
  HeatmapReport,
  OverfittingReport,
  StrategyLabTransfer
} from "./types";

const chartColors = ["#2563eb", "#0f8a63", "#a96700", "#d04444", "#7c3aed"];

const allStrategies: { id: BacktestStrategy; label: string }[] = [
  { id: "tqqq_daily_200ma", label: "보유 기반 일일 적립 감속" },
  { id: "qld_daily_200ma", label: "QLD 일일 적립 감속" },
  { id: "tqqq_200ma", label: "TQQQ 200일선 분할" },
  { id: "qld_200ma", label: "QLD 200일선" },
  { id: "qqq_buy_hold", label: "QQQ 장기 보유" },
  { id: "tqqq_buy_hold", label: "TQQQ 장기 보유" }
];

const presets: {
  id: string;
  title: string;
  summary: string;
  selected: BacktestStrategy[];
  config: Partial<CompareConfig>;
}[] = [
  {
    id: "best_practice_daily_cash_defense",
    title: "베스트 프랙티스 7:3 + 조기방어 2% + 현금 방어",
    summary:
      "2026-07 전 구간(1999~) 전수 1위(종합 83점): 월 적립 TQQQ 70%/QQQM 30% + 200일선 +2% 조기 방어 밴드 + 이탈 시 TQQQ·QQQM 전량 매도 후 현금/SGOV 100% 방어. 수익을 더 원하면 적립 비중만 80/20으로(전수 2위), 최종 금액 극대화는 방어를 SPYM+SGOV 반반으로(전수 3위).",
    selected: ["tqqq_daily_200ma", "tqqq_200ma", "qld_200ma", "qqq_buy_hold", "tqqq_buy_hold"],
    config: {
      initial_capital: 2500000,
      initial_tqqq_value: 1600000,
      initial_one_x_value: 500000,
      initial_cash_value: 400000,
      monthly_contribution: 1000000,
      daily_base_tqqq_ratio: 70,
      daily_base_one_x_ratio: 30,
      ma_exit_band_pct: 2,
      defense_mode: "cash",
      one_x_symbol: "QQQM",
      tqqq_target_ratio: 45,
      qld_target_ratio: 60,
      cash_yield: 4.5,
      risk_score: 80
    }
  },
  {
    id: "current_daily_7_3",
    title: "현재 보유 + 월 100만원 7:3",
    summary:
      "TQQQ 160만, QQQM 50만, 현금 40만에서 출발해 월 100만원을 TQQQ 70%, QQQM 30%로 적립합니다.",
    selected: ["tqqq_daily_200ma", "tqqq_200ma", "qld_200ma", "qqq_buy_hold", "tqqq_buy_hold"],
    config: {
      initial_capital: 2500000,
      initial_tqqq_value: 1600000,
      initial_one_x_value: 500000,
      initial_cash_value: 400000,
      monthly_contribution: 1000000,
      daily_base_tqqq_ratio: 70,
      daily_base_one_x_ratio: 30,
      ma_exit_band_pct: 0,
      defense_mode: "",
      one_x_symbol: "QQQM",
      tqqq_target_ratio: 45,
      qld_target_ratio: 60,
      cash_yield: 4.5,
      risk_score: 78
    }
  },
  {
    id: "daily_6_4",
    title: "보수적 적립 6:4",
    summary:
      "월 추가금을 TQQQ 60%, QQQM 40%로 낮춰 비교합니다. 주의: 현재 규칙에서 1x는 하락장에도 방어되지 않아, 1x 비중이 클수록 낙폭이 오히려 깊어질 수 있습니다(전 구간 검증 결과).",
    selected: ["tqqq_daily_200ma", "tqqq_200ma", "qqq_buy_hold"],
    config: {
      daily_base_tqqq_ratio: 60,
      daily_base_one_x_ratio: 40,
      monthly_contribution: 1000000,
      ma_exit_band_pct: 0,
      defense_mode: "",
      risk_score: 72
    }
  },
  {
    id: "daily_8_2",
    title: "공격적 적립 8:2",
    summary: "상승 추세 참여를 더 키우되 이격도 감속과 200일선 방어는 유지합니다.",
    selected: ["tqqq_daily_200ma", "tqqq_200ma", "tqqq_buy_hold"],
    config: {
      daily_base_tqqq_ratio: 80,
      daily_base_one_x_ratio: 20,
      monthly_contribution: 1000000,
      ma_exit_band_pct: 0,
      defense_mode: "",
      risk_score: 85
    }
  }
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
    watch: "관찰"
  }[verdict];
}

import {
  ADOPTABLE,
  requestAdopt,
  requestCompare,
  requestHeatmap,
  requestInsight,
  requestMonteCarlo,
  requestOverfitting,
  requestWalkForward
} from "./api";
import { HeatmapTab, MonteCarloTab, OverfittingTab, WalkForwardTab } from "./AdvancedValidation";
// Advanced validation remains available in the API and test suite, but is
// intentionally hidden from the everyday research workflow.
const SHOW_ADVANCED_VALIDATION = false;

export function ResearchWorkspace() {
  const location = useLocation();
  const transfer = location.state as StrategyLabTransfer | null;
  const [status, setStatus] = useState(
    "현재 보유 상태와 월 적립 규칙을 기준으로 여러 전략을 비교합니다."
  );
  const [loading, setLoading] = useState(false);
  const [loadingInsight, setLoadingInsight] = useState(false);
  const [adopting, setAdopting] = useState(false);
  const [researchTab, setResearchTab] = useState<
    "compare" | "montecarlo" | "walkforward" | "heatmap" | "overfitting"
  >("compare");
  const [mcReport, setMcReport] = useState<MonteCarloReport | null>(null);
  const [mcLoading, setMcLoading] = useState(false);
  const [mcPaths, setMcPaths] = useState(300);
  const [mcStatus, setMcStatus] = useState(
    "현재 설정한 전략을 수백 개의 '새로 생성된 미래'에서 검증합니다. 실행에 30~60초가 걸립니다."
  );
  const [wfReport, setWfReport] = useState<WalkForwardReport | null>(null);
  const [wfLoading, setWfLoading] = useState(false);
  const [wfStatus, setWfStatus] = useState(
    "과거의 각 시점에서 최적 규칙을 골랐다면 다음 구간(미래)에서 어땠을지 검증합니다. 실행에 약 50초가 걸립니다."
  );
  const [hmReport, setHmReport] = useState<HeatmapReport | null>(null);
  const [hmLoading, setHmLoading] = useState(false);
  const [hmStatus, setHmStatus] = useState(
    "적립비율 × 이탈밴드 격자를 훑어 현재 설정이 안정적인 '고원'인지 운 좋은 '봉우리'인지 봅니다. 약 40초."
  );
  const [ofReport, setOfReport] = useState<OverfittingReport | null>(null);
  const [ofLoading, setOfLoading] = useState(false);
  const [ofStatus, setOfStatus] = useState(
    "40개 설정을 시험한 선택 편향을 통계적으로 보정합니다 (디플레이티드 샤프 + 과최적화 확률). 약 10초."
  );
  const [result, setResult] = useState<StrategyCompareResponse | null>(null);
  const [insight, setInsight] = useState<InsightReport | null>(null);
  const [useAiInsight, setUseAiInsight] = useState(true);
  const [selectedDetail, setSelectedDetail] = useState<BacktestStrategy>("tqqq_daily_200ma");
  const [config, setConfig] = useState<CompareConfig>({
    start_date: "",
    end_date: "",
    initial_capital: 2500000,
    initial_tqqq_value: 1600000,
    initial_one_x_value: 500000,
    initial_cash_value: 400000,
    risk_score: 78,
    tqqq_target_ratio: 45,
    qld_target_ratio: 60,
    one_x_target_ratio: 30,
    one_x_symbol: "QQQM",
    cash_yield: 4.5,
    moving_average_days: 200,
    include_default_tqqq_comparison: true,
    default_tqqq_target_ratio: 60,
    monthly_contribution: 1000000,
    daily_base_tqqq_ratio: 70,
    daily_base_one_x_ratio: 30,
    ma_exit_band_pct: 0,
    defense_mode: "",
    reserve_redeploy_days: 0,
    one_x_upfront_monthly: true
  });
  const [selected, setSelected] = useState<BacktestStrategy[]>([
    "tqqq_daily_200ma",
    "tqqq_200ma",
    "qld_200ma",
    "qqq_buy_hold",
    "tqqq_buy_hold"
  ]);
  const [transferNotice, setTransferNotice] = useState<StrategyLabTransfer | null>(null);
  const winner = result?.rankings[0];
  const currentTotal =
    config.initial_tqqq_value + (config.initial_qld_value ?? 0) + config.initial_one_x_value + config.initial_cash_value;
  const detailBacktest = useMemo(
    () =>
      result?.backtests.find((item) => item.strategy === selectedDetail) ?? result?.backtests[0],
    [result, selectedDetail]
  );

  useEffect(() => {
    if (transfer?.source !== "strategy_recommendation") return;
    setConfig((current) => ({ ...current, ...transfer.config }));
    setSelected(transfer.selected);
    setSelectedDetail(transfer.selected[0]);
    setResearchTab("compare");
    setResult(null);
    setInsight(null);
    setTransferNotice(transfer);
    setStatus(`${transfer.plan_title} 추천안을 불러왔습니다. 전략 비교 실행으로 검증을 시작하세요.`);
  }, [transfer]);

  function updateConfig<K extends keyof CompareConfig>(key: K, value: CompareConfig[K]) {
    setConfig((current) => {
      const next = { ...current, [key]: value };
      const total = next.initial_tqqq_value + (next.initial_qld_value ?? 0) + next.initial_one_x_value + next.initial_cash_value;
      return total > 0 ? { ...next, initial_capital: total } : next;
    });
  }

  function toggleStrategy(strategy: BacktestStrategy) {
    setSelected((current) =>
      current.includes(strategy)
        ? current.filter((item) => item !== strategy)
        : [...current, strategy]
    );
  }

  function applyPreset(preset: (typeof presets)[number]) {
    setConfig((current) => {
      const next = { ...current, ...preset.config };
      const total = next.initial_tqqq_value + (next.initial_qld_value ?? 0) + next.initial_one_x_value + next.initial_cash_value;
      return total > 0 ? { ...next, initial_capital: total } : next;
    });
    setSelected(preset.selected);
    setSelectedDetail(preset.selected[0]);
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
    setStatus("현재 보유 상태와 월 적립 규칙으로 전략 성과를 계산하는 중입니다...");
    try {
      const response = await requestCompare({ ...config, strategies: selected });
      setResult(response);
      setSelectedDetail(response.recommended_strategy);
      setInsight(null);
      setStatus(response.summary);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "전략 비교 실패");
    } finally {
      setLoading(false);
    }
  }

  async function adoptStrategy(item: StrategyRankItem) {
    if (!ADOPTABLE.includes(item.strategy)) {
      setStatus("장기 보유 전략은 채택 없이도 유지할 수 있어 별도 관리 대상이 아닙니다.");
      return;
    }
    setAdopting(true);
    setStatus(`${item.strategy_name} 전략을 채택하는 중입니다...`);
    try {
      await requestAdopt(config, item);
      setStatus(
        `${item.strategy_name} 전략을 채택했습니다. 전략 관리의 '오늘의 판단' 탭에서 매일 실행 지시를 확인하세요.`
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "전략 채택 실패");
    } finally {
      setAdopting(false);
    }
  }

  async function runOverfitting() {
    setOfLoading(true);
    setOfStatus("40개 설정으로 디플레이티드 샤프와 과최적화 확률을 계산하는 중입니다... (약 10초)");
    try {
      const report = await requestOverfitting();
      setOfReport(report);
      setOfStatus(report.headline);
    } catch (error) {
      setOfStatus(error instanceof Error ? error.message : "과최적화 검증 실패");
    } finally {
      setOfLoading(false);
    }
  }

  async function runHeatmap() {
    setHmLoading(true);
    setHmStatus("45개 파라미터 조합을 전 구간 백테스트하는 중입니다... (약 40초)");
    try {
      const report = await requestHeatmap();
      setHmReport(report);
      setHmStatus(report.headline);
    } catch (error) {
      setHmStatus(error instanceof Error ? error.message : "히트맵 실패");
    } finally {
      setHmLoading(false);
    }
  }

  async function runWalkForward() {
    setWfLoading(true);
    setWfStatus("6개 학습/검증 창에서 84개 백테스트를 실행하는 중입니다... (약 50초)");
    try {
      const report = await requestWalkForward();
      setWfReport(report);
      setWfStatus(report.headline);
    } catch (error) {
      setWfStatus(error instanceof Error ? error.message : "워크포워드 실패");
    } finally {
      setWfLoading(false);
    }
  }

  async function runMonteCarlo() {
    setMcLoading(true);
    setMcStatus(`${mcPaths}개의 새로운 미래 경로를 생성하고 전략을 검증하는 중입니다... (30~60초)`);
    try {
      const report = await requestMonteCarlo(config, mcPaths);
      setMcReport(report);
      setMcStatus(report.headline);
    } catch (error) {
      setMcStatus(error instanceof Error ? error.message : "미래 시뮬레이션 실패");
    } finally {
      setMcLoading(false);
    }
  }

  async function runInsight() {
    if (!result) return;
    setLoadingInsight(true);
    setStatus("전략 비교 결과를 해석하는 중입니다...");
    try {
      const response = await requestInsight(result, useAiInsight);
      setInsight(response);
      setStatus(
        response.ai_used
          ? "AI 해석 리포트를 생성했습니다."
          : "규칙 기반 해석 리포트를 생성했습니다."
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "해석 리포트 생성 실패");
    } finally {
      setLoadingInsight(false);
    }
  }

  return (
    <section className="page-grid research-workspace">
      <div className="hero-panel compare research-hero">
        <div>
          <span className="section-label">03 · Research workspace</span>
          <h2>
            {researchTab === "compare"
              ? "과거 데이터로 전략을 비교·검증합니다"
              : researchTab === "montecarlo"
                ? "다양한 미래에서 전략을 검증합니다"
                : researchTab === "walkforward"
                  ? "시간을 거슬러 규칙의 강건성을 검증합니다"
                  : researchTab === "heatmap"
                    ? "파라미터 지형에서 과최적화를 검증합니다"
                    : "다중검정 편향을 통계로 보정합니다"}
          </h2>
          <p>
            {researchTab === "compare"
              ? status
              : researchTab === "montecarlo"
                ? mcStatus
                : researchTab === "walkforward"
                  ? wfStatus
                  : researchTab === "heatmap"
                    ? hmStatus
                    : ofStatus}
          </p>
        </div>
        {researchTab === "compare" ? (
          <button className="primary" onClick={runCompare} disabled={loading}>
            <RefreshCw size={17} />
            {loading ? "비교 중" : "전략 비교 실행"}
          </button>
        ) : researchTab === "montecarlo" ? (
          <button className="primary" onClick={runMonteCarlo} disabled={mcLoading}>
            <RefreshCw size={17} />
            {mcLoading ? "생성 중" : "미래 시뮬레이션 실행"}
          </button>
        ) : researchTab === "walkforward" ? (
          <button className="primary" onClick={runWalkForward} disabled={wfLoading}>
            <RefreshCw size={17} />
            {wfLoading ? "검증 중" : "워크포워드 실행"}
          </button>
        ) : researchTab === "heatmap" ? (
          <button className="primary" onClick={runHeatmap} disabled={hmLoading}>
            <RefreshCw size={17} />
            {hmLoading ? "계산 중" : "지형 계산 실행"}
          </button>
        ) : (
          <button className="primary" onClick={runOverfitting} disabled={ofLoading}>
            <RefreshCw size={17} />
            {ofLoading ? "계산 중" : "과최적화 검증 실행"}
          </button>
        )}
      </div>

      {transferNotice ? (
        <aside className={`research-transfer-note ${transferNotice.fidelity}`} aria-live="polite">
          <div>
            <span>추천안에서 불러옴</span>
            <strong>{transferNotice.plan_title}</strong>
          </div>
          <p>
            {transferNotice.fidelity === "exact"
              ? "추천안의 운용 규칙과 초기 금액을 그대로 채웠습니다. 비교 실행으로 과거 검증을 시작하세요."
              : "초기 금액과 비중을 채웠습니다. 일일 QLD·혼합형은 전용 검증 엔진이 없어 가장 가까운 200일선 전략과 비교합니다."}
          </p>
        </aside>
      ) : null}

      <div className="research-subtabs">
        <button
          className={researchTab === "compare" ? "selected" : ""}
          onClick={() => setResearchTab("compare")}
          type="button"
        >
          <BarChart3 size={16} /> 전략 비교 <small>과거 1999~2026 검증</small>
        </button>
        <button
          className={researchTab === "montecarlo" ? "selected" : ""}
          onClick={() => setResearchTab("montecarlo")}
          type="button"
        >
          <FlaskConical size={16} /> 미래 시뮬레이션 <small>레짐 몬테카를로</small>
        </button>
        {SHOW_ADVANCED_VALIDATION ? (
          <>
            <button
              className={researchTab === "walkforward" ? "selected" : ""}
              onClick={() => setResearchTab("walkforward")}
              type="button"
            >
              <LineChart size={16} /> 워크포워드 <small>시간축 과최적화 검증</small>
            </button>
            <button
              className={researchTab === "heatmap" ? "selected" : ""}
              onClick={() => setResearchTab("heatmap")}
              type="button"
            >
              <BarChart3 size={16} /> 파라미터 지형 <small>고원 vs 봉우리</small>
            </button>
            <button
              className={researchTab === "overfitting" ? "selected" : ""}
              onClick={() => setResearchTab("overfitting")}
              type="button"
            >
              <ShieldCheck size={16} /> 과최적화 검증 <small>DSR · PBO 통계</small>
            </button>
          </>
        ) : null}
      </div>

      {SHOW_ADVANCED_VALIDATION && researchTab === "walkforward" ? (
        <WalkForwardTab report={wfReport} loading={wfLoading} onRun={runWalkForward} />
      ) : null}
      {SHOW_ADVANCED_VALIDATION && researchTab === "heatmap" ? (
        <HeatmapTab report={hmReport} loading={hmLoading} onRun={runHeatmap} />
      ) : null}
      {SHOW_ADVANCED_VALIDATION && researchTab === "overfitting" ? (
        <OverfittingTab report={ofReport} loading={ofLoading} onRun={runOverfitting} />
      ) : null}

      {researchTab === "montecarlo" ? (
        <MonteCarloTab
          report={mcReport}
          loading={mcLoading}
          paths={mcPaths}
          setPaths={setMcPaths}
          config={config}
          onRun={runMonteCarlo}
        />
      ) : researchTab === "compare" ? (
        <div className="content-grid research-analysis-grid">
          <article className="panel span-12 research-lab-card research-presets-panel">
            <div className="report-head">
              <h2 className="panel-title">
                <FlaskConical size={18} />
                연구 프리셋
              </h2>
              <p>
                실전 추천과 분리된 연구 공간입니다. 현재 보유 상태에서 월 적립 비율을 바꿨을 때
                결과를 비교합니다.
              </p>
            </div>
            <div className="research-preset-grid">
              {presets.map((preset) => (
                <button key={preset.id} onClick={() => applyPreset(preset)}>
                  <strong>{preset.title}</strong>
                  <span>{preset.summary}</span>
                </button>
              ))}
            </div>
          </article>

          <article className="panel span-12 research-config-panel">
            <h2 className="panel-title">
              <BarChart3 size={18} />
              현재 보유와 적립 조건
            </h2>
            <div className="backtest-controls">
              <label>
                현재 TQQQ
                <input
                  type="number"
                  value={config.initial_tqqq_value}
                  onChange={(event) =>
                    updateConfig("initial_tqqq_value", Number(event.target.value))
                  }
                />
              </label>
              <label>
                현재 QLD
                <input
                  type="number"
                  value={config.initial_qld_value ?? 0}
                  onChange={(event) =>
                    updateConfig("initial_qld_value", Number(event.target.value))
                  }
                />
              </label>
              <label>
                현재 {config.one_x_symbol}
                <input
                  type="number"
                  value={config.initial_one_x_value}
                  onChange={(event) =>
                    updateConfig("initial_one_x_value", Number(event.target.value))
                  }
                />
              </label>
              <label>
                현재 현금
                <input
                  type="number"
                  value={config.initial_cash_value}
                  onChange={(event) =>
                    updateConfig("initial_cash_value", Number(event.target.value))
                  }
                />
              </label>
              <label>
                현재 총액
                <input
                  type="number"
                  value={currentTotal || config.initial_capital}
                  onChange={(event) => updateConfig("initial_capital", Number(event.target.value))}
                />
              </label>
              <label>
                월 추가금
                <input
                  type="number"
                  value={config.monthly_contribution}
                  onChange={(event) =>
                    updateConfig("monthly_contribution", Number(event.target.value))
                  }
                />
              </label>
              <label>
                리스크 점수
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={config.risk_score}
                  onChange={(event) => updateConfig("risk_score", Number(event.target.value))}
                />
              </label>
              <label>
                적립 TQQQ 비중
                <input
                  type="number"
                  value={config.daily_base_tqqq_ratio}
                  onChange={(event) =>
                    updateConfig("daily_base_tqqq_ratio", Number(event.target.value))
                  }
                />
              </label>
              <label>
                적립 1x 비중
                <input
                  type="number"
                  value={config.daily_base_one_x_ratio}
                  onChange={(event) =>
                    updateConfig("daily_base_one_x_ratio", Number(event.target.value))
                  }
                />
              </label>
              <label>
                1x 자산
                <select
                  value={config.one_x_symbol}
                  onChange={(event) => updateConfig("one_x_symbol", event.target.value)}
                >
                  <option value="QQQM">QQQM</option>
                  <option value="QQQ">QQQ</option>
                  <option value="SPYM">SPYM</option>
                </select>
              </label>
            </div>
            <details className="research-advanced-settings">
              <summary>
                <span>검증 조건과 고급 설정</span>
                <small>이동평균, 방어 밴드, 재투입, 기간</small>
              </summary>
              <div className="backtest-controls research-advanced-grid">
                <label>
                  현금/SGOV 기대수익
                  <input
                    type="number"
                    value={config.cash_yield}
                    onChange={(event) => updateConfig("cash_yield", Number(event.target.value))}
                  />
                </label>
                <label>
                  기준 이동평균
                  <input
                    type="number"
                    min={50}
                    max={300}
                    value={config.moving_average_days}
                    onChange={(event) =>
                      updateConfig("moving_average_days", Number(event.target.value))
                    }
                  />
                </label>
                <label>
                  조기 방어 밴드 %
                  <input
                    type="number"
                    min={-5}
                    max={5}
                    step={0.5}
                    value={config.ma_exit_band_pct}
                    onChange={(event) =>
                      updateConfig("ma_exit_band_pct", Number(event.target.value))
                    }
                  />
                </label>
                <label>
                  이월분 재투입 일수 (0=끄기)
                  <input
                    type="number"
                    min={0}
                    max={126}
                    value={config.reserve_redeploy_days}
                    onChange={(event) =>
                      updateConfig("reserve_redeploy_days", Number(event.target.value))
                    }
                  />
                </label>
                <label className="switch">
                  <input
                    type="checkbox"
                    checked={config.one_x_upfront_monthly}
                    onChange={(event) =>
                      updateConfig("one_x_upfront_monthly", event.target.checked)
                    }
                  />
                  1x 월급날 일괄 매수 (TQQQ는 매일 감속)
                </label>
                <label>
                  이탈 시 방어 모드
                  <select
                    value={config.defense_mode}
                    onChange={(event) =>
                      updateConfig(
                        "defense_mode",
                        event.target.value as CompareConfig["defense_mode"]
                      )
                    }
                  >
                    <option value="">전략 기본값</option>
                    <option value="cash">현금/SGOV 100%</option>
                    <option value="spym_sgov_half">SPYM+SGOV 반반</option>
                    <option value="hold_one_x">1x 계속 보유</option>
                  </select>
                </label>
                <label>
                  시작일 (비우면 1999년~)
                  <input
                    type="date"
                    min="1999-12-01"
                    value={config.start_date}
                    onChange={(event) => updateConfig("start_date", event.target.value)}
                  />
                </label>
                <label>
                  종료일 (비우면 최신)
                  <input
                    type="date"
                    value={config.end_date}
                    onChange={(event) => updateConfig("end_date", event.target.value)}
                  />
                </label>
              </div>
            </details>
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
                <ShieldCheck size={15} /> 시작 보유분은 그대로 출발
              </span>
              <span>각 전략별 방식으로 월 추가금 반영</span>
              <span>QQQ 200일선 위에서만 TQQQ 신규 적립</span>
              <span>상세 결과에서 거래 로그와 경로 확인</span>
            </div>
          </article>

          {winner ? (
            <article className="panel span-12 winner-card">
              <div>
                <span className="section-label">Recommended</span>
                <h2>
                  <Trophy size={22} />
                  {winner.strategy_name}
                </h2>
                <p>{winner.reason}</p>
                {ADOPTABLE.includes(winner.strategy) ? (
                  <button
                    className="primary"
                    type="button"
                    disabled={adopting}
                    onClick={() => void adoptStrategy(winner)}
                  >
                    {adopting ? "채택 중..." : "이 전략 채택하기 → 오늘의 판단으로 관리"}
                  </button>
                ) : null}
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
                판단 근거
              </h2>
              <div className="confidence-breakdown-grid">
                <Score label="수익성" value={winner.profit_score} />
                <Score label="방어력" value={winner.defense_score} />
                <Score label="실행 용이" value={winner.execution_score} />
                <Score label="성향 적합" value={winner.fit_score} />
                <Score label="일관성" value={winner.consistency_score} />
                <Score label="견고성" value={result?.sensitivity?.robustness_score ?? 0} />
              </div>
              <p className="muted">
                실행 용이 점수는 판단이 필요한 매매 이벤트 빈도(연{" "}
                {winner.decisions_per_year.toFixed(1)}회)와 규칙 복잡도를 반영합니다. 정기 적립
                매수처럼 기계적으로 자동화할 수 있는 행동은 부담으로 계산하지 않습니다.
              </p>
            </article>
          ) : null}

          {result ? (
            <article className="panel span-12">
              <h2 className="panel-title">
                <Medal size={18} />
                전략 순위
              </h2>
              <div className="ranking-list">
                {result.rankings.map((item) => (
                  <button
                    className={`ranking-row ${item.verdict}`}
                    key={item.strategy}
                    onClick={() => setSelectedDetail(item.strategy)}
                  >
                    <div className="rank-badge">{item.rank}</div>
                    <div>
                      <strong>{item.strategy_name}</strong>
                      <small>{item.reason}</small>
                    </div>
                    <div className="ranking-total">
                      <strong>{item.total_score}</strong>
                      <span>종합</span>
                    </div>
                    <Score label="수익" value={item.profit_score} />
                    <Score label="방어" value={item.defense_score} />
                    <Score label="실행" value={item.execution_score} />
                    <div className="rank-metrics">
                      <span>{formatKrw(item.final_capital)}</span>
                      <span>CAGR {formatPct(item.cagr)}</span>
                      <span>MDD {formatPct(item.max_drawdown)}</span>
                      <span>{verdictLabel(item.verdict)}</span>
                    </div>
                  </button>
                ))}
              </div>
            </article>
          ) : null}

          {result?.rule_robustness ? (
            <article className="panel span-12">
              <div className="report-head">
                <div>
                  <h2 className="panel-title">
                    <FlaskConical size={18} />
                    규칙 강건성 검증 — {result.rule_robustness.strategy_name}
                  </h2>
                  <p>{result.rule_robustness.note}</p>
                </div>
                <div className="winner-score">
                  <strong>{result.rule_robustness.robustness_score}</strong>
                  <span>{result.rule_robustness.verdict}</span>
                </div>
              </div>
              <div className="robustness-table">
                <div className="robustness-row head">
                  <span>규칙 변형</span>
                  <span>CAGR</span>
                  <span>MDD</span>
                  <span>종합 점수</span>
                </div>
                {result.rule_robustness.results.map((item) => (
                  <div className="robustness-row" key={item.label}>
                    <span>{item.label}</span>
                    <span>{formatPct(item.cagr)}</span>
                    <span>{formatPct(item.max_drawdown)}</span>
                    <span>{item.total_score}</span>
                  </div>
                ))}
              </div>
              <p className="muted">
                CAGR 변동폭 {formatPct(result.rule_robustness.cagr_range)} · MDD 변동폭{" "}
                {formatPct(result.rule_robustness.mdd_range)}
                {result.sensitivity
                  ? ` · 이동평균(150~250일) 견고성 ${result.sensitivity.robustness_score}점 (최적 ${result.sensitivity.best_window}일)`
                  : ""}
              </p>
            </article>
          ) : null}

          {result ? (
            <article className="panel span-12">
              <div className="report-head">
                <div>
                  <h2 className="panel-title">
                    <LineChart size={18} />
                    상세 테스트 결과
                  </h2>
                  <p>
                    전략별 자산곡선, 매수/매도 과정, 연도별 성과를 확인합니다. 순위표 또는 아래 탭을
                    눌러 전략을 바꿀 수 있습니다.
                  </p>
                </div>
                {(() => {
                  const detailRank = result.rankings.find(
                    (item) => item.strategy === detailBacktest?.strategy
                  );
                  return detailRank && ADOPTABLE.includes(detailRank.strategy) ? (
                    <button
                      type="button"
                      disabled={adopting}
                      onClick={() => void adoptStrategy(detailRank)}
                    >
                      {adopting ? "채택 중..." : `${detailRank.strategy_name} 채택`}
                    </button>
                  ) : null;
                })()}
              </div>
              <div className="detail-tabs">
                {result.backtests.map((backtest) => (
                  <button
                    className={backtest.strategy === detailBacktest?.strategy ? "selected" : ""}
                    key={backtest.strategy}
                    onClick={() => setSelectedDetail(backtest.strategy)}
                  >
                    {backtest.strategy_name}
                  </button>
                ))}
              </div>
              <MultiStrategyChart
                backtests={result.backtests}
                selected={detailBacktest?.strategy}
              />
              {detailBacktest ? <BacktestDetail result={detailBacktest} /> : null}
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
                    <input
                      type="checkbox"
                      checked={useAiInsight}
                      onChange={(event) => setUseAiInsight(event.target.checked)}
                    />
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
                  <span>
                    {insight.ai_used ? "AI" : "Rule"} / {confidenceLabel(insight.confidence_level)}
                  </span>
                  <h3>{insight.headline}</h3>
                  <p>{insight.summary}</p>
                  <div className="report-columns">
                    <ListBlock title="강한 근거" items={insight.strongest_evidence} />
                    <ListBlock title="주요 위험" items={insight.main_risks} />
                    <ListBlock title="다음 행동" items={insight.recommended_next_steps} />
                  </div>
                </div>
              ) : (
                <p className="muted">비교 결과를 바탕으로 해석 리포트를 생성할 수 있습니다.</p>
              )}
            </article>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

const MultiStrategyChart = memo(function MultiStrategyChart({
  backtests,
  selected
}: {
  backtests: BacktestResult[];
  selected?: BacktestStrategy;
}) {
  const allPoints = backtests.flatMap((item) => item.equity_curve);
  if (!allPoints.length) return null;
  const min = Math.min(...allPoints.map((point) => point.equity));
  const max = Math.max(...allPoints.map((point) => point.equity));
  const range = max - min || 1;
  const width = 1000;
  const height = 280;
  const chartTop = 24;
  const chartBottom = 24;
  const chartHeight = height - chartTop - chartBottom;
  const focused = backtests.find((item) => item.strategy === selected) ?? backtests[0];
  const focusedEnd = focused.equity_curve[focused.equity_curve.length - 1];

  function pathFor(points: EquityPoint[]) {
    if (points.length < 2) return "";
    return points
      .map((point, index) => {
        const x = (index / (points.length - 1)) * width;
        const y = chartTop + chartHeight - ((point.equity - min) / range) * chartHeight;
        return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }

  const focusedEndY = focusedEnd
    ? chartTop + chartHeight - ((focusedEnd.equity - min) / range) * chartHeight
    : chartTop + chartHeight;

  return (
    <div className="comparison-chart">
      <div className="comparison-chart-frame">
        <div className="comparison-chart-scale" aria-hidden="true">
          <span>{Math.round(max).toLocaleString("ko-KR")}원</span>
          <span>동일 원금 기준 자산 추이</span>
          <span>{Math.round(min).toLocaleString("ko-KR")}원</span>
        </div>
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="전략별 백테스트 자산 곡선">
          <title>전략별 백테스트 자산 곡선</title>
          <desc>선택한 전략은 진하게, 나머지 전략은 옅게 표시합니다. 범례의 전략명과 색상을 함께 확인하세요.</desc>
          <g className="comparison-chart-grid" aria-hidden="true">
            {[0.2, 0.4, 0.6, 0.8].map((ratio) => (
              <line key={ratio} x1="0" x2={width} y1={chartTop + chartHeight * ratio} y2={chartTop + chartHeight * ratio} />
            ))}
          </g>
          {backtests.map((item, index) => (
            <path
              d={pathFor(item.equity_curve)}
              key={item.strategy}
              style={{
                stroke: chartColors[index % chartColors.length],
                opacity: !selected || selected === item.strategy ? 1 : 0.28,
                strokeWidth: selected === item.strategy ? 3.2 : 2
              }}
            />
          ))}
          {focusedEnd ? (
            <g className="comparison-chart-endpoint">
              <circle cx={width - 2} cy={focusedEndY} r="6" fill="#fff" stroke="currentColor" strokeWidth="3" />
              <text x={width - 12} y={Math.max(chartTop + 12, focusedEndY - 12)} textAnchor="end">
                {Math.round(focusedEnd.equity).toLocaleString("ko-KR")}원
              </text>
            </g>
          ) : null}
        </svg>
      </div>
      <div className="chart-legend">
        {backtests.map((item, index) => (
          <span className={selected === item.strategy ? "selected" : ""} key={item.strategy}>
            <em style={{ background: chartColors[index % chartColors.length] }} />
            {item.strategy_name}
          </span>
        ))}
      </div>
    </div>
  );
});

function BacktestDetail({ result }: { result: BacktestResult }) {
  const [showAllTrades, setShowAllTrades] = useState(false);
  const displayedTrades = showAllTrades ? result.trades : result.trades.slice(-14).reverse();
  const firstTrade = result.trades[0];
  const lastTrade = result.trades[result.trades.length - 1];

  return (
    <div className="backtest-detail-grid">
      <div className="detail-summary-card">
        <span className="section-label">
          {result.period_start} - {result.period_end}
        </span>
        <h3>{result.strategy_name}</h3>
        <p>{result.interpretation?.[0] ?? "전략 규칙에 따른 백테스트 결과입니다."}</p>
        <div className="detail-metric-grid">
          <Score label="최종자산" value={Math.round(result.metrics.final_capital / 10000)} />
          <Score label="CAGR" value={Math.round(result.metrics.cagr)} />
          <Score label="MDD" value={Math.round(result.metrics.max_drawdown)} />
          <Score label="거래" value={result.metrics.trade_count} />
          <Score label="승률" value={Math.round(result.metrics.win_rate)} />
          <Score label="최장DD" value={result.metrics.longest_drawdown_days} />
        </div>
      </div>

      <div className="detail-summary-card">
        <span className="section-label">Process</span>
        <h3>어떤 과정으로 결과가 나왔나</h3>
        <p>
          첫 거래는{" "}
          {firstTrade
            ? `${firstTrade.date} ${firstTrade.symbol} ${firstTrade.action === "buy" ? "매수" : "매도"}`
            : "기록 없음"}
          이고, 마지막 거래는{" "}
          {lastTrade
            ? `${lastTrade.date} ${lastTrade.symbol} ${lastTrade.action === "buy" ? "매수" : "매도"}`
            : "기록 없음"}
          입니다. 거래 로그는 최근 기록부터 아래에 표시됩니다.
        </p>
        <ListBlock title="해석 메모" items={result.interpretation ?? []} />
        {result.data_notes?.length ? (
          <ListBlock title="데이터·계산 기준" items={result.data_notes} />
        ) : null}
      </div>

      <div className="detail-summary-card span-detail">
        <h3>연도별 성과</h3>
        <div className="year-return-grid">
          {result.yearly_returns.map((item) => (
            <span className={item.return_pct >= 0 ? "ok" : "danger"} key={item.year}>
              <small>{item.year}</small>
              <strong>{formatPct(item.return_pct)}</strong>
            </span>
          ))}
        </div>
      </div>

      <div className="detail-summary-card span-detail">
        <h3>시장 국면별 성과</h3>
        <div className="regime-grid">
          {result.regime_performance.map((item) => (
            <div className={`regime-card ${item.regime}`} key={item.regime}>
              <span>{item.label}</span>
              <strong>{formatPct(item.return_pct)}</strong>
              <small>
                {item.days}일 · 승률 {formatPct(item.win_rate)} · MDD {formatPct(item.max_drawdown)}
              </small>
            </div>
          ))}
        </div>
      </div>

      <div className="detail-summary-card span-detail">
        <div className="trade-log-head">
          <div>
            <h3>매수/매도 전략 로그</h3>
            <p>
              {showAllTrades
                ? "처음 거래부터 전체 로그를 표시합니다."
                : "최근 거래 14개를 표시합니다."}
            </p>
          </div>
          {result.trades.length > 14 ? (
            <button type="button" onClick={() => setShowAllTrades((current) => !current)}>
              {showAllTrades ? "최근 로그만 보기" : "처음부터 전체 로그"}
            </button>
          ) : null}
        </div>
        {displayedTrades.length ? (
          <div className="trade-log-table">
            {displayedTrades.map((trade, index) => (
              <div className={trade.action} key={`${trade.date}-${trade.symbol}-${index}`}>
                <span>{trade.date}</span>
                <strong>
                  {trade.symbol} {trade.action === "buy" ? "매수" : "매도"}
                </strong>
                <em>{trade.ratio.toFixed(1)}%</em>
                <small>{trade.reason}</small>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">해당 전략은 기간 중 별도 매수/매도 전환 로그가 없습니다.</p>
        )}
      </div>
    </div>
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

function Score({ label, value }: { label: string; value: number }) {
  return (
    <div className="mini-score">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
