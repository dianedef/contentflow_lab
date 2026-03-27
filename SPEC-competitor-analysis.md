# TASK: Competitor Analysis Pipeline

> **Robot**: Article Generator + SEO Robot
> **Tools**: Firecrawl (crawl/extract) + Hexowatch (monitoring)
> **Priority**: High

## Objective

Build an automated competitor analysis pipeline that crawls competitor websites, extracts structured data, and monitors changes over time.

---

## Implementation Checklist

### Phase 1: Firecrawl Integration

- [ ] **Setup**
  - [ ] Install SDK: `pip install firecrawl-py`
  - [ ] Add `FIRECRAWL_API_KEY` to `.env`
  - [ ] Create `src/tools/firecrawl_client.py`

- [ ] **Competitor Crawling Tool**
  - [ ] Create `@tool` decorated function for CrewAI
  - [ ] Implement crawl with configurable `limit` parameter
  - [ ] Return clean markdown content for LLM processing
  - [ ] Add error handling and retry logic

```python
# src/tools/firecrawl_tools.py
from crewai import tool
from firecrawl import Firecrawl
import os

@tool
def crawl_competitor_site(url: str, max_pages: int = 10) -> str:
    """Crawl a competitor website and return markdown content."""
    client = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))
    result = client.crawl(
        url=url,
        limit=max_pages,
        scrape_options={"formats": ["markdown"]}
    )
    return "\n\n---\n\n".join([doc.get("markdown", "") for doc in result.data])
```

- [ ] **Structured Extraction Tool**
  - [ ] Define Pydantic schemas for competitor data
  - [ ] Implement JSON extraction mode
  - [ ] Validate extracted data against schemas

```python
# src/schemas/competitor_schema.py
from pydantic import BaseModel

class CompetitorData(BaseModel):
    company_name: str
    products: list[str]
    pricing_tiers: list[dict]
    key_features: list[str]
    target_audience: str
    unique_selling_points: list[str]
```

### Phase 2: Hexowatch Monitoring

- [ ] **Setup**
  - [ ] Add `HEXOWATCH_API_KEY` to `.env`
  - [ ] Create `src/tools/hexowatch_client.py`

- [ ] **Monitoring Configuration**
  - [ ] Create monitoring for top 5-10 competitors
  - [ ] Configure intervals (weekly for content, daily for pricing)
  - [ ] Setup webhook endpoint for notifications

```python
# src/tools/hexowatch_tools.py
import requests
import os

def create_competitor_monitor(domain: str, tool_type: str = "contentMonitoringTool"):
    """Create a Hexowatch monitor for a competitor."""
    response = requests.post(
        "https://api.hexowatch.com/v2/app/services/v2/monitor",
        json={
            "key": os.getenv("HEXOWATCH_API_KEY"),
            "tool": tool_type,
            "address_list": [domain],
            "monitoring_interval": "1_WEEK",
            "tool_settings": {"mode": "ANY_CHANGE"}
        }
    )
    return response.json()
```

- [ ] **Alert Processing**
  - [ ] Webhook handler for change notifications
  - [ ] Trigger re-crawl on significant changes
  - [ ] Log changes to analysis database

### Phase 3: Analysis Pipeline

- [ ] **CrewAI Workflow**
  - [ ] Add tools to Research Analyst agent
  - [ ] Create "Competitor Analysis" task
  - [ ] Define expected output format

- [ ] **Data Storage**
  - [ ] Schema for competitor snapshots
  - [ ] Historical comparison capability
  - [ ] Gap analysis reporting

---

## Process Flow

```
1. Initial Setup
   └── Configure API keys
   └── Define competitor list

2. Data Collection (Firecrawl)
   └── Crawl each competitor site
   └── Extract structured data (pricing, features, content)
   └── Store raw + processed data

3. Monitoring Setup (Hexowatch)
   └── Create monitors for each competitor
   └── Configure notification webhooks
   └── Set appropriate intervals

4. Analysis (CrewAI Agents)
   └── Research Analyst processes crawl data
   └── Content Strategist identifies gaps
   └── Generate actionable insights

5. Continuous Loop
   └── Hexowatch detects changes → Webhook fires
   └── Re-crawl changed pages
   └── Update analysis
   └── Alert relevant agents
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Competitors monitored | 5-10 |
| Crawl freshness | < 7 days |
| Extraction accuracy | > 90% |
| Alert latency | < 1 hour |
| Cost per competitor/month | < $5 |

---

## Dependencies

- `firecrawl-py` - Web crawling SDK
- `requests` - HTTP client for Hexowatch API
- `pydantic` - Data validation schemas
- CrewAI Research Analyst agent

---

## Alternative: Firecrawl MCP Server

For local development or Claude Desktop integration:

```bash
env FIRECRAWL_API_KEY=fc-YOUR_API_KEY npx -y firecrawl-mcp
```

**Key MCP tools for competitor analysis:**
- `firecrawl_map` - Discover all URLs on competitor site
- `firecrawl_crawl` - Extract content from multiple pages
- `firecrawl_extract` - Structured data extraction with schema
- `firecrawl_search` - Find competitor content by topic

See: https://github.com/firecrawl/firecrawl-mcp-server

---

## Notes

- Cache Firecrawl responses (24h TTL) to reduce costs
- Start with contentMonitoringTool, add techStackTool later
- Respect robots.txt and rate limits
