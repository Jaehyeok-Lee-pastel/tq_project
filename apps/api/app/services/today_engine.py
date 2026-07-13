"""Today's decision for an adopted research strategy.

Computes what the strategy's rules say to do RIGHT NOW from live QQQ history,
using the SAME rule helpers the backtest engine was validated with
(deceleration tiers, exit band, 2-day confirmation, 21-day redeploy). If this
file and backtest_engine ever disagree, the backtest results stop meaning
anything — keep them sharing helpers.
"""

from datetime import date, datetime, timezone

from app.schemas.managed_strategy import ResearchStrategyConfig, TodayDecision
from app.services.backtest_engine import (
    REDEPLOY_DAYS,
    TRADING_DAYS_PER_MONTH,
    daily_accumulation_reason,
    daily_tqqq_buy_ratio,
    deceleration_tier,
)
from app.services.market_data import PriceRow

TIER_LABELS = {
    0: "정상 적립 구간 (이격 +10% 미만)",
    1: "1차 감속 구간 (이격 +10~20%)",
    2: "2차 감속 구간 (이격 +20~30%)",
    3: "신규 TQQQ 중지 구간 (이격 +30% 이상)",
}

DEFENSE_POSTURE = {
    "cash": "방어 자금은 SGOV/현금 100%로 유지합니다.",
    "spym_sgov_half": "방어 자금은 SPYM 50% + SGOV/현금 50%로 유지합니다.",
    "hold_one_x": "1x 완충 자산은 계속 보유하고 TQQQ만 방어합니다.",
}

# How far back to look for the most recent defense episode when deciding
# whether the 21-day redeploy schedule is still running.
REDEPLOY_LOOKBACK_DAYS = 120


def sma(closes: list[float], length: int) -> float:
    return sum(closes[-length:]) / length


def consecutive_below_days(
    closes: list[float],
    ma_days: int,
    exit_band: float,
) -> int:
    """Trading days (from the latest bar backwards) closed at/below the exit line."""
    count = 0
    for index in range(len(closes) - 1, ma_days - 2, -1):
        window = closes[index - ma_days + 1 : index + 1]
        line = (sum(window) / ma_days) * (1 + exit_band)
        if closes[index] <= line:
            count += 1
        else:
            break
    return count


def redeploy_state(closes: list[float], ma_days: int, exit_band: float) -> tuple[bool, int]:
    """(active, day_number 1..21) of the post-defense redeploy schedule.

    Mirrors the backtest rule: after a confirmed defense (>=2 consecutive
    closes below the exit line), proceeds re-enter over the next REDEPLOY_DAYS
    trading days once the line is reclaimed.
    """
    above_streak = 0
    index = len(closes) - 1
    lookback_limit = max(ma_days - 1, len(closes) - 1 - REDEPLOY_LOOKBACK_DAYS)
    while index >= lookback_limit:
        window = closes[index - ma_days + 1 : index + 1]
        line = (sum(window) / ma_days) * (1 + exit_band)
        if closes[index] <= line:
            break
        above_streak += 1
        index -= 1
    if above_streak == 0 or above_streak > REDEPLOY_DAYS:
        return False, 0
    # Was the streak below the line long enough to have triggered a defense?
    below_streak = 0
    while index >= lookback_limit:
        window = closes[index - ma_days + 1 : index + 1]
        line = (sum(window) / ma_days) * (1 + exit_band)
        if closes[index] <= line:
            below_streak += 1
            index -= 1
        else:
            break
    if below_streak < 2:
        return False, 0
    return True, above_streak


def data_age_days(as_of: str) -> int:
    try:
        parsed = date.fromisoformat(as_of)
    except ValueError:
        return 999
    return max((datetime.now(timezone.utc).date() - parsed).days, 0)


