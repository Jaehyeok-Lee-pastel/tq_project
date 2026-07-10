from collections import defaultdict
from dataclasses import dataclass
from math import sqrt

from app.api.routes.market import PriceRow, fetch_provider_history
from app.core.config import settings
from app.schemas.backtest import (
    BacktestMetrics,
    BacktestRunRequest,
    BacktestRunResponse,
    EquityPoint,
    ProjectionScenario,
    RegimePerformance,
    TradeLogItem,
    YearlyReturn,
)


@dataclass(frozen=True)
class BacktestFrame:
    date: str
    qqq: float
    tqqq: float
    qld: float
    sma200: float
    sma20: float | None = None
    sma50: float | None = None
    high20: float | None = None


STRATEGY_NAMES = {
    "qqq_buy_hold": "QQQ 장기 보유",
    "tqqq_buy_hold": "TQQQ 장기 보유",
    "tqqq_200ma": "QQQ 200일선 기반 TQQQ 전략",
    "qld_200ma": "QQQ 200일선 기반 QLD 전략",
    "tqqq_daily_200ma": "QQQ 200일선 기반 TQQQ 일일 적립 감속",
}


async def run_backtest(request: BacktestRunRequest) -> BacktestRunResponse:
    provider = settings.market_data_provider.lower()
    qqq_rows, tqqq_rows, qld_rows = await load_histories(provider)
    frames = build_frames(qqq_rows, tqqq_rows, qld_rows, request.moving_average_days)
    frames = filter_frames(frames, request.start_date, request.end_date)
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
    )


async def load_histories(provider: str) -> tuple[list[PriceRow], list[PriceRow], list[PriceRow]]:
    qqq_rows = await fetch_provider_history("QQQ", provider)
    tqqq_rows = await fetch_provider_history("TQQQ", provider)
    qld_rows = await fetch_provider_history("QLD", provider)
    return qqq_rows, tqqq_rows, qld_rows


