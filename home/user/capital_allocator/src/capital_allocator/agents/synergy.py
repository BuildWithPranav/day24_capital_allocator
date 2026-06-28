from __future__ import annotations
from ..models import TriageResult, SynergyAnalysis, PortfolioAsset, RawListing
from ..config import load_portfolio

async def analyze_synergy(listing: RawListing, triage: TriageResult) -> SynergyAnalysis:
    portfolio = load_portfolio()
    text = f"{listing.title} {listing.description_raw}".lower()

    synergy_types: list[str] = []
    cross_sell_customers = 0
    rationale_parts: list[str] = []

    for asset in portfolio:
        # Simple heuristic + LLM could go here. Keeping deterministic for v1.
        if any(k in text for k in ["shopify", "ecommerce", "saas", "app", "plugin"]):
            if "agency" in asset.industry or "saas" in asset.industry:
                synergy_types.append("cross_sell")
                cross_sell_customers += asset.customers
                rationale_parts.append(f"Cross-sell to {asset.name} ({asset.customers} customers)")

        if asset.industry in text:
            synergy_types.append("rollup")
            rationale_parts.append(f"Industry rollup with {asset.name}")

    synergy_types = sorted(set(synergy_types)) or ["financial_only"]
    
    # Cross-sell value: assume 8% attach, $29/mo ARPU, 12mo
    cross_sell_usd = None
    if cross_sell_customers > 0:
        cross_sell_usd = round(cross_sell_customers * 0.08 * 29 * 12, 2)
        rationale_parts.append(f"Est. cross-sell upside: ${cross_sell_usd:,.0f}/yr")

    profit = triage.financials.annual_profit_usd or 0
    synergy_value = profit * 0.25 + (cross_sell_usd or 0) * 0.4

    fit_score = 0.4
    if "cross_sell" in synergy_types: fit_score += 0.3
    if "rollup" in synergy_types: fit_score += 0.2
    if triage.quality_score > 0.75: fit_score += 0.1
    fit_score = min(1.0, fit_score)

    risks = []
    if triage.financials.churn_rate_pct and triage.financials.churn_rate_pct > 5:
        risks.append("Elevated churn vs portfolio")
    if not triage.financials.revenue_verified:
        risks.append("Unverified financials")

    return SynergyAnalysis(
        fit_score=round(fit_score, 3),
        synergy_type=synergy_types,
        cross_sell_opportunity_usd=cross_sell_usd,
        estimated_synergy_value_usd=round(synergy_value, 2) if synergy_value else None,
        strategic_rationale="; ".join(rationale_parts) or "Standalone financial acquisition",
        risks=risks,
    )
