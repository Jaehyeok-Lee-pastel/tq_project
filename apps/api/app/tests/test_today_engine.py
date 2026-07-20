"""Today-decision engine: same rules as the backtest, applied to live data."""

import pytest

from app.schemas.managed_strategy import ResearchStrategyConfig
from app.services.market_data import PriceRow
from app.services.today_engine import compute_today_decision

MA_DAYS = 200


def make_rows(closes: list[float]) -> list[PriceRow]:
    return [
        PriceRow(date=f"2026-{(index // 28) + 1:02d}-{(index % 28) + 1:02d}", close=close)
        for index, close in enumerate(closes)
    ]


def config(**overrides) -> ResearchStrategyConfig:
    base = dict(
        strategy="tqqq_daily_200ma",
        daily_base_tqqq_ratio=70,
        daily_base_one_x_ratio=30,
        one_x_symbol="QQQM",
        ma_exit_band_pct=0,
        defense_mode="cash",
        monthly_contribution=1_050_000,  # 50,000/trading day
        moving_average_days=MA_DAYS,
        one_x_upfront_monthly=False,
    )
    base.update(overrides)
    return ResearchStrategyConfig(**base)


def test_above_ma_normal_accumulation():
    closes = [100.0] * MA_DAYS + [105.0] * 10
    decision = compute_today_decision(config(), make_rows(closes))
    assert decision.regime == "above"
    assert decision.action == "accumulate"
    assert decision.tier == 0
    assert decision.tqqq_buy_ratio_pct == 70.0
    assert decision.tqqq_buy_amount == pytest.approx(35_000, abs=1)
    assert decision.one_x_buy_amount == pytest.approx(15_000, abs=1)


def test_stretched_market_decelerates_tqqq_buy():
    # Constant closes at 115 with an SMA near 101 -> distance ~ +14% -> tier 1.
    closes = [100.0] * (MA_DAYS - 20) + [115.0] * 30
    decision = compute_today_decision(config(), make_rows(closes))
    assert decision.regime == "above"
    assert decision.tier == 1
    assert decision.action == "accumulate_decelerated"
    assert decision.tqqq_buy_ratio_pct == pytest.approx(70 * 0.65, abs=0.1)


def test_first_below_day_holds_without_selling():
    closes = [100.0] * MA_DAYS + [105.0] * 10 + [94.0]
    decision = compute_today_decision(config(), make_rows(closes))
    assert decision.regime == "below_unconfirmed"
    assert decision.below_ma_days == 1
    assert decision.action == "hold_below_unconfirmed"
    assert decision.tqqq_buy_amount == 0


def test_second_below_day_triggers_defense_sell_per_mode():
    closes = [100.0] * MA_DAYS + [105.0] * 10 + [94.0, 93.0]
    cash = compute_today_decision(config(defense_mode="cash"), make_rows(closes))
    assert cash.regime == "defense"
    assert cash.action == "defense_sell"
    assert any("QQQM 전량 매도" in item for item in cash.instructions)

    half = compute_today_decision(config(defense_mode="spym_sgov_half"), make_rows(closes))
    assert any("SPYM" in item for item in half.instructions)

    hold = compute_today_decision(config(defense_mode="hold_one_x"), make_rows(closes))
    assert any("1x 완충 자산은 계속 보유" in item for item in hold.instructions)


def test_exit_band_shifts_the_defense_line():
    # Close sits ~1% above the SMA: fine without a band, below line with +2%.
    closes = [100.0] * MA_DAYS + [101.0] * 8
    no_band = compute_today_decision(config(ma_exit_band_pct=0), make_rows(closes))
    with_band = compute_today_decision(config(ma_exit_band_pct=2), make_rows(closes))
    assert no_band.regime == "above"
    assert with_band.regime == "defense"


def test_upfront_mode_moves_one_x_to_payday_instruction():
    closes = [100.0] * MA_DAYS + [105.0] * 10
    decision = compute_today_decision(
        config(one_x_upfront_monthly=True), make_rows(closes)
    )
    assert decision.one_x_buy_amount == 0
    assert decision.one_x_buy_ratio_pct == 0
    assert decision.tqqq_buy_amount == pytest.approx(35_000, abs=1)
    assert any("소수점 금액주문으로 일괄 매수" in item for item in decision.instructions)
    assert any("315,000" in item for item in decision.instructions)  # 1,050,000 x 30%


def test_redeploy_window_detected_after_recovery():
    # 3 days below (confirmed defense), then 5 days back above the line.
    closes = [100.0] * MA_DAYS + [90.0, 90.0, 90.0] + [112.0] * 5
    decision = compute_today_decision(config(), make_rows(closes))
    assert decision.regime == "above"
    assert decision.redeploy_active
    assert decision.redeploy_day == 5
    assert any("재투입" in item for item in decision.instructions)
