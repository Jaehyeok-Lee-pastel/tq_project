"""Market data service: fetch, cache, and extend daily price histories.

Design goals (see docs/01_strategy_philosophy):
- Full history with dividend-adjusted closes (Yahoo ``adjclose``), so the
  QQQ buy-and-hold benchmark is not understated.
- Reproducible backtests: an on-disk snapshot per (provider, symbol) per UTC
  day. The same backtest run twice on the same day sees identical data, and a
  provider outage falls back to the last good snapshot.
- Leveraged ETFs (TQQQ 2010-, QLD 2006-) are extended backwards with a
  synthetic daily series derived from QQQ returns, so the 2000-2002 and 2008
  crashes are part of every leveraged backtest instead of silently missing.
"""

import json
import time
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

import httpx
from pydantic import BaseModel

TRADING_DAYS_PER_YEAR = 252
CACHE_TTL_SECONDS = 600
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "market_cache"

_memory_cache: dict[str, tuple[float, list["PriceRow"]]] = {}


def business_days_since(latest_date: str, today: date | None = None) -> int:
    """Count weekdays after the latest observation, excluding weekends."""
    try:
        latest = date.fromisoformat(latest_date)
    except ValueError:
        return 999
    current = today or datetime.now(timezone.utc).date()
    if latest >= current:
        return 0
    cursor = latest + timedelta(days=1)
    count = 0
    while cursor <= current:
        if cursor.weekday() < 5:
            count += 1
        cursor += timedelta(days=1)
    return count


class PriceRow(BaseModel):
    date: str
    close: float


class MarketDataError(RuntimeError):
    """Raised when no provider (and no snapshot fallback) can serve a symbol."""


class LeveragedSpec(BaseModel):
    base_symbol: str
    leverage: float
    expense_ratio: float


# Daily leveraged ETFs that get a synthetic pre-inception extension.
LEVERAGED_SPECS: dict[str, LeveragedSpec] = {
    "TQQQ": LeveragedSpec(base_symbol="QQQ", leverage=3.0, expense_ratio=0.0095),
    "QLD": LeveragedSpec(base_symbol="QQQ", leverage=2.0, expense_ratio=0.0095),
}

# Approximate annual average short-term USD financing rates (percent).
# Used only for the synthetic pre-inception extension: a daily L-times ETF
# pays roughly (L-1) x short rate on its swap exposure. Values are rounded
# annual averages of 3-month rates; precision here has second-order impact.
ANNUAL_FINANCING_RATE_PCT: dict[int, float] = {
    1999: 5.0,
    2000: 6.0,
    2001: 3.8,
    2002: 1.7,
    2003: 1.1,
    2004: 1.4,
    2005: 3.2,
    2006: 4.9,
    2007: 5.0,
    2008: 2.0,
    2009: 0.3,
    2010: 0.2,
    2011: 0.1,
}
DEFAULT_FINANCING_RATE_PCT = 2.0
FINANCING_SPREAD_PCT = 0.5


def parse_yahoo_chart(payload: dict) -> list[PriceRow]:
    chart = payload.get("chart", {})
    result = chart.get("result") or []
    if not result:
        raise MarketDataError("Market data provider returned no result")

    item = result[0]
    timestamps = item.get("timestamp") or []
    indicators = item.get("indicators") or {}
    quote = (indicators.get("quote") or [{}])[0]
    adjclose_series = (indicators.get("adjclose") or [{}])[0].get("adjclose") or []
    closes = quote.get("close") or []
    use_adjusted = len(adjclose_series) == len(closes) and any(
        value is not None for value in adjclose_series
    )

    rows: list[PriceRow] = []
    for index, timestamp in enumerate(timestamps):
        raw_close = closes[index] if index < len(closes) else None
        adjusted = adjclose_series[index] if use_adjusted and index < len(adjclose_series) else None
        close = adjusted if adjusted is not None else raw_close
        if close is None:
            continue
        date = datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
        rows.append(PriceRow(date=date, close=float(close)))

    rows.sort(key=lambda row: row.date)
    if len(rows) < 2:
        raise MarketDataError("Market data provider returned no rows")
    return rows


