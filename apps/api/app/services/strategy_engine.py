from dataclasses import dataclass

from app.schemas.strategy import (
    CandidateOpinion,
    CoachReport,
    ConfidenceBreakdown,
    HoldingInput,
    MarketRegime,
    PortfolioAllocation,
    RiskMetric,
    SplitStep,
    StrategyPlan,
    StrategyRecommendRequest,
    StrategyRecommendResponse,
    StrategyScores,
    TradeAction,
)


@dataclass(frozen=True)
class CandidateAsset:
    symbol: str
    name: str
    category: str
    role: str
    risk_weight: float
    return_weight: float
    min_risk_score: int
    max_ratio: float
    stance: str
    reason: str


CANDIDATES: dict[str, CandidateAsset] = {
    "TQQQ": CandidateAsset(
        "TQQQ",
        "ProShares UltraPro QQQ",
        "nasdaq_leverage",
        "공격 엔진",
        1.45,
        1.20,
        55,
        50,
        "core",
        "QQQ 200일선 기반 TQQQ 전략의 핵심 후보입니다. 단, 진입 위치와 분할 규칙이 필수입니다.",
    ),
    "QLD": CandidateAsset(
        "QLD",
        "ProShares Ultra QQQ",
        "nasdaq_leverage",
        "완충형 레버리지",
        0.95,
        0.75,
        35,
        55,
        "core",
        "TQQQ보다 완만한 2배 나스닥 레버리지 후보입니다.",
    ),
    "QQQ": CandidateAsset(
        "QQQ",
        "Invesco QQQ Trust",
        "nasdaq",
        "나스닥 기준 자산",
        0.55,
        0.45,
        0,
        70,
        "core",
        "레버리지 강도를 낮출 때 중심축으로 쓰기 좋은 기준 후보입니다.",
    ),
    "QQQM": CandidateAsset(
        "QQQM",
        "Invesco NASDAQ 100 ETF",
        "nasdaq",
        "나스닥 1x 완충 자산",
        0.55,
        0.45,
        0,
        70,
        "core",
        "TQQQ와 같은 Nasdaq-100 방향성은 유지하되 3배 레버리지 위험을 1배로 낮추는 완충 후보입니다.",
    ),
    "SMH": CandidateAsset(
        "SMH",
        "VanEck Semiconductor ETF",
        "semiconductor",
        "미국 반도체 위성",
        0.75,
        0.65,
        45,
        30,
        "satellite",
        "반도체 노출을 미국 대형주 중심으로 가져가는 위성 후보입니다.",
    ),
    "SOXX": CandidateAsset(
        "SOXX",
        "iShares Semiconductor ETF",
        "semiconductor",
        "반도체 위성",
        0.70,
        0.60,
        40,
        30,
        "satellite",
        "반도체 업종 노출을 분산해서 가져가는 대표 ETF 후보입니다.",
    ),
    "ACE K반도체TOP2": CandidateAsset(
        "ACE K반도체TOP2",
        "ACE K반도체TOP2",
        "semiconductor",
        "한국 반도체 집중",
        0.80,
        0.65,
        55,
        25,
        "satellite",
        "한국 반도체 대형주 집중 후보입니다. TQQQ/QLD와 함께 들면 기술주 쏠림이 커집니다.",
    ),
    "VOO": CandidateAsset(
        "VOO",
        "Vanguard S&P 500 ETF",
        "broad_market",
        "광범위 지수 완충",
        0.35,
        0.32,
        0,
        50,
        "defense",
        "공격 비중을 낮출 때 포트폴리오를 넓혀주는 완충 후보입니다.",
    ),
    "SPYM": CandidateAsset(
        "SPYM",
        "SPDR Portfolio S&P 500 ETF",
        "broad_market",
        "저비용 S&P 500 코어",
        0.34,
        0.32,
        0,
        50,
        "defense",
        "낮은 비용으로 S&P 500을 보유해 TQQQ 전략의 계좌 변동성을 낮추는 코어 후보입니다.",
    ),
    "SGOV": CandidateAsset(
        "SGOV",
        "iShares 0-3 Month Treasury Bond ETF",
        "cash_like",
        "현금성 대기 자금",
        0.05,
        0.05,
        0,
        80,
        "defense",
        "분할매수 대기자금과 방어 비중을 표현하기 좋은 단기채 후보입니다.",
    ),
    "BIL": CandidateAsset(
        "BIL",
        "SPDR Bloomberg 1-3 Month T-Bill ETF",
        "cash_like",
        "분할매수 대기자금",
        0.05,
        0.05,
        0,
        80,
        "defense",
        "TQQQ 분할매수 대기자금을 짧은 만기 국채 성격으로 보관하는 후보입니다.",
    ),
    "SHY": CandidateAsset(
        "SHY",
        "iShares 1-3 Year Treasury Bond ETF",
        "short_bond",
        "단기채 완충",
        0.12,
        0.10,
        0,
        60,
        "defense",
        "현금보다 약간 더 채권 성격을 가져가되 금리 민감도는 낮게 두는 완충 후보입니다.",
    ),
    "IEF": CandidateAsset(
        "IEF",
        "iShares 7-10 Year Treasury Bond ETF",
        "intermediate_bond",
        "중기채 완충",
        0.25,
        0.18,
        0,
        45,
        "defense",
        "공격 전략의 변동성을 낮추기 위한 중기 국채 완충 후보입니다.",
    ),
    "TLT": CandidateAsset(
        "TLT",
        "iShares 20+ Year Treasury Bond ETF",
        "long_bond",
        "장기채 위성",
        0.45,
        0.25,
        35,
        30,
        "watch",
        "주식 급락 방어를 기대할 수 있지만 금리 민감도가 커서 소액 위성으로만 적합합니다.",
    ),
    "CASH": CandidateAsset(
        "CASH",
        "현금/MMF/단기채",
        "cash_like",
        "분할매수 대기",
        0.00,
        0.00,
        0,
        80,
        "defense",
        "급락과 200일선 이탈에 대응하기 위한 실행 여력입니다.",
    ),
}

