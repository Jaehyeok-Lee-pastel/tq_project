from collections import defaultdict
from math import sqrt

from app.schemas.backtest import (
    BacktestMetrics,
    BacktestRunRequest,
    EquityPoint,
    ProjectionScenario,
    RegimePerformance,
    TradeLogItem,
    YearlyReturn,
)
from app.services.backtesting.models import TRADING_DAYS_PER_YEAR, BacktestFrame, MarketDataset


def calculate_metrics(curve: list[EquityPoint], trades: list[TradeLogItem]) -> BacktestMetrics:
    if len(curve) < 2:
        raise ValueError("성과 지표 계산에 필요한 데이터가 부족합니다.")
    returns = adjusted_returns(curve)
    final_capital = curve[-1].equity
    years = max(len(curve) / TRADING_DAYS_PER_YEAR, 1 / TRADING_DAYS_PER_YEAR)
    total_return = compound_returns(returns) - 1
    cagr = (1 + total_return) ** (1 / years) - 1
    # Strategy risk metrics come from the cash-flow-adjusted return index;
    # the raw equity curve's drawdown is cushioned by contributions and would
    # understate what the strategy itself lost.
    max_drawdown, longest_dd_days = drawdown_stats(returns)
    yearly_returns = calculate_yearly_returns(curve)
    best_year = max((item.return_pct for item in yearly_returns), default=None)
    worst_year = min((item.return_pct for item in yearly_returns), default=None)

    return BacktestMetrics(
        final_capital=round(final_capital, 2),
        total_return=round(total_return * 100, 2),
        cagr=round(cagr * 100, 2),
        max_drawdown=round(max_drawdown * 100, 2),
        sharpe=sharpe_ratio(returns),
        sortino=sortino_ratio(returns),
        calmar=round(cagr / abs(max_drawdown), 2) if max_drawdown < 0 else None,
        win_rate=round(sum(1 for item in returns if item > 0) / len(returns) * 100, 2),
        trade_count=len(trades),
        best_year=best_year,
        worst_year=worst_year,
        longest_drawdown_days=longest_dd_days,
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


def sharpe_ratio(returns: list[float]) -> float | None:
    if len(returns) < 2:
        return None
    mean_return = sum(returns) / len(returns)
    variance = sum((item - mean_return) ** 2 for item in returns) / (len(returns) - 1)
    volatility = sqrt(variance)
    if volatility == 0:
        return None
    return round(mean_return / volatility * sqrt(TRADING_DAYS_PER_YEAR), 2)


def sortino_ratio(returns: list[float]) -> float | None:
    """Standard Sortino: downside deviation over ALL days with MAR=0.

    sqrt(mean(min(r, 0)^2)) — not the sample variance of only-negative days,
    which overstates downside volatility and understates the ratio.
    """
    if len(returns) < 2:
        return None
    mean_return = sum(returns) / len(returns)
    downside_squared = sum(min(item, 0.0) ** 2 for item in returns) / len(returns)
    downside_deviation = sqrt(downside_squared)
    if downside_deviation == 0:
        return None
    return round(mean_return / downside_deviation * sqrt(TRADING_DAYS_PER_YEAR), 2)


def drawdown_stats(returns: list[float]) -> tuple[float, int]:
    """Max drawdown and longest underwater streak of the TWR return index."""
    index_value = 1.0
    peak = 1.0
    max_drawdown = 0.0
    longest = 0
    current = 0
    for item in returns:
        index_value *= 1 + item
        peak = max(peak, index_value)
        drawdown = index_value / peak - 1
        max_drawdown = min(max_drawdown, drawdown)
        if drawdown < -1e-9:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return max_drawdown, longest


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
    # curve[i] corresponds to frames[i]; index 0 is the day-0 anchor with no
    # return, so regime buckets start from the first traded day.
    for index in range(1, len(curve)):
        frame = frames[index]
        prev_frame = frames[index - 1]
        equity_return = returns[index - 1] if index - 1 < len(returns) else 0.0
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
        base_annual_return = 0
        annualized_volatility = 0
    else:
        mean_return = sum(returns) / len(returns)
        variance = sum((item - mean_return) ** 2 for item in returns) / max(len(returns) - 1, 1)
        growth = compound_returns(returns)
        base_annual_return = growth ** (TRADING_DAYS_PER_YEAR / len(returns)) - 1
        annualized_volatility = sqrt(variance) * sqrt(TRADING_DAYS_PER_YEAR)

    yearly_contribution = request.monthly_contribution * 12
    total_contributions = yearly_contribution * request.projection_years
    scenarios = [
        (
            "bear",
            max(base_annual_return - annualized_volatility, -0.95),
            "과거 기하수익률에서 연환산 변동성을 차감한 보수 시나리오입니다.",
        ),
        ("base", base_annual_return, "과거 시간가중 기하수익률을 연율화한 기준 시나리오입니다."),
        (
            "bull",
            base_annual_return + annualized_volatility,
            "과거 기하수익률에 연환산 변동성을 더한 낙관 시나리오입니다.",
        ),
    ]
    output: list[ProjectionScenario] = []
    for name, annual_return, note in scenarios:
        growth = (1 + annual_return) ** request.projection_years
        ending = request.initial_capital * growth
        if yearly_contribution > 0:
            if abs(annual_return) < 1e-9:
                ending += total_contributions
            else:
                # Future value of an annual contribution stream.
                ending += yearly_contribution * ((growth - 1) / annual_return)
        output.append(
            ProjectionScenario(
                name=name,  # type: ignore[arg-type]
                annual_return=round(annual_return * 100, 2),
                ending_capital=round(ending, 2),
                profit=round(ending - request.initial_capital - total_contributions, 2),
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
    if metrics.cagr >= 35:
        notes.append(
            "연환산 수익률이 35% 이상으로 매우 높습니다. 합성 데이터 구간, 특정 상승장 편중, 세금·환율·추적오차를 반드시 함께 확인하세요."
        )
    if request.strategy in {"tqqq_200ma", "qld_200ma", "tqqq_daily_200ma"}:
        effective_defense = request.defense_mode or (
            "hold_one_x" if request.strategy == "tqqq_daily_200ma" else "cash"
        )
        defense_labels = {
            "cash": "200일선 아래에서는 방어 자금 전체가 SGOV/현금 수익률로 계산됩니다.",
            "spym_sgov_half": "200일선 아래에서는 방어 자금을 SPYM 50% + SGOV/현금 50%로 배치해 계산했습니다.",
            "hold_one_x": "200일선 아래에서도 1x 완충 자산은 계속 보유하는 방식으로 계산했습니다(방어는 TQQQ만).",
        }
        notes.append(f"방어 모드: {defense_labels[effective_defense]}")
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
        notes.append(
            "방어 매도로 확보한 현금은 200일선 회복 후 21거래일에 걸쳐 다시 분할 투입하도록 계산했습니다."
        )
        if (request.defense_mode or "hold_one_x") == "hold_one_x":
            notes.append(
                "1x 버퍼는 적립식 코어로서 200일선 아래에서도 보유를 유지합니다(신규 적립만 중단). "
                "대형 하락장에서는 1x 보유분의 낙폭이 그대로 반영되므로 MDD가 분할매수 전략보다 깊을 수 있습니다."
            )
        if request.monthly_contribution > 0:
            notes.append(
                f"월 {request.monthly_contribution:,.0f}원의 추가 투입을 일 단위로 나누어 반영한 현금흐름형 연구 백테스트입니다. "
                "단순 최종금액은 추가 납입액의 영향을 받으므로 CAGR/MDD와 함께 해석해야 합니다."
            )
    return notes


def build_data_notes(dataset: MarketDataset, curve: list[EquityPoint]) -> list[str]:
    notes = [
        "배당 재투자를 반영한 수정 종가(adjusted close) 기준으로 계산했습니다.",
        (
            "수익률은 USD 자산 기준입니다. 원/달러 환율 변동과 해외주식 양도소득세"
            "(연 250만원 공제 후 22%)는 반영되지 않았으며, 매매가 잦은 전략일수록 실제 세후 수익률과 차이가 커질 수 있습니다."
        ),
    ]
    period_start = curve[0].date if curve else ""
    if dataset.tqqq_synthetic_until and period_start <= dataset.tqqq_synthetic_until:
        notes.insert(
            0,
            (
                f"TQQQ의 {dataset.tqqq_synthetic_until} 이전 구간은 실제 상장 전이라 "
                "QQQ 일수익률 x3에 운용보수·차입비용을 차감한 합성 데이터로 계산했습니다. "
                "덕분에 2000-2002, 2008 급락장이 백테스트에 포함됩니다."
            ),
        )
    if dataset.qld_synthetic_until and period_start <= dataset.qld_synthetic_until:
        notes.insert(
            1 if dataset.tqqq_synthetic_until else 0,
            (
                f"QLD의 {dataset.qld_synthetic_until} 이전 구간은 QQQ 일수익률 x2 기반 합성 데이터입니다."
            ),
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


