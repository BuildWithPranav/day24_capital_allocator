# 💼 Capital Allocator — PE Deal Sourcing Agent

> **A production-grade autonomous PE deal sourcing agent that scrapes Acquire.com, Flippa, and BizBuySell — extracts TTM financials with PydanticAI — scores synergy against your portfolio — and generates institutional deal memos with LOI drafts delivered to Slack.**

---

## 📸 Overview

Private equity and search fund operators spend hundreds of hours manually triaging acquisition targets. Capital Allocator automates the entire first-pass pipeline: scrape listings → extract financials → triage against your investment criteria → score portfolio synergy → generate a full deal memo with recommendation (PASS / WATCH / BID / BID_AGGRESSIVE) → draft an LOI → deliver to Slack.

Configure your portfolio in `portfolio.yaml`. Everything else is autonomous.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│      FastAPI REST API + APScheduler (daily scrape run)      │
│      MCP Slack Server — deal memo delivery                  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              LangGraph Pipeline (3 nodes + gate)            │
│                                                             │
│  triage ──gate──► synergy ──► memo ──► Slack                │
│          │                                                  │
│          └── REJECT (below investment criteria → END)       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Node 1: Triage (PydanticAI + LLM)                  │   │
│  │  Extracts TTM financials from raw listing text:      │   │
│  │  revenue, profit, traffic, churn, growth rate        │   │
│  │  Calculates: profit multiple, revenue multiple       │   │
│  │  Flags: high churn, overpriced, low confidence       │   │
│  │  Quality score → pass_triage gate                    │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │  Node 2: Synergy Analysis (LLM)                      │   │
│  │  Cross-references deal vs your portfolio.yaml        │   │
│  │  Synergy types: cross_sell · cost_share · rollup     │   │
│  │  Estimates: cross-sell opportunity USD               │   │
│  │  Fit score 0.0–1.0 + strategic rationale             │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │  Node 3: Deal Memo (LLM)                             │   │
│  │  Investment thesis + recommendation:                 │   │
│  │  PASS · WATCH · BID · BID_AGGRESSIVE                 │   │
│  │  LOI price suggestion (if BID/BID_AGGRESSIVE)        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤖 What It Produces

### TriageResult
```json
{
  "financials": {
    "annual_revenue_usd": 480000,
    "annual_profit_usd": 192000,
    "churn_rate_pct": 3.2,
    "growth_rate_pct": 22.0,
    "revenue_verified": true,
    "confidence": 0.87
  },
  "profit_multiple": 2.6,
  "revenue_multiple": 1.04,
  "red_flags": [],
  "quality_score": 0.91,
  "pass_triage": true,
  "reasoning": "Verified revenue, healthy margin, growth trending positively, multiple within target range."
}
```

### SynergyAnalysis
```json
{
  "fit_score": 0.82,
  "synergy_type": ["cross_sell", "rollup"],
  "cross_sell_opportunity_usd": 96000,
  "estimated_synergy_value_usd": 140000,
  "strategic_rationale": "Target's SMB customer base maps directly to portfolio asset's distribution channel...",
  "risks": ["Key-man dependency on founder", "Seasonal revenue concentration"]
}
```

### DealMemo
```json
{
  "investment_thesis": "SaaS tool with verified $192K TTM profit, 22% YoY growth...",
  "recommendation": "BID",
  "loi_price_usd": 460000
}
```

---

## 📋 Configure Your Portfolio

Edit `config/portfolio.yaml`:
```yaml
assets:
  - name: "Wrkflw Agency"
    industry: "AI Automation / SaaS"
    customers: 45
    arr_usd: 180000
    distribution_channels: ["WhatsApp", "direct sales", "LinkedIn"]
    notes: "Strong in Indian SMB segment"

investment_criteria:
  min_annual_profit_usd: 50000
  max_profit_multiple: 4.0
  target_industries: ["SaaS", "AI tools", "Automation", "Marketing tech"]
```

