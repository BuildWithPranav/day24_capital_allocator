from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator, List
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from ..config import get_settings
from ..models import RawListing

log = structlog.get_logger()

class BaseScraper(ABC):
    source_name: str = "base"

    def __init__(self) -> None:
        s = get_settings()
        self.client = httpx.AsyncClient(
            timeout=20.0,
            headers={"User-Agent": s.SCRAPER_USER_AGENT},
            follow_redirects=True,
        )
        self._sem = asyncio.Semaphore(s.SCRAPER_REQUESTS_PER_MIN)

    async def close(self) -> None:
        await self.client.aclose()

    @abstractmethod
    async def scrape(self) -> AsyncIterator[RawListing]:
        ...

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_text(self, url: str) -> str:
        async with self._sem:
            r = await self.client.get(url)
            r.raise_for_status()
            return r.text

# --- Ethical marketplace adapters ---
# IMPORTANT: Respect each site's ToS. Use official APIs where available.
# These are pluggable adapters - wire in your Acquire.com API key, Flippa API, etc.
# By default they return [] so you don't accidentally violate ToS.

class AcquireScraper(BaseScraper):
    source_name = "acquire"
    async def scrape(self) -> AsyncIterator[RawListing]:
        # TODO: Plug in Acquire.com API: https://acquire.com/api
        # Example:
        # api_key = os.getenv("ACQUIRE_API_KEY")
        # async with self._sem: r = await self.client.get("https://api.acquire.com/listings", headers={"Authorization": f"Bearer {api_key}"})
        log.info("acquire_scraper.stub", msg="Wire ACQUIRE_API_KEY to enable")
        if False:
            yield RawListing(source="acquire", external_id="", title="", url="", description_raw="")
        return

class FlippaScraper(BaseScraper):
    source_name = "flippa"
    async def scrape(self) -> AsyncIterator[RawListing]:
        # TODO: Flippa API / RSS
        log.info("flippa_scraper.stub")
        return
        yield  # type: ignore

class BizBuySellScraper(BaseScraper):
    source_name = "bizbuysell"
    async def scrape(self) -> AsyncIterator[RawListing]:
        # TODO: BizBuySell - use their data feed / respect robots.txt
        log.info("bizbuysell_scraper.stub")
        return
        yield  # type: ignore

class CourtsScraper(BaseScraper):
    source_name = "courts"
    async def scrape(self) -> AsyncIterator[RawListing]:
        # US Courts PACER - requires PACER credentials
        # https://pacer.uscourts.gov/
        log.info("courts_scraper.stub")
        return
        yield  # type: ignore


SCRAPER_REGISTRY: List[type[BaseScraper]] = [
    AcquireScraper,
    FlippaScraper,
    BizBuySellScraper,
    CourtsScraper,
]

async def run_dragnet() -> List[RawListing]:
    """Run all scrapers concurrently, deduplicate."""
    listings: List[RawListing] = []
    scrapers = [cls() for cls in SCRAPER_REGISTRY]
    try:
        async def _collect(sc: BaseScraper):
            async for item in sc.scrape():
                listings.append(item)
        await asyncio.gather(*[_collect(s) for s in scrapers], return_exceptions=True)
    finally:
        for s in scrapers:
            await s.close()
    # dedupe by url
    seen = set()
    uniq = []
    for l in listings:
        if l.url not in seen:
            uniq.append(l); seen.add(l.url)
    log.info("dragnet_complete", count=len(uniq))
    return uniq