ALIASES = {
    "ACEK반도체TOP2": "ACE K반도체TOP2",
    "ACE K반도체 TOP2": "ACE K반도체TOP2",
    "K반도체TOP2": "ACE K반도체TOP2",
    "SOLTOP2": "ACE K반도체TOP2",
    "SOL TOP2": "ACE K반도체TOP2",
}
SEMICONDUCTOR_KEYWORDS = ("반도체", "semiconductor", "semi", "top2", "soxx", "smh", "ace")
NASDAQ_LEVERAGED = {"TQQQ", "QLD"}


def recommend_strategy(request: StrategyRecommendRequest) -> StrategyRecommendResponse:
    holdings = normalize_holdings(request.holdings)
    total = request.cash + sum(holding.amount for holding in holdings)
    if total <= 0:
        total = 1

    distance = (request.market.qqq_close / request.market.qqq_sma200 - 1) * 100
    regime = classify_market(distance)
    diagnosis = diagnose_current_portfolio(holdings, request.cash, total, distance)
    opinions = build_candidate_opinions(request, regime)
    plans = build_plans(request, holdings, total, distance, regime)
    plans.sort(key=lambda plan: plan.scores.fit_score, reverse=True)
    coach_report = build_rule_based_report(
        plans[0],
        diagnosis,
        regime,
        distance,
        request.profile.risk_score,
    )

    return StrategyRecommendResponse(
        total_capital=total,
        market_regime=regime,
        qqq_distance_from_200ma=round(distance, 2),
        current_diagnosis=diagnosis,
        candidate_opinions=opinions,
        plans=plans,
        coach_report=coach_report,
        ai_used=False,
    )


def normalize_holdings(holdings: list[HoldingInput]) -> list[HoldingInput]:
    normalized: list[HoldingInput] = []
    for holding in holdings:
        symbol = normalize_symbol(holding.symbol)
        asset = CANDIDATES.get(symbol)
        normalized.append(
            HoldingInput(
                symbol=symbol,
                name=holding.name or asset.name if asset else holding.name,
                amount=holding.amount,
                category=holding.category or asset.category if asset else holding.category,
            )
        )
    return normalized