def build_frames(
    qqq_rows: list[PriceRow],
    tqqq_rows: list[PriceRow],
    qld_rows: list[PriceRow],
    moving_average_days: int,
) -> list[BacktestFrame]:
    tqqq_by_date = {row.date: row.close for row in tqqq_rows}
    qld_by_date = {row.date: row.close for row in qld_rows}
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
            sma200=sma200,
            sma20=sma20,
            sma50=sma50,
            high20=high20,
        )
        for row, sma200, sma20, sma50, high20 in qqq_with_sma
        if row.date in tqqq_by_date and row.date in qld_by_date
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

    if request.strategy == "tqqq_daily_200ma":
        return simulate_daily_accumulation_200ma_strategy(
            frames=frames,
            initial_capital=request.initial_capital,
            monthly_contribution=request.monthly_contribution,
            base_tqqq_ratio=request.daily_base_tqqq_ratio / 100,
            base_one_x_ratio=request.daily_base_one_x_ratio / 100,
            one_x_symbol=request.one_x_symbol,
            initial_tqqq_value=request.initial_tqqq_value,
            initial_one_x_value=request.initial_one_x_value,
            initial_cash_value=request.initial_cash_value,
            daily_cash_return=((1 + request.cash_yield / 100) ** (1 / 252) - 1),
            cost_ratio=(request.fee_bps + request.slippage_bps) / 10_000,
            moving_average_days=request.moving_average_days,
        )

    target_symbol = "TQQQ" if request.strategy == "tqqq_200ma" else "QLD"
    target_ratio = (
        request.tqqq_target_ratio
        if target_symbol == "TQQQ"
        else request.qld_target_ratio
    )
    daily_cash_return = (1 + request.cash_yield / 100) ** (1 / 252) - 1
    cost_ratio = (request.fee_bps + request.slippage_bps) / 10_000
    if request.strategy in {"tqqq_200ma", "qld_200ma"}:
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
) -> tuple[list[EquityPoint], list[TradeLogItem]]:
    has_initial_holdings = any(
        value > 0 for value in (initial_tqqq_value, initial_one_x_value, initial_cash_value)
    )
    cash = initial_cash_value if has_initial_holdings else initial_capital
    tqqq_value = initial_tqqq_value if has_initial_holdings else 0.0
    one_x_value = initial_one_x_value if has_initial_holdings else 0.0
    starting_equity = cash + tqqq_value + one_x_value
    peak = starting_equity
    curve: list[EquityPoint] = []
    trades: list[TradeLogItem] = []
    below_ma_days = 0
    daily_contribution = monthly_contribution / 21 if monthly_contribution > 0 else 0
    initial_daily_deploy = 0 if has_initial_holdings else initial_capital / 21
    initial_deploy_days_left = 0 if has_initial_holdings else 21

    for index in range(1, len(frames)):
        prev = frames[index - 1]
        current = frames[index]
        tqqq_value *= 1 + price_return(prev, current, "TQQQ")
        one_x_value *= 1 + price_return(prev, current, one_x_symbol)
        cash *= 1 + daily_cash_return
        if daily_contribution:
            cash += daily_contribution
        cash_flow = daily_contribution

        distance = prev.qqq / prev.sma200 - 1
        above_ma = prev.qqq > prev.sma200
        below_ma_days = below_ma_days + 1 if not above_ma else 0

        if below_ma_days >= 2 and tqqq_value > 0:
            cash += tqqq_value * (1 - cost_ratio)
            trades.append(
                TradeLogItem(
                    date=current.date,
                    action="sell",
                    symbol="TQQQ",
                    ratio=0,
                    reason=f"QQQ가 {moving_average_days}일선 아래에서 2거래일 이상 마감해 TQQQ 전량 방어 전환",
                )
            )
            tqqq_value = 0.0

        if above_ma and cash > 0:
            tqqq_buy_ratio = daily_tqqq_buy_ratio(distance, base_tqqq_ratio)
            one_x_buy_ratio = min(base_one_x_ratio, max(0.0, 1 - tqqq_buy_ratio))
            total_buy_ratio = min(tqqq_buy_ratio + one_x_buy_ratio, 1.0)
            initial_deploy = initial_daily_deploy if initial_deploy_days_left > 0 else 0
            scheduled_buy_budget = daily_contribution + initial_deploy
            buy_budget = min(cash, scheduled_buy_budget)

            if buy_budget > 0 and total_buy_ratio > 0:
                tqqq_buy = buy_budget * tqqq_buy_ratio
                one_x_buy = buy_budget * one_x_buy_ratio
                if tqqq_buy > 0:
                    tqqq_value += tqqq_buy * (1 - cost_ratio)
                    trades.append(
                        TradeLogItem(
                            date=current.date,
                            action="buy",
                            symbol="TQQQ",
                            ratio=round(tqqq_buy_ratio * 100, 1),
                            reason=daily_accumulation_reason(distance),
                        )
                    )
                if one_x_buy > 0:
                    one_x_value += one_x_buy * (1 - cost_ratio)
                    trades.append(
                        TradeLogItem(
                            date=current.date,
                            action="buy",
                            symbol=one_x_symbol,
                            ratio=round(one_x_buy_ratio * 100, 1),
                            reason="TQQQ 과열 감속분을 1x 나스닥/코어 자산으로 적립",
                        )
                    )
                cash -= buy_budget
                if initial_deploy_days_left > 0:
                    initial_deploy_days_left -= 1

        total_equity = cash + tqqq_value + one_x_value
        peak = max(peak, total_equity)
        position = "CASH"
        if tqqq_value > 0 and one_x_value > 0:
            position = f"TQQQ+{one_x_symbol}"
        elif tqqq_value > 0:
            position = "TQQQ"
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


def daily_tqqq_buy_ratio(distance: float, base_tqqq_ratio: float) -> float:
    if distance <= 0:
        return 0.0
    if distance < 0.10:
        return base_tqqq_ratio
    if distance < 0.20:
        return base_tqqq_ratio * 0.65
    if distance < 0.30:
        return base_tqqq_ratio * 0.30
    return 0.0


