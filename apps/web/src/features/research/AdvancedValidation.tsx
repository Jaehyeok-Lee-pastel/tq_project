import { BarChart3, FlaskConical, LineChart, RefreshCw, ShieldCheck } from "lucide-react";

import type {
  CompareConfig,
  HeatmapReport,
  MonteCarloReport,
  OverfittingReport,
  Percentiles,
  WalkForwardReport
} from "./types";

export function OverfittingTab({
  report,
  loading,
  onRun
}: {
  report: OverfittingReport | null;
  loading: boolean;
  onRun: () => void;
}) {
  return (
    <div className="content-grid">
      <article className="panel span-12">
        <div className="report-head">
          <div>
            <h2 className="panel-title">
              <ShieldCheck size={18} />
              과최적화 검증 (디플레이티드 샤프 · PBO)
            </h2>
            <p>
              우리는 이 프로젝트에서 수십 개 설정을 시험했습니다 — 그중 "우승자"는 통계적으로
              부풀려져 있습니다.
              <strong> 디플레이티드 샤프(DSR)</strong>는 시험 횟수를 보정한 뒤에도 우위가 진짜인지,{" "}
              <strong> 과최적화 확률(PBO)</strong>은 학습 최고 설정이 미래에도 통하는지를
              정량화합니다 (Bailey & López de Prado).
            </p>
          </div>
          <button className="primary" type="button" onClick={onRun} disabled={loading}>
            <RefreshCw size={15} /> {loading ? "계산 중..." : "실행"}
          </button>
        </div>
      </article>
      {loading && !report ? (
        <article className="panel span-12">
          <p className="muted">40개 설정을 백테스트하고 CSCV 70개 분할을 계산 중입니다...</p>
        </article>
      ) : null}
      {report ? <OverfittingResult report={report} /> : null}
    </div>
  );
}