def normalize_symbol(symbol: str) -> str:
    compact = symbol.strip().upper().replace(" ", "")
    return ALIASES.get(compact, symbol.strip().upper())


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


def diagnose_current_portfolio(
    holdings: list[HoldingInput],
    cash: float,
    total: float,
    distance: float,
) -> list[str]:
    leveraged = sum(item.amount for item in holdings if item.symbol.upper() in NASDAQ_LEVERAGED)
    semiconductor = sum(item.amount for item in holdings if is_semiconductor(item))
    unknown = [item.symbol for item in holdings if item.symbol.upper() not in CANDIDATES]
    cash_ratio = cash / total * 100
    leveraged_ratio = leveraged / total * 100
    semiconductor_ratio = semiconductor / total * 100

    notes = [
        f"현재 현금 비중은 {cash_ratio:.1f}%입니다.",
        f"QLD/TQQQ 같은 나스닥 레버리지 노출은 약 {leveraged_ratio:.1f}%입니다.",
        f"반도체 집중 노출은 약 {semiconductor_ratio:.1f}%입니다.",
    ]
    if unknown:
        notes.append(
            f"{', '.join(unknown)}은 검증 후보군 밖의 자산이라 "
            "기본 추천에서는 제외 후보로 평가합니다."
        )
    if cash_ratio < 10:
        notes.append("공격성은 높지만 200일선 이탈에 대응할 현금 여력이 부족합니다.")
    if leveraged_ratio + semiconductor_ratio >= 80:
        notes.append("포트폴리오가 나스닥, AI, 반도체 상승 국면에 강하게 묶여 있습니다.")
    if distance > 15:
        notes.append("QQQ가 200일선보다 15% 이상 높아 TQQQ 신규 대매수보다 분할 진입이 적합합니다.")
    elif distance <= 0:
        notes.append("QQQ가 200일선 아래라 TQQQ 신규 진입보다 방어 모드가 우선입니다.")
    else:
        notes.append("QQQ가 200일선 위라 TQQQ 전략을 이용할 수 있는 추세 구간입니다.")
    return notes


def build_candidate_opinions(
    request: StrategyRecommendRequest,
    regime: MarketRegime,
) -> list[CandidateOpinion]:
    score = request.profile.risk_score
    symbols = ["TQQQ", "QLD", "QQQ", "SPYM", "VOO", "SGOV", "BIL", "SHY", "IEF", "TLT", "SMH", "SOXX", "ACE K반도체TOP2"]
    opinions: list[CandidateOpinion] = []
    for symbol in symbols:
        asset = CANDIDATES[symbol]
        stance = asset.stance
        reason = asset.reason
        if (
            symbol == "TQQQ"
            and (not request.profile.allow_tqqq or score < 55 or regime == "risk_off")
        ):
            stance = "watch"
            reason = "지금은 TQQQ를 핵심 비중으로 두기보다 조건 충족 시 분할 진입 후보로 둡니다."
        if symbol in {"SMH", "SOXX", "ACE K반도체TOP2"}:
            stance = "watch"
            reason = "검토했지만 TQQQ/QLD와 성장주·AI·나스닥 베타가 겹쳐 기본 추천에서는 제외합니다."
        opinions.append(
            CandidateOpinion(
                symbol=symbol,
                name=asset.name,
                stance=stance,  # type: ignore[arg-type]
                reason=reason,
            )
        )
    return opinions


def build_plans(
    request: StrategyRecommendRequest,
    holdings: list[HoldingInput],
    total: float,
    distance: float,
    regime: MarketRegime,
) -> list[StrategyPlan]:
    profile = request.profile
    score = profile.risk_score
    allocation_model = leverage_rotation_model(score, profile.max_tqqq_ratio, regime, distance)
    min_cash = allocation_model["cash_like"]
    tqqq_base = allocation_model["tqqq"]
    if not profile.allow_tqqq:
        tqqq_base = 0

    defense_symbol = choose_defense_symbol(score)
    ballast_symbol = choose_ballast_symbol(score)
    satellite_symbol = choose_growth_satellite_symbol(score)
    satellite_ratio = 0
    ballast_ratio = allocation_model["ballast"]
    one_x_ratio = allocation_model["one_x"]

    core_symbol = choose_one_x_symbol(score, holdings)
    core_ratio = one_x_ratio
    tqqq_cash = max(0, 100 - tqqq_base - core_ratio - satellite_ratio - ballast_ratio)
    tqqq_plan = make_plan(
        request=request,
        holdings=holdings,
        total=total,
        plan_id="tqqq_200ma_coach",
        title="TQQQ 200일선 레버리지 조절형",
        summary=(
            "QQQ 200일선 위에서는 SGOV/현금을 과도하게 들기보다 TQQQ와 1x ETF로 시장 참여를 유지하고, "
            "과열 구간에서는 TQQQ를 1x 또는 SGOV로 낮추는 전략입니다."
        ),
        ratios={
            symbol_if_allowed("TQQQ", profile): tqqq_base,
            core_symbol: core_ratio,
            satellite_symbol: satellite_ratio,
            ballast_symbol: ballast_ratio,
            defense_symbol: tqqq_cash,
        },
        distance=distance,
        regime=regime,
    )

    qld_ratio = clamp(18 + score * 0.32, 20, 55)
    qld_ratio = min(qld_ratio, profile.max_single_position_ratio)
    qld_core = clamp(18 + (70 - score) * 0.25, 8, 35)
    qld_satellite = min(satellite_ratio, 12)
    qld_ballast = recommended_ballast_ratio(max(score - 10, 0))
    qld_cash = max(min_cash, 100 - qld_ratio - qld_core - qld_satellite - qld_ballast)
    qld_plan = make_plan(
        request=request,
        holdings=holdings,
        total=total,
        plan_id="qld_stable_aggressive",
        title="QLD 완충형 레버리지",
        summary="TQQQ보다 완만한 2배 레버리지를 중심으로 현금성/채권 완충을 더 두는 후보입니다.",
        ratios={
            "QLD": qld_ratio,
            "QQQ" if score >= 50 else "VOO": qld_core,
            satellite_symbol: qld_satellite,
            qld_ballast and ballast_symbol or defense_symbol: qld_ballast,
            defense_symbol: qld_cash,
        },
        distance=distance,
        regime=regime,
    )

    broad_core = max(core_ratio, clamp(35 + (70 - score) * 0.25, 25, 70))
    mixed_tqqq = tqqq_base * 0.55
    mixed_qld = clamp(score * 0.12, 0, 15) if profile.target_count >= 3 else 0
    mixed_satellite = 0
    mixed_ballast = recommended_ballast_ratio(score)
    mixed_cash = max(min_cash, 100 - broad_core - mixed_tqqq - mixed_qld - mixed_satellite - mixed_ballast)
    mixed_plan = make_plan(
        request=request,
        holdings=holdings,
        total=total,
        plan_id="validated_universe_mix",
        title="검증 ETF 혼합형",
        summary=(
            "QQQ/VOO, 단기채/중기채, 소량 레버리지를 섞어 같은 원금에서 더 안정적인 후보를 만듭니다."
        ),
        ratios={
            "QQQ" if score >= 55 else "VOO": broad_core,
            "TQQQ": mixed_tqqq,
            "QLD": mixed_qld,
            satellite_symbol: mixed_satellite,
            ballast_symbol: mixed_ballast,
            defense_symbol: mixed_cash,
        },
        distance=distance,
        regime=regime,
    )
    return [tqqq_plan, qld_plan, mixed_plan]