def daily_accumulation_reason(distance: float) -> str:
    pct = distance * 100
    if distance < 0.10:
        return f"QQQ 200일선 위 +{pct:.1f}% 구간: 기본 7:3 적립 유지"
    if distance < 0.20:
        return f"QQQ 200일선 대비 +{pct:.1f}% 구간: TQQQ 일일 매수 65%로 감속"
    if distance < 0.30:
        return f"QQQ 200일선 대비 +{pct:.1f}% 구간: 과열 대응으로 TQQQ 일일 매수 30%로 감속"
    return f"QQQ 200일선 대비 +{pct:.1f}% 구간: TQQQ 신규 적립 중지"


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
) -> tuple[list[EquityPoint], list[TradeLogItem]]:
    equity = initial_capital
    peak = equity
    position_ratio = 0.0
    curve: list[EquityPoint] = []
    trades: list[TradeLogItem] = []
    buy_stage = 0
    staged_ratios = [0.30, 0.65, 1.00]
    daily_contribution = monthly_contribution / 21 if monthly_contribution > 0 else 0

    for index in range(1, len(frames)):
        prev = frames[index - 1]
        current = frames[index]
        cash_flow = 0.0
        distance = prev.qqq / prev.sma200 - 1
        desired_ratio = position_ratio
        reason = ""

        if prev.qqq <= prev.sma200:
            desired_ratio = 0.0
            buy_stage = 0
            reason = f"QQQ가 {moving_average_days}일선 아래라 방어 전환"
        elif position_ratio > 0 and prev.sma50 and prev.qqq <= prev.sma50 * 0.99:
            desired_ratio = min(position_ratio, target_ratio * 0.70)
            reason = "QQQ가 50일선 대비 -1% 이하로 이탈해 리스크 30% 축소"
        elif position_ratio >= target_ratio * 0.95 and distance >= 0.25:
            desired_ratio = min(position_ratio, target_ratio * 0.80)
            reason = "QQQ 200일선 대비 +25% 이상이라 수익 일부 회수"
        else:
            next_stage = buy_stage
            if buy_stage == 0 and 0 < distance < 0.15:
                next_stage = 1
                if distance > 0.08:
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
        active_one_x_ratio = 0.0 if prev.qqq <= prev.sma200 else min(one_x_ratio, max(0.0, 1 - position_ratio))
        cash_ratio = max(0.0, 1 - position_ratio - active_one_x_ratio)
        day_return = (
            position_ratio * asset_return
            + active_one_x_ratio * price_return(prev, current, one_x_symbol)
            + cash_ratio * daily_cash_return
        )
        equity *= 1 + day_return
        if daily_contribution:
            equity += daily_contribution
            cash_flow = daily_contribution
        peak = max(peak, equity)
        position_label = target_symbol if position_ratio > 0 else "CASH"
        if active_one_x_ratio > 0:
            position_label = f"{position_label}+{one_x_symbol}" if position_ratio > 0 else one_x_symbol
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
    curve: list[EquityPoint] = []
    trades: list[TradeLogItem] = []
    daily_contribution = monthly_contribution / 21 if monthly_contribution > 0 else 0
    for index in range(1, len(frames)):
        cash_flow = 0.0
        equity *= 1 + price_return(frames[index - 1], frames[index], symbol)
        if daily_contribution:
            equity += daily_contribution * (1 - cost_ratio)
            cash_flow = daily_contribution
            trades.append(
                TradeLogItem(
                    date=frames[index].date,
                    action="buy",
                    symbol=symbol,
                    ratio=100,
                    reason="월 추가금을 거래일 단위로 나누어 장기보유 전략에 적립",
                )
            )
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


def price_return(prev: BacktestFrame, current: BacktestFrame, symbol: str) -> float:
    if symbol.upper() in {"QQQ", "QQQM", "SPYM", "VOO", "SPLG"}:
        symbol = "QQQ"
    prev_price = getattr(prev, symbol.lower())
    current_price = getattr(current, symbol.lower())
    return current_price / prev_price - 1


