from __future__ import annotations
import os
import httpx
from fastmcp import FastMCP

mcp = FastMCP("capital-allocator-slack")

@mcp.tool()
async def post_deal_alert(
    title: str,
    url: str,
    asking_price: float | None = None,
    profit_multiple: float | None = None,
    thesis: str = "",
    recommendation: str = "WATCH",
    loi_price: float | None = None
) -> dict:
    """Post an institutional deal memo to Slack."""
    webhook = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook:
        return {"posted": False, "reason": "SLACK_WEBHOOK_URL not set"}

    multiple_txt = f"{profit_multiple:.1f}x" if profit_multiple else "N/A"
    price_txt = f"${asking_price:,.0f}" if asking_price else "N/A"
    color = {"BID_AGGRESSIVE": "#16a34a", "BID": "#22c55e", "WATCH": "#f59e0b", "PASS": "#6b7280"}.get(recommendation, "#6b7280")

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"🎯 {recommendation} — {title}"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Ask:*\n{price_txt}"},
            {"type": "mrkdwn", "text": f"*Multiple:*\n{multiple_txt}"},
            {"type": "mrkdwn", "text": f"*LOI Target:*\n${loi_price:,.0f}" if loi_price else "*LOI Target:*\n—"},
            {"type": "mrkdwn", "text": f"*Link:*\n<{url}|Open Listing>"},
        ]},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"_{thesis}_"}},
    ]
    payload = {"blocks": blocks}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(webhook, json=payload)
        r.raise_for_status()
    return {"posted": True}

if __name__ == "__main__":
    # Streamable HTTP - 2026 standard
    mcp.run(transport="http", host="0.0.0.0", port=8701)
