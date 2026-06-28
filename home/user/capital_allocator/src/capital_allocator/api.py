from __future__ import annotations
from typing import List
import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .models import RawListing, DealMemo, LOIRequest, LOIResponse
from .graph import run_deal
from .scrapers.base import run_dragnet
from .mcp.slack_server import post_deal_alert
from .config import get_settings

log = structlog.get_logger()
app = FastAPI(title="Capital Allocator Agent", version="0.1.0")

deals_db: dict[str, DealMemo] = {}

class ScanResult(BaseModel):
    scanned: int
    qualified: int
    deals: List[DealMemo]

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/scan", response_model=ScanResult)
async def scan():
    listings = await run_dragnet()
    qualified: List[DealMemo] = []
    for lst in listings:
        try:
            memo = await run_deal(lst)
            if memo:
                deals_db[memo.deal_id] = memo
                qualified.append(memo)
                # Alert to Slack
                s = get_settings()
                levels = {"PASS":0,"WATCH":1,"BID":2,"BID_AGGRESSIVE":3}
                if levels.get(memo.recommendation,0) >= levels.get(s.ALERT_MIN_RECOMMENDATION,2):
                    try:
                        await post_deal_alert.fn(  # type: ignore
                            title=memo.title, url=memo.url,
                            asking_price=memo.asking_price_usd,
                            profit_multiple=memo.profit_multiple,
                            thesis=memo.investment_thesis,
                            recommendation=memo.recommendation,
                            loi_price=memo.loi_price_usd
                        )
                    except Exception as e:
                        log.warning("slack_alert_failed", error=str(e))
        except Exception as e:
            log.error("deal_run_failed", error=str(e), listing=lst.url)
    return ScanResult(scanned=len(listings), qualified=len(qualified), deals=qualified)

@app.post("/evaluate", response_model=DealMemo)
async def evaluate_listing(listing: RawListing):
    memo = await run_deal(listing)
    if not memo:
        raise HTTPException(422, "Listing did not pass triage")
    deals_db[memo.deal_id] = memo
    return memo

@app.get("/deals", response_model=List[DealMemo])
async def list_deals():
    return sorted(deals_db.values(), key=lambda d: (d.profit_multiple or 99))

@app.post("/loi", response_model=LOIResponse)
async def generate_loi(req: LOIRequest):
    memo = deals_db.get(req.deal_id)
    if not memo:
        raise HTTPException(404, "deal not found")
    from jinja2 import Template
    loi_tpl = Template("""LETTER OF INTENT

Date: {{ date }}
To: Seller of {{ title }}
Re: Acquisition - {{ url }}

Dear Seller,

{{ buyer_name }} is pleased to submit this non-binding LOI to acquire 100% of the assets of {{ title }}.

Purchase Price: ${{ "%.2f"|format(offer_price) }} USD, cash at close
Close Timeline: {{ close_days }} days
Due Diligence: 14 days financial / traffic verification
Structure: Asset purchase

Investment Thesis: {{ thesis }}

This LOI is non-binding except for exclusivity (30 days) and confidentiality.

Sincerely,
{{ buyer_name }}
""")
    from datetime import date
    text = loi_tpl.render(
        date=date.today().isoformat(),
        title=memo.title,
        url=memo.url,
        buyer_name=req.buyer_name,
        offer_price=req.offer_price_usd,
        close_days=req.close_days,
        thesis=memo.investment_thesis,
    )
    return LOIResponse(deal_id=req.deal_id, loi_text=text)
