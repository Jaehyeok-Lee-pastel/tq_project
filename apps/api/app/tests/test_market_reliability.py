from datetime import date, datetime, timedelta, timezone

from app.api.routes.market import (
    PriceRow,
    apply_cross_validation,
    reliability_failure_item,
    reliability_item,
)
from app.services.market_data import business_days_since


def make_rows(count: int, latest_offset_days: int = 0) -> list[PriceRow]:
    latest = datetime.now(timezone.utc).date() - timedelta(days=latest_offset_days)
    start = latest - timedelta(days=count - 1)
    return [
        PriceRow(date=(start + timedelta(days=index)).isoformat(), close=100 + index)
        for index in range(count)
    ]


def test_reliability_item_scores_complete_recent_data_as_ok():
    item = reliability_item("QQQ", "test", make_rows(300))

    assert item.status == "ok"
    assert item.score >= 85
    assert item.has_sma20 is True
    assert item.has_sma50 is True
    assert item.has_sma200 is True


def test_reliability_item_warns_when_data_is_short_or_stale():
    item = reliability_item("TQQQ", "test", make_rows(40, latest_offset_days=7))

    assert item.status in {"watch", "danger"}
    assert item.score < 85
    assert item.has_sma20 is True
    assert item.has_sma50 is False
    assert item.has_sma200 is False


def test_reliability_failure_item_marks_provider_error_as_danger():
    item = reliability_failure_item("QQQ", "stooq", "All connection attempts failed")

    assert item.status == "danger"
    assert item.score == 0
    assert item.row_count == 0
    assert item.has_sma200 is False
    assert "시세 제공자 연결에 실패" in item.message


def test_business_day_age_does_not_penalize_weekend():
    assert business_days_since("2026-07-10", date(2026, 7, 12)) == 0
    assert business_days_since("2026-07-10", date(2026, 7, 13)) == 1


def test_business_day_age_rejects_invalid_date():
    assert business_days_since("not-a-date", date(2026, 7, 13)) == 999


def test_cross_validation_accepts_small_qqq_gap():
    item = reliability_item("QQQ", "yahoo", make_rows(300))
    secondary = [PriceRow(date=item.latest_date, close=make_rows(300)[-1].close * 1.004)]

    checked = apply_cross_validation(item, make_rows(300)[-1].close, "stooq", secondary)

    assert checked.status == "ok"
    assert checked.close_gap_pct is not None and checked.close_gap_pct < 0.8


def test_cross_validation_blocks_large_qqq_gap():
    rows = make_rows(300)
    item = reliability_item("QQQ", "yahoo", rows)
    secondary = [PriceRow(date=item.latest_date, close=rows[-1].close * 1.05)]

    checked = apply_cross_validation(item, rows[-1].close, "stooq", secondary)

    assert checked.status == "danger"
    assert checked.score < item.score
