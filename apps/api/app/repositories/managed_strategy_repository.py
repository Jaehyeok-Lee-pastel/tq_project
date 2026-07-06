from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.schemas.managed_strategy import (
    ContributionAllocationAdvice,
    ContributionPlanAdvice,
    ContributionPlanApplyRequest,
    ContributionPlanOption,
    ContributionPlanRequest,
    ComplianceIssue,
    ManagedStrategy,
    ManagedStrategyCreate,
    ManagedStrategyGuide,
    ManagedStrategyUpdate,
    SplitExecutionStep,
    StrategyAdjustmentAdvice,
    StrategyAdjustmentAllocation,
    StrategyAdjustmentApplyRequest,
    StrategyAdjustmentRequest,
    StrategyJournalCreate,
    StrategyJournalEntry,
    StrategyVersionAllocation,
    StrategyVersionEntry,
)
from app.schemas.backtest import BacktestRunRequest
from app.services.supabase import get_supabase

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "managed_strategies.json"
SUPABASE_TABLE = "managed_strategies"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _use_supabase(user_id: str | None) -> bool:
    return bool(user_id and settings.supabase_url and settings.supabase_service_role_key)


def _load(user_id: str | None = None) -> list[ManagedStrategy]:
    if _use_supabase(user_id):
        response = (
            get_supabase()
            .table(SUPABASE_TABLE)
            .select("data")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return [ManagedStrategy.model_validate(row["data"]) for row in response.data]
    if not DATA_PATH.exists():
        return []
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return [ManagedStrategy.model_validate(item) for item in raw]


def _save(items: list[ManagedStrategy], user_id: str | None = None) -> None:
    if _use_supabase(user_id):
        rows = [
            {
                "id": item.id,
                "user_id": user_id,
                "data": item.model_dump(),
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in items
        ]
        if rows:
            get_supabase().table(SUPABASE_TABLE).upsert(rows, on_conflict="id").execute()
        return
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps([item.model_dump() for item in items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_strategies(user_id: str | None = None) -> list[ManagedStrategy]:
    return sorted(_load(user_id), key=lambda item: item.created_at, reverse=True)


def import_local_strategies(user_id: str) -> list[ManagedStrategy]:
    if not _use_supabase(user_id):
        return list_strategies()
    if not DATA_PATH.exists():
        return list_strategies(user_id)

    now = utc_now()
    local_raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    existing = list_strategies(user_id)
    imported: list[ManagedStrategy] = []
    for item in local_raw:
        source = ManagedStrategy.model_validate(item)
        data = source.model_dump()
        data["id"] = uuid4().hex
        data["created_at"] = now
        data["updated_at"] = now
        data["selected_reason"] = f"{source.selected_reason} / 로그인 후 기존 로컬 데이터를 가져왔습니다."
        imported.append(ManagedStrategy.model_validate(data))

    if imported:
        _save([*imported, *existing], user_id)
    return list_strategies(user_id)


def get_strategy(strategy_id: str, user_id: str | None = None) -> ManagedStrategy:
    for strategy in _load(user_id):
        if strategy.id == strategy_id:
            return strategy
    raise KeyError(strategy_id)


def build_backtest_request_from_strategy(
    strategy: ManagedStrategy,
    projection_years: int = 3,
    cash_yield: float = 3.0,
) -> BacktestRunRequest:
    tqqq_ratio = _allocation_ratio(strategy, "TQQQ")
    qld_ratio = _allocation_ratio(strategy, "QLD")
    if tqqq_ratio >= 0.1:
        backtest_strategy = "tqqq_200ma"
    elif qld_ratio >= 0.1:
        backtest_strategy = "qld_200ma"
    else:
        backtest_strategy = "qqq_buy_hold"

    return BacktestRunRequest(
        strategy=backtest_strategy,
        initial_capital=max(strategy.total_capital, 1),
        tqqq_target_ratio=round(tqqq_ratio, 1),
        qld_target_ratio=round(qld_ratio, 1),
        cash_yield=cash_yield,
        projection_years=projection_years,
    )


def create_strategy(payload: ManagedStrategyCreate, user_id: str | None = None) -> ManagedStrategy:
    now = utc_now()
    version_history = [
        StrategyVersionEntry(
            version=1,
            created_at=now,
            change_type="created",
            title="원본 전략 채택",
            note=payload.selected_reason,
            before_allocations=[],
            after_allocations=_version_allocations_from_plan(payload.plan),
        )
    ]
    strategy = ManagedStrategy(
        **payload.model_dump(),
        id=uuid4().hex,
        status="active",
        created_at=now,
        updated_at=now,
        version=1,
        journal=[],
        version_history=version_history,
    )
    items = _load(user_id)
    items.insert(0, strategy)
    _save(items, user_id)
    return strategy


def update_strategy(strategy_id: str, payload: ManagedStrategyUpdate, user_id: str | None = None) -> ManagedStrategy:
    items = _load(user_id)
    for index, strategy in enumerate(items):
        if strategy.id == strategy_id:
            data = strategy.model_dump()
            data.update(payload.model_dump(exclude_none=True))
            data["updated_at"] = utc_now()
            data["version"] = strategy.version + 1
            items[index] = ManagedStrategy.model_validate(data)
            _save(items, user_id)
            return items[index]
    raise KeyError(strategy_id)


def add_journal_entry(strategy_id: str, payload: StrategyJournalCreate, user_id: str | None = None) -> ManagedStrategy:
    items = _load(user_id)
    for index, strategy in enumerate(items):
        if strategy.id == strategy_id:
            distance = (strategy.market.qqq_close / strategy.market.qqq_sma200 - 1) * 100
            entry = StrategyJournalEntry(
                **payload.model_dump(),
                id=uuid4().hex,
                created_at=utc_now(),
                qqq_close=strategy.market.qqq_close,
                qqq_sma200=strategy.market.qqq_sma200,
                qqq_distance_from_200ma=round(distance, 2),
            )
            data = strategy.model_dump()
            data["journal"] = [*strategy.journal, entry]
            data["updated_at"] = utc_now()
            items[index] = ManagedStrategy.model_validate(data)
            _save(items, user_id)
            return items[index]
    raise KeyError(strategy_id)


def delete_journal_entry(strategy_id: str, entry_id: str, user_id: str | None = None) -> ManagedStrategy:
    items = _load(user_id)
    for index, strategy in enumerate(items):
        if strategy.id != strategy_id:
            continue
        next_journal = [entry for entry in strategy.journal if entry.id != entry_id]
        if len(next_journal) == len(strategy.journal):
            raise KeyError(entry_id)
        data = strategy.model_dump()
        data["journal"] = next_journal
        data["updated_at"] = utc_now()
        items[index] = ManagedStrategy.model_validate(data)
        _save(items, user_id)
        return items[index]
    raise KeyError(strategy_id)


def build_guide(strategy: ManagedStrategy) -> ManagedStrategyGuide:
    distance = (strategy.market.qqq_close / strategy.market.qqq_sma200 - 1) * 100
    tqqq_ratio = _allocation_ratio(strategy, "TQQQ")
    cash_ratio = _allocation_ratio(strategy, "SGOV") + _allocation_ratio(strategy, "CASH")
    execution_plan = build_execution_plan(strategy, distance)
    issues = _build_issues(distance, tqqq_ratio, cash_ratio)

    danger_count = sum(1 for issue in issues if issue.level == "danger")
    watch_count = sum(1 for issue in issues if issue.level == "watch")
    ready_count = sum(1 for step in execution_plan if step.status == "ready")
    blocked_count = sum(1 for step in execution_plan if step.status == "blocked")
    score = max(0, 100 - danger_count * 35 - watch_count * 12 - blocked_count * 5 - min(ready_count, 2) * 3)

    if distance <= 0:
        action = "방어 모드: 신규 레버리지 매수 보류, 200일선 회복 전까지 현금/단기채 우선"
    elif distance >= 15:
        action = "감속 모드: 기존 전략 유지, 신규 매수는 1차 이하 분할만 검토"
    elif ready_count:
        action = "실행 후보 있음: 아래 단계 중 '실행 가능'만 금액 한도 안에서 검토"
    else:
        action = "대기 모드: 조건이 올 때까지 보유 유지, 추격 매수 금지"

    checklist = [
        "QQQ가 200일선 위에서 마감했는지 확인",
        "실행 가능 단계만 검토하고 대기/금지 단계는 건드리지 않기",
        "실행 후 TQQQ/QLD 목표 비중을 초과하지 않는지 확인",
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


def apply_adjustment(strategy_id: str, payload: StrategyAdjustmentApplyRequest, user_id: str | None = None) -> ManagedStrategy:
    items = _load(user_id)
    for index, strategy in enumerate(items):
        if strategy.id != strategy_id:
            continue
        advice = advise_adjustment(strategy, payload)
        before = _version_allocations_from_plan(strategy.plan)
        after = [
            StrategyVersionAllocation(symbol=item.symbol, ratio=item.suggested_ratio)
            for item in advice.suggested_allocations
            if item.suggested_ratio > 0.1
        ]
        data = strategy.model_dump()
        plan = data["plan"]
        allocation_by_symbol = {
            allocation["symbol"].upper(): allocation
            for allocation in plan["allocations"]
        }
        next_allocations = []
        for allocation in after:
            original = allocation_by_symbol.get(allocation.symbol, {})
            ratio = round(allocation.ratio, 1)
            next_allocations.append(
                {
                    "symbol": allocation.symbol,
                    "name": original.get("name", allocation.symbol),
                    "target_ratio": ratio,
                    "target_amount": round(strategy.total_capital * ratio / 100),
                    "role": original.get("role", _role_for_adjusted_symbol(allocation.symbol)),
                }
            )
        plan["allocations"] = next_allocations
        plan["summary"] = f"{plan['summary']} 조정 적용: {advice.headline}"
        data["plan"] = plan
        data["version"] = strategy.version + 1
        data["updated_at"] = utc_now()
        history = list(strategy.version_history)
        history.append(
            StrategyVersionEntry(
                version=data["version"],
                created_at=data["updated_at"],
                change_type="adjustment",
                title=payload.accepted_headline or advice.headline,
                note=" / ".join([*advice.issues, *advice.actions]),
                before_allocations=before,
                after_allocations=after,
            )
        )
        data["version_history"] = [item.model_dump() for item in history]
        items[index] = ManagedStrategy.model_validate(data)
        _save(items, user_id)
        return items[index]
    raise KeyError(strategy_id)


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
            reason = "분할매수 조건이 오기 전까지 현금 또는 SGOV 대기자금으로 보관합니다."
        elif symbol == "TQQQ":
            if tqqq_step:
                action = "buy"
                suggested = min(gap, remaining, tqqq_step.amount)
                reason = f"{tqqq_step.step} 조건이 준비 상태입니다. 단, 분할 한도 안에서만 추가합니다."
            else:
                action = "wait"
                suggested = 0
                reason = "TQQQ는 20일선/50일선 눌림, 신고가 돌파, 200일선 이격 완화 조건 전까지 추가매수를 보류합니다."
        elif symbol in {"QQQ", "QQQM", "SPYM", "VOO"}:
            action = "buy"
            suggested = min(gap, remaining)
            reason = "레버리지 타이밍 자산이 아니라 목표 비중 부족분을 보완하는 코어 자산입니다."
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
                reason="목표 부족분을 채운 뒤 남는 금액은 다음 분할매수 신호까지 대기합니다.",
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


def apply_contribution(strategy_id: str, payload: ContributionPlanApplyRequest, user_id: str | None = None) -> ManagedStrategy:
    items = _load(user_id)
    for index, strategy in enumerate(items):
        if strategy.id != strategy_id:
            continue
        advice = advise_contribution(strategy, payload)
        selected_plan = next(
            (plan for plan in advice.plans if plan.id == payload.selected_plan_id),
            next((plan for plan in advice.plans if plan.id == advice.recommended_plan_id), None),
        )
        data = strategy.model_dump()
        plan = data["plan"]
        plan["allocations"] = [
            {
                **allocation,
                "target_amount": round(advice.new_total_capital * allocation["target_ratio"] / 100),
            }
            for allocation in plan["allocations"]
        ]
        data["plan"] = plan
        data["total_capital"] = advice.new_total_capital
        data["version"] = strategy.version + 1
        data["updated_at"] = utc_now()
        history = list(strategy.version_history)
        history.append(
            StrategyVersionEntry(
                version=data["version"],
                created_at=data["updated_at"],
                change_type="manual",
                title=payload.accepted_headline or (selected_plan.headline if selected_plan else advice.headline),
                note=" / ".join((selected_plan.actions if selected_plan else advice.actions)),
                before_allocations=_version_allocations_from_plan(strategy.plan),
                after_allocations=_version_allocations_from_plan(ManagedStrategy.model_validate(data).plan),
            )
        )
        data["version_history"] = [item.model_dump() for item in history]
        distance = (strategy.market.qqq_close / strategy.market.qqq_sma200 - 1) * 100
        deposit_entry = StrategyJournalEntry(
            entry_type="deposit",
            symbol="CASH",
            amount=payload.contribution_amount,
            quantity=0,
            price=0,
            reason=f"월급 추가금 입금: {selected_plan.title if selected_plan else advice.recommended_plan_id}",
            mood="neutral",
            note=(
                "추가금은 먼저 미집행 현금으로 기록합니다. "
                "실제 ETF 매수는 오늘의 판단에서 조건을 확인한 뒤 별도 매수 기록으로 남깁니다."
            ),
            id=uuid4().hex,
            created_at=data["updated_at"],
            qqq_close=strategy.market.qqq_close,
            qqq_sma200=strategy.market.qqq_sma200,
            qqq_distance_from_200ma=round(distance, 2),
        )
        data["journal"] = [*data.get("journal", []), deposit_entry.model_dump()]
        items[index] = ManagedStrategy.model_validate(data)
        _save(items, user_id)
        return items[index]
    raise KeyError(strategy_id)


def _build_issues(distance: float, tqqq_ratio: float, cash_ratio: float) -> list[ComplianceIssue]:
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
    if cash_ratio < 15:
        issues.append(
            ComplianceIssue(
                level="watch",
                title="방어 자금 부족",
                detail="200일선 이탈 또는 급락 대응을 위한 현금성 비중이 낮습니다.",
            )
        )
    return issues


def build_execution_plan(strategy: ManagedStrategy, distance: float) -> list[SplitExecutionStep]:
    target_symbol = "TQQQ" if _allocation_ratio(strategy, "TQQQ") else "QLD"
    plan: list[SplitExecutionStep] = []
    for index, step in enumerate(strategy.plan.buy_plan):
        status, reason = _buy_step_status(strategy, index, step.step, distance)
        trigger = _buy_trigger_detail(strategy, index)
        amount = _buy_step_amount(strategy, index, step.amount, distance, status)
        plan.append(
            SplitExecutionStep(
                side="buy",
                step=step.step,
                symbol=target_symbol,
                status=status,
                trigger=step.trigger,
                trigger_price=trigger["price"],
                trigger_label=trigger["label"],
                current_price=strategy.market.qqq_close,
                distance_to_trigger_pct=trigger["distance"],
                amount=round(amount),
                ratio_of_target=round(amount / _allocation_amount(strategy, target_symbol) * 100, 1)
                if _allocation_amount(strategy, target_symbol)
                else step.ratio_of_target,
                reason=reason,
                action_label=_action_label("buy", status, amount),
            )
        )
    for index, step in enumerate(strategy.plan.sell_plan):
        status, reason = _sell_step_status(strategy, index, step.step, distance)
        trigger = _sell_trigger_detail(strategy, index)
        plan.append(
            SplitExecutionStep(
                side="sell",
                step=step.step,
                symbol=target_symbol,
                status=status,
                trigger=step.trigger,
                trigger_price=trigger["price"],
                trigger_label=trigger["label"],
                current_price=strategy.market.qqq_close,
                distance_to_trigger_pct=trigger["distance"],
                amount=step.amount,
                ratio_of_target=step.ratio_of_target,
                reason=reason,
                action_label=_action_label("sell", status, step.amount),
            )
        )
    return plan


def _price_distance(current: float, trigger_price: float | None) -> float | None:
    if not trigger_price:
        return None
    return round((current / trigger_price - 1) * 100, 2)


def _buy_trigger_detail(strategy: ManagedStrategy, index: int) -> dict[str, float | str | None]:
    current = strategy.market.qqq_close
    sma20 = getattr(strategy.market, "qqq_sma20", None)
    sma50 = strategy.market.qqq_sma50
    sma200 = strategy.market.qqq_sma200
    if index == 0:
        price = sma200
        label = f"QQQ가 200일선 ${sma200:,.2f} 위에서 마감 유지"
    elif index == 1:
        if sma20:
            price = sma20 * 1.01
            label = f"2차 매수: QQQ가 20일선 ${sma20:,.2f} 기준 +1% 이내(${price:,.2f} 이하)로 조정"
        else:
            price = sma200 * 1.08
            label = f"2차 매수: 20일선 데이터가 없으므로 QQQ 200일선 대비 +8% 이하(${price:,.2f})로 이격 완화"
    else:
        if sma50:
            base = sma50
            price = sma50 * 1.02
            defense_price = sma50 * 1.01
            label = (
                f"3차 매수: QQQ가 50일선 ${base:,.2f} 기준 +1~+2% 방어 구간"
                f"(${defense_price:,.2f} 초과 ~ ${price:,.2f} 이하)에 있을 때만 검토"
            )
        else:
            price = sma200 * 1.05
            label = f"3차 매수: QQQ 200일선 대비 +5% 이하(${price:,.2f})로 이격 완화"
    return {"price": price, "label": label, "distance": _price_distance(current, price)}


def _reload_execution_step(strategy: ManagedStrategy, target_symbol: str, distance: float) -> SplitExecutionStep | None:
    if target_symbol != "TQQQ":
        return None
    target_amount = _allocation_amount(strategy, "TQQQ")
    if target_amount <= 0:
        return None
    executed = _executed_amounts(strategy).get("TQQQ", 0)
    progress = executed / target_amount * 100
    target_gap = max(target_amount - executed, 0)
    status, reason = _reload_status(strategy, distance, progress, target_gap)
    amount = 0 if status in {"blocked", "wait", "done"} else min(target_gap, strategy.total_capital * 0.05)
    trigger_price = min(
        strategy.market.qqq_sma50 * 1.01 if strategy.market.qqq_sma50 else strategy.market.qqq_sma200 * 1.05,
        strategy.market.qqq_sma200 * 1.05,
    )
    label = (
        "3차 이후 재장전: QQQ가 50일선 +1% 이내이거나 200일선 대비 +5% 이하로 이격 완화되고, "
        "TQQQ 목표 미달이 원금 2% 이상일 때만 검토"
    )
    return SplitExecutionStep(
        side="buy",
        step="재장전 검토",
        symbol="TQQQ",
        status=status,  # type: ignore[arg-type]
        trigger="3차 완료 후 엄격한 재장전 조건",
        trigger_price=trigger_price,
        trigger_label=label,
        current_price=strategy.market.qqq_close,
        distance_to_trigger_pct=_price_distance(strategy.market.qqq_close, trigger_price),
        amount=round(amount),
        ratio_of_target=round(amount / target_amount * 100, 1) if target_amount else 0,
        reason=reason,
        action_label=_action_label("buy", status, amount),
    )


def _reload_status(
    strategy: ManagedStrategy,
    distance: float,
    progress: float,
    target_gap: float,
) -> tuple[str, str]:
    if _has_journal_marker(strategy, "buy", "재장전"):
        return "done", "이미 기록장에 재장전 매수 기록이 있습니다. 다음 재장전은 새 추가금 또는 전략 버전 변경 후 다시 검토합니다."
    if progress < 95:
        return "wait", "아직 1~3차 기존 분할매수 사이클이 끝나지 않았습니다. 재장전보다 원래 분할 규칙을 먼저 따릅니다."
    if distance <= 0:
        return "blocked", "QQQ가 200일선 아래입니다. SGOV/CASH를 TQQQ 매수 재원으로 전환하지 않습니다."
    if strategy.market.qqq_sma50 and strategy.market.qqq_close < strategy.market.qqq_sma50:
        return "blocked", "QQQ가 50일선 아래라 리스크 축소 조건이 우선입니다. 추가 TQQQ 매수는 금지합니다."
    if distance > 5:
        return "blocked", "3차 이후 재장전은 QQQ 200일선 대비 +5% 이하로 이격이 완화될 때만 허용합니다."
    if target_gap < strategy.total_capital * 0.02:
        return "wait", "TQQQ 목표 미달분이 원금의 2% 미만입니다. 새 추가금이나 전략 변경 전까지 추가매수하지 않습니다."
    return "ready", "3차 완료, 200일선 위, 50일선 방어, 이격 +5% 이하, 목표 미달 2% 이상을 모두 충족했습니다. 1회 재장전은 원금 5% 이내로 제한합니다."


def _sell_trigger_detail(strategy: ManagedStrategy, index: int) -> dict[str, float | str | None]:
    current = strategy.market.qqq_close
    sma50 = strategy.market.qqq_sma50
    sma200 = strategy.market.qqq_sma200
    if index == 0:
        price = sma50 * 0.99 if sma50 else None
        label = (
            f"리스크 축소: QQQ가 50일선 ${sma50:,.2f} 대비 -1% 이하(${price:,.2f})로 이탈하거나 "
            "50일선 아래 2거래일 연속 마감할 때 일부 매도"
            if sma50
            else "50일선 데이터가 필요합니다"
        )
    elif index == 1:
        price = sma200
        label = f"방어 전환: QQQ가 200일선 ${sma200:,.2f} 아래로 2거래일 연속 마감"
    else:
        price = sma200 * 1.25
        label = f"수익 회수: QQQ가 200일선 대비 +25% 수준 ${price:,.2f} 이상"
    return {"price": price, "label": label, "distance": _price_distance(current, price)}


def _buy_step_status(strategy: ManagedStrategy, index: int, step: str, distance: float) -> tuple[str, str]:
    close = strategy.market.qqq_close
    sma20 = getattr(strategy.market, "qqq_sma20", None)
    sma50 = strategy.market.qqq_sma50
    target_symbol = "TQQQ" if _allocation_ratio(strategy, "TQQQ") else "QLD"
    target_amount = _allocation_amount(strategy, target_symbol)
    executed_amount = _executed_amounts(strategy).get(target_symbol, 0)
    progress = executed_amount / target_amount * 100 if target_amount else 0
    if _has_journal_marker(strategy, "buy", step):
        return "done", "이미 기록장에 실행 기록이 있습니다."
    if distance <= 0:
        return "blocked", "QQQ가 200일선 아래라 신규 레버리지 매수는 금지합니다."
    if distance >= 15:
        return "blocked", "QQQ 200일선 대비 +15% 이상에서는 신규 TQQQ/QLD 분할매수를 금지합니다. 현금/SGOV 대기와 기존 보유 관리가 우선입니다."
    if index == 0:
        if distance > 8:
            return "ready", "QQQ가 200일선 위지만 이격이 +8%를 넘어 1차는 축소 진입만 허용합니다."
        return "ready", "QQQ가 200일선 위이고 이격이 +8% 이하라 1차 분할매수 조건을 검토할 수 있습니다."
    if index == 1:
        if progress < 10:
            return "wait", "2차는 1차가 최소 10% 이상 집행된 뒤에만 검토합니다. 순서를 건너뛰지 않습니다."
        if sma20 and close <= sma20 * 1.01:
            return "ready", "QQQ가 20일선 근처로 눌려 2차 분할매수 후보입니다."
        if distance <= 8:
            return "ready", "QQQ 200일선 이격도가 완화되어 2차 분할매수 후보입니다."
        return "wait", "2차는 20일선 +1% 이내 눌림 또는 200일선 대비 +8% 이하 이격 완화 전까지 보류합니다."
    if progress < 45:
        return "wait", "3차는 1차와 2차가 합쳐 최소 45% 이상 집행된 뒤에만 검토합니다. 깊은 눌림 전 예비 현금을 보존합니다."
    if sma50 and close < sma50:
        return "blocked", "QQQ가 50일선 아래라 3차 매수보다 리스크 축소 판단이 우선입니다."
    if sma50 and close <= sma50 * 1.01:
        return "wait", "QQQ가 50일선 바로 위 1% 이내라 3차 매수와 리스크 축소 신호가 충돌할 수 있습니다. 50일선 방어 확인 전까지 보류합니다."
    if distance <= 5:
        return "ready", "QQQ가 200일선에 가까워져 마지막 분할매수 조건을 검토할 수 있습니다."
    if sma50 and close <= sma50 * 1.02:
        return "ready", "QQQ가 50일선을 아직 방어한 +1~+2% 깊은 눌림 구간이라 마지막 분할매수 후보입니다."
    return "wait", "3차는 50일선 +1~+2% 방어 구간 또는 200일선 대비 +5% 이하 이격 완화 때만 검토합니다."


def _buy_step_amount(strategy: ManagedStrategy, index: int, planned_amount: float, distance: float, status: str) -> float:
    if status != "ready":
        return 0
    target_symbol = "TQQQ" if _allocation_ratio(strategy, "TQQQ") else "QLD"
    target_amount = _allocation_amount(strategy, target_symbol)
    if index == 0 and distance > 8:
        return min(planned_amount, target_amount * 0.15)
    return planned_amount


def _sell_step_status(strategy: ManagedStrategy, index: int, step: str, distance: float) -> tuple[str, str]:
    if _has_journal_marker(strategy, "sell", step):
        return "done", "이미 기록장에 실행 기록이 있습니다."
    if index == 0 and strategy.market.qqq_sma50:
        if strategy.market.qqq_close <= strategy.market.qqq_sma50 * 0.99:
            return "ready", "QQQ가 50일선 대비 -1% 이하로 이탈해 일부 감축을 검토합니다."
        if strategy.market.qqq_close < strategy.market.qqq_sma50:
            return "wait", "QQQ가 50일선 아래지만 -1% 이탈은 아닙니다. 2거래일 연속 이탈 확인 전까지 성급한 매도를 피합니다."
    if index == 1 and distance <= 0:
        return "ready", "QQQ가 200일선 아래라 방어 전환을 검토합니다. 2거래일 확인이면 강제 실행입니다."
    if index >= 2 and distance >= 25:
        return "ready", "QQQ가 200일선 대비 +25% 이상이라 일부 이익실현을 검토합니다."
    return "wait", "현재는 해당 매도 조건이 충족되지 않았습니다."


def _has_journal_marker(strategy: ManagedStrategy, action: str, step: str) -> bool:
    marker = step.lower()
    return any(
        entry.entry_type == action and (marker in entry.reason.lower() or marker in entry.note.lower())
        for entry in strategy.journal
    )


def _action_label(side: str, status: str, amount: float) -> str:
    if status == "ready":
        action = "매수" if side == "buy" else "매도"
        return f"{action} 후보 {amount:,.0f}원"
    if status == "done":
        return "실행 완료"
    if status == "blocked":
        return "실행 금지"
    return "대기"


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
