from fastapi.testclient import TestClient

from app.api.routes import strategy as strategy_route
from app.main import app
from app.repositories import managed_strategy_repository as strategy_repository

client = TestClient(app)


def strategy_payload(*, use_ai: bool = False) -> dict:
    return {
        "holdings": [
            {
                "symbol": "QLD",
                "name": "ProShares Ultra QQQ",
                "amount": 1_500_000,
                "category": "nasdaq_leverage",
            },
            {
                "symbol": "ACE K반도체TOP2",
                "name": "ACE K반도체TOP2",
                "amount": 1_000_000,
                "category": "semiconductor",
            },
        ],
        "cash": 0,
        "profile": {
            "risk_profile": "aggressive",
            "risk_score": 78,
            "target_count": 3,
            "allow_tqqq": True,
            "prefer_200ma": True,
            "min_cash_ratio": 20,
            "max_tqqq_ratio": 50,
            "max_semiconductor_ratio": 35,
            "max_single_position_ratio": 60,
            "goal": "TQQQ 200일선 기반 공격형 포트폴리오",
        },
        "market": {
            "qqq_close": 712.60,
            "qqq_sma200": 633.63,
            "qqq_sma20": 718.20,
            "qqq_sma50": 709.15,
            "qqq_high20": 736.40,
            "as_of": "2026-07-10",
        },
        "use_ai": use_ai,
    }


def test_strategy_recommendation_keeps_allocation_totals_consistent():
    response = client.post("/strategy/recommend", json=strategy_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["total_capital"] == 2_500_000
    assert data["plans"]
    assert data["ai_used"] is False
    for plan in data["plans"]:
        assert abs(sum(item["target_ratio"] for item in plan["allocations"]) - 100) <= 0.2
        assert abs(sum(item["target_amount"] for item in plan["allocations"]) - 2_500_000) <= 2


def test_strategy_ai_failure_falls_back_to_rule_based_report(monkeypatch):
    def fail_ai(*_args, **_kwargs):
        raise RuntimeError("AI unavailable")

    monkeypatch.setattr(strategy_route, "generate_coach_report", fail_ai)
    response = client.post("/strategy/recommend", json=strategy_payload(use_ai=True))

    assert response.status_code == 200
    assert response.json()["ai_used"] is False
    assert response.json()["coach_report"]["headline"]


def test_daily_accumulation_research_insight_context_is_accepted():
    response = client.post(
        "/insights/interpret",
        json={
            "context": "daily_accumulation_research",
            "use_ai": False,
            "payload": {
                "rankings": [
                    {
                        "strategy_name": "TQQQ 일일 적립 감속",
                        "total_score": 83,
                        "cagr": 18.2,
                        "max_drawdown": -42.5,
                        "verdict": "best_fit",
                    }
                ],
                "sensitivity": {"robustness_score": 78, "verdict": "robust"},
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["confidence_level"] == "high"
    assert data["ai_used"] is False
    assert data["strongest_evidence"]


def test_recommend_adopt_manage_and_delete_workflow(tmp_path, monkeypatch):
    monkeypatch.setattr(
        strategy_repository,
        "DATA_PATH",
        tmp_path / "managed_strategies.json",
    )
    recommendation = client.post("/strategy/recommend", json=strategy_payload()).json()
    selected_plan = next(
        plan
        for plan in recommendation["plans"]
        if plan["id"] == recommendation["coach_report"]["recommended_plan_id"]
    )

    adopted = client.post(
        "/managed-strategies",
        json={
            "plan": selected_plan,
            "market": strategy_payload()["market"],
            "total_capital": recommendation["total_capital"],
            "selected_reason": "통합 테스트에서 추천 전략 채택",
        },
    )
    assert adopted.status_code == 200
    strategy_id = adopted.json()["id"]

    listed = client.get("/managed-strategies")
    guide = client.get(f"/managed-strategies/{strategy_id}/guide")
    adjustment = client.post(
        f"/managed-strategies/{strategy_id}/adjustment-advice",
        json={"target_cash_ratio": 25, "note": "현금 비중 점검"},
    )
    contribution = client.post(
        f"/managed-strategies/{strategy_id}/contribution-advice",
        json={"contribution_amount": 1_000_000, "pay_day": 10},
    )
    journal = client.post(
        f"/managed-strategies/{strategy_id}/journal",
        json={
            "entry_type": "note",
            "symbol": "TQQQ",
            "reason": "규칙 확인",
            "note": "실행 전 점검",
        },
    )

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [strategy_id]
    assert guide.status_code == 200
    assert 0 <= guide.json()["compliance_score"] <= 100
    assert adjustment.status_code == 200
    assert adjustment.json()["suggested_allocations"]
    assert contribution.status_code == 200
    assert contribution.json()["plans"]
    assert journal.status_code == 200
    assert journal.json()["journal"][-1]["note"] == "실행 전 점검"

    deleted = client.delete(f"/managed-strategies/{strategy_id}")
    assert deleted.status_code == 200
    assert deleted.json() == []