def calculate_metrics(curve: list[EquityPoint], trades: list[TradeLogItem]) -> BacktestMetrics:
    if len(curve) < 2:
        raise ValueError("성과 지표 계산에 필요한 데이터가 부족합니다.")
    returns = adjusted_returns(curve)
    final_capital = curve[-1].equity
    years = max(len(curve) / 252, 1 / 252)
    total_return = compound_returns(returns) - 1
    cagr = (1 + total_return) ** (1 / years) - 1
    max_drawdown = min(point.drawdown for point in curve) / 100
    yearly_returns = calculate_yearly_returns(curve)
    best_year = max((item.return_pct for item in yearly_returns), default=None)
    worst_year = min((item.return_pct for item in yearly_returns), default=None)

    return BacktestMetrics(
        final_capital=round(final_capital, 2),
        total_return=round(total_return * 100, 2),
        cagr=round(cagr * 100, 2),
        max_drawdown=round(max_drawdown * 100, 2),
        sharpe=ratio_metric(returns, downside_only=False),
        sortino=ratio_metric(returns, downside_only=True),
        calmar=round(cagr / abs(max_drawdown), 2) if max_drawdown < 0 else None,
        win_rate=round(sum(1 for item in returns if item > 0) / len(returns) * 100, 2),
        trade_count=len(trades),
        best_year=best_year,
        worst_year=worst_year,
        longest_drawdown_days=longest_drawdown(curve),
    )


def adjusted_returns(curve: list[EquityPoint]) -> list[float]:
    returns: list[float] = []
    for index in range(1, len(curve)):
        previous = curve[index - 1].equity
        if previous <= 0:
            returns.append(0)
            continue
        returns.append((curve[index].equity - curve[index].cash_flow) / previous - 1)
    return returns


def compound_returns(returns: list[float]) -> float:
    value = 1.0
    for item in returns:
        value *= 1 + item
    return value


def ratio_metric(returns: list[float], downside_only: bool) -> float | None:
    if not returns:
        return None
    mean_return = sum(returns) / len(returns)
    sample = [item for item in returns if item < 0] if downside_only else returns
    if len(sample) < 2:
        return None
    variance = sum((item - mean_return) ** 2 for item in sample) / (len(sample) - 1)
    volatility = sqrt(variance)
    if volatility == 0:
        return None
    return round(mean_return / volatility * sqrt(252), 2)


def longest_drawdown(curve: list[EquityPoint]) -> int:
    longest = 0
    current = 0
    for point in curve:
        if point.drawdown < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def calculate_yearly_returns(curve: list[EquityPoint]) -> list[YearlyReturn]:
    by_year: dict[int, list[float]] = defaultdict(list)
    returns = adjusted_returns(curve)
    for index, item in enumerate(returns, start=1):
        by_year[int(curve[index].date[:4])].append(item)
    return [
        YearlyReturn(
            year=year,
            return_pct=round((compound_returns(items) - 1) * 100, 2),
        )
        for year, items in sorted(by_year.items())
        if items
    ]


def calculate_regime_performance(
    frames: list[BacktestFrame],
    curve: list[EquityPoint],
) -> list[RegimePerformance]:
    buckets: dict[str, list[tuple[BacktestFrame, float]]] = {
        "uptrend": [],
        "downtrend": [],
        "shock": [],
    }
    returns = adjusted_returns(curve)
    for index, point in enumerate(curve):
        frame = frames[index + 1]
        prev_frame = frames[index]
        equity_return = returns[index - 1] if index > 0 and index - 1 < len(returns) else 0.0
        qqq_return = frame.qqq / prev_frame.qqq - 1
        regime = (
            "shock"
            if qqq_return <= -0.025
            else "uptrend"
            if frame.qqq >= frame.sma200
            else "downtrend"
        )
        buckets[regime].append((frame, equity_return))

    labels = {
        "uptrend": "QQQ 장기선 위",
        "downtrend": "QQQ 장기선 아래",
        "shock": "QQQ 급락일",
    }
    output: list[RegimePerformance] = []
    for regime, rows in buckets.items():
        if not rows:
            output.append(
                RegimePerformance(
                    regime=regime,  # type: ignore[arg-type]
                    label=labels[regime],
                    days=0,
                    return_pct=0,
                    win_rate=0,
                    max_drawdown=0,
                )
            )
            continue
        regime_returns = [row[1] for row in rows]
        equity_index = 1.0
        peak = 1.0
        max_drawdown = 0.0
        for item in regime_returns:
            equity_index *= 1 + item
            peak = max(peak, equity_index)
            max_drawdown = min(max_drawdown, equity_index / peak - 1)
        output.append(
            RegimePerformance(
                regime=regime,  # type: ignore[arg-type]
                label=labels[regime],
                days=len(rows),
                return_pct=round((compound_returns(regime_returns) - 1) * 100, 2),
                win_rate=round(sum(1 for item in regime_returns if item > 0) / len(regime_returns) * 100, 2),
                max_drawdown=round(max_drawdown * 100, 2),
            )
        )
    return output


