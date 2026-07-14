from app.schemas.managed_strategy import ManagedStrategy, StrategyVersionAllocation
from app.schemas.strategy import HoldingInput, InvestorProfile, StrategyRecommendRequest


def _strategy_to_latest_recommend_request(strategy: ManagedStrategy) -> StrategyRecommendRequest:
    ratios = _allocation_map(strategy)
    holdings = [
        HoldingInput(
            symbol=allocation.symbol,
            name=allocation.name,
            amount=round(strategy.total_capital * allocation.target_ratio / 100),
            category=_category_for_symbol(allocation.symbol),
        )
        for allocation in strategy.plan.allocations
        if allocation.symbol.upper() != "CASH" and allocation.target_ratio >= 0.1
    ]
    cash = round(
        sum(
            strategy.total_capital * allocation.target_ratio / 100
            for allocation in strategy.plan.allocations
            if allocation.symbol.upper() == "CASH"
        )
    )
    risk_score = _infer_risk_score_for_latest_engine(strategy)
    return StrategyRecommendRequest(
        holdings=holdings,
        cash=max(cash, 0),
        market=strategy.market,
        use_ai=False,
        profile=InvestorProfile(
            risk_profile=_risk_profile_from_score(risk_score),
            risk_score=risk_score,

            target_count=max(2, min(5, len([ratio for ratio in ratios.values() if ratio >= 1]))),
            allow_tqqq=risk_score >= 45,
            prefer_200ma=True,
            min_cash_ratio=0 if risk_score >= 55 else 10,
            max_tqqq_ratio=_latest_max_tqqq_ratio(strategy, risk_score),
            max_semiconductor_ratio=20,
            max_single_position_ratio=80,
            goal="기존 저장 전략을 최신 TQQQ 200일선 철학 기준으로 재검토합니다.",
        ),
    )


def _infer_risk_score_for_latest_engine(strategy: ManagedStrategy) -> int:
    ratios = _allocation_map(strategy)
    tqqq = ratios.get("TQQQ", 0)
    qld = ratios.get("QLD", 0)
    cash_like = _cash_like_ratio(ratios)
    semi = sum(ratios.get(symbol, 0) for symbol in ("SMH", "SOXX", "ACE K반도체TOP2"))
    score = 55 + tqqq * 0.55 + qld * 0.35 + semi * 0.12 - cash_like * 0.12
    if tqqq >= 25:
        score += 8
    if qld >= 25 and tqqq <= 5:
        score += 5
    return int(round(_clamp(score, 35, 92)))


def _latest_max_tqqq_ratio(strategy: ManagedStrategy, risk_score: int) -> float:
    current = _allocation_ratio(strategy, "TQQQ")
    if risk_score >= 85:
        return max(current, 75)
    if risk_score >= 70:
        return max(current, 70)
    if risk_score >= 55:
        return max(current, 55)
    return max(current, 35)


def _risk_profile_from_score(score: int):
    if score >= 85:
        return "very_aggressive"
    if score >= 65:
        return "aggressive"
    if score >= 40:
        return "balanced"
    return "defensive"


def _category_for_symbol(symbol: str) -> str:
    symbol = symbol.upper()
    if symbol in {"TQQQ", "QLD"}:
        return "nasdaq_leverage"
    if symbol in {"QQQ", "QQQM"}:
        return "nasdaq"
    if symbol in {"SPYM", "VOO"}:
        return "broad_market"
    if symbol in {"SGOV", "BIL", "SHY", "IEF"}:
        return "bond"
    if symbol in {"SMH", "SOXX", "ACE K반도체TOP2"}:
        return "semiconductor"
    return "other"


def _philosophy_diff_reason(symbol: str, current: float, suggested: float, distance: float) -> str:
    delta = suggested - current
    if abs(delta) < 0.1:
        return "최신 철학에서도 현재 비중을 유지합니다."
    if symbol == "TQQQ":
        if delta > 0:
            return "리스크 허용도와 200일선 위치를 기준으로 공격 엔진 비중을 높입니다."
        return "과열도 또는 방어 필요성을 반영해 TQQQ 강도를 낮춥니다."
    if symbol in {"QQQ", "QQQM", "SPYM", "VOO"}:
        return "TQQQ를 전부 현금화하지 않고 1x 완충 자산으로 상승장 참여를 유지합니다."
    if symbol in {"SGOV", "BIL", "CASH"}:
        if distance > 0 and delta < 0:
            return "200일선 위에서는 과도한 대기자금을 줄이고 시장 참여 자산으로 이동합니다."
        return "방어 구간 또는 극단 과열에 대비한 대기/방어 자산입니다."
    if delta < 0:
        return "TQQQ 200일선 전략과 중복되거나 핵심성이 낮아 비중을 줄입니다."
    return "최신 철학 기준 보완 자산으로 일부 편입합니다."


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _allocation_ratio(strategy: ManagedStrategy, symbol: str) -> float:
    return sum(
        allocation.target_ratio
        for allocation in strategy.plan.allocations
        if allocation.symbol.upper() == symbol
    )


