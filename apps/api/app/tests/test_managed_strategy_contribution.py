from app.repositories import managed_strategy_repository as repository
from app.schemas.managed_strategy import (
    ContributionPlanApplyRequest,
    ManagedStrategyCreate,
    StrategyJournalCreate,
)
from app.schemas.strategy import (
    ConfidenceBreakdown,
    MarketSnapshot,
    PortfolioAllocation,
    RiskMetric,
    SplitStep,
    StrategyPlan,
    StrategyScores,
    TradeAction,
)


def make_plan(total_capital: float) -> StrategyPlan:
    return StrategyPlan(
        id="test-plan",
        title="테스트 전략",
        summary="QQQ 200일선 기반 테스트 전략",
        allocations=[
            PortfolioAllocation(
                symbol="TQQQ",
                name="ProShares UltraPro QQQ",
                target_ratio=30,
                target_amount=total_capital * 0.3,
                role="공격 엔진",
            ),
            PortfolioAllocation(
                symbol="SGOV",
                name="iShares 0-3 Month Treasury Bond ETF",
                target_ratio=30,
                target_amount=total_capital * 0.3,
                role="현금성 대기자산",
            ),
            PortfolioAllocation(
                symbol="SPYM",
                name="SPDR Portfolio S&P 500 ETF",
                target_ratio=40,
                target_amount=total_capital * 0.4,
                role="코어 자산",
            ),
        ],
        actions=[
            TradeAction(symbol="TQQQ", action="wait", amount=0, reason="조건 대기"),
        ],
        buy_plan=[
            SplitStep(step="1차 매수", trigger="QQQ 200일선 위", ratio_of_target=30, amount=total_capital * 0.09, note=""),
            SplitStep(step="2차 매수", trigger="QQQ 20일선 근처", ratio_of_target=35, amount=total_capital * 0.105, note=""),
            SplitStep(step="3차 매수", trigger="QQQ 50일선 근처", ratio_of_target=35, amount=total_capital * 0.105, note=""),
        ],
        sell_plan=[
            SplitStep(step="리스크 축소", trigger="QQQ 50일선 아래", ratio_of_target=30, amount=total_capital * 0.09, note=""),
        ],
        risk_metrics=[
            RiskMetric(label="리스크", value="중간", level="medium"),
        ],
        scores=StrategyScores(
            confidence_score=80,
            risk_score=70,
            fit_score=85,
            expected_return_score=75,
            execution_difficulty="medium",
            confidence_breakdown=ConfidenceBreakdown(
                rule_clarity=80,
                market_fit=80,
                cash_defense=80,
                drawdown_control=70,
                overfit_resistance=70,
                execution_quality=80,
                user_fit=85,
            ),
            confidence_notes=["테스트"],
        ),
        pros=["규칙 기반"],
        cons=["레버리지 위험"],
    )


