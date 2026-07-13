from app.schemas.strategy import HoldingInput, MarketRegime


def classify_market(distance: float) -> MarketRegime:
    if distance <= 0:
        return "risk_off"
    if distance <= 10:
        return "normal_entry"
    if distance <= 15:
        return "reduced_entry"
    return "stretched_entry"


def risk_band(score: int) -> str:
    if score <= 20:
        return "방어형"
    if score <= 40:
        return "안정 성장형"
    if score <= 60:
        return "균형형"
    if score <= 80:
        return "공격형"
    return "초공격형"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def symbol_if_allowed(symbol: str, profile) -> str:
    return symbol if profile.allow_tqqq else "QQQ"


def ratio_map(*items: tuple[str, float]) -> dict[str, float]:
    ratios: dict[str, float] = {}
    for symbol, ratio in items:
        ratios[symbol] = ratios.get(symbol, 0) + ratio
    return ratios


def choose_semiconductor_symbol(holdings: list[HoldingInput], score: int) -> str:
    held_symbols = {holding.symbol.upper() for holding in holdings}
    if "ACE K반도체TOP2" in held_symbols and score >= 60:
        return "ACE K반도체TOP2"
    if score >= 70:
        return "SMH"
    return "SOXX"


def choose_one_x_symbol(score: int, holdings: list[HoldingInput]) -> str:
    """Choose one 1x companion to avoid stacking overlapping Nasdaq sleeves."""
    held_symbols = {holding.symbol.upper() for holding in holdings}
    if "QQQM" in held_symbols or "QQQ" in held_symbols:
        return "QQQM"
    if score >= 75:
        return "QQQM"
    return "SPYM"


def one_x_selection_reason(symbol: str, selected: str, score: int, holdings: list[HoldingInput]) -> str:
    held_symbols = {holding.symbol.upper() for holding in holdings}
    if symbol == "QQQ":
        if selected == "QQQM":
            return "QQQ와 QQQM은 같은 Nasdaq-100 1x 완충축입니다. 한 주 가격과 비용 효율 때문에 신규 설계에서는 QQQM을 우선합니다."
        return "QQQ는 기준 지표로는 핵심이지만, 현재 전략의 1x 완충 보유축으로는 선택하지 않았습니다."
    if symbol == "QQQM":
        if selected == "QQQM":
            if "QQQ" in held_symbols or "QQQM" in held_symbols:
                return "이미 Nasdaq-100 계열 1x 노출이 있어 같은 방향성을 유지하되 TQQQ보다 낮은 배수로 완충합니다."
            return "리스크 점수가 높아 TQQQ와 같은 Nasdaq-100 상승 참여를 유지하는 1x 완충축으로 선택합니다."
        return "나스닥 집중이 이미 충분하거나 리스크 완화가 더 중요해 이번 설계에서는 SPYM을 우선합니다."
    if symbol == "SPYM":
        if selected == "SPYM":
            return "TQQQ가 Nasdaq-100에 집중되어 있으므로 1x 완충축은 S&P 500으로 넓혀 단일 테마 쏠림을 낮춥니다."
        return "공격적 나스닥 참여가 더 중요해 이번 설계에서는 QQQM을 우선하고, SPYM은 분산 대안으로만 둡니다."
    return ""


def leverage_rotation_model(
    score: int,
    max_tqqq_ratio: float,
    regime: MarketRegime,
    distance: float,
) -> dict[str, float]:
    """TQQQ 200-day model: participate above MA200, defend below it.

    The model intentionally uses broad bands instead of curve-fit thresholds:
    - below MA200: SGOV/CASH defense
    - normal uptrend: control risk by moving between TQQQ and 1x equity
    - stretched uptrend: reduce TQQQ first, then allow SGOV only in extreme stretch
    """
    if regime == "risk_off":
        return {"tqqq": 0, "one_x": 0, "ballast": 0, "cash_like": 100}

    if score >= 85:
        tqqq = 85
    elif score >= 70:
        tqqq = 70
    elif score >= 55:
        tqqq = 50
    elif score >= 40:
        tqqq = 30
    else:
        tqqq = 0

    leverage_cap = tqqq_cap_from_disparity(distance, score)
    tqqq = min(tqqq, leverage_cap)

    if distance >= 50:
        cash_like = 60
    elif distance >= 40:
        cash_like = 35
    elif distance >= 30:
        cash_like = 15
    elif distance >= 20:
        cash_like = 5
    else:
        cash_like = 0 if score >= 55 else 10

    tqqq = round(min(tqqq, max_tqqq_ratio), 1)
    ballast = 0 if score >= 55 else 10
    one_x = max(0, 100 - tqqq - cash_like - ballast)
    return {
        "tqqq": tqqq,
        "one_x": round(one_x, 1),
        "ballast": round(ballast, 1),
        "cash_like": round(cash_like, 1),
    }