---

## 📁 Folder Structure

```
capital_allocator/
├── src/capital_allocator/
│   ├── graph.py              # LangGraph state machine (triage → gate → synergy → memo)
│   ├── models.py             # Pydantic models (RawListing, Financials, DealMemo, LOI)
│   ├── config.py             # Pydantic settings
│   ├── api.py                # FastAPI REST endpoints
│   ├── main.py               # App entrypoint
│   ├── agents/
│   │   ├── triage.py         # PydanticAI financial extractor
│   │   ├── synergy.py        # Portfolio synergy analyzer
│   │   └── memo.py           # Deal memo + recommendation generator
│   ├── scrapers/
│   │   └── base.py           # Scraper base (Acquire/Flippa/BizBuySell)
│   └── mcp/
│       └── slack_server.py   # MCP Slack delivery server
├── config/
│   └── portfolio.yaml        # Your portfolio + investment criteria
├── .env.example
├── docker-compose.yml
└── Dockerfile
```

---

## ⚡ Quick Start

### 1. Clone & Configure
```bash
git clone <repo-url>
cd capital_allocator
cp .env.example .env
# Add OPENAI_API_KEY or ANTHROPIC_API_KEY + SLACK_WEBHOOK_URL
```

### 2. Configure Portfolio
```bash
nano config/portfolio.yaml
# Add your portfolio assets + investment criteria
```

### 3. Run with Docker
```bash
docker-compose up --build
```

### 4. Triage a Listing Manually
```bash
curl -X POST http://localhost:8000/deals \
  -H "Content-Type: application/json" \
  -d '{
    "source": "acquire",
    "external_id": "acq-12345",
    "title": "B2B SaaS tool - $480K ARR - 22% growth",
    "url": "https://acquire.com/listing/12345",
    "description_raw": "...",
    "asking_price_usd": 500000
  }'
```

### 5. Generate LOI
```bash
curl -X POST http://localhost:8000/deals/{deal_id}/loi \
  -d '{"offer_price_usd": 460000, "buyer_name": "Wrkflw Holdings", "close_days": 45}'
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/deals` | Triage a raw listing → full deal memo |
| `GET` | `/deals` | List all triaged deals |
| `GET` | `/deals/{id}` | Get specific deal memo |
| `POST` | `/deals/{id}/loi` | Generate LOI for a deal |
| `GET` | `/health` | Health check |

---

## ⚙️ Configuration

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | LLM for triage + synergy + memo |
| `ANTHROPIC_API_KEY` | Claude alternative |
| `LLM_TRIAGE_MODEL` | Model for financial extraction |
| `LLM_SYNERGY_MODEL` | Model for synergy analysis |
| `MIN_ANNUAL_PROFIT_USD` | Triage floor (default: $50,000) |
| `MAX_PROFIT_MULTIPLE` | Triage ceiling (default: 4.0x) |
| `SLACK_WEBHOOK_URL` | Deal memo delivery |

---

## 🚀 Scaling Path

| Stage | Upgrade |
|-------|---------|
| **Now** | Manual listing input + Slack delivery |
| **Active searcher** | Wire real Acquire/Flippa scrapers, daily automated runs |
| **Search fund** | PostgreSQL deal history, pipeline dashboard, comps database |
| **PE firm** | Multi-portfolio synergy scoring, LP reporting, CRM integration |

---

## 📦 Built With

- **LangGraph** — 3-node deal pipeline with conditional triage gate
- **PydanticAI** — Structured financial extraction from raw listing text
- **FastAPI** — REST API + deal management
- **FastMCP** — Slack deal memo delivery
- **Pydantic v2** — Institutional-grade typed models
- **structlog** — Structured logging
- **Docker** — Reproducible deployment

---

*Day 24/27 — Built by Pranav | IIT Kharagpur · AI Automation Agency*