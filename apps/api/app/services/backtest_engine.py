
from app.core.config import settings
from app.schemas.backtest import (
    BacktestRunRequest,
    BacktestRunResponse,
    EquityPoint,
    TradeLogItem,
)
from app.services.backtesting.models import (
    REDEPLOY_DAYS,
    STRATEGY_NAMES,
    TRADING_DAYS_PER_MONTH,
    TRADING_DAYS_PER_YEAR,
    BacktestFrame,
    MarketDataset,
)
from app.services.backtesting.reporting import (
    adjusted_returns,
    build_data_notes,
    build_interpretation,
    build_projection,
    calculate_metrics,
    calculate_regime_performance,
    calculate_yearly_returns,
    downsample_curve,
    sortino_ratio,
)
from app.services.market_data import (
    PriceRow,
    fetch_extended_history,
    fetch_provider_history,
)

__all__ = [
    "REDEPLOY_DAYS",
    "TRADING_DAYS_PER_MONTH",
    "TRADING_DAYS_PER_YEAR",
    "BacktestFrame",
    "adjusted_returns",
    "calculate_metrics",
    "calculate_regime_performance",
    "load_dataset",
    "run_backtest",
    "simulate_buy_hold",
    "simulate_daily_accumulation_200ma_strategy",
    "simulate_staged_200ma_strategy",
    "simulate_strategy",
    "sortino_ratio",
]


async def run_backtest(request: BacktestRunRequest) -> BacktestRunResponse:
    provider = settings.market_data_provider.lower()
    dataset = await load_dataset(provider, request.moving_average_days)
    frames = filter_frames(dataset.frames, request.start_date, request.end_date)
    if len(frames) < 220:
        raise ValueError("백테스트에는 최소 220거래일 이상의 데이터가 필요합니다.")

    result_curve, trades = simulate_strategy(frames, request)
    benchmark_curve, _ = simulate_buy_hold(
        frames,
        request.initial_capital,
        "QQQ",
        request.monthly_contribution,
        (request.fee_bps + request.slippage_bps) / 10_000,
    )
    metrics = calculate_metrics(result_curve, trades)
    benchmark_metrics = calculate_metrics(benchmark_curve, [])
    yearly = calculate_yearly_returns(result_curve)
    regime_performance = calculate_regime_performance(frames, result_curve)
    projection = build_projection(request, result_curve)

    return BacktestRunResponse(
        strategy=request.strategy,
        strategy_name=STRATEGY_NAMES[request.strategy],
        moving_average_days=request.moving_average_days,
        benchmark_name="QQQ 장기 보유",
        period_start=result_curve[0].date,
        period_end=result_curve[-1].date,
        equity_curve=downsample_curve(result_curve),
        benchmark_curve=downsample_curve(benchmark_curve),
        metrics=metrics,
        benchmark_metrics=benchmark_metrics,
        yearly_returns=yearly,
        regime_performance=regime_performance,
        trades=trades,
        projection=projection,
        interpretation=build_interpretation(metrics, benchmark_metrics, request),
        data_notes=build_data_notes(dataset, result_curve),
    )


async def load_dataset(provider: str, moving_average_days: int) -> MarketDataset:
    qqq_rows = await fetch_provider_history("QQQ", provider)
    spy_rows = await fetch_provider_history("SPY", provider)
    tqqq_rows, tqqq_synthetic_until = await fetch_extended_history("TQQQ", provider)
    qld_rows, qld_synthetic_until = await fetch_extended_history("QLD", provider)
    frames = build_frames(qqq_rows, tqqq_rows, qld_rows, spy_rows, moving_average_days)
    return MarketDataset(
        frames=frames,
        tqqq_synthetic_until=tqqq_synthetic_until,
        qld_synthetic_until=qld_synthetic_until,
    )


