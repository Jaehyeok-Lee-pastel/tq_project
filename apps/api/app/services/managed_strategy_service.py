from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.managed_strategy_repository import (
    _load,
    _save,
    delete_strategy_record,
)
from app.repositories.managed_strategy_repository import (
    get_strategy as repository_get_strategy,
)
from app.repositories.managed_strategy_repository import (
    list_strategies as repository_list_strategies,
)
from app.schemas.backtest import BacktestRunRequest
from app.schemas.managed_strategy import (
    ContributionPlanApplyRequest,
    DepositRequest,
    ManagedStrategy,
    ManagedStrategyCreate,
    ManagedStrategyUpdate,
    PhilosophyUpgradeApplyRequest,
    StrategyAdjustmentApplyRequest,
    StrategyJournalCreate,
    StrategyJournalEntry,
    StrategyVersionAllocation,
    StrategyVersionEntry,
)
from app.services.managed_strategy_model import (
    _allocation_ratio,
    _one_x_buffer_ratio,
    _primary_one_x_symbol,
    _role_for_adjusted_symbol,
    _strategy_to_latest_recommend_request,
    _version_allocations_from_plan,
)
from app.services.strategy_coaching import (
    advise_adjustment,
    advise_contribution,
    advise_philosophy_upgrade,
    build_guide,
)
from app.services.strategy_engine import recommend_strategy
from app.services.strategy_execution import build_execution_plan