def build_projection(
    request: BacktestRunRequest,
    curve: list[EquityPoint],
) -> list[ProjectionScenario]:
    returns = adjusted_returns(curve)
    if not returns:
        annualized_mean = 0
        annualized_volatility = 0
    else:
        mean_return = sum(returns) / len(returns)
        variance = sum((item - mean_return) ** 2 for item in returns) / max(len(returns) - 1, 1)
        annualized_mean = mean_return * 252
        annualized_volatility = sqrt(variance) * sqrt(252)

    scenarios = [
        (
            "bear",
            annualized_mean - annualized_volatility,
            "과거 변동성을 반영한 보수 시나리오입니다.",
        ),
        ("base", annualized_mean, "과거 일평균 수익률을 단순 연율화한 기준 시나리오입니다."),
        (
            "bull",
            annualized_mean + annualized_volatility,
            "과거 변동성을 반영한 낙관 시나리오입니다.",
        ),
    ]
    output: list[ProjectionScenario] = []
    for name, annual_return, note in scenarios:
        ending = request.initial_capital * (1 + annual_return) ** request.projection_years
        output.append(
            ProjectionScenario(
                name=name,  # type: ignore[arg-type]
                annual_return=round(annual_return * 100, 2),
                ending_capital=round(ending, 2),
                profit=round(ending - request.initial_capital, 2),
                note=note,
            )
        )
    return output


def build_interpretation(
    metrics: BacktestMetrics,
    benchmark: BacktestMetrics,
    request: BacktestRunRequest,
) -> list[str]:
    notes = [
        f"선택 전략의 CAGR은 {metrics.cagr:.2f}%, 최대낙폭은 {metrics.max_drawdown:.2f}%입니다.",
        (
            "QQQ 장기 보유 대비 총수익률 차이는 "
            f"{metrics.total_return - benchmark.total_return:.2f}%p입니다."
        ),
        "미래 모의 수익은 예측이 아니라 과거 수익률과 변동성을 이용한 시나리오입니다.",
    ]
    if request.strategy == "tqqq_buy_hold":
        notes.append("TQQQ 장기 보유는 상승장 탄력은 크지만 손실 구간의 낙폭도 매우 큽니다.")
    if request.strategy in {"tqqq_200ma", "qld_200ma"}:
        notes.append("QQQ 200일선 기반 전략은 급락 방어를 노리지만 횡보장에서는 잦은 매매가 약점입니다.")
        if request.one_x_target_ratio > 0:
            notes.append(
                f"저장 전략의 1x 완충 비중 {request.one_x_target_ratio:.1f}%는 200일선 위에서 "
                f"{request.one_x_symbol} 기준 시장참여 수익으로 반영하고, 200일선 아래에서는 방어자산으로 전환해 계산했습니다."
            )
    if request.strategy == "tqqq_daily_200ma":
        notes.append(
            "일일 적립 감속 전략은 QQQ가 200일선 위에 있을 때만 적립하고, 이격도가 커질수록 TQQQ 신규 매수 비중을 줄입니다."
        )
        if request.monthly_contribution > 0:
            notes.append(
                f"월 {request.monthly_contribution:,.0f}원의 추가 투입을 일 단위로 나누어 반영한 현금흐름형 연구 백테스트입니다. "
                "단순 최종금액은 추가 납입액의 영향을 받으므로 CAGR/MDD와 함께 해석해야 합니다."
            )
    return notes


def downsample_curve(curve: list[EquityPoint], max_points: int = 260) -> list[EquityPoint]:
    if len(curve) <= max_points:
        return curve
    step = max(len(curve) // max_points, 1)
    sampled = curve[::step]
    if sampled[-1].date != curve[-1].date:
        sampled.append(curve[-1])
    return sampled
