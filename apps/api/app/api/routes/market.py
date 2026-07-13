from datetime import datetime, timezone
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.market_data import (
    MarketDataError,
    PriceRow,
    business_days_since,
    fetch_provider_history,
    parse_yahoo_chart,
)

router = APIRouter(prefix="/market", tags=["market"])

AllowedSymbol = Literal[
    "QQQ",
    "QQQM",
    "SPY",
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

__all__ = ["router", "PriceRow", "fetch_provider_history"]


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
    secondary_provider: str | None = None
    secondary_latest_date: str | None = None
    close_gap_pct: float | None = None


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
    return business_days_since(latest_date)


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


def apply_cross_validation(
    item: DataReliabilityItem,
    primary_close: float,
    secondary_provider: str,
    secondary_rows: list[PriceRow],
) -> DataReliabilityItem:
    secondary = secondary_rows[-1]
    gap = abs(primary_close / secondary.close - 1) * 100 if secondary.close else 999.0
    score = item.score
    status = item.status
    if gap > 2:
        score = max(score - 30, 0)
        status = "danger"
        message = f"두 시세 제공자의 QQQ 종가 차이가 {gap:.2f}%로 커서 판단에 사용하면 안 됩니다."
    elif gap > 0.8:
        score = max(score - 10, 0)
        status = "watch" if status == "ok" else status
        message = f"두 시세 제공자의 QQQ 종가 차이가 {gap:.2f}%입니다. 최신 거래일을 확인하세요."
    else:
        message = f"{item.message} {secondary_provider} 교차검증 차이 {gap:.2f}%입니다."
    return item.model_copy(
        update={
            "score": score,
            "status": status,
            "message": message,
            "secondary_provider": secondary_provider,
            "secondary_latest_date": secondary.date,
            "close_gap_pct": round(gap, 2),
        }
    )


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


@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(symbol: AllowedSymbol) -> QuoteResponse:
    provider = settings.market_data_provider.lower()
    if provider not in {"yahoo", "stooq"}:
        raise HTTPException(status_code=501, detail=f"Provider is not configured: {provider}")

    try:
        if provider == "yahoo":
            return await fetch_yahoo_intraday_quote(symbol)
        rows = await fetch_provider_history(symbol, provider)
    except (httpx.HTTPError, MarketDataError) as exc:
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
    except (httpx.HTTPError, MarketDataError) as exc:
        raise HTTPException(status_code=502, detail=f"FX rate request failed: {exc}") from exc


@router.get("/reliability", response_model=DataReliabilityResponse)
async def get_data_reliability(
    symbols: Annotated[list[AllowedSymbol] | None, Query()] = None,
) -> DataReliabilityResponse:
    provider = settings.market_data_provider.lower()
    if provider not in {"yahoo", "stooq"}:
        raise HTTPException(status_code=501, detail=f"Provider is not configured: {provider}")

    items: list[DataReliabilityItem] = []
    requested_symbols = symbols or ["QQQ", "TQQQ", "QLD", "SGOV"]
    unique_symbols = list(dict.fromkeys(requested_symbols))
    for symbol in unique_symbols:
        try:
            rows = await fetch_provider_history(symbol, provider)
            item = reliability_item(symbol, provider, rows)
            if symbol == "QQQ":
                secondary_provider = "stooq" if provider == "yahoo" else "yahoo"
                try:
                    secondary_rows = await fetch_provider_history(symbol, secondary_provider)
                    item = apply_cross_validation(item, rows[-1].close, secondary_provider, secondary_rows)
                except (MarketDataError, httpx.HTTPError) as exc:
                    item = item.model_copy(
                        update={
                            "status": "watch" if item.status == "ok" else item.status,
                            "score": max(item.score - 5, 0),
                            "message": f"{item.message} 보조 제공자 교차확인은 실패했습니다: {exc}",
                            "secondary_provider": secondary_provider,
                        }
                    )
            items.append(item)
        except MarketDataError as exc:
            items.append(reliability_failure_item(symbol, provider, str(exc)))
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
    except (httpx.HTTPError, MarketDataError) as exc:
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