def symbol_if_allowed(symbol: str, profile) -> str:
    return symbol if profile.allow_tqqq else "QQQ"


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

    if regime == "reduced_entry":
        tqqq *= 0.75
    elif regime == "stretched_entry":
        tqqq *= 0.45

    if distance >= 50:
        tqqq = min(tqqq, 10)
        cash_like = 50
    elif distance >= 40:
        tqqq = min(tqqq, 25)
        cash_like = 20
    elif distance >= 25:
        tqqq = min(tqqq, 40)
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
    if score <= 35:
        return "SHY"
    if score <= 65:
        return "IEF"
    return "SHY"


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


def make_plan(
    request: StrategyRecommendRequest,
    holdings: list[HoldingInput],
    total: float,
    plan_id: str,
    title: str,
    summary: str,
    ratios: dict[str, float],
    distance: float,
    regime: MarketRegime,
) -> StrategyPlan:
    normalized = normalize_ratios(ratios)
    allocations = [
        PortfolioAllocation(
            symbol=symbol,
            name=name_for_symbol(symbol),
            target_ratio=round(ratio, 1),
            target_amount=round(total * ratio / 100),
            role=role_for_symbol(symbol),
        )
        for symbol, ratio in normalized.items()
        if ratio > 0.1
    ]
    scores = build_scores(normalized, distance, regime, request.profile.risk_score, plan_id)
    return StrategyPlan(
        id=plan_id,
        title=title,
        summary=summary,
        allocations=allocations,
        actions=build_actions(holdings, request.cash, total, allocations),
        buy_plan=build_buy_plan(
            total,
            allocation_ratio(normalized, "TQQQ"),
            distance,
            regime,
            request.profile.risk_score,
        ),
        sell_plan=build_sell_plan(
            total,
            allocation_ratio(normalized, "TQQQ"),
            distance,
            request.profile.risk_score,
        ),
        risk_metrics=build_risk_metrics(normalized, distance, regime),
        scores=scores,
        pros=build_pros(plan_id),
        cons=build_cons(plan_id, regime),
    )


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


def build_scores(
    ratios: dict[str, float],
    distance: float,
    regime: MarketRegime,
    user_risk_score: int,
    plan_id: str,
) -> StrategyScores:
    strategy_risk = round(
        clamp(
            sum(
                allocation_ratio(ratios, symbol) * CANDIDATES[symbol].risk_weight
                for symbol in ratios
            )
            + max(distance, 0) * 0.7,
            0,
            100,
        )
    )
    risk_gap = abs(strategy_risk - user_risk_score)
    tqqq = allocation_ratio(ratios, "TQQQ")
    cash = defensive_ratio(ratios)
    one_x = one_x_equity_ratio(ratios)
    buffer_ratio = cash if regime == "risk_off" else cash + one_x * 0.35

    rule_clarity = 18
    market_fit = (
        8
        if regime == "risk_off" and tqqq > 0
        else 18
        if regime != "stretched_entry"
        else 13
    )
    cash_defense = round(clamp(buffer_ratio * 0.45, 4, 15))
    drawdown_control = round(clamp(18 - tqqq * 0.13 + cash * 0.08 + one_x * 0.03, 4, 15))
    overfit_resistance = 10 if plan_id == "validated_universe_mix" else 8
    execution_quality = 8 if tqqq >= 45 else 10
    user_fit = round(clamp(10 - risk_gap / 10, 1, 10))
    confidence = round(
        rule_clarity
        + market_fit
        + cash_defense
        + drawdown_control
        + overfit_resistance
        + execution_quality
        + user_fit
    )
    expected_return = round(
        clamp(
            sum(
                allocation_ratio(ratios, symbol) * CANDIDATES[symbol].return_weight
                for symbol in ratios
            ),
            0,
            100,
        )
    )
    difficulty = (
        "very_high"
        if tqqq >= 45
        else "high"
        if tqqq >= 30
        else "medium"
        if strategy_risk >= 55
        else "low"
    )

    notes = [
        "신뢰도는 수익 보장이 아니라 규칙 명확성, 방어력, 시장 적합성, "
        "실행 가능성의 종합 점수입니다.",
        (
            f"사용자 리스크 허용치 {user_risk_score}점과 전략 위험도 "
            f"{strategy_risk}점의 차이를 반영했습니다."
        ),
        "검증 후보군 밖의 보유 종목은 기본적으로 유지 근거가 약하면 축소 또는 제외 후보로 봅니다.",
    ]
    if regime == "stretched_entry":
        notes.append("QQQ가 200일선보다 많이 높아 신규 진입 신뢰도는 일부 감점했습니다.")
    if regime == "risk_off" and cash < 80:
        notes.append("QQQ 200일선 아래에서는 SGOV/CASH 방어 비중이 충분해야 합니다.")
    elif regime != "risk_off" and cash < 10 and one_x < 25:
        notes.append("현금은 적어도 괜찮지만, TQQQ를 낮춰 받을 1x 완충 자산이 부족합니다.")

    return StrategyScores(
        confidence_score=int(clamp(confidence, 0, 100)),
        risk_score=int(strategy_risk),
        fit_score=int(clamp(100 - risk_gap - max(distance - 15, 0) * 1.5, 0, 100)),
        expected_return_score=int(expected_return),
        execution_difficulty=difficulty,
        confidence_breakdown=ConfidenceBreakdown(
            rule_clarity=rule_clarity,
            market_fit=market_fit,
            cash_defense=cash_defense,
            drawdown_control=drawdown_control,
            overfit_resistance=overfit_resistance,
            execution_quality=execution_quality,
            user_fit=user_fit,
        ),
        confidence_notes=notes,
    )


