from __future__ import annotations
import hashlib
from pydantic_ai import Agent
from ..models import RawListing, TriageResult, SynergyAnalysis, DealMemo
from ..config import get_settings

memo_agent = Agent(
    get_settings().LLM_MEMO_MODEL,
    result_type=str,
    system_prompt="You are a PE Investment Committee memo writer. Be crisp, data-backed, institutional grade. 120-180 words."
)

async def build_memo(listing: RawListing, triage: TriageResult, synergy: SynergyAnalysis) -> DealMemo:
    deal_id = hashlib.sha1(listing.url.encode()).hexdigest()[:12]
    
    multiple_str = f"{triage.profit_multiple:.1f}x" if triage.profit_multiple else "N/A"
    
    # Investment thesis via LLM
    prompt = f"""Write an IC investment thesis for:
{listing.title} - ${listing.asking_price_usd or 0:,.0f} ask, {multiple_str} profit multiple
Profit: ${triage.financials.annual_profit_usd or 0:,.0f}/yr, Revenue: ${triage.financials.annual_revenue_usd or 0:,.0f}
Churn: {triage.financials.churn_rate_pct or 'unknown'}%, Growth: {triage.financials.growth_rate_pct or 'unknown'}%
Synergy: {synergy.strategic_rationale}
Risks: {', '.join(synergy.risks) or 'None'}

3-5 sentences, thesis only."""
    try:
        res = await memo_agent.run(prompt)
        thesis = res.output.strip()
    except Exception:
        thesis = f"Profitable asset at {multiple_str} SDE. {synergy.strategic_rationale}. Quality score {triage.quality_score}."

    # Recommendation logic
    rec = "PASS"
    if triage.pass_triage and synergy.fit_score >= 0.6:
        rec = "BID"
    if triage.profit_multiple and triage.profit_multiple < 2.5 and synergy.fit_score >= 0.7:
        rec = "BID_AGGRESSIVE"
    if triage.pass_triage and synergy.fit_score < 0.6:
        rec = "WATCH"

    # LOI price: 85% of ask for BID, 78% for AGGRESSIVE, else None
    loi_price = None
    if listing.asking_price_usd and rec in ("BID", "BID_AGGRESSIVE"):
        disc = 0.78 if rec == "BID_AGGRESSIVE" else 0.85
        loi_price = round(listing.asking_price_usd * disc, 2)

    return DealMemo(
        deal_id=deal_id,
        title=listing.title,
        source=listing.source,
        url=listing.url,
        asking_price_usd=listing.asking_price_usd,
        profit_multiple=triage.profit_multiple,
        financials=triage.financials,
        triage=triage,
        synergy=synergy,
        investment_thesis=thesis,
        recommendation=rec,  # type: ignore
        loi_price_usd=loi_price,
    )
