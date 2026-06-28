from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, HttpUrl

DealSource = Literal["acquire", "flippa", "bizbuysell", "courts", "manual"]

class RawListing(BaseModel):
    """Raw scraped listing from any marketplace."""
    source: DealSource
    external_id: str
    title: str
    url: str
    description_raw: str
    asking_price_usd: Optional[float] = None
    posted_at: Optional[datetime] = None
    seller_note: Optional[str] = None

class Financials(BaseModel):
    """Structured financial extraction - PydanticAI result_type."""
    annual_revenue_usd: Optional[float] = Field(None, description="TTM revenue")
    annual_profit_usd: Optional[float] = Field(None, description="TTM SDE / EBITDA / net profit")
    monthly_traffic: Optional[int] = None
    churn_rate_pct: Optional[float] = None
    growth_rate_pct: Optional[float] = None
    revenue_verified: bool = False
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)

class TriageResult(BaseModel):
    financials: Financials
    profit_multiple: Optional[float] = None
    revenue_multiple: Optional[float] = None
    red_flags: list[str] = Field(default_factory=list)
    quality_score: float = Field(ge=0.0, le=1.0)
    pass_triage: bool
    reasoning: str

class PortfolioAsset(BaseModel):
    name: str
    industry: str
    customers: int
    arr_usd: Optional[float] = None
    distribution_channels: list[str] = Field(default_factory=list)
    notes: Optional[str] = None

class SynergyAnalysis(BaseModel):
    fit_score: float = Field(ge=0.0, le=1.0)
    synergy_type: list[str] = Field(default_factory=list)  # cross_sell, cost_share, rollup, etc
    cross_sell_opportunity_usd: Optional[float] = None
    estimated_synergy_value_usd: Optional[float] = None
    strategic_rationale: str
    risks: list[str] = Field(default_factory=list)

class DealMemo(BaseModel):
    deal_id: str
    title: str
    source: DealSource
    url: str
    asking_price_usd: Optional[float]
    profit_multiple: Optional[float]
    financials: Financials
    triage: TriageResult
    synergy: SynergyAnalysis
    investment_thesis: str
    recommendation: Literal["PASS", "WATCH", "BID", "BID_AGGRESSIVE"]
    loi_price_usd: Optional[float] = None

class AllocatorState(BaseModel):
    """LangGraph state."""
    listing: RawListing
    financials: Optional[Financials] = None
    triage: Optional[TriageResult] = None
    synergy: Optional[SynergyAnalysis] = None
    memo: Optional[DealMemo] = None
    error: Optional[str] = None

class LOIRequest(BaseModel):
    deal_id: str
    offer_price_usd: float
    buyer_name: str = "Acquirer LLC"
    close_days: int = 30

class LOIResponse(BaseModel):
    deal_id: str
    loi_text: str
    pdf_url: Optional[str] = None
