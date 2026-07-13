"""Regime-switching Monte Carlo: test the strategy across many novel futures.

Unlike block bootstrap (which re-stitches real historical windows), this
GENERATES new daily returns from a calibrated regime-switching model, so the
paths never literally happened — new crash timings, new bull durations — while
preserving the market's statistical character (trend persistence via regime
memory, fat tails via Student-t, vol clustering via a high-vol bear regime).

Honest scope (shown to the user): every path is still consistent with the
STATISTICAL physics of 1999~ QQQ. It cannot invent a regime whose signature
never appeared (e.g. Treasuries ceasing to be safe). That novelty class is
deliberately out of scope — untestable and excluded by design.
"""

import math
import random
from dataclasses import dataclass

from app.schemas.montecarlo import (
    MonteCarloReport,
    MonteCarloRequest,
    Percentiles,
    RegimeSummaryItem,
    SamplePath,
)
from app.services.backtest_engine import (
    TRADING_DAYS_PER_YEAR,
    BacktestFrame,
    simulate_daily_accumulation_200ma_strategy,
    simulate_staged_200ma_strategy,
)
from app.services.market_data import PriceRow

BULL, BEAR, SIDE = "bull", "bear", "sideways"
REGIME_LABELS = {BULL: "상승장", BEAR: "하락·급락장", SIDE: "횡보장"}
TREND_LOOKBACK = 60
BULL_TREND = 0.03  # +3% trailing 60d and above MA200 => bull
STUDENT_T_DF = 5.0  # fat tails; lower = fatter
SYNTH_FINANCING_PCT = 2.0  # representative short rate for synthetic leverage


@dataclass(frozen=True)
class RegimeStats:
    regime: str
    mean: float
    scale: float  # Student-t scale so that Var = scale^2 * df/(df-2)
    day_share: float
    ann_return_pct: float
    ann_vol_pct: float


@dataclass(frozen=True)
class RegimeModel:
    regimes: dict[str, RegimeStats]
    df: float


def _label_regime(close: float, ma200: float, trend60: float) -> str:
    if close <= ma200:
        return BEAR
    if trend60 >= BULL_TREND:
        return BULL
    return SIDE


def calibrate_regime_model(qqq_rows: list[PriceRow], df: float = STUDENT_T_DF) -> RegimeModel:
    closes = [row.close for row in qqq_rows]
    if len(closes) < 260:
        raise ValueError("레짐 보정에는 최소 260거래일 이상의 QQQ 데이터가 필요합니다.")

    returns_by_regime: dict[str, list[float]] = {BULL: [], BEAR: [], SIDE: []}
    for index in range(200, len(closes) - 1):
        ma200 = sum(closes[index - 199 : index + 1]) / 200
        trend60 = closes[index] / closes[index - TREND_LOOKBACK] - 1
        label = _label_regime(closes[index], ma200, trend60)
        # Return realized on the NEXT day belongs to today's regime (causal).
        next_return = math.log(closes[index + 1] / closes[index])
        returns_by_regime[label].append(next_return)

    stats: dict[str, RegimeStats] = {}
    total_days = sum(len(v) for v in returns_by_regime.values())
    for regime, rets in returns_by_regime.items():
        if len(rets) < 2:
            # Degenerate market with no such regime: use a tiny neutral bucket.
            stats[regime] = RegimeStats(regime, 0.0, 0.0001, 0.0, 0.0, 0.0)
            continue
        mean = sum(rets) / len(rets)
        variance = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        std = math.sqrt(variance)
        scale = std * math.sqrt((df - 2) / df) if df > 2 else std
        stats[regime] = RegimeStats(
            regime=regime,
            mean=mean,
            scale=scale,
            day_share=round(len(rets) / total_days * 100, 1),
            ann_return_pct=round((math.exp(mean * TRADING_DAYS_PER_YEAR) - 1) * 100, 1),
            ann_vol_pct=round(std * math.sqrt(TRADING_DAYS_PER_YEAR) * 100, 1),
        )

    return RegimeModel(regimes=stats, df=df)


def _student_t(rng: random.Random, df: float) -> float:
    z = rng.gauss(0.0, 1.0)
    chi2 = rng.gammavariate(df / 2.0, 2.0)
    return z / math.sqrt(chi2 / df)