def build_frames(
    qqq_rows: list[PriceRow],
    tqqq_rows: list[PriceRow],
    qld_rows: list[PriceRow],
    spy_rows: list[PriceRow],
    moving_average_days: int,
) -> list[BacktestFrame]:
    tqqq_by_date = {row.date: row.close for row in tqqq_rows}
    qld_by_date = {row.date: row.close for row in qld_rows}
    spy_by_date = {row.date: row.close for row in spy_rows}
    qqq_with_sma: list[tuple[PriceRow, float, float | None, float | None, float | None]] = []

    for index, row in enumerate(qqq_rows):
        if index < moving_average_days - 1:
            continue
        closes = [item.close for item in qqq_rows[index - moving_average_days + 1 : index + 1]]
        closes20 = [item.close for item in qqq_rows[max(0, index - 19) : index + 1]]
        closes50 = [item.close for item in qqq_rows[max(0, index - 49) : index + 1]]
        high20_values = [item.close for item in qqq_rows[max(0, index - 20) : index]]
        qqq_with_sma.append(
            (
                row,
                sum(closes) / moving_average_days,
                sum(closes20) / 20 if len(closes20) >= 20 else None,
                sum(closes50) / 50 if len(closes50) >= 50 else None,
                max(high20_values) if len(high20_values) >= 20 else None,
            )
        )

    frames = [
        BacktestFrame(
            date=row.date,
            qqq=row.close,
            tqqq=tqqq_by_date[row.date],
            qld=qld_by_date[row.date],
            spy=spy_by_date[row.date],
            sma200=sma200,
            sma20=sma20,
            sma50=sma50,
            high20=high20,
        )
        for row, sma200, sma20, sma50, high20 in qqq_with_sma
        if row.date in tqqq_by_date and row.date in qld_by_date and row.date in spy_by_date
    ]
    frames.sort(key=lambda frame: frame.date)
    return frames


def filter_frames(
    frames: list[BacktestFrame],
    start_date: str | None,
    end_date: str | None,
) -> list[BacktestFrame]:
    if start_date:
        frames = [frame for frame in frames if frame.date >= start_date]
    if end_date:
        frames = [frame for frame in frames if frame.date <= end_date]
    return frames


def simulate_strategy(
    frames: list[BacktestFrame],
    request: BacktestRunRequest,
) -> tuple[list[EquityPoint], list[TradeLogItem]]:
    if request.strategy in {"qqq_buy_hold", "tqqq_buy_hold"}:
        symbol = "QQQ" if request.strategy == "qqq_buy_hold" else "TQQQ"
        return simulate_buy_hold(
            frames,
            request.initial_capital,
            symbol,
            request.monthly_contribution,
            (request.fee_bps + request.slippage_bps) / 10_000,
        )

    if request.strategy in {"tqqq_daily_200ma", "qld_daily_200ma"}:
        leveraged_symbol = "TQQQ" if request.strategy == "tqqq_daily_200ma" else "QLD"
        return simulate_daily_accumulation_200ma_strategy(
            frames=frames,
            initial_capital=request.initial_capital,
            monthly_contribution=request.monthly_contribution,
            base_tqqq_ratio=request.daily_base_tqqq_ratio / 100,
            base_one_x_ratio=request.daily_base_one_x_ratio / 100,
            one_x_symbol=request.one_x_symbol,
            initial_tqqq_value=(
                request.initial_tqqq_value
                if leveraged_symbol == "TQQQ"
                else request.initial_qld_value
            ),
            initial_one_x_value=request.initial_one_x_value,
            initial_cash_value=request.initial_cash_value,
            daily_cash_return=((1 + request.cash_yield / 100) ** (1 / TRADING_DAYS_PER_YEAR) - 1),
            cost_ratio=(request.fee_bps + request.slippage_bps) / 10_000,
            moving_average_days=request.moving_average_days,
            exit_band=request.ma_exit_band_pct / 100,
            band_scale=request.disparity_band_scale,
            decel_mid=request.daily_decel_mid,
            decel_high=request.daily_decel_high,
            decel_stop=request.daily_decel_stop,
            defense_mode=request.defense_mode or "hold_one_x",
            reserve_redeploy_days=request.reserve_redeploy_days,
            dip_buy_multiple=request.dip_buy_multiple,
            tqqq_batch_days=request.tqqq_batch_days,
            one_x_batch_days=request.one_x_batch_days,
            one_x_upfront_monthly=request.one_x_upfront_monthly,
            leveraged_symbol=leveraged_symbol,
        )

    target_symbol = "TQQQ" if request.strategy == "tqqq_200ma" else "QLD"
    target_ratio = (
        request.tqqq_target_ratio
        if target_symbol == "TQQQ"
        else request.qld_target_ratio
    )
    daily_cash_return = (1 + request.cash_yield / 100) ** (1 / TRADING_DAYS_PER_YEAR) - 1
    cost_ratio = (request.fee_bps + request.slippage_bps) / 10_000
    return simulate_staged_200ma_strategy(
        frames=frames,
        initial_capital=request.initial_capital,
        target_symbol=target_symbol,
        target_ratio=target_ratio / 100,
        one_x_ratio=request.one_x_target_ratio / 100,
        one_x_symbol=request.one_x_symbol,
        daily_cash_return=daily_cash_return,
        cost_ratio=cost_ratio,
        moving_average_days=request.moving_average_days,
        monthly_contribution=request.monthly_contribution,
        exit_band=request.ma_exit_band_pct / 100,
        overheat_trim_distance=request.overheat_trim_distance_pct / 100,
        defense_mode=request.defense_mode or "cash",
    )