def build_actions(
    holdings: list[HoldingInput],
    cash: float,
    total: float,
    allocations: list[PortfolioAllocation],
) -> list[TradeAction]:
    current = {item.symbol.upper(): item.amount for item in holdings}
    current["CASH"] = cash
    actions: list[TradeAction] = []
    target_symbols = {allocation.symbol.upper() for allocation in allocations}

    for allocation in allocations:
        symbol = allocation.symbol.upper()
        current_amount = current.get(symbol, 0)
        diff = allocation.target_amount - current_amount
        threshold = max(total * 0.03, 10000)
        if abs(diff) < threshold:
            action, amount, reason = "hold", 0, "목표 비중과 현재 비중 차이가 작습니다."
        elif diff > 0:
            action, amount, reason = (
                "buy",
                round(diff),
                "검증 후보군 기준 목표 비중보다 부족합니다.",
            )
        else:
            action, amount, reason = (
                "sell",
                round(abs(diff)),
                "검증 후보군 기준 목표 비중보다 큽니다.",
            )
        actions.append(TradeAction(symbol=symbol, action=action, amount=amount, reason=reason))

    for symbol, amount in current.items():
        if symbol not in target_symbols and amount > 0 and symbol != "CASH":
            reason = "추천 포트폴리오에 포함되지 않았습니다."
            if symbol not in CANDIDATES:
                reason = "검증 후보군 밖의 자산이라 이번 추천에서는 제외 후보입니다."
            actions.append(
                TradeAction(
                    symbol=symbol,
                    action="sell",
                    amount=round(amount),
                    reason=reason,
                )
            )
    return actions


def build_buy_plan(
    total: float,
    tqqq_ratio: float,
    distance: float,
    regime: MarketRegime,
    user_risk_score: int,
) -> list[SplitStep]:
    target = total * tqqq_ratio / 100
    if target <= 0 or regime == "risk_off":
        return [
            SplitStep(
                step="대기",
                trigger="QQQ가 200일선 위로 2거래일 연속 회복",
                ratio_of_target=0,
                amount=0,
                note="방어 구간에서는 TQQQ 신규 매수를 보류합니다.",
            )
        ]

    if user_risk_score >= 85 and distance <= 10:
        ratios = [60, 25, 15]
    elif user_risk_score >= 70:
        ratios = [40, 30, 30] if distance <= 15 else [30, 35, 35]
    else:
        ratios = [25, 35, 40]

    triggers = [
        "전략 선택 후 1차 진입",
        "2차: QQQ 20일선 +1% 이내 눌림, 또는 200일선 대비 +8% 이하 이격 완화",
        "3차: QQQ 50일선 +1~+2% 방어 구간, 또는 200일선 대비 +5% 이하 이격 완화",
    ]
    notes = [
        "추세 참여용 초기 진입입니다.",
        "2차는 단기 추격이 아니라 얕은 눌림 또는 200일선 이격 완화가 확인될 때만 실행합니다.",
        "3차는 50일선을 깨기 직전의 충돌 구간이 아니라, 50일선 방어가 확인된 깊은 눌림이나 200일선 이격 완화 때만 쓰는 마지막 진입입니다.",
    ]
    return [
        SplitStep(
            step=f"{index + 1}차 매수",
            trigger=triggers[index],
            ratio_of_target=ratios[index],
            amount=round(target * ratios[index] / 100),
            note=notes[index],
        )
        for index in range(3)
    ]


