import csv
from datetime import date, datetime, timezone
from io import StringIO
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter(prefix="/market", tags=["market"])

AllowedSymbol = Literal[
    "QQQ",
    "QQQM",
    "SPYM",
    "TQQQ",
    "QLD",
    "SMH",
    "SOXX",
    "VGT",
    "VOO",
    "VTI",
    "SGOV",
    "BIL",
    "SHY",
    "IEF",
    "TLT",
]
CACHE_TTL_SECONDS = 600
_history_cache: dict[str, tuple[float, list["PriceRow"]]] = {}


class PriceRow(BaseModel):
    date: str
    close: float


class HistoryResponse(BaseModel):
    symbol: str
    provider: str
    rows: list[PriceRow]
    latest: PriceRow
    sma20: float | None = Field(default=None)
    sma50: float | None = Field(default=None)
    sma200: float | None = Field(default=None)
    high20: float | None = Field(default=None)


class QuoteResponse(BaseModel):
    symbol: str
    provider: str
    price: float
    as_of: str
    freshness: str
    source_note: str


class FxRateResponse(BaseModel):
    pair: str
    provider: str
    rate: float
    as_of: str
    freshness: str
    source_note: str


class DataReliabilityItem(BaseModel):
    symbol: str
    provider: str
    latest_date: str
    age_days: int
    row_count: int
    has_sma20: bool
    has_sma50: bool
    has_sma200: bool
    score: int = Field(ge=0, le=100)
    status: Literal["ok", "watch", "danger"]
    message: str


class DataReliabilityResponse(BaseModel):
    provider: str
    checked_at: str
    items: list[DataReliabilityItem]


def calculate_sma(rows: list[PriceRow], length: int) -> float | None:
    if len(rows) < length:
        return None
    closes = [row.close for row in rows[-length:]]
    return sum(closes) / length


def calculate_high(rows: list[PriceRow], length: int) -> float | None:
    if len(rows) < length:
        return None
    return max(row.close for row in rows[-length:])


def data_age_days(latest_date: str) -> int:
    try:
        parsed = date.fromisoformat(latest_date)
    except ValueError:
        return 999
    return max((datetime.now(timezone.utc).date() - parsed).days, 0)


def reliability_item(symbol: str, provider: str, rows: list[PriceRow]) -> DataReliabilityItem:
    latest = rows[-1]
    age_days = data_age_days(latest.date)
    has_sma20 = calculate_sma(rows, 20) is not None
    has_sma50 = calculate_sma(rows, 50) is not None
    has_sma200 = calculate_sma(rows, 200) is not None
    score = 100
    if age_days > 1:
        score -= min((age_days - 1) * 8, 40)
    if not has_sma20:
        score -= 10
    if not has_sma50:
        score -= 15
    if not has_sma200:
        score -= 30
    if len(rows) < 260:
        score -= 10
    score = max(min(score, 100), 0)
    if score >= 85:
        status = "ok"
        message = "판단에 사용할 수 있는 최신 일봉 데이터입니다."
    elif score >= 60:
        status = "watch"
        message = "사용은 가능하지만 기준일 또는 일부 지표를 확인해야 합니다."
    else:
        status = "danger"
        message = "전략 판단에 쓰기 전 데이터 갱신 또는 대체 소스 확인이 필요합니다."
    return DataReliabilityItem(
        symbol=symbol,
        provider=provider,
        latest_date=latest.date,
        age_days=age_days,
        row_count=len(rows),
        has_sma20=has_sma20,
        has_sma50=has_sma50,
        has_sma200=has_sma200,
        score=score,
        status=status,  # type: ignore[arg-type]
        message=message,
    )


def reliability_failure_item(symbol: str, provider: str, reason: str) -> DataReliabilityItem:
    return DataReliabilityItem(
        symbol=symbol,
        provider=provider,
        latest_date="-",
        age_days=999,
        row_count=0,
        has_sma20=False,
        has_sma50=False,
        has_sma200=False,
        score=0,
        status="danger",
        message=f"시세 제공자 연결에 실패했습니다. 저장된 지표나 대체 소스로 확인하세요. 원인: {reason}",
    )


