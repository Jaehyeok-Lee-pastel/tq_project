"""Backtest-overfitting statistics: Deflated Sharpe Ratio + PBO (CSCV).

We have tested dozens of configurations across this project, so the "winner"
is subject to selection bias — the more you try, the higher the best-looking
Sharpe climbs by pure luck. These two Bailey & Lopez de Prado statistics
correct for exactly that:

- Deflated Sharpe Ratio (DSR): the probability that the adopted config's
  Sharpe is real AFTER deflating for the number of trials, sample length, and
  non-normality (skew/kurtosis). DSR > 0.95 = significant; < 0.5 = likely a
  false discovery from multiple testing.
- Probability of Backtest Overfitting (PBO) via CSCV: split time into blocks,
  in every combinatorial half-split pick the in-sample-best config, and see
  how often it lands below the median out-of-sample. ~0 = robust, ~0.5 =
  coin-flip (overfit).
"""

import math
from itertools import combinations
from statistics import NormalDist

from app.schemas.overfitting import OverfittingReport, OverfittingRequest
from app.services.backtest_engine import (
    adjusted_returns,
    load_dataset,
    simulate_daily_accumulation_200ma_strategy,
)

EULER_MASCHERONI = 0.5772156649015329
TRADING_DAYS = 252
CSCV_BLOCKS = 8  # C(8,4) = 70 combinatorial splits
CORRECTION_TRIALS = 100  # allowance for prior exploratory variants
GRID = [
    {"ratio": ratio, "band": band, "defense": defense}
    for ratio in (50, 60, 70, 80, 90)
    for band in (0.0, 1.0, 2.0, 3.0)
    for defense in ("cash", "spym_sgov_half")
]
ADOPTED = {"ratio": 80, "band": 2.0, "defense": "cash"}
_ND = NormalDist()


def _label(cfg: dict) -> str:
    defense = "현금" if cfg["defense"] == "cash" else "반반"
    return f"{cfg['ratio']}:{100 - cfg['ratio']} 밴드{cfg['band']:.0f} {defense}"


def _returns_for(cfg: dict, frames, req: OverfittingRequest) -> list[float]:
    daily_cash_return = (1 + req.cash_yield / 100) ** (1 / TRADING_DAYS) - 1
    curve, _ = simulate_daily_accumulation_200ma_strategy(
        frames=frames,
        initial_capital=req.initial_capital,
        monthly_contribution=req.monthly_contribution,
        base_tqqq_ratio=cfg["ratio"] / 100,
        base_one_x_ratio=(100 - cfg["ratio"]) / 100,
        one_x_symbol="QQQM",
        initial_tqqq_value=req.initial_tqqq_value,
        initial_one_x_value=req.initial_one_x_value,
        initial_cash_value=req.initial_cash_value,
        daily_cash_return=daily_cash_return,
        cost_ratio=0.001,
        moving_average_days=200,
        exit_band=cfg["band"] / 100,
        defense_mode=cfg["defense"],
        one_x_upfront_monthly=True,
    )
    strategy_returns = adjusted_returns(curve)
    benchmark_returns = [
        frames[index].qqq / frames[index - 1].qqq - 1
        for index in range(1, len(frames))
    ]
    return [
        strategy - benchmark
        for strategy, benchmark in zip(strategy_returns, benchmark_returns, strict=False)
    ]


def _moments(returns: list[float]) -> tuple[float, float, float, float]:
    """mean, sample-std, skew, kurtosis(non-excess)."""
    n = len(returns)
    mean = sum(returns) / n
    m2 = sum((r - mean) ** 2 for r in returns) / n
    m3 = sum((r - mean) ** 3 for r in returns) / n
    m4 = sum((r - mean) ** 4 for r in returns) / n
    std_pop = math.sqrt(m2)
    std_sample = math.sqrt(m2 * n / (n - 1)) if n > 1 else 0.0
    skew = m3 / std_pop**3 if std_pop > 0 else 0.0
    kurt = m4 / std_pop**4 if std_pop > 0 else 3.0
    return mean, std_sample, skew, kurt