def simulate_daily_accumulation_200ma_strategy(
    frames: list[BacktestFrame],
    initial_capital: float,
    monthly_contribution: float,
    base_tqqq_ratio: float,
    base_one_x_ratio: float,
    one_x_symbol: str,
    initial_tqqq_value: float,
    initial_one_x_value: float,
    initial_cash_value: float,
    daily_cash_return: float,
    cost_ratio: float,
    moving_average_days: int,
    exit_band: float = 0.0,
    band_scale: float = 1.0,
    decel_mid: float = 0.65,
    decel_high: float = 0.30,
    decel_stop: float = 0.0,
    defense_mode: str = "hold_one_x",
    reserve_redeploy_days: int = 0,
    dip_buy_multiple: float = 0.0,
    tqqq_batch_days: int = 1,
    one_x_batch_days: int = 1,
    one_x_upfront_monthly: bool = False,
    leveraged_symbol: str = "TQQQ",
) -> tuple[list[EquityPoint], list[TradeLogItem]]:
    has_initial_holdings = any(
        value > 0 for value in (initial_tqqq_value, initial_one_x_value, initial_cash_value)
    )
    cash = initial_cash_value if has_initial_holdings else initial_capital
    tqqq_value = initial_tqqq_value if has_initial_holdings else 0.0
    one_x_value = initial_one_x_value if has_initial_holdings else 0.0
    starting_equity = cash + tqqq_value + one_x_value
    peak = starting_equity
    curve: list[EquityPoint] = [starting_point(frames[0].date, starting_equity, "CASH")]
    trades: list[TradeLogItem] = []
    below_ma_days = 0
    daily_contribution = monthly_contribution / TRADING_DAYS_PER_MONTH if monthly_contribution > 0 else 0
    initial_daily_deploy = 0 if has_initial_holdings else initial_capital / REDEPLOY_DAYS
    initial_deploy_days_left = 0 if has_initial_holdings else REDEPLOY_DAYS
    # After a defensive sell, the proceeds must return to the market once QQQ
    # reclaims the MA; otherwise the strategy drifts into permanent cash,
    # which contradicts philosophy principles 2 and 6 (no idle cash uptrend).
    redeploy_pending = False
    redeploy_daily_amount = 0.0
    redeploy_days_left = 0
    # Cash left unspent by deceleration, waiting to re-enter when disparity
    # normalizes (only tracked when reserve_redeploy_days > 0).
    decel_reserve = 0.0
    # One-day disparity drop that counts as a "sharp dip" for dip_buy_multiple.
    dip_trigger_drop = 0.03
    prev_distance: float | None = None
    # Batch buying (whole-share modeling): earmarked budgets wait in cash and
    # execute every N eligible days.
    tqqq_pending = 0.0
    one_x_pending = 0.0
    tqqq_batch_counter = 0
    one_x_batch_counter = 0
    # Salary-day mode state: which calendar month we already received, and
    # the month's 1x allocation still waiting to be bought (waits below MA).
    current_salary_month = ""
    upfront_one_x_pending = 0.0
    # Routine daily buys are the strategy's normal operation, not decisions.
    # Log a trade only when the deceleration tier changes, so trade_count
    # reflects regime shifts instead of counting every scheduled purchase.
    last_logged_tier: int | None = None

    defense_spy_value = 0.0

    for index in range(1, len(frames)):
        prev = frames[index - 1]
        current = frames[index]
        tqqq_value *= 1 + price_return(prev, current, leveraged_symbol)
        one_x_value *= 1 + price_return(prev, current, one_x_symbol)
        defense_spy_value *= 1 + price_return(prev, current, "SPY")
        cash *= 1 + daily_cash_return
        cash_flow = 0.0
        if one_x_upfront_monthly and monthly_contribution > 0:
            month = current.date[:7]
            if month != current_salary_month:
                current_salary_month = month
                cash += monthly_contribution
                cash_flow = monthly_contribution
                upfront_one_x_pending += monthly_contribution * base_one_x_ratio
        elif daily_contribution:
            cash += daily_contribution
            cash_flow = daily_contribution

        distance = prev.qqq / prev.sma200 - 1
        above_ma = prev.qqq > prev.sma200 * (1 + exit_band)
        below_ma_days = below_ma_days + 1 if not above_ma else 0

        sell_one_x = defense_mode != "hold_one_x" and one_x_value > 0
        if below_ma_days >= 2 and (tqqq_value > 0 or sell_one_x):
            proceeds = 0.0
            if tqqq_value > 0:
                proceeds += tqqq_value * (1 - cost_ratio)
                trades.append(
                    TradeLogItem(
                        date=current.date,
                        action="sell",
                        symbol=leveraged_symbol,
                        ratio=0,
                        reason=f"QQQ가 {moving_average_days}일선 아래에서 2거래일 이상 마감해 {leveraged_symbol} 전량 방어 전환",
                    )
                )
                tqqq_value = 0.0
            if sell_one_x:
                proceeds += one_x_value * (1 - cost_ratio)
                trades.append(
                    TradeLogItem(
                        date=current.date,
                        action="sell",
                        symbol=one_x_symbol,
                        ratio=0,
                        reason="방어 모드에 따라 1x 완충 자산도 함께 방어 전환",
                    )
                )
                one_x_value = 0.0
            if defense_mode == "spym_sgov_half" and proceeds > 0:
                spym_buy = proceeds * 0.5
                defense_spy_value += spym_buy * (1 - cost_ratio)
                cash += proceeds - spym_buy
                trades.append(
                    TradeLogItem(
                        date=current.date,
                        action="buy",
                        symbol="SPYM",
                        ratio=50,
                        reason="방어 자금의 절반을 SPYM으로, 나머지는 SGOV/현금으로 배치",
                    )
                )
            else:
                cash += proceeds
            redeploy_pending = True
            redeploy_days_left = 0
            last_logged_tier = None
            # The reserve merges back into general cash; the post-defense
            # 21-day redeploy takes over from here.
            decel_reserve = 0.0
            tqqq_pending = 0.0
            one_x_pending = 0.0
            tqqq_batch_counter = 0
            one_x_batch_counter = 0

        if above_ma and defense_spy_value > 0:
            cash += defense_spy_value * (1 - cost_ratio)
            defense_spy_value = 0.0
            trades.append(
                TradeLogItem(
                    date=current.date,
                    action="sell",
                    symbol="SPYM",
                    ratio=0,
                    reason=f"QQQ가 {moving_average_days}일선을 회복해 방어용 SPYM을 재배치 대기 현금으로 전환",
                )
            )

        if above_ma and cash > 0:
            if redeploy_pending:
                redeploy_daily_amount = cash / REDEPLOY_DAYS
                redeploy_days_left = REDEPLOY_DAYS
                redeploy_pending = False
            if one_x_upfront_monthly and upfront_one_x_pending > 0:
                spend = min(upfront_one_x_pending, cash)
                one_x_value += spend * (1 - cost_ratio)
                cash -= spend
                upfront_one_x_pending -= spend
            tqqq_buy_ratio = daily_tqqq_buy_ratio(
                distance, base_tqqq_ratio, band_scale, decel_mid, decel_high, decel_stop
            )
            one_x_buy_ratio = min(base_one_x_ratio, max(0.0, 1 - tqqq_buy_ratio))
            total_buy_ratio = min(tqqq_buy_ratio + one_x_buy_ratio, 1.0)
            initial_deploy = initial_daily_deploy if initial_deploy_days_left > 0 else 0
            redeploy = redeploy_daily_amount if redeploy_days_left > 0 else 0
            reserve_deploy = 0.0
            if (
                reserve_redeploy_days > 0
                and decel_reserve > 0
                and deceleration_tier(distance) == 0
            ):
                # Disparity normalized: feed the carried reserve back in at
                # 1/N per day on top of the regular budget.
                reserve_deploy = min(decel_reserve / reserve_redeploy_days, decel_reserve)
            dip_boost = 0.0
            if (
                dip_buy_multiple > 0
                and prev_distance is not None
                and prev_distance - distance >= dip_trigger_drop
            ):
                # Sharp one-day disparity drop while still above the MA:
                # treat it as a discount and buy extra from cash.
                dip_boost = dip_buy_multiple * daily_contribution

            scheduled_buy_budget = (
                daily_contribution + initial_deploy + redeploy + reserve_deploy + dip_boost
            )
            buy_budget = min(cash, scheduled_buy_budget)

            if buy_budget > 0 and total_buy_ratio > 0:
                tqqq_buy = buy_budget * tqqq_buy_ratio
                if one_x_upfront_monthly:
                    # The regular contribution's 1x share was already bought
                    # on salary day; only redeploy/initial-deploy money still
                    # buys the 1x at the normal ratio.
                    non_contribution_budget = max(0.0, buy_budget - daily_contribution)
                    one_x_buy = non_contribution_budget * one_x_buy_ratio
                else:
                    one_x_buy = buy_budget * one_x_buy_ratio
                tier = deceleration_tier(distance)
                log_this_day = tier != last_logged_tier
                if tqqq_buy > 0 and log_this_day:
                    trades.append(
                        TradeLogItem(
                            date=current.date,
                            action="buy",
                            symbol=leveraged_symbol,
                            ratio=round(tqqq_buy_ratio * 100, 1),
                            reason=daily_accumulation_reason(distance, leveraged_symbol),
                        )
                    )
                if one_x_buy > 0 and log_this_day:
                    trades.append(
                        TradeLogItem(
                            date=current.date,
                            action="buy",
                            symbol=one_x_symbol,
                            ratio=round(one_x_buy_ratio * 100, 1),
                            reason=f"{leveraged_symbol} 과열 감속분을 1x 나스닥/코어 자산으로 적립",
                        )
                    )
                if log_this_day:
                    last_logged_tier = tier
                # Earmark at today's deceleration ratio; execute per batch
                # cadence. Pending money waits in cash (earns cash yield),
                # mirroring whole-share accumulation.
                tqqq_pending += tqqq_buy
                one_x_pending += one_x_buy
                tqqq_batch_counter += 1
                one_x_batch_counter += 1
                invested = 0.0
                if tqqq_batch_counter >= tqqq_batch_days and tqqq_pending > 0:
                    spend = min(tqqq_pending, cash)
                    tqqq_value += spend * (1 - cost_ratio)
                    cash -= spend
                    invested += spend
                    tqqq_pending = 0.0
                    tqqq_batch_counter = 0
                if one_x_batch_counter >= one_x_batch_days and one_x_pending > 0:
                    spend = min(one_x_pending, cash)
                    one_x_value += spend * (1 - cost_ratio)
                    cash -= spend
                    invested += spend
                    one_x_pending = 0.0
                    one_x_batch_counter = 0
                if reserve_redeploy_days > 0:
                    earmarked = tqqq_buy + one_x_buy
                    if tier == 0:
                        # Reserve being spent down (plus any same-day surplus).
                        decel_reserve = max(0.0, decel_reserve - reserve_deploy)
                    else:
                        # Track today's unspent remainder for later redeploy.
                        decel_reserve += max(0.0, buy_budget - earmarked)
                    decel_reserve = min(decel_reserve, cash)
                if initial_deploy_days_left > 0:
                    initial_deploy_days_left -= 1
                if redeploy_days_left > 0:
                    redeploy_days_left -= 1

        prev_distance = distance
        total_equity = cash + tqqq_value + one_x_value + defense_spy_value
        peak = max(peak, total_equity)
        position = "CASH"
        if defense_spy_value > 0:
            position = "SPYM+SGOV"
        elif tqqq_value > 0 and one_x_value > 0:
            position = f"{leveraged_symbol}+{one_x_symbol}"
        elif tqqq_value > 0:
            position = leveraged_symbol
        elif one_x_value > 0:
            position = one_x_symbol
        curve.append(
            EquityPoint(
                date=current.date,
                equity=round(total_equity, 2),
                drawdown=round((total_equity / peak - 1) * 100, 2),
                position=position,
                cash_flow=round(cash_flow, 2),
            )
        )
    return curve, trades