def _allocation_amount(strategy: ManagedStrategy, symbol: str) -> float:
    return sum(
        allocation.target_amount
        for allocation in strategy.plan.allocations
        if allocation.symbol.upper() == symbol
    )


def _one_x_buffer_ratio(strategy: ManagedStrategy) -> float:
    return sum(
        _allocation_ratio(strategy, symbol)
        for symbol in ("QQQ", "QQQM", "SPYM", "VOO", "SPLG")
    )


def _primary_one_x_symbol(strategy: ManagedStrategy) -> str:
    for symbol in ("QQQM", "QQQ", "SPYM", "VOO", "SPLG"):
        if _allocation_ratio(strategy, symbol) >= 0.1:
            return symbol
    return "QQQ"


def _allocation_map(strategy: ManagedStrategy) -> dict[str, float]:
    ratios: dict[str, float] = {}
    for allocation in strategy.plan.allocations:
        symbol = allocation.symbol.upper()
        ratios[symbol] = ratios.get(symbol, 0) + allocation.target_ratio
    return ratios


def _executed_amounts(strategy: ManagedStrategy) -> dict[str, float]:
    amounts: dict[str, float] = {}
    for entry in strategy.journal:
        if entry.entry_type not in {"buy", "sell", "rebalance"}:
            continue
        symbol = entry.symbol.upper()
        sign = -1 if entry.entry_type == "sell" else 1
        amounts[symbol] = amounts.get(symbol, 0) + sign * entry.amount
    return {symbol: max(amount, 0) for symbol, amount in amounts.items()}


def _cash_like_ratio(ratios: dict[str, float]) -> float:
    return sum(ratios.get(symbol, 0) for symbol in ("CASH", "SGOV", "BIL"))


def _set_cash_like_ratio(ratios: dict[str, float], target_cash: float) -> None:
    for symbol in ("SGOV", "BIL"):
        ratios[symbol] = 0
    ratios["CASH"] = max(target_cash, 0)


def _add_ratio(ratios: dict[str, float], symbol: str, value: float) -> None:
    ratios[symbol] = ratios.get(symbol, 0) + max(value, 0)


def _recommended_cash_floor(distance: float, tqqq_ratio: float) -> float:
    if distance <= 0:
        return 45
    if distance >= 15:
        return 35 if tqqq_ratio >= 20 else 30
    if distance >= 8:
        return 25
    return 15


def _reduce_growth_for_cash(ratios: dict[str, float], amount: float) -> None:
    remaining = amount
    for symbol in ("TQQQ", "QLD", "QQQ", "SPYM", "VOO"):
        available = max(ratios.get(symbol, 0), 0)
        cut = min(available, remaining)
        ratios[symbol] = available - cut
        remaining -= cut
        if remaining <= 0:
            break


def _normalize_map(ratios: dict[str, float]) -> dict[str, float]:
    positive = {symbol: max(value, 0) for symbol, value in ratios.items()}
    total = sum(positive.values())
    if total <= 0:
        return {"CASH": 100}
    return {symbol: value / total * 100 for symbol, value in positive.items() if value > 0.01}


def _version_allocations_from_plan(plan) -> list[StrategyVersionAllocation]:
    return [
        StrategyVersionAllocation(
            symbol=allocation.symbol,
            ratio=round(allocation.target_ratio, 1),
        )
        for allocation in plan.allocations
    ]


def _role_for_adjusted_symbol(symbol: str) -> str:
    return {
        "TQQQ": "공격 엔진",
        "QLD": "완충형 레버리지",
        "QQQ": "나스닥 기준 자산",
        "SPYM": "저비용 S&P 500 코어",
        "VOO": "광범위 코어",
        "CASH": "분할매수 대기",
        "SGOV": "현금성 대기자금",
        "BIL": "현금성 대기자금",
        "SHY": "단기채 완충",
        "IEF": "중기채 완충",
    }.get(symbol, "조정 자산")


def _adjustment_reason(symbol: str, delta: float, distance: float) -> str:
    if abs(delta) < 0.1:
        return "원 전략 비중을 유지합니다."
    direction = "늘립니다" if delta > 0 else "줄입니다"
    if symbol == "CASH":
        return f"사용자가 요청한 현금 목표에 맞춰 {direction}."
    if symbol == "TQQQ":
        if delta > 0 and distance >= 15:
            return "과열 구간에서는 TQQQ 증액을 권장하지 않습니다."
        return f"전략 공격성 조절을 위해 {direction}."
    if symbol in {"QQQ", "SPYM", "VOO"}:
        return f"TQQQ보다 완만한 코어 완충 자산으로 {direction}."
    return f"목표 현금 조정에 맞춰 {direction}."


