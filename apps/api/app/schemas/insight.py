from typing import Any, Literal

from pydantic import BaseModel, Field


class InsightRequest(BaseModel):
    context: Literal["strategy_compare", "backtest"] = "strategy_compare"
    payload: dict[str, Any]
    use_ai: bool = True


class InsightReport(BaseModel):
    headline: str
    confidence_level: Literal["low", "medium", "high"]
    summary: str
    strongest_evidence: list[str] = Field(default_factory=list)
    main_risks: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    ai_used: bool = False