def _daily_sharpe(returns: list[float]) -> float:
    mean, std, _, _ = _moments(returns)
    return mean / std if std > 0 else 0.0


def _deflated_sharpe(
    adopted_returns: list[float], all_sharpes: list[float], n_trials: int
) -> tuple[float, float, float, float, float]:
    mean, std, skew, kurt = _moments(adopted_returns)
    sr = mean / std if std > 0 else 0.0
    t = len(adopted_returns)

    # Cross-trial Sharpe dispersion (sample std of the N trial Sharpes).
    sr_mean = sum(all_sharpes) / len(all_sharpes)
    sr_var = sum((s - sr_mean) ** 2 for s in all_sharpes) / max(len(all_sharpes) - 1, 1)
    sigma_sr = math.sqrt(sr_var)

    # Expected max Sharpe under the null across N independent trials.
    sr0 = sigma_sr * (
        (1 - EULER_MASCHERONI) * _ND.inv_cdf(1 - 1 / n_trials)
        + EULER_MASCHERONI * _ND.inv_cdf(1 - 1 / (n_trials * math.e))
    )

    denom = math.sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr**2, 1e-9))
    dsr = _ND.cdf((sr - sr0) * math.sqrt(t - 1) / denom)
    return dsr, sr * math.sqrt(TRADING_DAYS), sr0 * math.sqrt(TRADING_DAYS), skew, kurt


def _block_stats(returns: list[float], blocks: int) -> list[tuple[int, float, float]]:
    """Per-block (count, sum, sumsq) so any block-union Sharpe is O(blocks)."""
    size = len(returns) // blocks
    stats: list[tuple[int, float, float]] = []
    for b in range(blocks):
        start = b * size
        end = len(returns) if b == blocks - 1 else (b + 1) * size
        seg = returns[start:end]
        stats.append((len(seg), sum(seg), sum(r * r for r in seg)))
    return stats


def _sharpe_over_blocks(stats: list[tuple[int, float, float]], block_ids) -> float:
    n = sum(stats[b][0] for b in block_ids)
    s1 = sum(stats[b][1] for b in block_ids)
    s2 = sum(stats[b][2] for b in block_ids)
    if n < 2:
        return 0.0
    mean = s1 / n
    var = (s2 - n * mean * mean) / (n - 1)
    return mean / math.sqrt(var) if var > 1e-18 else 0.0


def _pbo(return_matrix: list[list[float]], blocks: int) -> tuple[float, int]:
    """CSCV probability of backtest overfitting."""
    per_config_blocks = [_block_stats(r, blocks) for r in return_matrix]
    all_ids = list(range(blocks))
    splits = list(combinations(all_ids, blocks // 2))
    overfit = 0
    counted = 0
    n_configs = len(return_matrix)
    for is_ids in splits:
        oos_ids = [b for b in all_ids if b not in is_ids]
        is_sharpes = [_sharpe_over_blocks(per_config_blocks[c], is_ids) for c in range(n_configs)]
        oos_sharpes = [_sharpe_over_blocks(per_config_blocks[c], oos_ids) for c in range(n_configs)]
        best_is = max(range(n_configs), key=lambda c: is_sharpes[c])
        # OOS rank of the IS-best (1 = worst .. n = best); below median => overfit.
        below = sum(1 for c in range(n_configs) if oos_sharpes[c] < oos_sharpes[best_is])
        relative_rank = below / (n_configs - 1)  # 0..1, higher = better OOS
        if relative_rank < 0.5:
            overfit += 1
        counted += 1
    return (overfit / counted if counted else 0.0), counted


async def run_overfitting(req: OverfittingRequest, provider: str) -> OverfittingReport:
    dataset = await load_dataset(provider, 200)
    frames = dataset.frames
    if len(frames) < 500:
        raise ValueError("과최적화 검증에는 더 긴 데이터가 필요합니다.")

    matrix = [_returns_for(cfg, frames, req) for cfg in GRID]
    sharpes = [_daily_sharpe(r) for r in matrix]
    adopted_idx = next(
        i for i, cfg in enumerate(GRID)
        if cfg["ratio"] == ADOPTED["ratio"] and cfg["band"] == ADOPTED["band"] and cfg["defense"] == ADOPTED["defense"]
    )

    dsr, obs_sr, sr0, skew, kurt = _deflated_sharpe(
        matrix[adopted_idx], sharpes, CORRECTION_TRIALS
    )
    pbo, splits = _pbo(matrix, CSCV_BLOCKS)

    dsr_verdict = "유의미(강건)" if dsr >= 0.95 else "보통" if dsr >= 0.6 else "과최적화 의심"
    pbo_verdict = "낮음(강건)" if pbo <= 0.2 else "보통" if pbo <= 0.4 else "높음(과최적화)"
    headline = (
        f"QQQ 초과수익 DSR {dsr * 100:.1f}% ({dsr_verdict}) · "
        f"과최적화 확률(PBO) {pbo * 100:.1f}% ({pbo_verdict}). "
        f"초과수익 샤프 {obs_sr:.2f} vs 우연 기대 최고 {sr0:.2f}."
    )
    notes = [
        f"{len(GRID)}개 대표 설정을 계산하고 과거 탐색까지 감안해 {CORRECTION_TRIALS}회 시험으로 보수적으로 보정했습니다.",
        "수익률은 QQQ 일수익률을 차감한 초과수익입니다. 주식시장 자체의 장기 상승 효과는 DSR에서 제외했습니다.",
        "디플레이티드 샤프(DSR)는 '많이 시험해서 우연히 좋아 보일 가능성'을 관측 샤프에서 차감한 뒤의 유의확률입니다. "
        "95% 이상은 강한 조건부 근거지만 미래 초과수익을 보장하지 않습니다.",
        "과최적화 확률(PBO)은 학습 최고 설정이 검증에서 중앙값 아래로 떨어지는 비율(순위 지속성)입니다.",
    ]
    if dsr >= 0.95 and pbo > 0.5:
        notes.append(
            "⚠ 해석 주의: DSR은 높은데 PBO도 높은 이 조합은 모순이 아닙니다. 40개 설정이 거의 동일한 '고원'"
            "(파라미터 지형 탭 참고)이라 '어느 설정이 최고인가'는 노이즈(PBO 높음)이지만, 전략 자체의 우위는 "
            "공통 구조에 초과수익 근거가 있다는 뜻입니다. PBO는 순위를 볼 뿐 수익 크기를 안 봅니다. "
            "결론: 조건부 강건성 근거는 있지만 특정 설정의 우월성이나 미래 성과를 확정하지는 못합니다."
        )
    else:
        notes.append(
            "PBO 0%에 가까울수록 강건, 50% 이상이면 학습 최고 설정이 미래에 안 통하는 과최적화 신호입니다."
        )
    notes.append(f"비정규성 반영: 왜도 {skew:.2f}, 첨도 {kurt:.2f}. CSCV 분할 {splits}개.")
    return OverfittingReport(
        n_trials=len(GRID),
        correction_trials=CORRECTION_TRIALS,
        sample_days=len(matrix[adopted_idx]),
        adopted_label=_label(ADOPTED),
        observed_sharpe=round(obs_sr, 2),
        deflated_benchmark_sharpe=round(sr0, 2),
        deflated_sharpe_ratio=round(dsr, 4),
        skew=round(skew, 2),
        kurtosis=round(kurt, 2),
        pbo=round(pbo, 4),
        cscv_splits=splits,
        dsr_verdict=dsr_verdict,
        pbo_verdict=pbo_verdict,
        headline=headline,
        notes=notes,
    )
