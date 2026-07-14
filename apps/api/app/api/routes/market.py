from datetime import datetime, timezone
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.schemas.market import (
    DataReliabilityItem,
    DataReliabilityResponse,
    FxRateResponse,
    HistoryResponse,
    QuoteResponse,
)
from app.services.market_data import MarketDataError, PriceRow, fetch_provider_history
from app.services.market_snapshot import (
    apply_cross_validation,
    calculate_high,
    calculate_sma,
    fetch_yahoo_fx_rate,
    fetch_yahoo_intraday_quote,
    reliability_failure_item,
    reliability_item,
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