__all__ = [
    "add_journal_entry",
    "advise_adjustment",
    "advise_contribution",
    "advise_philosophy_upgrade",
    "apply_adjustment",
    "apply_contribution",
    "apply_deposit",
    "apply_philosophy_upgrade",
    "build_backtest_request_from_strategy",
    "build_execution_plan",
    "build_guide",
    "create_strategy",
    "delete_journal_entry",
    "delete_strategy",
    "get_strategy",
    "list_strategies",
    "update_strategy",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_strategies(user_id: str | None = None) -> list[ManagedStrategy]:
    return repository_list_strategies(user_id)


def get_strategy(strategy_id: str, user_id: str | None = None) -> ManagedStrategy:
    return repository_get_strategy(strategy_id, user_id)


def build_backtest_request_from_strategy(
    strategy: ManagedStrategy,
    projection_years: int = 3,
    cash_yield: float = 3.0,
) -> BacktestRunRequest:
    if strategy.research_config is not None:
        # Run exactly the rules the research lab validated, starting from the
        # strategy's current holdings split.
        config = strategy.research_config
        total = max(strategy.total_capital, 1)
        return BacktestRunRequest(
            strategy=config.strategy,
            initial_capital=total,
            initial_tqqq_value=_allocation_ratio(strategy, "TQQQ") / 100 * total,
            initial_one_x_value=_allocation_ratio(strategy, config.one_x_symbol) / 100 * total,
            initial_cash_value=_allocation_ratio(strategy, "CASH") / 100 * total,
            monthly_contribution=config.monthly_contribution,
            daily_base_tqqq_ratio=config.daily_base_tqqq_ratio,
            daily_base_one_x_ratio=config.daily_base_one_x_ratio,
            one_x_symbol=config.one_x_symbol,
            ma_exit_band_pct=config.ma_exit_band_pct,
            defense_mode=config.defense_mode,
            one_x_upfront_monthly=config.one_x_upfront_monthly,
            moving_average_days=config.moving_average_days,
            tqqq_target_ratio=config.tqqq_target_ratio,
            qld_target_ratio=config.qld_target_ratio,
            cash_yield=cash_yield,
            projection_years=projection_years,
        )

    tqqq_ratio = _allocation_ratio(strategy, "TQQQ")
    qld_ratio = _allocation_ratio(strategy, "QLD")
    one_x_ratio = _one_x_buffer_ratio(strategy)
    one_x_symbol = _primary_one_x_symbol(strategy)
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
        one_x_target_ratio=round(one_x_ratio, 1),
        one_x_symbol=one_x_symbol,
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


def apply_deposit(
    strategy_id: str,
    payload: DepositRequest,
    user_id: str | None = None,
) -> ManagedStrategy:
    """Salary-day deposit: grow cash + total capital, log it, bump version."""
    items = _load(user_id)
    for index, strategy in enumerate(items):
        if strategy.id != strategy_id:
            continue
        before = _version_allocations_from_plan(strategy.plan)
        data = strategy.model_dump()
        new_total = strategy.total_capital + payload.amount

        allocations = data["plan"]["allocations"]
        cash_allocation = next(
            (item for item in allocations if item["symbol"].upper() == "CASH"), None
        )
        if cash_allocation is None:
            cash_allocation = {
                "symbol": "CASH",
                "name": "현금/SGOV",
                "target_ratio": 0.0,
                "target_amount": 0.0,
                "role": "방어·집행 대기",
            }
            allocations.append(cash_allocation)
        cash_allocation["target_amount"] = round(cash_allocation["target_amount"] + payload.amount, 2)
        for item in allocations:
            item["target_ratio"] = round(item["target_amount"] / new_total * 100, 1) if new_total else 0.0

        data["total_capital"] = new_total
        now = utc_now()
        distance = (strategy.market.qqq_close / strategy.market.qqq_sma200 - 1) * 100
        entry = StrategyJournalEntry(
            entry_type="deposit",
            symbol="CASH",
            amount=payload.amount,
            quantity=0,
            price=0,
            reason="월급 추가금 입금 — 규칙에 따라 일 단위로 분할 집행됩니다",
            mood="calm",
            note=payload.note or "월급일 정기 입금",
            id=uuid4().hex,
            created_at=now,
            qqq_close=strategy.market.qqq_close,
            qqq_sma200=strategy.market.qqq_sma200,
            qqq_distance_from_200ma=round(distance, 2),
        )
        data["journal"] = [*data["journal"], entry.model_dump()]
        data["version"] = strategy.version + 1
        data["updated_at"] = now
        updated = ManagedStrategy.model_validate(data)
        data["version_history"] = [
            *data["version_history"],
            StrategyVersionEntry(
                version=updated.version,
                created_at=now,
                change_type="manual",
                title=f"월급 추가금 {payload.amount:,.0f}원 입금",
                note=payload.note,
                before_allocations=before,
                after_allocations=_version_allocations_from_plan(updated.plan),
            ).model_dump(),
        ]
        items[index] = ManagedStrategy.model_validate(data)
        _save(items, user_id)
        return items[index]
    raise KeyError(strategy_id)


def delete_strategy(strategy_id: str, user_id: str | None = None) -> list[ManagedStrategy]:
    return delete_strategy_record(strategy_id, user_id)


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
                note=" / ".join(selected_plan.actions if selected_plan else advice.actions),
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


def apply_philosophy_upgrade(
    strategy_id: str,
    payload: PhilosophyUpgradeApplyRequest,
    user_id: str | None = None,
) -> ManagedStrategy:
    items = _load(user_id)
    for index, strategy in enumerate(items):
        if strategy.id != strategy_id:
            continue
        request = _strategy_to_latest_recommend_request(strategy)
        response = recommend_strategy(request)
        suggested = response.plans[0]
        data = strategy.model_dump()
        before = _version_allocations_from_plan(strategy.plan)
        data["plan"] = suggested.model_dump()
        data["version"] = strategy.version + 1
        data["updated_at"] = utc_now()
        updated = ManagedStrategy.model_validate(data)
        history = list(strategy.version_history)
        history.append(
            StrategyVersionEntry(
                version=updated.version,
                created_at=updated.updated_at,
                change_type="philosophy",
                title=payload.accepted_headline or "최신 TQQQ 200일선 철학 반영",
                note=(
                    f"기존 '{strategy.plan.title}' 전략을 최신 철학 '{suggested.title}' 기준으로 재설계했습니다. "
                    f"QQQ 200일선 이격 {response.qqq_distance_from_200ma:.2f}%, 추정 리스크 {request.profile.risk_score}점."
                ),
                before_allocations=before,
                after_allocations=_version_allocations_from_plan(suggested),
            )
        )
        data["version_history"] = [item.model_dump() for item in history]
        items[index] = ManagedStrategy.model_validate(data)
        _save(items, user_id)
        return items[index]
    raise KeyError(strategy_id)


