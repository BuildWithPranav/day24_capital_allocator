from __future__ import annotations
import os
from functools import lru_cache
from typing import List
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
from .models import PortfolioAsset

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_TRIAGE_MODEL: str = "openai:gpt-4o"
    LLM_MEMO_MODEL: str = "openai:gpt-4o"

    # App
    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8080

    # Triage thresholds
    MAX_PROFIT_MULTIPLE: float = 3.5
    MIN_ANNUAL_PROFIT_USD: float = 50000
    MIN_QUALITY_SCORE: float = 0.65

    # Alerts
    SLACK_WEBHOOK_URL: str = ""
    ALERT_MIN_RECOMMENDATION: str = "BID"  # WATCH, BID, BID_AGGRESSIVE

    # Memory / Observability
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"
    LANGSMITH_TRACING: str = "false"
    LANGSMITH_API_KEY: str = ""

    # Scraping - be ethical
    SCRAPER_USER_AGENT: str = "CapitalAllocatorBot/0.1 (+contact@yourdomain.com)"
    SCRAPER_REQUESTS_PER_MIN: int = 10
    SCRAPER_RESPECT_ROBOTS: bool = True

    PORTFOLIO_YAML_PATH: str = "config/portfolio.yaml"

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore

def load_portfolio(path: str | None = None) -> List[PortfolioAsset]:
    s = get_settings()
    p = path or s.PORTFOLIO_YAML_PATH
    if not os.path.exists(p):
        return [
            PortfolioAsset(name="AgencyCo", industry="digital_agency", customers=500,
                           distribution_channels=["agency_retainers", "email_list"],
                           notes="500 SMB e-commerce clients, Shopify focused")
        ]
    with open(p, "r") as f:
        data = yaml.safe_load(f)
    return [PortfolioAsset(**a) for a in data.get("assets", [])]