def build_sell_plan(
    total: float,
    tqqq_ratio: float,
    distance: float,
    user_risk_score: int,
) -> list[SplitStep]:
    target = total * max(tqqq_ratio, 30) / 100
    first_sell = 50 if user_risk_score <= 50 else 30
    return [
        SplitStep(
            step="리스크 축소",
            trigger="QQQ가 50일선 대비 -1% 이하로 이탈하거나 50일선 아래 2거래일 연속 마감",
            ratio_of_target=first_sell,
            amount=round(target * first_sell / 100),
            note="50일선 단순 터치에는 흔들리지 않고, 이탈이 확인될 때 먼저 일부 비중을 줄입니다.",
        ),
        SplitStep(
            step="방어 전환",
            trigger="QQQ가 200일선 아래 2거래일 연속 마감",
            ratio_of_target=100,
            amount=round(target),
            note="200일선 전략의 핵심 방어 규칙입니다.",
        ),
        SplitStep(
            step="수익 회수",
            trigger="TQQQ 수익률 +50% 또는 QQQ 200일선 대비 +25% 이상",
            ratio_of_target=20,
            amount=round(target * 0.2),
            note=(
                f"현재 200일선 대비 거리는 {distance:.1f}%입니다. "
                "과열 구간에서는 원금 회수를 고려합니다."
            ),
        ),
    ]


def build_risk_metrics(
    ratios: dict[str, float],
    distance: float,
    regime: MarketRegime,
) -> list[RiskMetric]:
    tqqq = allocation_ratio(ratios, "TQQQ")
    qld = allocation_ratio(ratios, "QLD")
    semi = sum(allocation_ratio(ratios, symbol) for symbol in ("SMH", "SOXX", "ACE K반도체TOP2"))
    cash = defensive_ratio(ratios)
    one_x = one_x_equity_ratio(ratios)
    leverage_exposure = tqqq * 3 + qld * 2

    return [
        RiskMetric(
            label="레버리지 노출",
            value=f"{leverage_exposure:.0f}%",
            level=(
                "very_high"
                if leverage_exposure >= 120
                else "high"
                if leverage_exposure >= 80
                else "medium"
            ),
        ),
        RiskMetric(
            label="1x 완충 자산",
            value=f"{one_x:.1f}%",
            level="low" if one_x >= 45 else "medium" if one_x >= 25 else "high",
        ),
        RiskMetric(
            label="반도체 집중",
            value=f"{semi:.1f}%",
            level="high" if semi >= 30 else "medium" if semi >= 20 else "low",
        ),
        RiskMetric(
            label="SGOV/현금 방어",
            value=f"{cash:.1f}%",
            level=(
                "low"
                if (regime == "risk_off" and cash >= 80) or (regime != "risk_off" and cash >= 5)
                else "medium"
                if cash > 0
                else "high"
            ),
        ),
        RiskMetric(
            label="시장 진입 위치",
            value=f"QQQ 200일선 대비 {distance:.1f}%",
            level=(
                "high"
                if regime == "stretched_entry"
                else "medium"
                if regime == "reduced_entry"
                else "low"
            ),
        ),
    ]


