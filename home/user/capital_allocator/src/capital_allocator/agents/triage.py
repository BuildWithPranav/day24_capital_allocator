from __future__ import annotations
import os
import structlog
from pydantic_ai import Agent
from ..models import Financials, TriageResult, RawListing
from ..config import get_settings

log = structlog.get_logger()

triage_agent = Agent(
    get_settings().LLM_TRIAGE_MODEL,
    result_type=Financials,
    system_prompt=(
        "You are a senior PE analyst. Extract structured TTM financials from a business-for-sale listing. "
        "Be conservative. If revenue/profit is not clearly stated, leave it None. "
        "Infer annual from monthly if labeled. Detect verified vs unverified claims. "
        "Return strict JSON matching Financials."
    ),
)

async def run_triage(listing: RawListing) -> TriageResult:
    s = get_settings()
    prompt = f"""
Listing: {listing.title}
Source: {listing.source}
Asking: ${listing.asking_price_usd or 'N/A'}
URL: {listing.url}

Description:
{listing.description_raw[:6000]}

Extract: annual_revenue_usd, annual_profit_usd, monthly_traffic, churn_rate_pct, growth_rate_pct, revenue_verified, confidence
"""
    try:
        result = await triage_agent.run(prompt)
        fin: Financials = result.output
    except Exception as e:
        log.error("triage_llm_failed", error=str(e))
        fin = Financials(confidence=0.0)

    profit_multiple = None
    revenue_multiple = None
    if listing.asking_price_usd and fin.annual_profit_usd and fin.annual_profit_usd > 0:
        profit_multiple = listing.asking_price_usd / fin.annual_profit_usd
    if listing.asking_price_usd and fin.annual_revenue_usd and fin.annual_revenue_usd > 0:
        revenue_multiple = listing.asking_price_usd / fin.annual_revenue_usd

    red_flags: list[str] = []
    if fin.confidence < 0.5:
        red_flags.append("low_extraction_confidence")
    if fin.annual_profit_usd and fin.annual_profit_usd < s.MIN_ANNUAL_PROFIT_USD:
        red_flags.append("profit_below_floor")
    if profit_multiple and profit_multiple > s.MAX_PROFIT_MULTIPLE:
        red_flags.append(f"multiple_high_{profit_multiple:.1f}x")
    if fin.churn_rate_pct and fin.churn_rate_pct > 8:
        red_flags.append("high_churn")

    quality = fin.confidence
    if fin.revenue_verified: quality += 0.15
    if profit_multiple and profit_multiple < 2.5: quality += 0.15
    if fin.growth_rate_pct and fin.growth_rate_pct > 10: quality += 0.1
    quality = max(0.0, min(1.0, quality - 0.15 * len(red_flags)))

    pass_triage = quality >= s.MIN_QUALITY_SCORE and "profit_below_floor" not in red_flags and "multiple_high" not in "".join(red_flags)

    return TriageResult(
        financials=fin,
        profit_multiple=profit_multiple,
        revenue_multiple=revenue_multiple,
        red_flags=red_flags,
        quality_score=round(quality, 3),
        pass_triage=pass_triage,
        reasoning=f"Profit {profit_multiple:.1f}x" if profit_multiple else "No profit multiple",
    )