def daily_tqqq_buy_ratio(
    distance: float,
    base_tqqq_ratio: float,
    band_scale: float = 1.0,
    mid_factor: float = 0.65,
    high_factor: float = 0.30,
    stop_factor: float = 0.0,
) -> float:
    """Disparity-based deceleration of the daily TQQQ buy.

    band_scale/mid_factor/high_factor/stop_factor are exposed for
    rule-robustness sensitivity tests; production callers use the defaults.
    """
    if distance <= 0:
        return 0.0
    if distance < 0.10 * band_scale:
        return base_tqqq_ratio
    if distance < 0.20 * band_scale:
        return base_tqqq_ratio * mid_factor
    if distance < 0.30 * band_scale:
        return base_tqqq_ratio * high_factor
    return base_tqqq_ratio * stop_factor


def deceleration_tier(distance: float) -> int:
    if distance < 0.10:
        return 0
    if distance < 0.20:
        return 1
    if distance < 0.30:
        return 2
    return 3


def daily_accumulation_reason(distance: float, leveraged_symbol: str = "TQQQ") -> str:
    pct = distance * 100
    if distance < 0.10:
        return f"QQQ 200일선 위 +{pct:.1f}% 구간: 기본 7:3 적립 유지"
    if distance < 0.20:
        return f"QQQ 200일선 대비 +{pct:.1f}% 구간: {leveraged_symbol} 일일 매수 65%로 감속"
    if distance < 0.30:
        return f"QQQ 200일선 대비 +{pct:.1f}% 구간: 과열 대응으로 {leveraged_symbol} 일일 매수 30%로 감속"
    return f"QQQ 200일선 대비 +{pct:.1f}% 구간: {leveraged_symbol} 신규 적립 중지"


