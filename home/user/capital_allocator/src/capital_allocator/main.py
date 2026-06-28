from __future__ import annotations
import asyncio
import structlog
from .config import get_settings
from .api import app
import uvicorn

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()],
)

log = structlog.get_logger()

async def scan_loop(interval_minutes: int = 60):
    """Continuous dragnet loop."""
    from .scrapers.base import run_dragnet
    from .graph import run_deal
    from .mcp.slack_server import post_deal_alert
    from .config import get_settings as gs

    while True:
        try:
            listings = await run_dragnet()
            log.info("scan_loop_run", count=len(listings))
            for lst in listings:
                memo = await run_deal(lst)
                if memo and memo.recommendation in ("BID", "BID_AGGRESSIVE"):
                    s = gs()
                    if s.SLACK_WEBHOOK_URL:
                        await post_deal_alert.fn(title=memo.title, url=memo.url, asking_price=memo.asking_price_usd, profit_multiple=memo.profit_multiple, thesis=memo.investment_thesis, recommendation=memo.recommendation, loi_price=memo.loi_price_usd)  # type: ignore
        except Exception as e:
            log.error("scan_loop_error", error=str(e))
        await asyncio.sleep(interval_minutes * 60)

if __name__ == "__main__":
    s = get_settings()
    uvicorn.run("capital_allocator.api:app", host="0.0.0.0", port=s.PORT, reload=False)
