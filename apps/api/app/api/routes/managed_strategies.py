import httpx
from fastapi import APIRouter, HTTPException, Query

from app.api.deps import OptionalCurrentUserDep
from app.repositories.managed_strategy_repository import (
    add_journal_entry,
    advise_adjustment,
    apply_deposit,
    advise_contribution,
    advise_philosophy_upgrade,
    apply_adjustment,
    apply_contribution,
    apply_philosophy_upgrade,
    build_backtest_request_from_strategy,
    build_guide,
    create_strategy,
    delete_journal_entry,
    delete_strategy,
    get_strategy,
    list_strategies,
    update_strategy,
)
from app.core.config import settings
from app.schemas.backtest import BacktestRunResponse
from app.schemas.managed_strategy import (
    AdoptResearchRequest,
    ContributionPlanAdvice,
    ContributionPlanApplyRequest,
    ContributionPlanRequest,
    DepositRequest,
    ManagedStrategy,
    ManagedStrategyCreate,
    ManagedStrategyGuide,
    ManagedStrategyUpdate,
    PhilosophyUpgradeAdvice,
    PhilosophyUpgradeApplyRequest,
    StrategyAdjustmentAdvice,
    StrategyAdjustmentApplyRequest,
    StrategyAdjustmentRequest,
    StrategyJournalCreate,
    TodayDecision,
)
from app.services.backtest_engine import run_backtest
from app.services.market_data import MarketDataError, fetch_provider_history
from app.services.research_adoption import build_research_adoption
from app.services.today_engine import compute_today_decision

router = APIRouter(prefix="/managed-strategies", tags=["managed-strategies"])


@router.get("", response_model=list[ManagedStrategy])
async def get_managed_strategies(current_user: OptionalCurrentUserDep) -> list[ManagedStrategy]:
    return list_strategies(current_user.user_id if current_user else None)


@router.post("", response_model=ManagedStrategy)
async def post_managed_strategy(payload: ManagedStrategyCreate, current_user: OptionalCurrentUserDep) -> ManagedStrategy:
    return create_strategy(payload, current_user.user_id if current_user else None)


