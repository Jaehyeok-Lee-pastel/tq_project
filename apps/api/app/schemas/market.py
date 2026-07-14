from typing import Literal

from pydantic import BaseModel, Field

from app.services.market_data import PriceRow


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



