from datetime import datetime, timedelta, timezone

from app.schemas.managed_strategy import (
    ComplianceIssue,
    ContributionAllocationAdvice,
    ContributionPlanAdvice,
    ContributionPlanOption,
    ContributionPlanRequest,
    ManagedStrategy,
    ManagedStrategyGuide,
    PhilosophyAllocationDiff,
    PhilosophyUpgradeAdvice,
    StrategyAdjustmentAdvice,
    StrategyAdjustmentAllocation,
    StrategyAdjustmentRequest,
)
from app.services.managed_strategy_model import (
    _add_ratio,
    _adjustment_reason,
    _allocation_map,
    _allocation_ratio,
    _cash_like_ratio,
    _executed_amounts,
    _normalize_map,
    _one_x_buffer_ratio,
    _philosophy_diff_reason,
    _recommended_cash_floor,
    _reduce_growth_for_cash,
    _set_cash_like_ratio,
    _strategy_to_latest_recommend_request,
)
from app.services.strategy_engine import recommend_strategy
from app.services.strategy_execution import build_execution_plan


def build_guide(strategy: ManagedStrategy) -> ManagedStrategyGuide:
    distance = (strategy.market.qqq_close / strategy.market.qqq_sma200 - 1) * 100
    tqqq_ratio = _allocation_ratio(strategy, "TQQQ")

    ratios = _allocation_map(strategy)
    cash_like_ratio = _cash_like_ratio(ratios)
    one_x_ratio = _one_x_buffer_ratio(strategy)
    execution_plan = build_execution_plan(strategy, distance)
    issues = _build_issues(distance, tqqq_ratio, cash_like_ratio, one_x_ratio)

    danger_count = sum(1 for issue in issues if issue.level == "danger")
    watch_count = sum(1 for issue in issues if issue.level == "watch")
    ready_count = sum(1 for step in execution_plan if step.status == "ready")
    blocked_count = sum(1 for step in execution_plan if step.status == "blocked")
    score = max(0, 100 - danger_count * 35 - watch_count * 12 - blocked_count * 5 - min(ready_count, 2) * 3)

    if distance <= 0:
        action = "방어 모드: 신규 레버리지 매수 보류, 200일선 회복 전까지 SGOV/CASH 우선"
    elif distance >= 15:
        action = "감속 모드: TQQQ 추격보다 1x 완충 ETF로 참여 유지, 신규 TQQQ는 축소 집행만 검토"
    elif ready_count:
        action = "실행 후보 있음: 아래 단계 중 '실행 가능'만 금액 한도 안에서 검토"
    else:
        action = "대기 모드: TQQQ 조건은 기다리되 시장 참여는 1x 완충/기존 보유로 유지"

    checklist = [
        "QQQ가 200일선 위에서 마감했는지 확인",
        "실행 가능 단계만 검토하고 대기/금지 단계는 건드리지 않기",
        "실행 후 TQQQ/QLD 목표 비중과 이격도별 실효 레버리지 상한을 초과하지 않는지 확인",
        "매수/매도 전 판단 이유를 기록장에 먼저 남기기",
    ]
    next_review = (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat()
    return ManagedStrategyGuide(
        strategy=strategy,
        compliance_score=score,
        current_action=action,
        checklist=checklist,
        issues=issues,
        execution_plan=execution_plan,
        next_review=next_review,
    )



def advise_adjustment(strategy: ManagedStrategy, payload: StrategyAdjustmentRequest) -> StrategyAdjustmentAdvice:
    distance = round((strategy.market.qqq_close / strategy.market.qqq_sma200 - 1) * 100, 2)
    current = _allocation_map(strategy)
    current_cash = _cash_like_ratio(current)
    target_cash = round(payload.target_cash_ratio, 1)
    minimum_cash = _recommended_cash_floor(distance, _allocation_ratio(strategy, "TQQQ"))
    proposed = dict(current)
    issues: list[str] = []
    actions: list[str] = []

    verdict = "ok"
    if target_cash < minimum_cash:
        verdict = "danger" if distance >= 15 else "watch"
        issues.append(
            f"현재 QQQ가 200일선 대비 {distance:.1f}% 위치라 권장 최소 현금은 {minimum_cash:.0f}%입니다."
        )
    if target_cash < 15:
        verdict = "danger"
        issues.append("현금 15% 미만은 급락 또는 200일선 재접근 시 분할매수 여력이 부족합니다.")

    cash_delta = current_cash - target_cash
    if cash_delta > 0:
        _set_cash_like_ratio(proposed, target_cash)
        if distance >= 15:
            _add_ratio(proposed, "SPYM", cash_delta * 0.65)
            _add_ratio(proposed, "QQQ", cash_delta * 0.35)
            actions.append("과열 구간이므로 줄인 현금은 TQQQ 추가매수가 아니라 SPYM/QQQ 완충으로만 배치합니다.")
        elif distance >= 8:
            _add_ratio(proposed, "SPYM", cash_delta * 0.50)
            _add_ratio(proposed, "QQQ", cash_delta * 0.35)
            _add_ratio(proposed, "TQQQ", cash_delta * 0.15)
            actions.append("중간 이격 구간이므로 TQQQ 증액은 작게 제한하고 대부분은 SPYM/QQQ로 보냅니다.")
        else:
            _add_ratio(proposed, "TQQQ", cash_delta * 0.35)
            _add_ratio(proposed, "QQQ", cash_delta * 0.35)
            _add_ratio(proposed, "SPYM", cash_delta * 0.30)
            actions.append("200일선 이격도가 완화된 구간에서만 TQQQ 증액을 일부 허용합니다.")
    elif cash_delta < 0:
        need = abs(cash_delta)
        _set_cash_like_ratio(proposed, target_cash)
        _reduce_growth_for_cash(proposed, need)
        actions.append("현금을 늘리는 조정은 TQQQ부터 줄이고, 부족하면 QQQ/SPYM을 순서대로 낮춥니다.")
    else:
        actions.append("현금 비중은 이미 요청값과 거의 같습니다. 다른 종목 비중 조정만 검토하면 됩니다.")

    proposed = _normalize_map(proposed)
    suggested = [
        StrategyAdjustmentAllocation(
            symbol=symbol,
            current_ratio=round(current.get(symbol, 0), 1),
            suggested_ratio=round(ratio, 1),
            delta_ratio=round(ratio - current.get(symbol, 0), 1),
            reason=_adjustment_reason(symbol, ratio - current.get(symbol, 0), distance),
        )
        for symbol, ratio in proposed.items()
        if ratio >= 0.1 or current.get(symbol, 0) >= 0.1
    ]
    suggested.sort(key=lambda item: (item.symbol != "CASH", item.symbol))

    if verdict == "ok":
        headline = f"현금 {target_cash:.0f}% 조정은 현재 규칙 안에서 검토 가능합니다."
    elif verdict == "watch":

        headline = f"현금 {target_cash:.0f}%는 가능하지만 방어 여력이 줄어듭니다."
    else:
        headline = f"현금 {target_cash:.0f}%는 현재 구간에서 공격성이 과합니다."

    summary = (
        "원 전략을 완전히 바꾸는 것이 아니라, 현재 시장 위치에서 허용 가능한 조정안인지 점검한 결과입니다. "
        "TQQQ 추가매수는 눌림, 돌파, 이격도 완화 조건이 없으면 제한합니다."
    )
    if payload.note:
        actions.append(f"사용자 메모 반영: {payload.note}")

    return StrategyAdjustmentAdvice(
        verdict=verdict,  # type: ignore[arg-type]
        headline=headline,
        summary=summary,
        current_cash_ratio=round(current_cash, 1),
        target_cash_ratio=target_cash,
        minimum_cash_ratio=round(minimum_cash, 1),
        qqq_distance_from_200ma=distance,
        suggested_allocations=suggested,
        issues=issues,
        actions=actions,
    )




def advise_contribution(strategy: ManagedStrategy, payload: ContributionPlanRequest) -> ContributionPlanAdvice:
    contribution = round(payload.contribution_amount)
    new_total = strategy.total_capital + contribution
    distance = round((strategy.market.qqq_close / strategy.market.qqq_sma200 - 1) * 100, 2)
    executed = _executed_amounts(strategy)
    spent = sum(executed.values())
    current_idle_cash = max(strategy.total_capital - spent, 0)
    available_cash = current_idle_cash + contribution
    buy_plan = build_execution_plan(strategy, distance)
    tqqq_step = next(
        (step for step in buy_plan if step.side == "buy" and step.symbol == "TQQQ" and step.status == "ready"),
        None,
    )

    allocations: list[ContributionAllocationAdvice] = []
    remaining = contribution
    allocation_targets = [
        (allocation, round(new_total * allocation.target_ratio / 100))
        for allocation in strategy.plan.allocations
    ]

    for allocation, target_after in allocation_targets:
        symbol = allocation.symbol.upper()
        current_amount = current_idle_cash if symbol == "CASH" else executed.get(symbol, 0)
        if symbol == "QQQ":
            current_amount += executed.get("QQQM", 0)
        gap = max(target_after - current_amount, 0)
        action = "hold"
        suggested = 0
        reason = "목표 비중 대비 추가 실행 필요가 작습니다."

        if symbol in {"CASH", "SGOV", "BIL"}:
            action = "wait"
            suggested = min(max(gap, 0), remaining)
            reason = "하락장, 극과열, 또는 가까운 TQQQ 집행 재원으로 필요한 금액만 현금/SGOV로 보관합니다."
        elif symbol == "TQQQ":
            if tqqq_step:
                action = "buy"
                suggested = min(gap, remaining, tqqq_step.amount)
                reason = f"{tqqq_step.step} 조건이 준비 상태입니다. 단, 분할 한도 안에서만 추가합니다."
            else:
                action = "wait"
                suggested = 0
                reason = "TQQQ는 조건 전까지 추가매수를 보류합니다. 다만 200일선 위라면 미집행분은 QQQM/SPYM 완충으로 참여 유지 여부를 함께 봅니다."
        elif symbol in {"QQQ", "QQQM", "SPYM", "VOO"}:
            action = "buy"
            suggested = min(gap, remaining)
            reason = "TQQQ 미집행분을 무기한 현금화하지 않기 위한 1x 완충 코어 자산입니다."
        else:
            action = "rebalance"
            suggested = min(gap, remaining)
            reason = "목표 비중과 중복 위험을 확인한 뒤 소액 보완합니다."

        if suggested > 0:
            remaining -= suggested

        allocations.append(
            ContributionAllocationAdvice(
                symbol=allocation.symbol,
                role=allocation.role,
                current_amount=round(current_amount),
                target_amount_after=round(target_after),
                gap_amount=round(gap),
                suggested_amount=round(suggested),
                action=action,  # type: ignore[arg-type]
                    reason=reason,
            )
        )

    if remaining > 0:
        allocations.append(
            ContributionAllocationAdvice(
                symbol="CASH",
                role="추가입금 잔여 대기",
                current_amount=round(current_idle_cash),
                target_amount_after=round(available_cash),
                gap_amount=round(remaining),
                suggested_amount=round(remaining),
                action="wait",
                reason="목표 부족분을 채운 뒤 남는 금액은 시장 국면에 따라 QQQM/SPYM 참여 또는 SGOV/CASH 대기로 다시 검토합니다.",
            )
        )

    actions = [
        f"매달 {payload.pay_day}일 입금액 {contribution:,.0f}원을 먼저 미사용 현금으로 반영합니다.",
        "입금 직후 전액 매수하지 않고, TQQQ는 분할매수 조건 충족 여부를 먼저 확인합니다.",
        "QQQ/SPYM 같은 코어 자산은 목표 비중 부족분 안에서 우선 보완할 수 있습니다.",
    ]
    if distance >= 15:
        actions.append("QQQ가 200일선 대비 +15% 이상이면 TQQQ 추가금 추격매수는 보류하고 코어/현금성 비중을 우선합니다.")
    if payload.note:
        actions.append(f"사용자 메모 반영: {payload.note}")

    headline = f"{contribution:,.0f}원 추가 입금 후 총 운용자본은 {new_total:,.0f}원입니다."
    summary = (
        "추가입금은 별도 수익이 아니라 새 원금입니다. 따라서 기존 비중을 무리하게 흔들기보다 "
        "새 총자본 기준 목표금액을 다시 계산하고, 부족한 자산부터 조건부로 채우는 방식이 적합합니다."
    )
    balanced = ContributionPlanOption(
        id="balanced",
        title="균형형 추가금 운용",
        risk_level="balanced",
        recommendation_score=88,
        headline=headline,
        summary=summary,
        contribution_amount=contribution,
        pay_day=payload.pay_day,
        current_total_capital=round(strategy.total_capital),
        new_total_capital=round(new_total),
        qqq_distance_from_200ma=distance,
        available_cash_after_deposit=round(available_cash),
        actions=actions,
        allocations=allocations,
    )
    keep_current = ContributionPlanOption(
        id="keep_current",
        title="현재 전략 유지",

        risk_level="balanced",
        recommendation_score=90 if 8 <= distance < 15 else 84,
        headline=f"현재 저장된 '{strategy.plan.title}' 전략을 유지하면서 {contribution:,.0f}원을 반영합니다.",
        summary=(
            "새 전략 성향을 추가하지 않고 현재 저장된 목표 비중과 분할매수/분할매도 규칙을 그대로 유지합니다. "
            "추가금은 새 원금 기준 목표금액의 부족분을 채우되, TQQQ는 기존 분할 조건을 계속 따릅니다."
        ),
        contribution_amount=contribution,
        pay_day=payload.pay_day,
        current_total_capital=round(strategy.total_capital),
        new_total_capital=round(new_total),
        qqq_distance_from_200ma=distance,
        available_cash_after_deposit=round(available_cash),
        actions=[
            "현재 저장된 전략의 종목 구성과 목표 비중을 바꾸지 않습니다.",
            "총 운용자본만 늘리고 각 종목 목표금액을 새 원금 기준으로 다시 계산합니다.",
            "TQQQ는 기존 200일선/20일선/50일선 분할매수 조건을 그대로 따릅니다.",
            "실제 주문은 자동 적용하지 않고 실행 기록에서 체결가와 수량을 남깁니다.",
        ],
        allocations=allocations,
    )
    defensive_allocations = [
        item.model_copy(
            update={
                "suggested_amount": 0,
                "action": "wait",
                "reason": "보수형에서는 TQQQ 추가매수를 다음 눌림 신호까지 보류합니다.",
            }
        )
        if item.symbol.upper() == "TQQQ"
        else item
        for item in allocations
    ]
    defensive = ContributionPlanOption(
        id="defensive",
        title="보수형 대기자금 우선",
        risk_level="defensive",
        recommendation_score=92 if distance >= 12 else 82,
        headline=f"{contribution:,.0f}원 추가금은 방어 여력을 우선 확보합니다.",
        summary="입금액을 바로 공격 자산에 넣기보다 현금/SGOV 대기와 코어 부족분 보완에 집중하는 안입니다.",
        contribution_amount=contribution,
        pay_day=payload.pay_day,
        current_total_capital=round(strategy.total_capital),
        new_total_capital=round(new_total),
        qqq_distance_from_200ma=distance,
        available_cash_after_deposit=round(available_cash),
        actions=[
            "TQQQ 추가매수는 20일선/50일선 눌림 신호가 더 명확해질 때까지 보류합니다.",
            "입금액 중 남는 금액은 CASH 또는 SGOV 대기자금으로 둡니다.",
            "코어 자산 부족분만 제한적으로 보완합니다.",
        ],
        allocations=defensive_allocations,
    )
    aggressive_allocations: list[ContributionAllocationAdvice] = []
    tqqq_gap = next((item.gap_amount for item in allocations if item.symbol.upper() == "TQQQ"), 0)
    cash_to_shift = sum(item.suggested_amount for item in allocations if item.symbol.upper() in {"CASH", "SGOV", "BIL"})
    aggressive_tqqq_add = min(tqqq_gap, cash_to_shift * 0.5, contribution * 0.25) if distance < 15 else 0
    for item in allocations:
        if item.symbol.upper() == "TQQQ" and aggressive_tqqq_add > 0:
            aggressive_allocations.append(
                item.model_copy(
                    update={
                        "suggested_amount": round(aggressive_tqqq_add),
                        "action": "buy",
                        "reason": "공격형에서는 2차 조건이 준비됐을 때 추가금 일부를 TQQQ 분할매수 후보로 둡니다.",
                    }
                )
            )
        elif item.symbol.upper() in {"CASH", "SGOV", "BIL"} and aggressive_tqqq_add > 0:
            aggressive_allocations.append(
                item.model_copy(update={"suggested_amount": max(round(item.suggested_amount - aggressive_tqqq_add), 0)})
            )
            aggressive_tqqq_add = 0
        else:
            aggressive_allocations.append(item)
    aggressive = ContributionPlanOption(
        id="aggressive",
        title="공격형 TQQQ 조건부 증액",
        risk_level="aggressive",
        recommendation_score=78 if distance < 15 else 55,
        headline=f"{contribution:,.0f}원 중 일부를 TQQQ 분할매수 후보로 둡니다.",
        summary="현재 시장이 완전 방어 구간은 아니지만, 레버리지 추가금은 조건부로만 집행하는 공격형 안입니다.",
        contribution_amount=contribution,
        pay_day=payload.pay_day,
        current_total_capital=round(strategy.total_capital),
        new_total_capital=round(new_total),
        qqq_distance_from_200ma=distance,
        available_cash_after_deposit=round(available_cash),
        actions=[
            "TQQQ는 한 번에 몰아서 사지 않고 추천 분할 한도 안에서만 실행합니다.",
            "조건이 애매하면 공격형 안을 선택해도 실제 주문은 보류할 수 있습니다.",
            "코어 자산과 현금성 대기자금은 유지해 다음 눌림에 대응합니다.",
        ],
        allocations=aggressive_allocations,
    )
    plans = [keep_current, defensive, balanced, aggressive]
    recommended = max(plans, key=lambda item: item.recommendation_score).id
    return ContributionPlanAdvice(
        headline=balanced.headline,
        summary=balanced.summary,
        contribution_amount=balanced.contribution_amount,
        pay_day=balanced.pay_day,
        current_total_capital=balanced.current_total_capital,
        new_total_capital=balanced.new_total_capital,
        qqq_distance_from_200ma=balanced.qqq_distance_from_200ma,
        available_cash_after_deposit=balanced.available_cash_after_deposit,
        actions=balanced.actions,
        allocations=balanced.allocations,
        recommended_plan_id=recommended,
        plans=plans,
    )



def advise_philosophy_upgrade(strategy: ManagedStrategy) -> PhilosophyUpgradeAdvice:
    request = _strategy_to_latest_recommend_request(strategy)
    response = recommend_strategy(request)
    suggested = response.plans[0]
    current = _allocation_map(strategy)
    next_ratios = {allocation.symbol.upper(): allocation.target_ratio for allocation in suggested.allocations}
    symbols = sorted(set(current) | set(next_ratios), key=lambda symbol: (symbol not in {"TQQQ", "QQQM", "SPYM", "SGOV", "CASH"}, symbol))
    diffs = [
        PhilosophyAllocationDiff(
            symbol=symbol,
            current_ratio=round(current.get(symbol, 0), 1),
            suggested_ratio=round(next_ratios.get(symbol, 0), 1),
            delta_ratio=round(next_ratios.get(symbol, 0) - current.get(symbol, 0), 1),
            reason=_philosophy_diff_reason(symbol, current.get(symbol, 0), next_ratios.get(symbol, 0), response.qqq_distance_from_200ma),
        )
        for symbol in symbols
        if current.get(symbol, 0) >= 0.1 or next_ratios.get(symbol, 0) >= 0.1
    ]
    total_delta = sum(abs(item.delta_ratio) for item in diffs)
    if total_delta < 5:
        verdict = "up_to_date"
        headline = "현재 전략은 최신 TQQQ 200일선 철학과 큰 차이가 없습니다."
    elif total_delta < 25:
        verdict = "update_recommended"
        headline = "최신 철학 기준으로 일부 비중 조정이 권장됩니다."
    else:
        verdict = "major_change"

        headline = "최신 철학과 현재 저장 전략의 차이가 큽니다."

    changes = [
        "200일선 위에서는 시장 참여를 유지하되 TQQQ 강도를 조절합니다.",
        "TQQQ를 줄이는 구간에서는 현금만 늘리기보다 QQQM/SPYM 같은 1x 완충 자산을 우선 검토합니다.",
        "200일선 아래 또는 극단 과열 구간에서는 SGOV/CASH 방어 비중을 명확히 높입니다.",
    ]
    cautions = [
        "기존 전략은 당시 판단 기록으로 보존하고, 적용 시 새 버전으로만 반영합니다.",
        "새 버전 적용 후에도 실제 매수는 오늘의 실행 기준과 분할매수 조건을 다시 확인해야 합니다.",
    ]
    if response.qqq_distance_from_200ma >= 15:
        cautions.append("QQQ가 200일선 대비 +15% 이상이면 TQQQ 추가 집행은 추격매수로 보지 않도록 더 엄격히 점검합니다.")

    return PhilosophyUpgradeAdvice(
        verdict=verdict,  # type: ignore[arg-type]
        headline=headline,
        summary=(
            f"저장된 '{strategy.plan.title}' 전략을 최신 엔진으로 다시 계산했습니다. "
            f"현재 QQQ 200일선 이격은 {response.qqq_distance_from_200ma:.2f}%이고, "
            f"추정 리스크 허용도는 {request.profile.risk_score}점입니다."
        ),
        qqq_distance_from_200ma=response.qqq_distance_from_200ma,
        inferred_risk_score=request.profile.risk_score,
        current_plan_title=strategy.plan.title,

        suggested_plan_id=suggested.id,
        suggested_plan_title=suggested.title,
        suggested_plan_summary=suggested.summary,
        allocation_diffs=diffs,
        changes=changes,
        cautions=cautions,
    )



def _build_issues(
    distance: float,
    tqqq_ratio: float,
    cash_like_ratio: float,
    one_x_ratio: float,
) -> list[ComplianceIssue]:
    issues: list[ComplianceIssue] = []
    if distance <= 0:
        issues.append(
            ComplianceIssue(
                level="danger",
                title="QQQ 200일선 아래",
                detail="신규 TQQQ/QLD 매수보다 방어 전환과 현금 확보를 우선합니다.",
            )
        )
    elif distance >= 15:
        issues.append(
            ComplianceIssue(
                level="watch",
                title="QQQ 200일선 대비 과열",
                detail="대매수보다 1차 이하 분할 진입, 추격 매수 제한, 현금 보존이 필요합니다.",
            )

        )
    else:
        issues.append(
            ComplianceIssue(
                level="ok",
                title="전략 운용 가능 구간",
                detail="QQQ가 200일선 위에 있어 레버리지 전략을 검토할 수 있습니다.",
            )
        )
    if tqqq_ratio >= 50:
        issues.append(
            ComplianceIssue(
                level="watch",
                title="TQQQ 비중 높음",
                detail="10% 조정에도 계좌 변동이 커질 수 있어 분할매도 규칙을 미리 확인하세요.",
            )
        )
    if distance <= 0 and cash_like_ratio < 60:
        issues.append(
            ComplianceIssue(
                level="danger",
                title="방어 자산 부족",
                detail="QQQ가 200일선 아래일 때는 SGOV/CASH 방어 비중을 충분히 확보해야 합니다.",
            )
        )
    elif distance > 0 and one_x_ratio < 20 and cash_like_ratio >= 25:
        issues.append(
            ComplianceIssue(
                level="watch",
                title="1x 완충 부족",
                detail="200일선 위에서는 현금성 자산만 늘리기보다 QQQM/SPYM 같은 1x 완충 자산으로 시장 참여를 유지하는지 점검하세요.",
            )
        )
    return issues