def generate_path_frames(
    model: RegimeModel,
    n_days: int,
    rng: random.Random,
    ma_days: int,
) -> list[BacktestFrame]:
    """Generate one novel path as ready-to-simulate frames, in a single O(n) pass.

    Endogenous regime: each day's regime is determined by the SIMULATED price's
    own state (below MA200 -> bear, above + uptrend -> bull, else sideways), so
    the dynamics driving returns stay consistent with the MA200 signal the
    strategy trades on. This removes the decoupling that made an independent
    Markov chain over-generate volatility decay on 3x leverage.

    Financing/expense for synthetic TQQQ(3x)/QLD(2x) use a single representative
    rate. QQQM == QQQ; SPY uses QQQ as a proxy (only matters for spym defense).
    """
    financing = (SYNTH_FINANCING_PCT + 0.5) / 100
    expense = 0.0095
    cost3 = expense / TRADING_DAYS_PER_YEAR + 2 * financing / TRADING_DAYS_PER_YEAR
    cost2 = expense / TRADING_DAYS_PER_YEAR + 1 * financing / TRADING_DAYS_PER_YEAR

    total = ma_days + n_days
    qqq = [100.0]
    tqqq = [100.0]
    qld = [100.0]
    sum200 = 100.0
    sum20 = 100.0
    sum50 = 100.0

    frames: list[BacktestFrame] = []
    bull, bear, side = model.regimes[BULL], model.regimes[BEAR], model.regimes[SIDE]

    for i in range(1, total):
        # Endogenous regime from the path so far.
        if i > ma_days:
            ma200_prev = sum200 / ma_days
            trend60 = qqq[i - 1] / qqq[i - 1 - TREND_LOOKBACK] - 1
            if qqq[i - 1] <= ma200_prev:
                stats = bear
            elif trend60 >= BULL_TREND:
                stats = bull
            else:
                stats = side
        else:
            stats = bull  # burn-in: establish an uptrend baseline

        daily_log = stats.mean + stats.scale * _student_t(rng, model.df)
        daily_log = max(min(daily_log, 0.25), -0.25)
        base_ret = math.exp(daily_log) - 1
        qqq.append(qqq[-1] * (1 + base_ret))
        tqqq.append(tqqq[-1] * (1 + max(3 * base_ret - cost3, -0.99)))
        qld.append(qld[-1] * (1 + max(2 * base_ret - cost2, -0.99)))

        # Rolling sums (updated after appending the new close).
        sum200 += qqq[i] - (qqq[i - ma_days] if i >= ma_days else 0.0)
        sum20 += qqq[i] - (qqq[i - 20] if i >= 20 else 0.0)
        sum50 += qqq[i] - (qqq[i - 50] if i >= 50 else 0.0)

        if i < ma_days:
            continue
        year = 2000 + (i - ma_days) // 252
        month = ((i - ma_days) % 252) // 21 + 1
        day = ((i - ma_days) % 21) + 1
        frames.append(
            BacktestFrame(
                date=f"{year:04d}-{month:02d}-{day:02d}",
                qqq=qqq[i],
                tqqq=tqqq[i],
                qld=qld[i],
                spy=qqq[i],
                sma200=sum200 / ma_days,
                sma20=sum20 / 20 if i >= 20 else None,
                sma50=sum50 / 50 if i >= 50 else None,
                high20=None,
            )
        )
    return frames


def _percentiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    n = len(ordered)

    def pick(p: float) -> float:
        idx = min(n - 1, max(0, int(round(p * (n - 1)))))
        return round(ordered[idx], 2)

    return {
        "p5": pick(0.05),
        "p25": pick(0.25),
        "median": pick(0.50),
        "p75": pick(0.75),
        "p95": pick(0.95),
        "mean": round(sum(ordered) / n, 2),
    }


def _fast_cagr_mdd(curve: list) -> tuple[float, float]:
    """CAGR% and MDD% from an equity curve, TWR (cash-flow adjusted). O(n)."""
    index_value = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for i in range(1, len(curve)):
        prev = curve[i - 1].equity
        if prev <= 0:
            continue
        r = (curve[i].equity - curve[i].cash_flow) / prev - 1
        index_value *= 1 + r
        peak = max(peak, index_value)
        drawdown = index_value / peak - 1
        if drawdown < max_drawdown:
            max_drawdown = drawdown
    years = max(len(curve) / TRADING_DAYS_PER_YEAR, 1 / TRADING_DAYS_PER_YEAR)
    cagr = index_value ** (1 / years) - 1
    return cagr * 100, max_drawdown * 100