def target_effective_leverage_by_disparity(distance: float, score: int) -> float:
    """Research-informed leverage target from QQQ/MA200 distance.

    Effective leverage assumes the rest of the growth sleeve is held in a 1x
    ETF, so a 50% TQQQ + 50% 1x mix is roughly 2.0x.
    """
    if distance <= 0:
        return 0.0
    if distance < 10:
        base = 2.5
    elif distance < 20:
        base = 2.0
    elif distance < 30:
        base = 1.5
    else:
        base = 1.0

    if score >= 85 and distance < 30:
        base += 0.5
    elif score <= 45:
        base -= 0.5
    return round(clamp(base, 0.0, 3.0), 2)


def tqqq_cap_from_disparity(distance: float, score: int) -> float:
    if distance <= 0:
        return 0
    if distance >= 50:
        return 0
    if distance >= 40:
        return 5
    if distance >= 30:
        return 15
    effective = target_effective_leverage_by_disparity(distance, score)
    return round(clamp((effective - 1) / 2 * 100, 0, 85), 1)


def choose_growth_satellite_symbol(score: int) -> str:
    """Pick a broad-market companion, not another Nasdaq/semiconductor bet."""
    if score < 55:
        return "SPYM"
    if score >= 65:
        return "SPYM"
    return "VOO"


def choose_defense_symbol(score: int) -> str:
    if score <= 45:
        return "SGOV"
    if score <= 70:
        return "BIL"
    return "CASH"


def choose_ballast_symbol(score: int) -> str:
    return "SGOV" if score <= 65 else "BIL"


def recommended_min_cash(score: int) -> float:
    return round(clamp(45 - score * 0.35, 10, 45), 1)


def recommended_semi_ratio(score: int) -> float:
    return round(clamp(8 + score * 0.23, 10, 30), 1)


def recommended_satellite_ratio(score: int, max_semiconductor_ratio: float) -> float:
    if score < 55:
        return 0
    if score < 70:
        return round(clamp((score - 50) * 0.45, 0, 8), 1)
    return round(min(clamp((score - 55) * 0.45, 8, 18), max_semiconductor_ratio), 1)


def recommended_ballast_ratio(score: int) -> float:
    if score <= 30:
        return 25
    if score <= 55:
        return round(clamp(20 - (score - 30) * 0.35, 8, 20), 1)
    if score <= 75:
        return round(clamp(10 - (score - 55) * 0.25, 3, 10), 1)
    return 0


def recommended_core_ratio(
    score: int,
    tqqq_ratio: float,
    satellite_ratio: float,
    ballast_ratio: float,
    min_cash: float,
) -> float:
    if score <= 40:
        return clamp(35 + (40 - score) * 0.3, 30, 50)
    if score <= 65:
        return clamp(28 - (score - 40) * 0.3, 15, 30)
    spare = 100 - tqqq_ratio - satellite_ratio - ballast_ratio - min_cash
    return round(clamp(spare * 0.35, 5, 18), 1)


def recommended_tqqq_ratio(score: int, max_ratio: float, regime: MarketRegime) -> float:
    if regime == "risk_off" or score < 55:
        return 0
    base = clamp((score - 35) * 0.85, 10, max_ratio)
    if regime == "reduced_entry":
        base *= 0.78
    elif regime == "stretched_entry":
        base *= 0.62
    return round(min(base, max_ratio), 1)


def normalize_ratios(ratios: dict[str, float]) -> dict[str, float]:
    positive: dict[str, float] = {}
    for key, value in ratios.items():
        positive[key] = positive.get(key, 0) + max(value, 0)
    total = sum(positive.values())
    if total <= 0:
        return {"CASH": 100}
    return {key: value / total * 100 for key, value in positive.items()}


def allocation_ratio(ratios: dict[str, float], symbol: str) -> float:
    return ratios.get(symbol, 0)


def defensive_ratio(ratios: dict[str, float]) -> float:
    return sum(allocation_ratio(ratios, symbol) for symbol in ("CASH", "SGOV", "BIL", "SHY", "IEF", "TLT"))


def one_x_equity_ratio(ratios: dict[str, float]) -> float:
    return sum(allocation_ratio(ratios, symbol) for symbol in ("QQQ", "QQQM", "SPYM", "VOO", "SPLG"))