def build_pros(plan_id: str) -> list[str]:
    common = [
        "검증 후보군 안에서만 추천해 설명 가능성이 높습니다.",
        "QQQ 200일선 기준으로 매도 규칙이 명확합니다.",
    ]
    if plan_id == "tqqq_200ma_coach":
        return [*common, "작은 시드에서 공격성을 가장 크게 가져갈 수 있습니다."]
    if plan_id == "qld_stable_aggressive":
        return [*common, "TQQQ보다 변동성이 낮아 심리적으로 버티기 쉽습니다."]
    return [*common, "레버리지, 위성, 방어 자산의 역할이 더 분명합니다."]


def build_cons(plan_id: str, regime: MarketRegime) -> list[str]:
    cons = ["나스닥과 반도체 방향성이 동시에 꺾이면 손실이 빠르게 커질 수 있습니다."]
    if regime == "stretched_entry":
        cons.append("현재 진입 위치가 높아 TQQQ 대매수에는 부담이 있습니다.")
    if plan_id == "tqqq_200ma_coach":
        cons.append("TQQQ 비중이 커서 10% 조정에도 계좌 변동이 크게 나타납니다.")
    elif plan_id == "qld_stable_aggressive":
        cons.append("상승장에서는 TQQQ 전략보다 수익 탄력이 낮을 수 있습니다.")
    else:
        cons.append("종목 수가 늘어 단순한 2종목 집중 전략보다 관리할 항목이 많습니다.")
    return cons


def build_rule_based_report(
    plan: StrategyPlan,
    diagnosis: list[str],
    regime: MarketRegime,
    distance: float,
    user_risk_score: int,
) -> CoachReport:
    if regime == "risk_off":
        headline = "지금은 공격보다 방어 규칙을 먼저 확인할 구간입니다."
    elif regime == "stretched_entry":
        headline = "TQQQ 전략은 가능하지만 대매수보다 분할 진입이 맞습니다."
    else:
        headline = "QQQ 200일선 기준으로 공격 전략을 이용할 수 있는 구간입니다."

    return CoachReport(
        headline=headline,
        diagnosis=" ".join(diagnosis),
        recommended_plan_id=plan.id,
        why=[
            (
                f"사용자 리스크 허용도는 {user_risk_score}점, "
                f"성향은 {risk_band(user_risk_score)}입니다."
            ),
            f"QQQ가 200일선 대비 {distance:.1f}% 위치에 있어 진입 강도를 조절해야 합니다.",
            "추천은 현재 보유 종목을 고집하지 않고 검증 후보군 안에서 다시 구성했습니다.",
        ],
        next_actions=[
            f"우선 추천안 '{plan.title}'의 목표 비중과 현재 보유 종목 차이를 확인하세요.",
            "TQQQ 목표금액은 한 번에 넣지 말고 화면의 1~3차 매수 조건으로 나누세요.",
            "검증 후보군 밖 종목은 유지 이유가 명확하지 않으면 축소 후보로 봅니다.",
        ],
        warnings=[
            "이 앱은 투자 자문이 아니라 전략 점검 도구이며 수익을 보장하지 않습니다.",
            "TQQQ는 일일 3배 레버리지 상품이라 장기 성과가 QQQ의 단순 3배와 다를 수 있습니다.",
            "신뢰도 점수가 높아도 미래 시장에서 손실은 발생할 수 있습니다.",
        ],
        monitoring_rules=[
            "매일 장마감 후 QQQ와 200일선의 위치를 확인합니다.",
            "주 1회 목표 비중과 실제 비중을 비교합니다.",
            "월 1회 현금성 비중이 최소 기준 아래로 내려갔는지 확인합니다.",
        ],
    )


def is_semiconductor(holding: HoldingInput) -> bool:
    text = f"{holding.symbol} {holding.name} {holding.category}".lower()
    return any(keyword in text for keyword in SEMICONDUCTOR_KEYWORDS)


def name_for_symbol(symbol: str) -> str:
    asset = CANDIDATES.get(symbol)
    return asset.name if asset else symbol


def role_for_symbol(symbol: str) -> str:
    asset = CANDIDATES.get(symbol)
    return asset.role if asset else "전략 자산"