def compute_today_decision(
    config: ResearchStrategyConfig,
    qqq_rows: list[PriceRow],
) -> TodayDecision:
    ma_days = config.moving_average_days
    if len(qqq_rows) < ma_days + 5:
        raise ValueError("오늘 판단에는 이동평균 계산에 충분한 QQQ 일봉 데이터가 필요합니다.")

    closes = [row.close for row in qqq_rows]
    latest = qqq_rows[-1]
    sma200 = sma(closes, ma_days)
    exit_band = config.ma_exit_band_pct / 100
    exit_line = sma200 * (1 + exit_band)
    distance = latest.close / sma200 - 1
    below_days = consecutive_below_days(closes, ma_days, exit_band)
    tier = deceleration_tier(distance)
    daily_budget = (
        config.monthly_contribution / TRADING_DAYS_PER_MONTH
        if config.monthly_contribution > 0
        else 0.0
    )
    tqqq_ratio = daily_tqqq_buy_ratio(distance, config.daily_base_tqqq_ratio / 100)
    one_x_ratio = (
        0.0
        if config.one_x_upfront_monthly
        else min(config.daily_base_one_x_ratio / 100, max(0.0, 1 - tqqq_ratio))
    )
    monthly_one_x_amount = round(
        config.monthly_contribution * config.daily_base_one_x_ratio / 100
    )
    redeploy_active, redeploy_day = redeploy_state(closes, ma_days, exit_band)

    checklist = [
        f"QQQ 종가 {latest.close:,.2f} / {ma_days}일선 {sma200:,.2f} (이탈 기준선 {exit_line:,.2f})",
        "시세 데이터가 최신 거래일인지 확인",
        "실행 후 아래 기록 버튼으로 저널에 남기기",
    ]

    if below_days == 0:
        tqqq_amount = round(daily_budget * tqqq_ratio)
        one_x_amount = round(daily_budget * one_x_ratio)
        if tier >= 3:
            action = "stop_new_tqqq"
            headline = "신규 TQQQ 적립 중지 — 1x/현금으로만 적립"
        elif tier >= 1:
            action = "accumulate_decelerated"
            headline = f"감속 적립 — TQQQ 일일 매수 {tqqq_ratio * 100:.0f}%로 축소"
        else:
            action = "accumulate"
            headline = "정상 적립 — 기본 비율대로 매수"
        instructions = [daily_accumulation_reason(distance)]
        if daily_budget > 0:
            if config.one_x_upfront_monthly:
                instructions.append(
                    f"오늘 TQQQ 적립 {tqqq_amount:,.0f}원"
                    + (
                        f" (일 예산 {daily_budget:,.0f}원 중 잔여는 현금 대기)"
                        if daily_budget - tqqq_amount > 1
                        else ""
                    )
                )
                instructions.append(
                    f"{config.one_x_symbol}는 매일 사지 않습니다 — 월급일 입금 시 "
                    f"월 적립의 {config.daily_base_one_x_ratio:.0f}%({monthly_one_x_amount:,.0f}원)를 "
                    "소수점 금액주문으로 일괄 매수하세요."
                )
            else:
                instructions.append(
                    f"오늘 적립 {daily_budget:,.0f}원: TQQQ {tqqq_amount:,.0f}원 + "
                    f"{config.one_x_symbol} {one_x_amount:,.0f}원"
                    + (
                        f" (잔여 {daily_budget - tqqq_amount - one_x_amount:,.0f}원은 현금 대기)"
                        if daily_budget - tqqq_amount - one_x_amount > 1
                        else ""
                    )
                )
        if redeploy_active:
            instructions.append(
                f"방어 현금 재투입 {redeploy_day}/{REDEPLOY_DAYS}일차: "
                f"남은 방어 현금의 1/{REDEPLOY_DAYS - redeploy_day + 1}을 같은 비율로 추가 매수"
            )
        return TodayDecision(
            as_of=latest.date,
            data_age_days=data_age_days(latest.date),
            qqq_close=round(latest.close, 2),
            qqq_sma200=round(sma200, 2),
            distance_pct=round(distance * 100, 2),
            exit_line=round(exit_line, 2),
            regime="above",
            below_ma_days=0,
            tier=tier,
            tier_label=TIER_LABELS[tier],
            action=action,  # type: ignore[arg-type]
            headline=headline,
            instructions=instructions,
            daily_budget=round(daily_budget, 2),
            tqqq_buy_amount=tqqq_amount,
            one_x_buy_amount=one_x_amount,
            tqqq_buy_ratio_pct=round(tqqq_ratio * 100, 1),
            one_x_buy_ratio_pct=round(one_x_ratio * 100, 1),
            redeploy_active=redeploy_active,
            redeploy_day=redeploy_day,
            defense_mode=config.defense_mode,
            checklist=checklist,
        )

    if below_days == 1:
        headline = "이탈 1일차 — 아직 매도하지 않습니다"
        instructions = [
            f"QQQ가 이탈 기준선({exit_line:,.2f}) 아래에서 1일 마감했습니다. 규칙상 2일 연속 확인 전에는 매도하지 않습니다.",
            "오늘 신규 TQQQ/1x 매수는 중단하고, 적립금은 현금으로 대기합니다.",
            "내일도 기준선 아래로 마감하면 방어 전환을 실행합니다.",
        ]
        action = "hold_below_unconfirmed"
        regime = "below_unconfirmed"
    else:
        regime = "defense"
        if below_days == 2:
            action = "defense_sell"
            headline = "방어 전환 실행일 — 규칙에 따라 매도"
            if config.defense_mode == "hold_one_x":
                instructions = ["TQQQ 전량 매도 → 현금/SGOV. 1x 완충 자산은 계속 보유합니다."]
            elif config.defense_mode == "spym_sgov_half":
                instructions = [
                    f"TQQQ와 {config.one_x_symbol} 전량 매도.",
                    "매도 대금의 50%는 SPYM 매수, 50%는 SGOV/현금으로 배치합니다.",
                ]
            else:
                instructions = [
                    f"TQQQ와 {config.one_x_symbol} 전량 매도 → 전액 SGOV/현금 방어."
                ]
        else:
            action = "hold_defense"
            headline = f"방어 유지 — 이탈 {below_days}일차"
            instructions = [
                "이미 방어 전환이 완료됐어야 하는 구간입니다. 미실행분이 있으면 지금 실행하세요.",
                DEFENSE_POSTURE[config.defense_mode],
            ]
        instructions.append(
            f"적립금은 현금으로 대기하고, QQQ가 기준선({exit_line:,.2f}) 위로 복귀하면 "
            f"{REDEPLOY_DAYS}거래일 분할 재투입을 시작합니다."
        )

    return TodayDecision(
        as_of=latest.date,
        data_age_days=data_age_days(latest.date),
        qqq_close=round(latest.close, 2),
        qqq_sma200=round(sma200, 2),
        distance_pct=round(distance * 100, 2),
        exit_line=round(exit_line, 2),
        regime=regime,  # type: ignore[arg-type]
        below_ma_days=below_days,
        tier=tier,
        tier_label=TIER_LABELS[tier],
        action=action,  # type: ignore[arg-type]
        headline=headline,
        instructions=instructions,
        daily_budget=round(daily_budget, 2),
        tqqq_buy_amount=0,
        one_x_buy_amount=0,
        tqqq_buy_ratio_pct=0,
        one_x_buy_ratio_pct=0,
        redeploy_active=False,
        redeploy_day=0,
        defense_mode=config.defense_mode,
        checklist=checklist,
    )
