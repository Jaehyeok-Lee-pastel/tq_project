"""Walk-forward pure helpers (windowing + aggregation). No network."""

from datetime import date

from app.schemas.walkforward import WalkForwardRequest, WalkForwardWindow
from app.services.walkforward_engine import _aggregate, _median, _window_defs


def test_window_defs_roll_and_tile():
    first = date(2000, 1, 1)
    last = date(2026, 1, 1)
    defs = _window_defs(first, last, WalkForwardRequest(is_years=8, oos_years=3, step_years=3))
    assert len(defs) >= 5
    for is_s, is_e, oos_s, oos_e in defs:
        assert is_s < is_e == oos_s < oos_e <= last


def test_median_even_and_odd():
    assert _median([3.0, 1.0, 2.0]) == 2.0
    assert _median([1.0, 2.0, 3.0, 4.0]) == 2.5
    assert _median([]) == 0.0


def _win(idx, sel, is_cagr, oos_cagr, bench, fixed):
    return WalkForwardWindow(
        index=idx, is_start="2010-01-01", is_end="2018-01-01",
        oos_start="2018-01-01", oos_end="2021-01-01",
        selected_label=sel, is_cagr=is_cagr, is_score=70,
        oos_cagr=oos_cagr, oos_mdd=-50, oos_beat_benchmark=oos_cagr > bench,
        benchmark_oos_cagr=bench, fixed_oos_cagr=fixed, fixed_oos_mdd=-55,
    )


def test_aggregate_wfe_and_stability():
    windows = [
        _win(1, "A", is_cagr=10, oos_cagr=8, bench=5, fixed=9),
        _win(2, "A", is_cagr=10, oos_cagr=12, bench=15, fixed=11),
        _win(3, "B", is_cagr=20, oos_cagr=10, bench=8, fixed=10),
    ]
    report = _aggregate(windows)
    # WFE = mean(8/10, 12/10, 10/20) = mean(0.8, 1.2, 0.5) = 0.833 -> 83.3%
    assert report.walk_forward_efficiency_pct == 83.3
    assert report.modal_config == "A"
    assert report.selection_stability_pct == round(2 / 3 * 100, 1)
    # beat benchmark: win1 (8>5) yes, win2 (12>15) no, win3 (10>8) yes -> 2/3
    assert report.oos_beat_benchmark_pct == round(2 / 3 * 100, 1)
    assert report.adaptive_oos_cagr_median == 10.0
    assert report.fixed_oos_cagr_median == 10.0