def parse_stooq_csv(text: str) -> list[PriceRow]:
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
    url = f"https://stooq.com/q/d/l/?s={symbol.lower()}&i=d"
    timeout = httpx.Timeout(10.0, connect=5.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    rows = parse_stooq_csv(response.text)
    if len(rows) < 2:
        raise HTTPException(status_code=502, detail="Market data provider returned no rows")
    return rows


def parse_yahoo_chart(payload: dict) -> list[PriceRow]:
    chart = payload.get("chart", {})
    result = chart.get("result") or []
    if not result:
        raise HTTPException(status_code=502, detail="Market data provider returned no result")

    item = result[0]
    timestamps = item.get("timestamp") or []
    quote = ((item.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    rows: list[PriceRow] = []

    for timestamp, close in zip(timestamps, closes, strict=False):
        if close is None:
            continue
        date = datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
        rows.append(PriceRow(date=date, close=float(close)))

    rows.sort(key=lambda row: row.date)
    if len(rows) < 2:
        raise HTTPException(status_code=502, detail="Market data provider returned no rows")
    return rows


async def fetch_yahoo_history(symbol: str) -> list[PriceRow]:
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": "10y", "interval": "1d"}
    headers = {
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
        ),
    }
    timeout = httpx.Timeout(10.0, connect=5.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()

    return parse_yahoo_chart(response.json())


async def fetch_yahoo_intraday_quote(symbol: str) -> QuoteResponse:
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": "1d", "interval": "1m"}
    headers = {
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
        ),
    }
    timeout = httpx.Timeout(10.0, connect=5.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()

    rows = parse_yahoo_chart(response.json())
    latest = rows[-1]
    return QuoteResponse(
        symbol=symbol,
        provider="yahoo",
        price=latest.close,
        as_of=latest.date,
        freshness="intraday",
        source_note=(
            "Yahoo 1분봉 최신값입니다. 거래소 공식 실시간이 아니라 지연 또는 "
            "제공자 정책에 따른 최신값일 수 있습니다."
        ),
    )


async def fetch_yahoo_fx_rate(symbol: str = "USDKRW=X") -> FxRateResponse:
    quote = await fetch_yahoo_intraday_quote(symbol)
    return FxRateResponse(
        pair="USD/KRW",
        provider=quote.provider,
        rate=quote.price,
        as_of=quote.as_of,
        freshness=quote.freshness,
        source_note="Yahoo Finance USDKRW=X 기준 환율입니다. 증권사 실제 환전 환율과는 차이가 날 수 있습니다.",
    )


async def fetch_provider_history(symbol: str, provider: str) -> list[PriceRow]:
    import time

    cache_key = f"{provider}:{symbol}"
    cached = _history_cache.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    if provider == "yahoo":
        rows = await fetch_yahoo_history(symbol)
    else:
        rows = await fetch_stooq_history(symbol)
    _history_cache[cache_key] = (now, rows)
    return rows


@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(symbol: AllowedSymbol) -> QuoteResponse:
    provider = settings.market_data_provider.lower()
    if provider not in {"yahoo", "stooq"}:
        raise HTTPException(status_code=501, detail=f"Provider is not configured: {provider}")

    try:
        if provider == "yahoo":
            return await fetch_yahoo_intraday_quote(symbol)
        rows = await fetch_provider_history(symbol, provider)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Market quote request failed: {exc}") from exc

    latest = rows[-1]
    return QuoteResponse(
        symbol=symbol,
        provider=provider,
        price=latest.close,
        as_of=latest.date,
        freshness="daily",
        source_note="Stooq 일봉 최신 종가입니다. 장중 실시간 가격은 아닙니다.",
    )


@router.get("/fx/usd-krw", response_model=FxRateResponse)
async def get_usd_krw_rate() -> FxRateResponse:
    try:
        return await fetch_yahoo_fx_rate()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"FX rate request failed: {exc}") from exc


@router.get("/reliability", response_model=DataReliabilityResponse)
async def get_data_reliability(
    symbols: list[AllowedSymbol] = Query(default=["QQQ", "TQQQ", "QLD", "SGOV"]),
) -> DataReliabilityResponse:
    provider = settings.market_data_provider.lower()
    if provider not in {"yahoo", "stooq"}:
        raise HTTPException(status_code=501, detail=f"Provider is not configured: {provider}")

    items: list[DataReliabilityItem] = []
    unique_symbols = list(dict.fromkeys(symbols))
    for symbol in unique_symbols:
        try:
            rows = await fetch_provider_history(symbol, provider)
            items.append(reliability_item(symbol, provider, rows))
        except HTTPException as exc:
            items.append(reliability_failure_item(symbol, provider, str(exc.detail)))
        except httpx.HTTPError as exc:
            items.append(reliability_failure_item(symbol, provider, str(exc)))

    return DataReliabilityResponse(
        provider=provider,
        checked_at=datetime.now(timezone.utc).isoformat(),
        items=items,
    )


@router.get("/history/{symbol}", response_model=HistoryResponse)
async def get_history(
    symbol: AllowedSymbol,
    limit: int = Query(default=800, ge=2, le=5000),
) -> HistoryResponse:
    provider = settings.market_data_provider.lower()
    if provider not in {"yahoo", "stooq"}:
        raise HTTPException(status_code=501, detail=f"Provider is not configured: {provider}")

    try:
        rows = await fetch_provider_history(symbol, provider)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Market data request failed: {exc}") from exc

    limited_rows = rows[-limit:]
    return HistoryResponse(
        symbol=symbol,
        provider=provider,
        rows=limited_rows,
        latest=limited_rows[-1],
        sma20=calculate_sma(limited_rows, 20),
        sma50=calculate_sma(limited_rows, 50),
        sma200=calculate_sma(limited_rows, 200),
        high20=calculate_high(limited_rows, 20),
    )
