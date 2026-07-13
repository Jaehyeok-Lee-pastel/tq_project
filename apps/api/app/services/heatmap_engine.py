"""Parameter sensitivity heatmap: is the adopted config a plateau or a peak?

Sweeps the two live knobs (accumulation ratio x exit band) over a grid and
reports the score surface. A broad plateau of similar scores around the
adopted point means the choice is robust to small parameter changes; a sharp
solitary peak means it is curve-fit and would likely not survive live.
"""

import asyncio

from app.schemas.backtest import BacktestRunRequest
from app.schemas.heatmap import HeatmapCell, HeatmapReport, HeatmapRequest
from app.services.backtest_engine import run_backtest
from app.services.compare_engine import score_backtest

RATIOS = [50, 55, 60, 65, 70, 75, 80, 85, 90]
BANDS = [-1.0, 0.0, 1.0, 2.0, 3.0]
ADOPTED_RATIO = 80
ADOPTED_BAND = 2.0
PLATEAU_SCORE_TOLERANCE = 5


def _request(ratio: int, band: float, req: HeatmapRequest) -> BacktestRunRequest:
    return BacktestRunRequest(
        strategy="tqqq_daily_200ma",
        initial_capital=req.initial_capital,
        initial_tqqq_value=req.initial_tqqq_value,
        initial_one_x_value=req.initial_one_x_value,
        initial_cash_value=req.initial_cash_value,
        monthly_contribution=req.monthly_contribution,
        cash_yield=req.cash_yield,
        daily_base_tqqq_ratio=ratio,
        daily_base_one_x_ratio=100 - ratio,
        one_x_symbol="QQQM",
        ma_exit_band_pct=band,
        defense_mode=req.defense_mode,
        one_x_upfront_monthly=True,
    )


async def run_heatmap(req: HeatmapRequest, provider: str) -> HeatmapReport:
    tasks = [
        (ratio, band, run_backtest(_request(ratio, band, req)))
        for ratio in RATIOS
        for band in BANDS
    ]
    results = await asyncio.gather(*[t[2] for t in tasks])

    cells: list[HeatmapCell] = []
    score_by_key: dict[tuple[int, float], int] = {}
    for (ratio, band, _), result in zip(tasks, results, strict=False):
        score = score_backtest(result, req.risk_score).total_score
        score_by_key[(ratio, band)] = score
        cells.append(
            HeatmapCell(
                ratio=ratio,
                band=band,
                cagr=result.metrics.cagr,
                mdd=result.metrics.max_drawdown,
                score=score,
                is_adopted=(ratio == ADOPTED_RATIO and band == ADOPTED_BAND),
                is_best=False,
            )
        )

    best_cell = max(cells, key=lambda c: c.score)
    for cell in cells:
        if cell.ratio == best_cell.ratio and cell.band == best_cell.band:
            cell.is_best = True

    adopted_score = score_by_key.get((ADOPTED_RATIO, ADOPTED_BAND), 0)
    ranked = sorted(cells, key=lambda c: c.score, reverse=True)
    adopted_rank = next(
        (i + 1 for i, c in enumerate(ranked) if c.ratio == ADOPTED_RATIO and c.band == ADOPTED_BAND),
        len(cells),
    )

    neighbor_scores = _neighbor_scores(score_by_key, ADOPTED_RATIO, ADOPTED_BAND)
    neighbor_spread = max(neighbor_scores) - min(neighbor_scores)
    global_spread = best_cell.score - min(c.score for c in cells)
    plateau_pct = round(
        sum(1 for c in cells if c.score >= best_cell.score - PLATEAU_SCORE_TOLERANCE) / len(cells) * 100,
        1,
    )

    verdict = "고원(강건)" if neighbor_spread <= 6 else "완만" if neighbor_spread <= 12 else "봉우리(민감)"
    headline = (
        f"현재 8:2·밴드2는 {len(cells)}개 중 {adopted_rank}위 (점수 {adopted_score}), "
        f"이웃과의 점수 편차 {neighbor_spread}점 → {verdict}. "
        f"최고점 부근 고원 비율 {plateau_pct}%."
    )
    notes = [
        f"적립비율({RATIOS[0]}~{RATIOS[-1]}%) × 이탈밴드({BANDS[0]:.0f}~{BANDS[-1]:.0f}%) 격자를 전 구간 백테스트했습니다.",
        "이웃 점수 편차가 작을수록(고원) 파라미터를 조금 바꿔도 성과가 비슷 = 강건. "
        "현재 점만 뾰족하게 높으면(봉우리) 과최적화 신호입니다.",
        "현재 점이 최고점이 아니어도 괜찮습니다 — 넓은 고원 위에 있으면 그 자체로 강건합니다.",
        "점수는 수익·방어·실행·적합을 합친 종합점수(리스크 80 기준)입니다.",
    ]
    return HeatmapReport(
        ratios=RATIOS,
        bands=BANDS,
        cells=cells,
        adopted_ratio=ADOPTED_RATIO,
        adopted_band=ADOPTED_BAND,
        adopted_score=adopted_score,
        adopted_rank=adopted_rank,
        total_cells=len(cells),
        best_score=best_cell.score,
        best_label=f"{best_cell.ratio}:{100 - best_cell.ratio} 밴드{best_cell.band:.0f}",
        neighbor_score_spread=neighbor_spread,
        global_score_spread=global_spread,
        plateau_ratio_pct=plateau_pct,
        verdict=verdict,
        headline=headline,
        notes=notes,
    )


def _neighbor_scores(scores: dict[tuple[int, float], int], ratio: int, band: float) -> list[int]:
    out: list[int] = []
    for dr in (-5, 0, 5):
        for db in (-1.0, 0.0, 1.0):
            key = (ratio + dr, band + db)
            if key in scores:
                out.append(scores[key])
    return out or [scores.get((ratio, band), 0)]