async def fetch_yahoo_history(symbol: str) -> list[PriceRow]:
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
    # range=max silently downgrades granularity to monthly; explicit epoch
    # bounds are the only way to get full-history DAILY rows from this API.
    params = {"period1": "0", "period2": "9999999999", "interval": "1d", "events": "div,split"}
    headers = {
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
        ),
    }
    timeout = httpx.Timeout(15.0, connect=5.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()

    return parse_yahoo_chart(response.json())


def parse_stooq_csv(text: str) -> list[PriceRow]:
    import csv

    reader = csv.DictReader(StringIO(text))
    rows: list[PriceRow] = []
    for row in reader:
        date = row.get("Date")
        close = row.get("Close")
        if not date or not close:
            continue
        try:
            rows.append(PriceRow(date=date, close=float(close)))
        except ValueError:
            continue
    rows.sort(key=lambda item: item.date)
    return rows


async def fetch_stooq_history(symbol: str) -> list[PriceRow]:
    url = f"https://stooq.com/q/d/l/?s={symbol.lower()}.us&i=d"
    timeout = httpx.Timeout(15.0, connect=5.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    rows = parse_stooq_csv(response.text)
    if len(rows) < 2:
        raise MarketDataError("Market data provider returned no rows")
    return rows


def _snapshot_path(provider: str, symbol: str) -> Path:
    return CACHE_DIR / f"{provider}_{symbol.upper()}.json"


def _load_snapshot(provider: str, symbol: str) -> tuple[str, list[PriceRow]] | None:
    path = _snapshot_path(provider, symbol)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = [PriceRow(**row) for row in payload["rows"]]
        return payload["fetched_on"], rows
    except (ValueError, KeyError, TypeError):
        return None


def _save_snapshot(provider: str, symbol: str, rows: list[PriceRow]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "provider": provider,
        "symbol": symbol.upper(),
        "fetched_on": datetime.now(timezone.utc).date().isoformat(),
        "rows": [row.model_dump() for row in rows],
    }
    _snapshot_path(provider, symbol).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


async def fetch_provider_history(symbol: str, provider: str) -> list[PriceRow]:
    """Daily history with memory TTL cache, daily disk snapshot, stale fallback."""
    cache_key = f"{provider}:{symbol.upper()}"
    now = time.time()
    cached = _memory_cache.get(cache_key)
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    today = datetime.now(timezone.utc).date().isoformat()
    snapshot = _load_snapshot(provider, symbol)
    if snapshot and snapshot[0] == today:
        _memory_cache[cache_key] = (now, snapshot[1])
        return snapshot[1]

    try:
        if provider == "yahoo":
            rows = await fetch_yahoo_history(symbol)
        else:
            rows = await fetch_stooq_history(symbol)
    except (httpx.HTTPError, MarketDataError):
        if snapshot:
            _memory_cache[cache_key] = (now, snapshot[1])
            return snapshot[1]
        raise

    _memory_cache[cache_key] = (now, rows)
    _save_snapshot(provider, symbol, rows)
    return rows


def financing_rate_pct(year: int) -> float:
    return ANNUAL_FINANCING_RATE_PCT.get(year, DEFAULT_FINANCING_RATE_PCT)


def synthetic_daily_return(
    base_return: float,
    year: int,
    leverage: float,
    expense_ratio: float,
) -> float:
    """Model a daily L-times ETF return from its index return.

    return = L * base - expense/252 - (L-1) * (short rate + spread)/252
    """
    financing = (financing_rate_pct(year) + FINANCING_SPREAD_PCT) / 100
    daily_cost = expense_ratio / TRADING_DAYS_PER_YEAR
    daily_financing = (leverage - 1) * financing / TRADING_DAYS_PER_YEAR
    return leverage * base_return - daily_cost - daily_financing


def extend_with_synthetic(
    base_rows: list[PriceRow],
    real_rows: list[PriceRow],
    leverage: float,
    expense_ratio: float,
) -> tuple[list[PriceRow], str | None]:
    """Prepend a synthetic pre-inception series to a leveraged ETF history.

    The synthetic segment is anchored at the first real price and walked
    backwards along the base index's daily returns, so the two segments join
    without a jump. Returns (rows, synthetic_until) where synthetic_until is
    the last synthetic date, or None when nothing was prepended.
    """
    if not real_rows:
        raise MarketDataError("Leveraged symbol has no real history to anchor on")

    first_real_date = real_rows[0].date
    prior_base = [row for row in base_rows if row.date <= first_real_date]
    if len(prior_base) < 2:
        return real_rows, None

    anchor_price = real_rows[0].close
    synthetic: list[PriceRow] = []
    price = anchor_price
    # Walk backwards: undo each day's synthetic return, most recent first.
    for index in range(len(prior_base) - 1, 0, -1):
        current = prior_base[index]
        previous = prior_base[index - 1]
        base_return = current.close / previous.close - 1
        year = int(current.date[:4])
        day_return = synthetic_daily_return(base_return, year, leverage, expense_ratio)
        if day_return <= -1:
            # A daily loss at/beyond -100% would have wiped the fund out.
            break
        price = price / (1 + day_return)
        synthetic.append(PriceRow(date=previous.date, close=price))

    synthetic.reverse()
    if not synthetic:
        return real_rows, None
    synthetic_until = prior_base[-1].date if prior_base[-1].date < first_real_date else None
    merged = synthetic + [row for row in real_rows if row.date > synthetic[-1].date]
    last_synthetic = synthetic[-1].date
    return merged, synthetic_until or last_synthetic


async def fetch_extended_history(
    symbol: str,
    provider: str,
) -> tuple[list[PriceRow], str | None]:
    """History for backtests: leveraged ETFs get the synthetic extension.

    Returns (rows, synthetic_until). synthetic_until is the last date covered
    by the synthetic model instead of real ETF prices (None if fully real).
    """
    spec = LEVERAGED_SPECS.get(symbol.upper())
    if spec is None:
        return await fetch_provider_history(symbol, provider), None

    real_rows = await fetch_provider_history(symbol, provider)
    base_rows = await fetch_provider_history(spec.base_symbol, provider)
    return extend_with_synthetic(base_rows, real_rows, spec.leverage, spec.expense_ratio)


def synthetic_overlap_report(
    base_rows: list[PriceRow],
    real_rows: list[PriceRow],
    leverage: float,
    expense_ratio: float,
) -> dict[str, float]:
    """Compare the synthetic model against real ETF returns on their overlap.

    Used by scripts/validate_synthetic.py to quantify model quality.
    """
    base_by_date = {row.date: row.close for row in base_rows}
    dates = [row.date for row in real_rows if row.date in base_by_date]
    if len(dates) < 3:
        raise MarketDataError("Not enough overlapping rows to validate")

    real_by_date = {row.date: row.close for row in real_rows}
    model_errors: list[float] = []
    synthetic_growth = 1.0
    real_growth = 1.0
    for index in range(1, len(dates)):
        prev_date, curr_date = dates[index - 1], dates[index]
        base_return = base_by_date[curr_date] / base_by_date[prev_date] - 1
        year = int(curr_date[:4])
        model_return = synthetic_daily_return(base_return, year, leverage, expense_ratio)
        real_return = real_by_date[curr_date] / real_by_date[prev_date] - 1
        model_errors.append(model_return - real_return)
        synthetic_growth *= 1 + model_return
        real_growth *= 1 + real_return

    days = len(model_errors)
    mean_error = sum(model_errors) / days
    variance = sum((err - mean_error) ** 2 for err in model_errors) / max(days - 1, 1)
    years = days / TRADING_DAYS_PER_YEAR
    return {
        "overlap_days": days,
        "mean_daily_error_bps": round(mean_error * 10_000, 3),
        "tracking_error_daily_bps": round(variance**0.5 * 10_000, 3),
        "synthetic_cagr_pct": round((synthetic_growth ** (1 / years) - 1) * 100, 2),
        "real_cagr_pct": round((real_growth ** (1 / years) - 1) * 100, 2),
        "end_value_ratio": round(synthetic_growth / real_growth, 4),
    }
