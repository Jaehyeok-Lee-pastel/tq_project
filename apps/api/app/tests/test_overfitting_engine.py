"""DSR / PBO pure math checks (no network)."""

import math

from app.services.overfitting_engine import (
    _daily_sharpe,
    _deflated_sharpe,
    _moments,
    _pbo,
)


def test_moments_of_known_series():
    r = [0.01, -0.01, 0.02, -0.02, 0.0]
    mean, std, skew, kurt = _moments(r)
    assert abs(mean) < 1e-9
    assert std > 0
    assert abs(skew) < 1e-9  # symmetric


def test_deflated_sharpe_high_when_edge_far_above_trials():
    import random

    rng = random.Random(1)
    # Adopted: clear positive drift. Trial Sharpes: tight cluster of small values.
    adopted = [0.001 + rng.gauss(0, 0.01) for _ in range(3000)]
    trial_sharpes = [rng.gauss(0.02, 0.01) for _ in range(40)]
    dsr, obs, sr0, skew, kurt = _deflated_sharpe(adopted, trial_sharpes, 40)
    assert 0.0 <= dsr <= 1.0
    assert obs > sr0  # observed beats the luck benchmark
    assert dsr > 0.9


def test_pbo_high_for_pure_noise_configs():
    import random

    rng = random.Random(2)
    # 10 configs of pure noise, no persistent skill -> IS-best should not
    # persist OOS -> PBO should be substantial (not near zero).
    matrix = [[rng.gauss(0, 0.01) for _ in range(800)] for _ in range(10)]
    pbo, splits = _pbo(matrix, 8)
    assert splits == 70
    assert 0.0 <= pbo <= 1.0
    assert pbo > 0.2


def test_pbo_low_for_one_genuinely_dominant_config():
    import random

    rng = random.Random(3)
    matrix = []
    for c in range(8):
        drift = 0.002 if c == 0 else 0.0  # config 0 truly dominates everywhere
        matrix.append([drift + rng.gauss(0, 0.01) for _ in range(1200)])
    pbo, _ = _pbo(matrix, 8)
    assert pbo < 0.2  # the dominant config persists OOS


def test_daily_sharpe_sign():
    assert _daily_sharpe([0.01, 0.01, 0.02, 0.01]) > 0
    assert _daily_sharpe([-0.01, -0.02, -0.01]) < 0