def simulate_staged_200ma_strategy(
    frames: list[BacktestFrame],
    initial_capital: float,
    target_symbol: str,
    target_ratio: float,
    one_x_ratio: float,
    one_x_symbol: str,
    daily_cash_return: float,
    cost_ratio: float,
    moving_average_days: int,
    monthly_contribution: float = 0,
    exit_band: float = 0.0,
    overheat_trim_distance: float = 0.25,
    defense_mode: str = "cash",
) -> tuple[list[EquityPoint], list[TradeLogItem]]:
    equity = initial_capital
    peak = equity
    position_ratio = 0.0
    curve: list[EquityPoint] = [starting_point(frames[0].date, equity, "CASH")]
    trades: list[TradeLogItem] = []
    buy_stage = 0
    staged_ratios = [0.30, 0.65, 1.00]
    daily_contribution = monthly_contribution / TRADING_DAYS_PER_MONTH if monthly_contribution > 0 else 0
    # Risk reductions must be recoverable; otherwise a single 50MA dip or
    # overheat trim permanently ratchets exposure down until the next full
    # MA200 reset (contradicts principle 2: participate above the line).
    dip_reduced = False
    overheat_trimmed = False

    for index in range(1, len(frames)):
        prev = frames[index - 1]
        current = frames[index]
        cash_flow = 0.0
        distance = prev.qqq / prev.sma200 - 1
        desired_ratio = position_ratio
        reason = ""
        below_exit_line = prev.qqq <= prev.sma200 * (1 + exit_band)

        if below_exit_line:
            desired_ratio = 0.0
            buy_stage = 0
            dip_reduced = False
            overheat_trimmed = False
            reason = f"QQQ가 {moving_average_days}일선 아래라 방어 전환"
        elif position_ratio > 0 and prev.sma50 and prev.qqq <= prev.sma50 * 0.99:
            if not dip_reduced:
                desired_ratio = min(position_ratio, target_ratio * 0.70)
                dip_reduced = True
                reason = "QQQ가 50일선 대비 -1% 이하로 이탈해 리스크 30% 축소"
        elif position_ratio >= target_ratio * 0.95 and distance >= overheat_trim_distance:
            if not overheat_trimmed:
                desired_ratio = min(position_ratio, target_ratio * 0.80)
                overheat_trimmed = True
                reason = f"QQQ 200일선 대비 +{overheat_trim_distance * 100:.0f}% 이상이라 수익 일부 회수"
        elif dip_reduced and prev.sma50 and prev.qqq >= prev.sma50 * 1.01:
            dip_reduced = False
            if buy_stage > 0:
                desired_ratio = target_ratio * staged_ratios[buy_stage - 1]
                reason = "QQQ가 50일선을 회복해 축소 전 비중으로 복귀"
        elif overheat_trimmed and distance < overheat_trim_distance - 0.05:
            overheat_trimmed = False
            if buy_stage > 0:
                desired_ratio = target_ratio * staged_ratios[buy_stage - 1]
                reason = (
                    f"200일선 이격이 +{(overheat_trim_distance - 0.05) * 100:.0f}% 아래로 완화돼 "
                    "회수 전 비중으로 복귀"
                )
        else:
            next_stage = buy_stage
            if buy_stage == 0 and distance > 0:
                next_stage = 1
                if distance >= 0.15:
                    desired_ratio = target_ratio * 0.15
                    reason = "1차 축소 매수: 200일선 위지만 이격 과다(+15% 이상)라 최소 참여만 유지"
                elif distance > 0.08:
                    desired_ratio = target_ratio * 0.15
                    reason = "1차 축소 매수: QQQ가 200일선 위지만 +8% 초과라 절반만 진입"
                else:
                    reason = "1차 매수: QQQ가 200일선 위이고 +8% 이하"
            elif buy_stage == 1 and second_buy_condition(prev, distance):
                next_stage = 2
                reason = "2차 매수: 20일선 눌림 또는 200일선 이격 완화"
            elif buy_stage == 2 and third_buy_condition(prev, distance):
                next_stage = 3
                reason = "3차 매수: 50일선 눌림 또는 200일선 대비 +5% 이하 이격 완화"

            if next_stage != buy_stage:
                buy_stage = next_stage
                if desired_ratio == position_ratio:
                    desired_ratio = target_ratio * staged_ratios[buy_stage - 1]
            elif not reason:
                desired_ratio = position_ratio

        if abs(desired_ratio - position_ratio) > 0.001:
            action = "buy" if desired_ratio > position_ratio else "sell"
            equity *= 1 - abs(desired_ratio - position_ratio) * cost_ratio
            trades.append(
                TradeLogItem(
                    date=current.date,
                    action=action,
                    symbol=target_symbol,
                    ratio=round(desired_ratio * 100, 1),
                    reason=reason or "분할 규칙에 따른 비중 조정",
                )
            )
            position_ratio = desired_ratio

        asset_return = price_return(prev, current, target_symbol)
        if below_exit_line and defense_mode == "hold_one_x":
            # The 1x sleeve stays invested through the downtrend.
            active_one_x_ratio = min(one_x_ratio, max(0.0, 1 - position_ratio))
        else:
            active_one_x_ratio = 0.0 if below_exit_line else min(one_x_ratio, max(0.0, 1 - position_ratio))
        cash_ratio = max(0.0, 1 - position_ratio - active_one_x_ratio)
        if below_exit_line and defense_mode == "spym_sgov_half":
            # Defensive posture: idle capital sits 50% SPYM / 50% SGOV-like cash.
            idle_return = 0.5 * price_return(prev, current, "SPY") + 0.5 * daily_cash_return
        else:
            idle_return = daily_cash_return
        day_return = (
            position_ratio * asset_return
            + active_one_x_ratio * price_return(prev, current, one_x_symbol)
            + cash_ratio * idle_return
        )
        equity *= 1 + day_return
        if daily_contribution:
            # Contributions join at the current allocation (pro-rata), so they
            # respect whatever ratio the staged rules currently allow.
            equity += daily_contribution
            cash_flow = daily_contribution
        peak = max(peak, equity)
        position_label = target_symbol if position_ratio > 0 else "CASH"
        if active_one_x_ratio > 0:
            position_label = f"{position_label}+{one_x_symbol}" if position_ratio > 0 else one_x_symbol
        elif below_exit_line and defense_mode == "spym_sgov_half" and position_ratio == 0:
            position_label = "SPYM+SGOV"
        curve.append(
            EquityPoint(
                date=current.date,
                equity=round(equity, 2),
                drawdown=round((equity / peak - 1) * 100, 2),
                position=position_label,
                cash_flow=round(cash_flow, 2),
            )
        )
    return curve, trades