def test_apply_contribution_records_deposit_without_auto_trade(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DATA_PATH", tmp_path / "managed_strategies.json")
    strategy = repository.create_strategy(
        ManagedStrategyCreate(
            plan=make_plan(2_500_000),
            market=MarketSnapshot(
                qqq_close=736.4,
                qqq_sma200=633.63,
                qqq_sma20=720.18,
                qqq_sma50=706.22,
                qqq_high20=736.4,
                as_of="2026-07-02",
            ),
            total_capital=2_500_000,
            selected_reason="테스트 생성",
        )
    )

    updated = repository.apply_contribution(
        strategy.id,
        ContributionPlanApplyRequest(
            contribution_amount=1_000_000,
            pay_day=10,
            selected_plan_id="keep_current",
        ),
    )

    assert updated.total_capital == 3_500_000
    assert updated.version == 2
    assert updated.plan.allocations[0].target_amount == 1_050_000
    assert updated.journal[-1].entry_type == "deposit"
    assert updated.journal[-1].symbol == "CASH"
    assert updated.journal[-1].amount == 1_000_000
    assert "실제 ETF 매수" in updated.journal[-1].note
    assert updated.version_history[-1].change_type == "manual"


def test_default_execution_plan_hides_reload_step_after_three_buys(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DATA_PATH", tmp_path / "managed_strategies.json")
    plan = make_plan(2_500_000)
    plan.allocations[0].target_ratio = 50
    plan.allocations[0].target_amount = 1_250_000
    plan.allocations[1].target_ratio = 20
    plan.allocations[1].target_amount = 500_000
    plan.allocations[2].target_ratio = 30
    plan.allocations[2].target_amount = 750_000
    strategy = repository.create_strategy(
        ManagedStrategyCreate(
            plan=plan,
            market=MarketSnapshot(
                qqq_close=655,
                qqq_sma200=633.63,
                qqq_sma20=650,
                qqq_sma50=640,
                qqq_high20=670,
                as_of="2026-07-02",
            ),
            total_capital=2_500_000,
            selected_reason="재장전 테스트",
        )
    )
    strategy = repository.add_journal_entry(
        strategy.id,
        StrategyJournalCreate(
            entry_type="buy",
            symbol="TQQQ",
            amount=1_190_000,
            reason="1차 매수 2차 매수 3차 매수 완료",
            note="기존 분할 완료",
        ),
    )

    guide = repository.build_guide(strategy)

    assert all(step.step != "재장전 검토" for step in guide.execution_plan)


def test_split_buy_blocks_first_entry_when_qqq_is_too_stretched(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DATA_PATH", tmp_path / "managed_strategies.json")
    strategy = repository.create_strategy(
        ManagedStrategyCreate(
            plan=make_plan(2_500_000),
            market=MarketSnapshot(
                qqq_close=736.4,
                qqq_sma200=633.63,
                qqq_sma20=720.18,
                qqq_sma50=706.22,
                qqq_high20=736.4,
                as_of="2026-07-02",
            ),
            total_capital=2_500_000,
            selected_reason="과열 분할매수 테스트",
        )
    )

    guide = repository.build_guide(strategy)
    first_buy = next(step for step in guide.execution_plan if step.step == "1차 매수")

    assert first_buy.status == "blocked"
    assert first_buy.amount == 0
    assert "+15% 이상" in first_buy.reason


def test_split_buy_requires_sequence_before_second_and_third(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DATA_PATH", tmp_path / "managed_strategies.json")
    strategy = repository.create_strategy(
        ManagedStrategyCreate(
            plan=make_plan(2_500_000),
            market=MarketSnapshot(
                qqq_close=655,
                qqq_sma200=633.63,
                qqq_sma20=660,
                qqq_sma50=650,
                qqq_high20=670,
                as_of="2026-07-02",
            ),
            total_capital=2_500_000,
            selected_reason="순서 제한 테스트",
        )
    )

    guide = repository.build_guide(strategy)
    second_buy = next(step for step in guide.execution_plan if step.step == "2차 매수")
    third_buy = next(step for step in guide.execution_plan if step.step == "3차 매수")

    assert second_buy.status == "wait"
    assert third_buy.status == "wait"
    assert "1차" in second_buy.reason
    assert "45%" in third_buy.reason


def test_third_buy_waits_when_too_close_to_50ma_and_sell_is_not_ready(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DATA_PATH", tmp_path / "managed_strategies.json")
    strategy = repository.create_strategy(
        ManagedStrategyCreate(
            plan=make_plan(2_500_000),
            market=MarketSnapshot(
                qqq_close=712.60,
                qqq_sma200=633.63,
                qqq_sma20=720.18,
                qqq_sma50=709.15,
                qqq_high20=736.4,
                as_of="2026-07-02",
            ),
            total_capital=2_500_000,
            selected_reason="50일선 충돌 방지 테스트",
        )
    )
    strategy = repository.add_journal_entry(
        strategy.id,
        StrategyJournalCreate(
            entry_type="buy",
            symbol="TQQQ",
            amount=225_000,
            reason="1차 매수 완료",
        ),
    )
    strategy = repository.add_journal_entry(
        strategy.id,
        StrategyJournalCreate(
            entry_type="buy",
            symbol="TQQQ",
            amount=262_500,
            reason="2차 매수 완료",
        ),
    )

    guide = repository.build_guide(strategy)
    third_buy = next(step for step in guide.execution_plan if step.step == "3차 매수")
    first_sell = next(step for step in guide.execution_plan if step.step == "리스크 축소")

    assert third_buy.status == "wait"
    assert "50일선 바로 위 1% 이내" in third_buy.reason
    assert first_sell.status == "wait"


def test_first_sell_is_ready_only_after_confirmed_50ma_break(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DATA_PATH", tmp_path / "managed_strategies.json")
    strategy = repository.create_strategy(
        ManagedStrategyCreate(
            plan=make_plan(2_500_000),
            market=MarketSnapshot(
                qqq_close=701.50,
                qqq_sma200=633.63,
                qqq_sma20=720.18,
                qqq_sma50=709.15,
                qqq_high20=736.4,
                as_of="2026-07-02",
            ),
            total_capital=2_500_000,
            selected_reason="50일선 이탈 확인 테스트",
        )
    )

    guide = repository.build_guide(strategy)
    first_sell = next(step for step in guide.execution_plan if step.step == "리스크 축소")

    assert first_sell.status == "ready"
    assert "-1% 이하" in first_sell.reason


def test_managed_strategy_builds_tqqq_backtest_request(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DATA_PATH", tmp_path / "managed_strategies.json")
    strategy = repository.create_strategy(
        ManagedStrategyCreate(
            plan=make_plan(2_500_000),
            market=MarketSnapshot(
                qqq_close=655,
                qqq_sma200=633.63,
                qqq_sma20=660,
                qqq_sma50=650,
                qqq_high20=670,
                as_of="2026-07-02",
            ),
            total_capital=2_500_000,
            selected_reason="백테스트 변환 테스트",
        )
    )

    request = repository.build_backtest_request_from_strategy(
        strategy,
        projection_years=5,
        cash_yield=4.2,
    )

    assert request.strategy == "tqqq_200ma"
    assert request.initial_capital == 2_500_000
    assert request.tqqq_target_ratio == 30
    assert request.qld_target_ratio == 0
    assert request.projection_years == 5
    assert request.cash_yield == 4.2


def test_managed_strategy_builds_qld_backtest_when_no_tqqq(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DATA_PATH", tmp_path / "managed_strategies.json")
    plan = make_plan(2_500_000)
    plan.allocations = [
        PortfolioAllocation(
            symbol="QLD",
            name="ProShares Ultra QQQ",
            target_ratio=45,
            target_amount=1_125_000,
            role="중간 레버리지 엔진",
        ),
        PortfolioAllocation(
            symbol="SGOV",
            name="iShares 0-3 Month Treasury Bond ETF",
            target_ratio=55,
            target_amount=1_375_000,
            role="현금성 대기자산",
        ),
    ]
    strategy = repository.create_strategy(
        ManagedStrategyCreate(
            plan=plan,
            market=MarketSnapshot(
                qqq_close=655,
                qqq_sma200=633.63,
                qqq_sma20=660,
                qqq_sma50=650,
                qqq_high20=670,
                as_of="2026-07-02",
            ),
            total_capital=2_500_000,
            selected_reason="QLD 백테스트 변환 테스트",
        )
    )

    request = repository.build_backtest_request_from_strategy(strategy)

    assert request.strategy == "qld_200ma"
    assert request.tqqq_target_ratio == 0
    assert request.qld_target_ratio == 45