function OverfittingResult({ report }: { report: OverfittingReport }) {
  const dsrGood = report.deflated_sharpe_ratio >= 0.95;
  const pboGood = report.pbo <= 0.4;
  return (
    <>
      <article className="panel span-12 mc-headline">
        <span className="section-label">
          과최적화 검증 결과 ({report.n_trials}개 설정 · {report.sample_days}일)
        </span>
        <h2>{report.headline}</h2>
      </article>

      <article className="panel span-6">
        <h2 className="panel-title">디플레이티드 샤프 (전략이 진짜인가)</h2>
        <div className="mc-prob-grid">
          <div className={dsrGood ? "mc-prob ok" : "mc-prob watch"}>
            <strong>{(report.deflated_sharpe_ratio * 100).toFixed(1)}%</strong>
            <span>DSR — 다중검정 보정 후 유의확률</span>
          </div>
          <div className="mc-prob ok">
            <strong>{report.observed_sharpe}</strong>
            <span>관측 샤프 (연율)</span>
          </div>
          <div className="mc-prob watch">
            <strong>{report.deflated_benchmark_sharpe}</strong>
            <span>우연 기대 최고 샤프 (40회 중)</span>
          </div>
          <div className="mc-prob watch">
            <strong>{report.dsr_verdict}</strong>
            <span>
              왜도 {report.skew} · 첨도 {report.kurtosis}
            </span>
          </div>
        </div>
      </article>

      <article className="panel span-6">
        <h2 className="panel-title">과최적화 확률 PBO (미세조정이 통하나)</h2>
        <div className="mc-prob-grid">
          <div className={pboGood ? "mc-prob ok" : "mc-prob danger"}>
            <strong>{(report.pbo * 100).toFixed(1)}%</strong>
            <span>PBO — 학습최고가 검증서 중앙값 아래일 확률</span>
          </div>
          <div className="mc-prob watch">
            <strong>{report.pbo_verdict}</strong>
            <span>CSCV {report.cscv_splits}개 분할</span>
          </div>
        </div>
        <p className="muted">
          PBO는 순위 지속성만 봅니다(수익 크기 아님). 높은 PBO + 높은 DSR은 "전략은 진짜지만 설정
          미세조정은 무의미"라는 뜻일 수 있습니다 — 아래 해석 참고.
        </p>
      </article>

      <article className="panel span-12 mc-notes">
        <h2 className="panel-title">해석</h2>
        <ul>
          {report.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      </article>
    </>
  );
}

export function HeatmapTab({
  report,
  loading,
  onRun
}: {
  report: HeatmapReport | null;
  loading: boolean;
  onRun: () => void;
}) {
  return (
    <div className="content-grid">
      <article className="panel span-12">
        <div className="report-head">
          <div>
            <h2 className="panel-title">
              <BarChart3 size={18} />
              파라미터 지형 (고원 vs 봉우리)
            </h2>
            <p>
              적립비율(50~90%)과 이탈밴드(−1~3%)를 격자로 훑어 종합점수 지형을 그립니다. 현재 설정
              주변이 <strong>평평한 고원</strong>이면 파라미터를 조금 바꿔도 성과가 비슷 = 강건.
              현재 점만 <strong>뾰족한 봉우리</strong>면 운 좋은 과최적화 신호입니다.
            </p>
          </div>
          <button className="primary" type="button" onClick={onRun} disabled={loading}>
            <RefreshCw size={15} /> {loading ? "계산 중..." : "실행"}
          </button>
        </div>
      </article>
      {loading && !report ? (
        <article className="panel span-12">
          <p className="muted">45개 조합을 전 구간 백테스트 중입니다...</p>
        </article>
      ) : null}
      {report ? <HeatmapResult report={report} /> : null}
    </div>
  );
}

function HeatmapResult({ report }: { report: HeatmapReport }) {
  const scores = report.cells.map((c) => c.score);
  const lo = Math.min(...scores);
  const hi = Math.max(...scores);
  const color = (score: number) => {
    const t = hi > lo ? (score - lo) / (hi - lo) : 0.5;
    const h = 8 + t * 130; // red(8) -> green(138)
    return `hsl(${h}, 62%, ${88 - t * 18}%)`;
  };
  const cellAt = (ratio: number, band: number) =>
    report.cells.find((c) => c.ratio === ratio && c.band === band);
  const isPlateau = report.verdict.startsWith("고원");
  return (
    <>
      <article className="panel span-12 mc-headline">
        <span className="section-label">파라미터 지형 결과</span>
        <h2>{report.headline}</h2>
      </article>

      <article className="panel span-6">
        <h2 className="panel-title">핵심 지표</h2>
        <div className="mc-prob-grid">
          <div className={isPlateau ? "mc-prob ok" : "mc-prob watch"}>
            <strong>{report.verdict}</strong>
            <span>이웃 점수 편차 {report.neighbor_score_spread}점 (작을수록 고원)</span>
          </div>
          <div className={report.plateau_ratio_pct >= 50 ? "mc-prob ok" : "mc-prob watch"}>
            <strong>{report.plateau_ratio_pct}%</strong>
            <span>최고점 부근 고원 비율</span>
          </div>
          <div className="mc-prob watch">
            <strong>
              {report.adopted_rank}/{report.total_cells}
            </strong>
            <span>현재 8:2·밴드2 순위 (점수 {report.adopted_score})</span>
          </div>
          <div className="mc-prob watch">
            <strong>{report.global_score_spread}점</strong>
            <span>전체 점수 폭 (작을수록 어디 골라도 비슷)</span>
          </div>
        </div>
      </article>

      <article className="panel span-6 mc-notes">
        <h2 className="panel-title">해석</h2>
        <ul>
          {report.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      </article>

      <article className="panel span-12">
        <h2 className="panel-title">종합점수 지형 (★현재 · ◆최고)</h2>
        <div className="heatmap-scroll">
          <table className="heatmap-table">
            <thead>
              <tr>
                <th>밴드＼비율</th>
                {report.ratios.map((r) => (
                  <th key={r}>
                    {r}:{100 - r}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {report.bands.map((band) => (
                <tr key={band}>
                  <th>
                    {band >= 0 ? "+" : ""}
                    {band}%
                  </th>
                  {report.ratios.map((ratio) => {
                    const c = cellAt(ratio, band);
                    if (!c) return <td key={ratio} />;
                    return (
                      <td
                        key={ratio}
                        style={{ background: color(c.score) }}
                        className={c.is_adopted ? "hm-adopted" : c.is_best ? "hm-best" : ""}
                        title={`${ratio}:${100 - ratio} 밴드${band}% · CAGR ${c.cagr}% · MDD ${c.mdd}%`}
                      >
                        {c.score}
                        {c.is_adopted ? "★" : c.is_best ? "◆" : ""}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted">
          칸에 마우스를 올리면 CAGR·MDD를 볼 수 있습니다. 색이 고를수록(전부 비슷한 초록) 지형이
          평평 = 강건합니다.
        </p>
      </article>
    </>
  );
}

export function WalkForwardTab({
  report,
  loading,
  onRun
}: {
  report: WalkForwardReport | null;
  loading: boolean;
  onRun: () => void;
}) {
  return (
    <div className="content-grid">
      <article className="panel span-12">
        <div className="report-head">
          <div>
            <h2 className="panel-title">
              <LineChart size={18} />
              워크포워드 분석 (시간축 과최적화 검증)
            </h2>
            <p>
              과거를 학습(IS) 8년 / 검증(OOS) 3년 창으로 굴리며, 각 학습 구간에서 12개 규칙 중
              최고를 고른 뒤<strong> 한 번도 안 본 다음 구간</strong>에서만 채점합니다. "지금 규칙이
              과거에 잘 맞은 우연인지, 시대가 바뀌어도 통하는지"를 시간축으로 검증하는 표준
              방법입니다.
            </p>
          </div>
          <button className="primary" type="button" onClick={onRun} disabled={loading}>
            <RefreshCw size={15} /> {loading ? "검증 중..." : "실행"}
          </button>
        </div>
      </article>
      {loading && !report ? (
        <article className="panel span-12">
          <p className="muted">6개 창 × 12개 규칙 = 84개 백테스트를 실행 중입니다...</p>
        </article>
      ) : null}
      {report ? <WalkForwardResult report={report} /> : null}
    </div>
  );
}

function WalkForwardResult({ report }: { report: WalkForwardReport }) {
  const adaptiveWins = report.adaptive_oos_cagr_median >= report.fixed_oos_cagr_median;
  return (
    <>
      <article className="panel span-12 mc-headline">
        <span className="section-label">워크포워드 결과</span>
        <h2>{report.headline}</h2>
      </article>

      <article className="panel span-6">
        <h2 className="panel-title">핵심 지표</h2>
        <div className="mc-prob-grid">
          <div className={report.adaptive_compound_oos_cagr >= 0 ? "mc-prob ok" : "mc-prob danger"}>
            <strong>{report.adaptive_compound_oos_cagr}%</strong>
            <span>적응형 OOS 복리 CAGR · 최악 구간 MDD {report.adaptive_worst_oos_mdd}%</span>
          </div>
          <div className={report.fixed_compound_oos_cagr >= 0 ? "mc-prob ok" : "mc-prob danger"}>
            <strong>{report.fixed_compound_oos_cagr}%</strong>
            <span>고정 규칙 OOS 복리 CAGR · 최악 구간 MDD {report.fixed_worst_oos_mdd}%</span>
          </div>
          <div
            className={
              report.walk_forward_efficiency_pct >= 60
                ? "mc-prob ok"
                : report.walk_forward_efficiency_pct >= 35
                  ? "mc-prob watch"
                  : "mc-prob danger"
            }
          >
            <strong>{report.walk_forward_efficiency_pct}%</strong>
            <span>워크포워드 효율 (OOS÷IS, 높을수록 강건)</span>
          </div>
          <div className={report.oos_beat_benchmark_pct >= 50 ? "mc-prob ok" : "mc-prob watch"}>
            <strong>{report.oos_beat_benchmark_pct}%</strong>
            <span>OOS 창에서 QQQ 장기보유 이김</span>
          </div>
          <div className="mc-prob watch">
            <strong>{report.selection_stability_pct}%</strong>
            <span>같은 규칙이 뽑힌 비율 ({report.modal_config})</span>
          </div>
          <div className={adaptiveWins ? "mc-prob watch" : "mc-prob ok"}>
            <strong>{adaptiveWins ? "적응형" : "고정 우세"}</strong>
            <span>
              적응형 {report.adaptive_oos_cagr_median}% vs 고정(현재) {report.fixed_oos_cagr_median}
              %
            </span>
          </div>
        </div>
      </article>

      <article className="panel span-6 mc-notes">
        <h2 className="panel-title">해석</h2>
        <ul>
          {report.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      </article>

      <article className="panel span-12">
        <h2 className="panel-title">창별 결과 (고정 규칙 = {report.fixed_label})</h2>
        <div className="robustness-table">
          <div className="robustness-row wf-row head">
            <span>OOS 구간</span>
            <span>IS 선택 규칙</span>
            <span>OOS CAGR</span>
            <span>벤치마크</span>
            <span>고정(현재)</span>
            <span>승</span>
          </div>
          {report.windows.map((w) => (
            <div className="robustness-row wf-row" key={w.index}>
              <span>
                {w.oos_start.slice(0, 7)}~{w.oos_end.slice(0, 7)}
              </span>
              <span>{w.selected_label}</span>
              <span>
                {w.oos_cagr >= 0 ? "+" : ""}
                {w.oos_cagr}%
              </span>
              <span>{w.benchmark_oos_cagr}%</span>
              <span>
                {w.fixed_oos_cagr >= 0 ? "+" : ""}
                {w.fixed_oos_cagr}%
              </span>
              <span>{w.oos_beat_benchmark ? "✓" : "—"}</span>
            </div>
          ))}
        </div>
      </article>
    </>
  );
}

export function MonteCarloTab({
  report,
  loading,
  paths,
  setPaths,
  config,
  onRun
}: {
  report: MonteCarloReport | null;
  loading: boolean;
  paths: number;
  setPaths: (n: number) => void;
  config: CompareConfig;
  onRun: () => void;
}) {
  return (
    <div className="content-grid">
      <article className="panel span-12">
        <div className="report-head">
          <div>
            <h2 className="panel-title">
              <FlaskConical size={18} />
              레짐 스위칭 미래 시뮬레이션
            </h2>
            <p>
              1999년 이후 QQQ의 상승·하락·횡보 국면 통계를 학습해{" "}
              <strong>완전히 새로운 26년 차트</strong>를 수백 개 생성하고, 현재 설정한 전략(TQQQ{" "}
              {config.daily_base_tqqq_ratio}:{config.daily_base_one_x_ratio} · 밴드{" "}
              {config.ma_exit_band_pct}% ·
              {config.defense_mode === "spym_sgov_half" ? " SPYM+SGOV 반반" : " 현금"} 방어)을 그
              미래들에 돌려 결과 분포를 봅니다. 과거를 그대로 재사용하는 부트스트랩과 달리, 실제로
              일어난 적 없는 미래를 생성합니다.
            </p>
          </div>
          <div className="mc-run-controls">
            <label>
              경로 수
              <select value={paths} onChange={(e) => setPaths(Number(e.target.value))}>
                <option value={150}>150 (빠름 ~25초)</option>
                <option value={300}>300 (권장 ~50초)</option>
                <option value={600}>600 (정밀 ~100초)</option>
              </select>
            </label>
            <button className="primary" type="button" onClick={onRun} disabled={loading}>
              <RefreshCw size={15} /> {loading ? "생성 중..." : "실행"}
            </button>
          </div>
        </div>
      </article>

      {loading && !report ? (
        <article className="panel span-12">
          <p className="muted">수백 개의 미래를 생성·검증하는 중입니다. 잠시만 기다려 주세요...</p>
        </article>
      ) : null}

      {report ? <MonteCarloResult report={report} /> : null}
    </div>
  );
}

function MonteCarloResult({ report }: { report: MonteCarloReport }) {
  return (
    <>
      <article className="panel span-12 mc-headline">
        <span className="section-label">
          {report.n_paths}개 미래 · {report.years}년 · 시드 {report.seed}
        </span>
        <h2>{report.headline}</h2>
      </article>

      <article className="panel span-6">
        <h2 className="panel-title">이 전략이 규칙대로 굴러가면</h2>
        <div className="mc-prob-grid">
          <div className={report.prob_beat_benchmark >= 50 ? "mc-prob ok" : "mc-prob watch"}>
            <strong>{report.prob_beat_benchmark}%</strong>
            <span>미래에서 QQQ 장기보유를 이김</span>
          </div>
          <div className={report.prob_cagr_positive >= 80 ? "mc-prob ok" : "mc-prob watch"}>
            <strong>{report.prob_cagr_positive}%</strong>
            <span>26년 후 플러스 수익</span>
          </div>
          <div className="mc-prob watch">
            <strong>{report.prob_mdd_worse_than_60}%</strong>
            <span>최대낙폭 −60%보다 깊음</span>
          </div>
          <div className="mc-prob danger">
            <strong>{report.prob_mdd_worse_than_70}%</strong>
            <span>최대낙폭 −70%보다 깊음</span>
          </div>
        </div>
      </article>

      <article className="panel span-6">
        <h2 className="panel-title">결과 분포 (하위5% · 중간값 · 상위5%)</h2>
        <DistBar label="CAGR" unit="%" p={report.cagr} benchMedian={report.benchmark_cagr.median} />
        <DistBar label="최대낙폭" unit="%" p={report.max_drawdown} negative />
        <DistBar label="최종자산 배수" unit="x" p={report.final_multiple} />
        <p className="muted">
          QQQ 장기보유 CAGR 중간값 {report.benchmark_cagr.median}%와 비교하세요.
        </p>
      </article>

      <article className="panel span-12">
        <h2 className="panel-title">생성된 미래 국면 통계</h2>
        <div className="robustness-table">
          <div className="robustness-row head">
            <span>국면</span>
            <span>기간 비중</span>
            <span>연 수익률</span>
            <span>연 변동성</span>
          </div>
          {report.regime_summary.map((r) => (
            <div className="robustness-row" key={r.regime}>
              <span>{r.label}</span>
              <span>{r.day_share_pct}%</span>
              <span>{r.ann_return_pct}%</span>
              <span>{r.ann_vol_pct}%</span>
            </div>
          ))}
        </div>
      </article>

      <article className="panel span-12">
        <h2 className="panel-title">대표 미래 경로 (자산곡선)</h2>
        <FanChart samples={report.sample_paths} />
        <p className="muted">
          불운한 미래(하위 5%) · 중간 미래 · 행운의 미래(상위 5%)의 자산 성장 경로입니다.
        </p>
      </article>

      <article className="panel span-12 mc-notes">
        <h2 className="panel-title">해석 시 주의</h2>
        <ul>
          {report.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      </article>
    </>
  );
}

function DistBar({
  label,
  unit,
  p,
  benchMedian,
  negative
}: {
  label: string;
  unit: string;
  p: Percentiles;
  benchMedian?: number;
  negative?: boolean;
}) {
  const lo = Math.min(p.p5, negative ? p.p5 : 0, benchMedian ?? p.p5);
  const hi = Math.max(p.p95, benchMedian ?? p.p95);
  const range = hi - lo || 1;
  const pos = (v: number) => `${((v - lo) / range) * 100}%`;
  return (
    <div className="mc-dist">
      <div className="mc-dist-head">
        <strong>{label}</strong>
        <span>
          중간값 {p.median}
          {unit}
        </span>
      </div>
      <div className="mc-dist-track">
        <div
          className="mc-dist-span"
          style={{ left: pos(p.p5), width: `calc(${pos(p.p95)} - ${pos(p.p5)})` }}
        />
        <div className="mc-dist-mid" style={{ left: pos(p.median) }} />
        {benchMedian !== undefined ? (
          <div
            className="mc-dist-bench"
            style={{ left: pos(benchMedian) }}
            title={`QQQ ${benchMedian}${unit}`}
          />
        ) : null}
      </div>
      <div className="mc-dist-scale">
        <span>
          {p.p5}
          {unit}
        </span>
        <span>
          {p.p95}
          {unit}
        </span>
      </div>
    </div>
  );
}

function FanChart({ samples }: { samples: { kind: string; points: number[] }[] }) {
  if (!samples.length) return null;
  const width = 1000;
  const height = 240;
  const all = samples.flatMap((s) => s.points);
  const max = Math.max(...all);
  const min = Math.min(...all);
  const range = max - min || 1;
  const colors: Record<string, string> = { p5: "#d04444", median: "#2563eb", p95: "#0f8a63" };
  const labels: Record<string, string> = {
    p5: "하위 5% (불운)",
    median: "중간",
    p95: "상위 5% (행운)"
  };
  function pathFor(points: number[]) {
    return points
      .map((v, i) => {
        const x = (i / (points.length - 1)) * width;
        const y = height - ((v - min) / range) * height;
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }
  return (
    <div className="comparison-chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="미래 자산곡선 분포">
        {samples.map((s) => (
          <path
            d={pathFor(s.points)}
            key={s.kind}
            style={{
              stroke: colors[s.kind] ?? "#888",
              strokeWidth: s.kind === "median" ? 3 : 2,
              fill: "none"
            }}
          />
        ))}
      </svg>
      <div className="chart-legend">
        {samples.map((s) => (
          <span key={s.kind}>
            <em style={{ background: colors[s.kind] }} />
            {labels[s.kind] ?? s.kind}
          </span>
        ))}
      </div>
    </div>
  );
}