def second_buy_condition(frame: BacktestFrame, distance: float) -> bool:
    if distance <= 0.08:
        return True
    if frame.sma20 and frame.qqq <= frame.sma20 * 1.01:
        return True
    return False


def third_buy_condition(frame: BacktestFrame, distance: float) -> bool:
    if frame.sma50 and frame.qqq <= frame.sma50 * 1.01:
        return False
    if distance <= 0.05:
        return True
    return bool(frame.sma50 and frame.qqq <= frame.sma50 * 1.02)


def simulate_buy_hold(
    frames: list[BacktestFrame],
    initial_capital: float,
    symbol: str,
    monthly_contribution: float = 0,
    cost_ratio: float = 0,
) -> tuple[list[EquityPoint], list[TradeLogItem]]:
    equity = initial_capital
    peak = equity
    curve: list[EquityPoint] = [starting_point(frames[0].date, equity, symbol)]
    trades: list[TradeLogItem] = []
    daily_contribution = monthly_contribution / TRADING_DAYS_PER_MONTH if monthly_contribution > 0 else 0
    for index in range(1, len(frames)):
        cash_flow = 0.0
        equity *= 1 + price_return(frames[index - 1], frames[index], symbol)
        if daily_contribution:
            # Routine contributions are cash flows, not strategy decisions,
            # so they are tracked via cash_flow instead of the trade log.
            equity += daily_contribution * (1 - cost_ratio)
            cash_flow = daily_contribution
        peak = max(peak, equity)
        curve.append(
            EquityPoint(
                date=frames[index].date,
                equity=round(equity, 2),
                drawdown=round((equity / peak - 1) * 100, 2),
                position=symbol,
                cash_flow=round(cash_flow, 2),
            )
        )
    return curve, trades


def starting_point(date: str, equity: float, position: str) -> EquityPoint:
    """Day-0 anchor so the first trading day's return is part of the metrics."""
    return EquityPoint(
        date=date,
        equity=round(equity, 2),
        drawdown=0.0,
        position=position,
        cash_flow=0.0,
    )


def price_return(prev: BacktestFrame, current: BacktestFrame, symbol: str) -> float:
    normalized = symbol.upper()
    if normalized in {"QQQ", "QQQM"}:
        field = "qqq"
    elif normalized in {"SPY", "SPYM", "VOO", "SPLG", "VTI"}:
        field = "spy"
    else:
        field = normalized.lower()
    prev_price = getattr(prev, field)
    current_price = getattr(current, field)
    return current_price / prev_price - 1
