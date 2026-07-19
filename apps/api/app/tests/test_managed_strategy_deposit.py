"""Salary-day deposit: cash grows, journal records it, rules stay untouched."""

import pytest

from app.repositories import managed_strategy_repository as repo
from app.schemas.managed_strategy import (
    AdoptResearchRequest,
    DepositRequest,
    ResearchStrategyConfig,
)
from app.schemas.strategy import MarketSnapshot
from app.services.research_adoption import build_research_adoption


@pytest.fixture()
def strategy(monkeypatch, tmp_path):
    monkeypatch.setattr(repo, "DATA_PATH", tmp_path / "managed_strategies.json")
    payload = AdoptResearchRequest(
        research_config=ResearchStrategyConfig(
            strategy="tqqq_daily_200ma",
            daily_base_tqqq_ratio=80,
            daily_base_one_x_ratio=20,
            ma_exit_band_pct=2,
            defense_mode="cash",
            monthly_contribution=1_000_000,
            preset_id="daily_70_30_early_defense_cash_v1",
            preset_version="2026-07",
        ),
        market=MarketSnapshot(qqq_close=720.0, qqq_sma200=636.0, as_of="2026-07-09"),
        tqqq_value=1_600_000,
        one_x_value=500_000,
        cash_value=400_000,
        selected_reason="test",
    )
    return repo.create_strategy(build_research_adoption(payload))


def test_deposit_grows_cash_and_total(strategy):
    updated = repo.apply_deposit(strategy.id, DepositRequest(amount=1_000_000))

    assert updated.total_capital == 3_500_000
    cash = next(a for a in updated.plan.allocations if a.symbol == "CASH")
    assert cash.target_amount == pytest.approx(1_400_000)
    assert cash.target_ratio == pytest.approx(40.0)
    tqqq = next(a for a in updated.plan.allocations if a.symbol == "TQQQ")
    assert tqqq.target_amount == pytest.approx(1_600_000)  # holdings untouched
    assert tqqq.target_ratio == pytest.approx(45.7, abs=0.1)


def test_deposit_leaves_audit_trail(strategy):
    updated = repo.apply_deposit(
        strategy.id, DepositRequest(amount=1_000_000, note="7월 월급")
    )

    deposits = [e for e in updated.journal if e.entry_type == "deposit"]
    assert len(deposits) == 1
    assert deposits[0].amount == 1_000_000
    assert deposits[0].symbol == "CASH"
    assert updated.version == strategy.version + 1
    assert any("월급 추가금" in v.title for v in updated.version_history)


def test_deposit_does_not_touch_rules(strategy):
    updated = repo.apply_deposit(strategy.id, DepositRequest(amount=500_000))
    assert updated.research_config == strategy.research_config
    assert updated.research_config.preset_id == "daily_70_30_early_defense_cash_v1"
    assert updated.research_config.preset_version == "2026-07"


def test_deposit_unknown_strategy_raises(strategy):
    with pytest.raises(KeyError):
        repo.apply_deposit("missing-id", DepositRequest(amount=1_000))
