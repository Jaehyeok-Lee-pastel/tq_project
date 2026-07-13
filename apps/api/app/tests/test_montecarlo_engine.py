"""Regime-switching Monte Carlo: calibration + distribution sanity checks."""

import math

import pytest

from app.schemas.montecarlo import MonteCarloRequest
from app.services.market_data import PriceRow
from app.services.montecarlo_engine import (
    calibrate_regime_model,
    generate_path_frames,
    run_montecarlo,
)

TRADING_DAYS = 252


def synthetic_qqq(days: int = 1600) -> list[PriceRow]:
    """A deterministic price series with an up-trend, a crash, and a recovery."""
    closes: list[float] = [100.0]
    for i in range(1, days):
        if i < days * 0.4:
            drift = 0.0006  # bull
        elif i < days * 0.5:
            drift = -0.004  # crash
        else:
            drift = 0.0007  # recovery
        wobble = 0.004 * math.sin(i / 7.0)
        closes.append(closes[-1] * (1 + drift + wobble))
    return [PriceRow(date=f"2020-{(i // 28) % 12 + 1:02d}-{i % 28 + 1:02d}", close=c) for i, c in enumerate(closes)]


def test_calibration_produces_three_regimes():
    model = calibrate_regime_model(synthetic_qqq())
    assert set(model.regimes) == {"bull", "bear", "sideways"}
    # Bear regime should carry higher volatility than bull.
    assert model.regimes["bear"].ann_vol_pct >= model.regimes["bull"].ann_vol_pct


def test_generated_path_is_deterministic_for_a_seed():
    import random

    model = calibrate_regime_model(synthetic_qqq())
    frames_a = generate_path_frames(model, 400, random.Random(7), 200)
    frames_b = generate_path_frames(model, 400, random.Random(7), 200)
    assert len(frames_a) == len(frames_b)
    assert frames_a[100].qqq == frames_b[100].qqq  # same seed -> same path


def test_montecarlo_report_shape_and_reproducibility():
    qqq = synthetic_qqq(1800)
    req = MonteCarloRequest(n_paths=60, years=8, seed=123)
    a = run_montecarlo(req, qqq)
    b = run_montecarlo(req, qqq)

    assert a.n_paths == 60
    assert a.cagr.p5 <= a.cagr.median <= a.cagr.p95
    assert a.max_drawdown.p5 <= a.max_drawdown.median <= a.max_drawdown.p95
    assert 0 <= a.prob_beat_benchmark <= 100
    assert 0 <= a.prob_cagr_positive <= 100
    assert len(a.sample_paths) == 3
    # Same seed -> identical distribution.
    assert a.cagr.median == b.cagr.median
    assert a.headline == b.headline


def test_short_history_raises():
    with pytest.raises(ValueError):
        calibrate_regime_model([PriceRow(date="2020-01-01", close=100.0)] * 100)