def _benchmark_cagr_mdd(frames: list[BacktestFrame]) -> tuple[float, float]:
    """QQQ buy-and-hold TWR CAGR%/MDD% straight from the QQQ series.

    For buy-and-hold the cash-flow-adjusted daily return equals the QQQ daily
    return exactly, so the benchmark needs no separate simulation.
    """
    index_value = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for i in range(1, len(frames)):
        r = frames[i].qqq / frames[i - 1].qqq - 1
        index_value *= 1 + r
        peak = max(peak, index_value)
        drawdown = index_value / peak - 1
        if drawdown < max_drawdown:
            max_drawdown = drawdown
    years = max(len(frames) / TRADING_DAYS_PER_YEAR, 1 / TRADING_DAYS_PER_YEAR)
    return (index_value ** (1 / years) - 1) * 100, max_drawdown * 100


def _run_strategy_on_frames(frames: list[BacktestFrame], req: MonteCarloRequest) -> float:
    """One path's strategy: returns (cagr, mdd, equity_curve)."""
    daily_cash_return = (1 + req.cash_yield / 100) ** (1 / TRADING_DAYS_PER_YEAR) - 1
    if req.strategy == "tqqq_daily_200ma":
        curve, trades = simulate_daily_accumulation_200ma_strategy(
            frames=frames,
            initial_capital=req.initial_capital,
            monthly_contribution=req.monthly_contribution,
            base_tqqq_ratio=req.daily_base_tqqq_ratio / 100,
            base_one_x_ratio=req.daily_base_one_x_ratio / 100,
            one_x_symbol=req.one_x_symbol,
            initial_tqqq_value=req.initial_tqqq_value,
            initial_one_x_value=req.initial_one_x_value,
            initial_cash_value=req.initial_cash_value,
            daily_cash_return=daily_cash_return,
            cost_ratio=0.001,
            moving_average_days=req.moving_average_days,
            exit_band=req.ma_exit_band_pct / 100,
            defense_mode=req.defense_mode,
            one_x_upfront_monthly=req.one_x_upfront_monthly,
        )
    else:
        target_ratio = req.tqqq_target_ratio if req.strategy == "tqqq_200ma" else req.qld_target_ratio
        curve, trades = simulate_staged_200ma_strategy(
            frames=frames,
            initial_capital=req.initial_capital,
            target_symbol="TQQQ" if req.strategy == "tqqq_200ma" else "QLD",
            target_ratio=target_ratio / 100,
            one_x_ratio=req.one_x_target_ratio / 100,
            one_x_symbol=req.one_x_symbol,
            daily_cash_return=daily_cash_return,
            cost_ratio=0.001,
            moving_average_days=req.moving_average_days,
            monthly_contribution=req.monthly_contribution,
            exit_band=req.ma_exit_band_pct / 100,
            defense_mode=req.defense_mode,
        )
    cagr, mdd = _fast_cagr_mdd(curve)
    return cagr, mdd, curve


