
import httpx

from app.schemas.market import DataReliabilityItem, FxRateResponse, QuoteResponse
from app.services.market_data import PriceRow, business_days_since, parse_yahoo_chart


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