@router.post("/adopt-research", response_model=ManagedStrategy)
async def post_adopt_research(
    payload: AdoptResearchRequest, current_user: OptionalCurrentUserDep
) -> ManagedStrategy:
    try:
        create = build_research_adoption(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return create_strategy(create, current_user.user_id if current_user else None)


@router.get("/{strategy_id}/today", response_model=TodayDecision)
async def get_today_decision(
    strategy_id: str, current_user: OptionalCurrentUserDep
) -> TodayDecision:
    try:
        strategy = get_strategy(strategy_id, current_user.user_id if current_user else None)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc
    if strategy.research_config is None:
        raise HTTPException(
            status_code=400,
            detail="이 전략에는 연구 규칙 설정이 없습니다. 개인연구 탭에서 전략을 채택하면 오늘 판단을 사용할 수 있습니다.",
        )
    if strategy.research_config.strategy != "tqqq_daily_200ma":
        raise HTTPException(
            status_code=400,
            detail="이 전략은 분할 실행 카드로 관리됩니다. 오늘 판단 계산은 매일 적립 전략 전용입니다.",
        )
    try:
        qqq_rows = await fetch_provider_history("QQQ", settings.market_data_provider.lower())
    except (httpx.HTTPError, MarketDataError) as exc:
        raise HTTPException(status_code=502, detail=f"Market data request failed: {exc}") from exc
    try:
        return compute_today_decision(strategy.research_config, qqq_rows)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{strategy_id}", response_model=ManagedStrategy)
async def get_managed_strategy(strategy_id: str, current_user: OptionalCurrentUserDep) -> ManagedStrategy:
    try:
        return get_strategy(strategy_id, current_user.user_id if current_user else None)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc


@router.delete("/{strategy_id}", response_model=list[ManagedStrategy])
async def delete_managed_strategy(
    strategy_id: str, current_user: OptionalCurrentUserDep
) -> list[ManagedStrategy]:
    try:
        return delete_strategy(strategy_id, current_user.user_id if current_user else None)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc


@router.patch("/{strategy_id}", response_model=ManagedStrategy)
async def patch_managed_strategy(strategy_id: str, payload: ManagedStrategyUpdate, current_user: OptionalCurrentUserDep) -> ManagedStrategy:
    try:
        return update_strategy(strategy_id, payload, current_user.user_id if current_user else None)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc


@router.post("/{strategy_id}/deposit", response_model=ManagedStrategy)
async def post_deposit(
    strategy_id: str, payload: DepositRequest, current_user: OptionalCurrentUserDep
) -> ManagedStrategy:
    try:
        return apply_deposit(strategy_id, payload, current_user.user_id if current_user else None)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc


@router.post("/{strategy_id}/journal", response_model=ManagedStrategy)
async def post_journal(strategy_id: str, payload: StrategyJournalCreate, current_user: OptionalCurrentUserDep) -> ManagedStrategy:
    try:
        return add_journal_entry(strategy_id, payload, current_user.user_id if current_user else None)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc


@router.delete("/{strategy_id}/journal/{entry_id}", response_model=ManagedStrategy)
async def delete_journal(strategy_id: str, entry_id: str, current_user: OptionalCurrentUserDep) -> ManagedStrategy:
    try:
        return delete_journal_entry(strategy_id, entry_id, current_user.user_id if current_user else None)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy or journal entry not found") from exc


@router.get("/{strategy_id}/guide", response_model=ManagedStrategyGuide)
async def get_guide(strategy_id: str, current_user: OptionalCurrentUserDep) -> ManagedStrategyGuide:
    try:
        return build_guide(get_strategy(strategy_id, current_user.user_id if current_user else None))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc


@router.post("/{strategy_id}/backtest", response_model=BacktestRunResponse)
async def post_managed_strategy_backtest(
    strategy_id: str,
    current_user: OptionalCurrentUserDep,
    projection_years: int = Query(default=3, ge=1, le=10),
    cash_yield: float = Query(default=3.0, ge=0, le=10),
) -> BacktestRunResponse:
    try:
        request = build_backtest_request_from_strategy(
            get_strategy(strategy_id, current_user.user_id if current_user else None),
            projection_years=projection_years,
            cash_yield=cash_yield,
        )
        return await run_backtest(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Market data request failed: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{strategy_id}/adjustment-advice", response_model=StrategyAdjustmentAdvice)
async def post_adjustment_advice(
    strategy_id: str,
    payload: StrategyAdjustmentRequest,
    current_user: OptionalCurrentUserDep,
) -> StrategyAdjustmentAdvice:
    try:
        return advise_adjustment(get_strategy(strategy_id, current_user.user_id if current_user else None), payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc


@router.post("/{strategy_id}/apply-adjustment", response_model=ManagedStrategy)
async def post_apply_adjustment(
    strategy_id: str,
    payload: StrategyAdjustmentApplyRequest,
    current_user: OptionalCurrentUserDep,
) -> ManagedStrategy:
    try:
        return apply_adjustment(strategy_id, payload, current_user.user_id if current_user else None)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc


@router.post("/{strategy_id}/contribution-advice", response_model=ContributionPlanAdvice)
async def post_contribution_advice(
    strategy_id: str,
    payload: ContributionPlanRequest,
    current_user: OptionalCurrentUserDep,
) -> ContributionPlanAdvice:
    try:
        return advise_contribution(get_strategy(strategy_id, current_user.user_id if current_user else None), payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc


@router.post("/{strategy_id}/apply-contribution", response_model=ManagedStrategy)
async def post_apply_contribution(
    strategy_id: str,
    payload: ContributionPlanApplyRequest,
    current_user: OptionalCurrentUserDep,
) -> ManagedStrategy:
    try:
        return apply_contribution(strategy_id, payload, current_user.user_id if current_user else None)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc


@router.post("/{strategy_id}/philosophy-advice", response_model=PhilosophyUpgradeAdvice)
async def post_philosophy_advice(
    strategy_id: str,
    current_user: OptionalCurrentUserDep,
) -> PhilosophyUpgradeAdvice:
    try:
        return advise_philosophy_upgrade(get_strategy(strategy_id, current_user.user_id if current_user else None))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc


@router.post("/{strategy_id}/apply-philosophy-upgrade", response_model=ManagedStrategy)
async def post_apply_philosophy_upgrade(
    strategy_id: str,
    payload: PhilosophyUpgradeApplyRequest,
    current_user: OptionalCurrentUserDep,
) -> ManagedStrategy:
    try:
        return apply_philosophy_upgrade(strategy_id, payload, current_user.user_id if current_user else None)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc
