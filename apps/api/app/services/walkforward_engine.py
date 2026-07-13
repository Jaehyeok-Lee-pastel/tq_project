"""Walk-forward analysis: does the IS-best rule hold up out-of-sample?

The gold-standard answer to "is this in-sample luck?". On each rolling
in-sample (IS) window we pick the best config from a grid; we then score it
ONLY on the immediately following out-of-sample (OOS) window it never saw.
Stitching the OOS results gives a genuine forward track record, and comparing
it to the fixed adopted config tells us whether chasing the IS-best is even
worth it.
"""

import asyncio
from datetime import date, timedelta

from app.schemas.backtest import BacktestRunRequest
from app.schemas.walkforward import (
    WalkForwardReport,
    WalkForwardRequest,
    WalkForwardWindow,
)
from app.services.backtest_engine import load_dataset, run_backtest
from app.services.compare_engine import score_backtest

# The live tuning knobs, as a grid. Defense is included because it is a real
# open choice; upfront 1x is fixed (already validated as free).
CANDIDATE_GRID = [
    {"ratio": ratio, "band": band, "defense": defense}
    for ratio in (60, 70, 80)
    for band in (0, 2)
    for defense in ("cash", "spym_sgov_half")
]
FIXED_CONFIG = {"ratio": 80, "band": 2, "defense": "cash"}  # the adopted strategy


def _label(cfg: dict) -> str:
    defense = "현금" if cfg["defense"] == "cash" else "반반"
    return f"{cfg['ratio']}:{100 - cfg['ratio']} 밴드{cfg['band']} {defense}"


def _request(cfg: dict, start: date, end: date, req: WalkForwardRequest) -> BacktestRunRequest:
    return BacktestRunRequest(
        strategy="tqqq_daily_200ma",
        initial_capital=req.initial_capital,
        monthly_contribution=req.monthly_contribution,
        cash_yield=req.cash_yield,
        daily_base_tqqq_ratio=cfg["ratio"],
        daily_base_one_x_ratio=100 - cfg["ratio"],
        one_x_symbol="QQQM",
        ma_exit_band_pct=cfg["band"],
        defense_mode=cfg["defense"],
        one_x_upfront_monthly=True,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
    )


def _window_defs(first: date, last: date, req: WalkForwardRequest) -> list[tuple[date, date, date, date]]:
    defs: list[tuple[date, date, date, date]] = []
    index = 0
    while True:
        is_start = first + timedelta(days=int(365.25 * req.step_years * index))
        is_end = is_start + timedelta(days=int(365.25 * req.is_years))
        oos_start = is_end
        oos_end = oos_start + timedelta(days=int(365.25 * req.oos_years))
        if oos_end > last:
            break
        defs.append((is_start, is_end, oos_start, oos_end))
        index += 1
    return defs


async def run_walkforward(req: WalkForwardRequest, provider: str) -> WalkForwardReport:
    dataset = await load_dataset(provider, 200)
    frames = dataset.frames
    if not frames:
        raise ValueError("워크포워드 분석에 필요한 데이터가 없습니다.")
    first = date.fromisoformat(frames[0].date)
    last = date.fromisoformat(frames[-1].date)
    defs = _window_defs(first, last, req)
    if len(defs) < 2:
        raise ValueError("창 길이에 비해 데이터 기간이 짧습니다. IS/OOS 연수를 줄이세요.")

    windows: list[WalkForwardWindow] = []
    for idx, (is_s, is_e, oos_s, oos_e) in enumerate(defs):
        is_results = await asyncio.gather(
            *[run_backtest(_request(cfg, is_s, is_e, req)) for cfg in CANDIDATE_GRID]
        )
        scored = [
            (score_backtest(result, req.risk_score), cfg, result)
            for result, cfg in zip(is_results, CANDIDATE_GRID, strict=False)
        ]
        best_item, best_cfg, best_is = max(scored, key=lambda x: x[0].total_score)

        sel_oos = await run_backtest(_request(best_cfg, oos_s, oos_e, req))
        fix_oos = await run_backtest(_request(FIXED_CONFIG, oos_s, oos_e, req))

        windows.append(
            WalkForwardWindow(
                index=idx + 1,
                is_start=is_s.isoformat(),
                is_end=is_e.isoformat(),
                oos_start=oos_s.isoformat(),
                oos_end=oos_e.isoformat(),
                selected_label=_label(best_cfg),
                is_cagr=best_is.metrics.cagr,
                is_score=best_item.total_score,
                oos_cagr=sel_oos.metrics.cagr,
                oos_mdd=sel_oos.metrics.max_drawdown,
                oos_beat_benchmark=sel_oos.metrics.cagr > sel_oos.benchmark_metrics.cagr,
                benchmark_oos_cagr=sel_oos.benchmark_metrics.cagr,
                fixed_oos_cagr=fix_oos.metrics.cagr,
                fixed_oos_mdd=fix_oos.metrics.max_drawdown,
            )
        )

    return _aggregate(windows)


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[mid], 2)
    return round((ordered[mid - 1] + ordered[mid]) / 2, 2)


def _compound_window_metrics(
    windows: list[WalkForwardWindow], cagr_attr: str, mdd_attr: str
) -> tuple[float, float]:
    if not windows:
        return 0.0, 0.0
    growth = 1.0
    total_years = 0.0
    for window in windows:
        start = date.fromisoformat(window.oos_start)
        end = date.fromisoformat(window.oos_end)
        years = max((end - start).days / 365.25, 1 / 365.25)
        growth *= (1 + getattr(window, cagr_attr) / 100) ** years
        total_years += years
    compound_cagr = growth ** (1 / total_years) - 1 if growth > 0 else -1.0
    worst_mdd = min(getattr(window, mdd_attr) for window in windows)
    return round(compound_cagr * 100, 2), round(worst_mdd, 2)


def _aggregate(windows: list[WalkForwardWindow]) -> WalkForwardReport:
    n = len(windows)
    efficiencies = [
        w.oos_cagr / w.is_cagr for w in windows if w.is_cagr > 0.5
    ]
    wfe = round(sum(efficiencies) / len(efficiencies) * 100, 1) if efficiencies else 0.0

    counts: dict[str, int] = {}
    for w in windows:
        counts[w.selected_label] = counts.get(w.selected_label, 0) + 1
    modal_config, modal_count = max(counts.items(), key=lambda x: x[1])
    stability = round(modal_count / n * 100, 1)

    beat_rate = round(sum(1 for w in windows if w.oos_beat_benchmark) / n * 100, 1)
    adaptive_median = _median([w.oos_cagr for w in windows])
    fixed_median = _median([w.fixed_oos_cagr for w in windows])
    adaptive_compound_cagr, adaptive_worst_mdd = _compound_window_metrics(
        windows, "oos_cagr", "oos_mdd"
    )
    fixed_compound_cagr, fixed_worst_mdd = _compound_window_metrics(
        windows, "fixed_oos_cagr", "fixed_oos_mdd"
    )

    verdict = "강건" if wfe >= 60 else "보통" if wfe >= 35 else "과최적화 의심"
    headline = (
        f"워크포워드 효율 {wfe}% ({verdict}) · OOS 벤치마크 승률 {beat_rate}% · "
        f"적응형 OOS CAGR 중간값 {adaptive_median}% vs 고정(현재) {fixed_median}%"
    )
    notes = [
        f"학습(IS) 창에서 12개 규칙 중 최고를 고르고, 곧바로 다음 검증(OOS) 창에서만 채점했습니다. 총 {n}개 OOS 창.",
        "워크포워드 효율(WFE)은 OOS 성과 ÷ IS 성과입니다. 100%에 가까울수록 IS 우위가 OOS로 이어졌다는 뜻이고, "
        "낮을수록 IS 성과가 과최적화(미래엔 안 통함)였다는 신호입니다.",
        "적응형(매번 IS 최고 선택)이 고정(현재 8:2 규칙)과 비슷하거나 못하면, 규칙을 시대마다 바꿀 필요 없이 "
        "현재 규칙이 강건하다는 뜻입니다.",
        "각 OOS 창은 초기 보유 없이 순수 적립으로 규칙만 검증했습니다(포트폴리오 시작 상태 효과 제거).",
    ]
    return WalkForwardReport(
        windows=windows,
        fixed_label=_label(FIXED_CONFIG),
        walk_forward_efficiency_pct=wfe,
        selection_stability_pct=stability,
        modal_config=modal_config,
        oos_beat_benchmark_pct=beat_rate,
        adaptive_oos_cagr_median=adaptive_median,
        fixed_oos_cagr_median=fixed_median,
        adaptive_compound_oos_cagr=adaptive_compound_cagr,
        adaptive_worst_oos_mdd=adaptive_worst_mdd,
        fixed_compound_oos_cagr=fixed_compound_cagr,
        fixed_worst_oos_mdd=fixed_worst_mdd,
        headline=headline,
        notes=notes,
    )