def run_montecarlo(req: MonteCarloRequest, qqq_rows: list[PriceRow]) -> MonteCarloReport:
    model = calibrate_regime_model(qqq_rows)
    rng = random.Random(req.seed)
    n_days = req.years * TRADING_DAYS_PER_YEAR

    cagrs: list[float] = []
    mdds: list[float] = []
    finals: list[float] = []
    bench_cagrs: list[float] = []
    beat_count = 0
    equity_curves: list[list[float]] = []

    total_invested = req.initial_capital + req.monthly_contribution * 12 * req.years

    for _ in range(req.n_paths):
        frames = generate_path_frames(model, n_days, rng, req.moving_average_days)
        if len(frames) < 220:
            continue
        cagr, mdd, curve = _run_strategy_on_frames(frames, req)
        bench_cagr, _ = _benchmark_cagr_mdd(frames)
        cagrs.append(cagr)
        mdds.append(mdd)
        finals.append(round(curve[-1].equity / max(total_invested, 1), 3))
        bench_cagrs.append(bench_cagr)
        if cagr > bench_cagr:
            beat_count += 1
        # Store a downsampled curve (~120 pts) for the fan chart, not all 6800.
        step = max(len(curve) // 120, 1)
        equity_curves.append([round(curve[i].equity, 0) for i in range(0, len(curve), step)])

    runs = len(cagrs)
    if runs == 0:
        raise ValueError("몬테카를로 경로 생성에 실패했습니다. 파라미터를 확인하세요.")

    sample_paths = _pick_sample_paths(equity_curves, cagrs)
    cagr_pct = _percentiles(cagrs)
    mdd_pct = _percentiles(mdds)

    notes = [
        f"각 경로는 1999년 이후 QQQ에서 추정한 3개 국면(상승·하락·횡보)의 통계적 성질을 "
        f"유지한 채 새로 생성한 {req.years}년입니다 — 과거를 그대로 재사용하지 않습니다.",
        "다만 과거에 나타난 적 없는 완전히 새로운 시장 구조(예: 국채가 안전자산이 아닌 세계)는 "
        "원리상 생성할 수 없으며, 이는 의도적으로 범위에서 제외했습니다.",
        "⚠ 최대낙폭은 보수적(비관적)으로 읽으세요: 이 모델은 국면 내부의 '추세 지속성'까지는 "
        "재현하지 못해 200일선 부근 휩쏘를 실제보다 많이 만들고, 3배 레버리지에서 낙폭을 과대평가하는 "
        "경향이 있습니다. 절대 낙폭보다 '벤치마크 대비 승률·양수 확률' 같은 상대 지표가 더 견고합니다.",
        "레버리지(TQQQ)는 합성 3배−비용, QQQM은 QQQ와 동일 수익률로 계산했습니다.",
        f"총 {runs}개 미래 경로 · {req.years}년 · 시드 {req.seed}(재현 가능).",
    ]
    headline = _build_headline(cagr_pct, mdd_pct, beat_count / runs * 100)

    return MonteCarloReport(
        n_paths=runs,
        years=req.years,
        seed=req.seed,
        strategy=req.strategy,
        regime_summary=[
            RegimeSummaryItem(
                regime=stats.regime,
                label=REGIME_LABELS[stats.regime],
                day_share_pct=stats.day_share,
                ann_return_pct=stats.ann_return_pct,
                ann_vol_pct=stats.ann_vol_pct,
            )
            for stats in model.regimes.values()
        ],
        cagr=Percentiles(**cagr_pct),
        max_drawdown=Percentiles(**mdd_pct),
        final_multiple=Percentiles(**_percentiles(finals)),
        benchmark_cagr=Percentiles(**_percentiles(bench_cagrs)),
        prob_cagr_positive=round(sum(1 for c in cagrs if c > 0) / runs * 100, 1),
        prob_beat_benchmark=round(beat_count / runs * 100, 1),
        prob_mdd_worse_than_60=round(sum(1 for m in mdds if m <= -60) / runs * 100, 1),
        prob_mdd_worse_than_70=round(sum(1 for m in mdds if m <= -70) / runs * 100, 1),
        sample_paths=sample_paths,
        headline=headline,
        notes=notes,
    )


def _pick_sample_paths(curves: list[list[float]], cagrs: list[float]) -> list[SamplePath]:
    if not curves:
        return []
    order = sorted(range(len(cagrs)), key=lambda i: cagrs[i])
    picks = {
        "p5": order[max(0, int(0.05 * (len(order) - 1)))],
        "median": order[len(order) // 2],
        "p95": order[min(len(order) - 1, int(0.95 * (len(order) - 1)))],
    }
    return [SamplePath(kind=kind, points=curves[idx]) for kind, idx in picks.items()]


def _build_headline(cagr: dict[str, float], mdd: dict[str, float], beat_pct: float) -> str:
    return (
        f"다양한 미래 {int(beat_pct)}%에서 QQQ 장기보유를 이겼고, "
        f"중간값 CAGR {cagr['median']:.1f}% (하위 5% {cagr['p5']:.1f}%), "
        f"최대낙폭 중간값 {mdd['median']:.1f}% (하위 5% {mdd['p5']:.1f}%)입니다."
    )
