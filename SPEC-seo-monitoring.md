# TASK: SEO & Tech Stack Monitoring

> **Robot**: SEO Robot + Scheduling Robot
> **Tools**: Hexowatch (monitoring), Firecrawl (AI readiness analysis)
> **Priority**: Medium

## Objective

Implement continuous SEO monitoring for competitor sites and own properties using Hexowatch, feeding insights to SEO Robot agents.

---

## Implementation Checklist

### Phase 1: Hexowatch Setup

- [ ] **Account & Configuration**
  - [ ] Create Hexowatch account
  - [ ] Add `HEXOWATCH_API_KEY` to `.env`
  - [ ] Create notification integration (webhook)

- [ ] **API Client Module**
  - [ ] Create `src/tools/hexowatch_client.py`
  - [ ] Implement monitor CRUD operations
  - [ ] Add log retrieval functions

```python
# src/tools/hexowatch_client.py
import requests
import os
from typing import Literal

MonitorTool = Literal[
    "techStackTool",
    "keywordTool",
    "contentMonitoringTool",
    "backlinkTool",
    "availabilityMonitoringTool"
]

class HexowatchClient:
    BASE_URL = "https://api.hexowatch.com/v2/app/services"

    def __init__(self):
        self.api_key = os.getenv("HEXOWATCH_API_KEY")

    def create_monitor(
        self,
        domains: list[str],
        tool: MonitorTool,
        interval: str = "1_WEEK"
    ) -> dict:
        """Create a new monitoring job."""
        response = requests.post(
            f"{self.BASE_URL}/v2/monitor",
            json={
                "key": self.api_key,
                "tool": tool,
                "address_list": domains,
                "monitoring_interval": interval,
                "tool_settings": {"mode": "ANY_CHANGE"}
            }
        )
        return response.json()

    def list_monitors(self) -> list:
        """Get all active monitors."""
        response = requests.get(
            f"{self.BASE_URL}/v1/monitored_urls",
            params={"key": self.api_key}
        )
        return response.json()

    def get_logs(self, monitor_id: str) -> list:
        """Get change logs for a monitor."""
        response = requests.get(
            f"{self.BASE_URL}/v1/monitoring_logs/{monitor_id}",
            params={"key": self.api_key}
        )
        return response.json()

    def trigger_check(self, monitor_id: str) -> dict:
        """Manually trigger a check."""
        response = requests.patch(
            f"{self.BASE_URL}/v1/action",
            json={
                "key": self.api_key,
                "id": monitor_id,
                "action": "check_now"
            }
        )
        return response.json()
```

### Phase 2: Monitoring Types

- [ ] **Tech Stack Monitoring**
  - [ ] Track competitor technology changes
  - [ ] Alert on new tools/frameworks adoption
  - [ ] Feed insights to Technical SEO agent

```python
# Monitor competitor tech stacks
client = HexowatchClient()
client.create_monitor(
    domains=["competitor1.com", "competitor2.com"],
    tool="techStackTool",
    interval="1_WEEK"
)
```

- [ ] **Keyword Monitoring**
  - [ ] Track target keyword presence on pages
  - [ ] Alert on keyword additions/removals
  - [ ] Feed to Content Strategist agent

- [ ] **Backlink Monitoring**
  - [ ] Track new/lost backlinks for competitors
  - [ ] Identify link building opportunities
  - [ ] Alert on significant changes

- [ ] **Content Change Monitoring**
  - [ ] Monitor competitor blog/content updates
  - [ ] Trigger content gap analysis on changes

### Phase 3: Webhook Integration

- [ ] **Webhook Endpoint**
  - [ ] Create FastAPI endpoint for notifications
  - [ ] Parse Hexowatch webhook payload
  - [ ] Route to appropriate agent workflow

```python
# src/api/webhooks.py
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhooks/hexowatch")
async def hexowatch_webhook(request: Request):
    """Handle Hexowatch change notifications."""
    payload = await request.json()

    change_type = payload.get("tool")
    domain = payload.get("domain")
    changes = payload.get("changes")

    # Route to appropriate handler
    if change_type == "techStackTool":
        await handle_tech_change(domain, changes)
    elif change_type == "contentMonitoringTool":
        await handle_content_change(domain, changes)
    elif change_type == "backlinkTool":
        await handle_backlink_change(domain, changes)

    return {"status": "processed"}
```

### Phase 4: Agent Integration

- [ ] **SEO Robot Tools**
  - [ ] Create `@tool` decorated functions
  - [ ] Add to Technical SEO Specialist agent
  - [ ] Implement analysis tasks

```python
# src/seo/tools/monitoring_tools.py
from crewai import tool
from src.tools.hexowatch_client import HexowatchClient

@tool
def get_competitor_tech_changes(domain: str) -> str:
    """Get recent technology changes for a competitor site."""
    client = HexowatchClient()
    monitors = client.list_monitors()

    for monitor in monitors:
        if domain in monitor.get("address_list", []):
            logs = client.get_logs(monitor["id"])
            return format_tech_changes(logs)

    return f"No monitoring configured for {domain}"

@tool
def check_keyword_presence(domain: str, keywords: list[str]) -> str:
    """Check if target keywords are present on competitor pages."""
    # Implementation using keywordTool results
    pass
```

### Phase 5: AI Readiness Analysis

Analyze sites for LLM/AI crawler compatibility using Firecrawl.

- [ ] **AI Readiness Client**
  - [ ] Create `src/tools/ai_readiness.py`
  - [ ] Implement scoring algorithm
  - [ ] Add llms.txt detection

```python
# src/tools/ai_readiness.py
from firecrawl import Firecrawl
from pydantic import BaseModel
from crewai import tool
import os
import re

class AIReadinessScore(BaseModel):
    url: str
    overall_score: int  # 0-100
    checks: dict[str, dict]  # Individual check results
    recommendations: list[str]

class AIReadinessAnalyzer:
    """Analyze website AI-readiness for LLM crawlers."""

    def __init__(self):
        self.client = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

    def analyze(self, url: str) -> AIReadinessScore:
        """Run full AI readiness analysis on a URL."""
        # Scrape the page
        result = self.client.scrape(url, formats=["html"])
        html = result.data.get("html", "")
        metadata = result.data.get("metadata", {})

        checks = {}
        recommendations = []

        # 1. Check llms.txt
        checks["llms_txt"] = self._check_llms_txt(url)
        if checks["llms_txt"]["score"] < 100:
            recommendations.append("Add llms.txt file to define AI usage permissions")

        # 2. Heading structure
        checks["headings"] = self._check_headings(html)
        if checks["headings"]["score"] < 80:
            recommendations.append("Use exactly one H1 and maintain logical heading hierarchy")

        # 3. Readability
        checks["readability"] = self._check_readability(html)
        if checks["readability"]["score"] < 80:
            recommendations.append("Simplify sentences for better AI comprehension")

        # 4. Metadata quality
        checks["metadata"] = self._check_metadata(html, metadata)
        if checks["metadata"]["score"] < 70:
            recommendations.append("Add title, description, author, and publish date metadata")

        # 5. Semantic HTML
        checks["semantic"] = self._check_semantic_html(html)
        if checks["semantic"]["score"] < 80:
            recommendations.append("Use semantic HTML5 elements (article, main, section)")

        # 6. robots.txt + sitemap
        checks["crawlability"] = self._check_crawlability(url)
        if checks["crawlability"]["score"] < 80:
            recommendations.append("Add sitemap reference to robots.txt")

        # Calculate weighted overall score
        weights = {
            "readability": 1.5,
            "headings": 1.4,
            "metadata": 1.2,
            "semantic": 1.0,
            "crawlability": 0.9,
            "llms_txt": 0.3
        }

        weighted_sum = sum(checks[k]["score"] * weights[k] for k in weights)
        total_weight = sum(weights.values())
        overall = round(weighted_sum / total_weight)

        return AIReadinessScore(
            url=url,
            overall_score=overall,
            checks=checks,
            recommendations=recommendations
        )

    def _check_llms_txt(self, url: str) -> dict:
        """Check for llms.txt file."""
        from urllib.parse import urlparse
        import requests

        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        for filename in ["llms.txt", "LLMs.txt", "llms-full.txt"]:
            try:
                resp = requests.get(f"{base}/{filename}", timeout=3)
                if resp.ok and not resp.text.startswith("<!DOCTYPE"):
                    return {"score": 100, "status": "pass", "details": f"{filename} found"}
            except:
                pass
        return {"score": 0, "status": "fail", "details": "No llms.txt found"}

    def _check_headings(self, html: str) -> dict:
        """Check heading structure."""
        h1_count = len(re.findall(r'<h1[^>]*>', html, re.I))
        score = 100
        issues = []

        if h1_count == 0:
            score -= 40
            issues.append("No H1 found")
        elif h1_count > 1:
            score -= 30
            issues.append(f"Multiple H1s ({h1_count})")

        return {
            "score": max(0, score),
            "status": "pass" if score >= 80 else "warning" if score >= 50 else "fail",
            "details": ", ".join(issues) if issues else "Good heading structure"
        }

    def _check_readability(self, html: str) -> dict:
        """Calculate Flesch Reading Ease score."""
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()

        sentences = [s for s in re.split(r'[.!?]+', text) if s.strip()]
        words = text.split()
        if not sentences or not words:
            return {"score": 0, "status": "fail", "details": "No content"}

        # Count syllables (approximation)
        syllables = sum(len(re.findall(r'[aeiouAEIOU]+', w)) or 1 for w in words)

        flesch = 206.835 - 1.015 * (len(words)/len(sentences)) - 84.6 * (syllables/len(words))
        flesch = max(0, min(100, flesch))

        if flesch >= 60:
            return {"score": 100, "status": "pass", "details": f"Flesch: {round(flesch)}"}
        elif flesch >= 40:
            return {"score": 70, "status": "warning", "details": f"Flesch: {round(flesch)}"}
        return {"score": 40, "status": "fail", "details": f"Flesch: {round(flesch)}"}

    def _check_metadata(self, html: str, metadata: dict) -> dict:
        """Check metadata quality."""
        score = 30  # Base score
        details = []

        if metadata.get("title") or "<title" in html.lower():
            score += 30
            details.append("Title ✓")
        if metadata.get("description") or 'name="description"' in html.lower():
            score += 25
            details.append("Description ✓")
        if 'name="author"' in html.lower():
            score += 10
            details.append("Author ✓")
        if 'article:published_time' in html.lower():
            score += 10
            details.append("Date ✓")

        return {
            "score": min(100, score),
            "status": "pass" if score >= 70 else "warning" if score >= 40 else "fail",
            "details": ", ".join(details) if details else "Missing metadata"
        }

    def _check_semantic_html(self, html: str) -> dict:
        """Check for semantic HTML5 elements."""
        tags = ['<article', '<nav', '<main', '<section', '<header', '<footer']
        found = sum(1 for tag in tags if tag in html.lower())
        score = min(100, (found / 5) * 80 + 20)

        return {
            "score": round(score),
            "status": "pass" if score >= 80 else "warning" if score >= 40 else "fail",
            "details": f"Found {found}/6 semantic elements"
        }

    def _check_crawlability(self, url: str) -> dict:
        """Check robots.txt and sitemap."""
        from urllib.parse import urlparse
        import requests

        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        score = 0
        details = []

        try:
            robots = requests.get(f"{base}/robots.txt", timeout=3)
            if robots.ok:
                score += 50
                details.append("robots.txt ✓")
                if "sitemap" in robots.text.lower():
                    score += 30
                    details.append("Sitemap ref ✓")
        except:
            pass

        try:
            sitemap = requests.get(f"{base}/sitemap.xml", timeout=3)
            if sitemap.ok and "<?xml" in sitemap.text:
                score += 20
                details.append("sitemap.xml ✓")
        except:
            pass

        return {
            "score": min(100, score),
            "status": "pass" if score >= 80 else "warning" if score >= 40 else "fail",
            "details": ", ".join(details) if details else "Missing crawl files"
        }
```

- [ ] **CrewAI Tools**
  - [ ] Add AI readiness tools to SEO agents
  - [ ] Compare competitor AI-readiness scores
  - [ ] Track score changes over time

```python
# src/seo/tools/ai_readiness_tools.py
from crewai import tool
from src.tools.ai_readiness import AIReadinessAnalyzer

@tool
def analyze_ai_readiness(url: str) -> str:
    """
    Analyze a website's AI readiness score.
    Checks: llms.txt, headings, readability, metadata, semantic HTML, crawlability.
    Returns overall score (0-100) and recommendations.
    """
    analyzer = AIReadinessAnalyzer()
    result = analyzer.analyze(url)

    output = f"AI Readiness Score for {url}: {result.overall_score}/100\n\n"
    output += "Checks:\n"
    for name, check in result.checks.items():
        output += f"  - {name}: {check['score']}/100 ({check['status']})\n"

    if result.recommendations:
        output += "\nRecommendations:\n"
        for rec in result.recommendations:
            output += f"  - {rec}\n"

    return output

@tool
def compare_ai_readiness(urls: list[str]) -> str:
    """
    Compare AI readiness scores across multiple sites.
    Use to benchmark competitors vs own properties.
    """
    analyzer = AIReadinessAnalyzer()
    results = []

    for url in urls:
        try:
            score = analyzer.analyze(url)
            results.append((url, score.overall_score, score.checks))
        except Exception as e:
            results.append((url, 0, {"error": str(e)}))

    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)

    output = "AI Readiness Comparison:\n\n"
    output += "| Rank | Site | Score | Best | Worst |\n"
    output += "|------|------|-------|------|-------|\n"

    for i, (url, score, checks) in enumerate(results, 1):
        if "error" not in checks:
            best = max(checks.items(), key=lambda x: x[1]["score"])[0]
            worst = min(checks.items(), key=lambda x: x[1]["score"])[0]
            output += f"| {i} | {url[:30]} | {score} | {best} | {worst} |\n"
        else:
            output += f"| {i} | {url[:30]} | Error | - | - |\n"

    return output
```

- [ ] **Scheduled Audits**
  - [ ] Weekly AI readiness scan for all monitored sites
  - [ ] Alert on score drops > 10 points
  - [ ] Track industry benchmarks

---

## Process Flow

```
1. Initial Setup
   └── Configure Hexowatch + Firecrawl APIs
   └── Create monitors for competitors + own sites
   └── Setup webhook endpoint
   └── Run baseline AI readiness scan

2. Continuous Monitoring (Hexowatch)
   └── Tech stack changes detected
   └── Content updates captured
   └── Backlink changes tracked

3. AI Readiness Audits (Weekly, Firecrawl)
   └── Scan all monitored sites
   └── Calculate AI readiness scores
   └── Check llms.txt, headings, readability
   └── Compare vs previous scores

4. Webhook Processing
   └── Receive change notification
   └── Parse and categorize change
   └── Store in monitoring database
   └── Trigger AI readiness re-scan if content changed

5. Agent Analysis (Scheduled)
   └── Technical SEO reviews tech changes + AI readiness
   └── Content Strategist reviews content changes
   └── Research Analyst reviews backlink changes

6. Action Generation
   └── Create recommendations
   └── Prioritize by AI readiness impact
   └── Update content strategy
   └── Alert on critical changes or score drops
```

---

## Monitor Configuration

| Target | Tool | Interval | Purpose |
|--------|------|----------|---------|
| Competitors (5-10) | techStackTool | Weekly | Tech trends |
| Competitors (5-10) | contentMonitoringTool | Weekly | Content gaps |
| Competitors (5-10) | backlinkTool | Weekly | Link opportunities |
| Competitors (5-10) | AI Readiness (Firecrawl) | Weekly | LLM optimization |
| Own sites | availabilityMonitoringTool | 5 min | Uptime |
| Own sites | keywordTool | Daily | Ranking check |
| Own sites | AI Readiness (Firecrawl) | Weekly | Self-audit |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Monitors active | 20-50 |
| Alert latency | < 1 hour |
| False positive rate | < 10% |
| Insights actionable | > 70% |
| Own sites AI readiness | > 80/100 |
| Competitor benchmark gap | < 10 points |
| llms.txt adoption | 100% own sites |

---

## Environment Variables

```bash
# .env
HEXOWATCH_API_KEY=your_api_key_here
HEXOWATCH_WEBHOOK_SECRET=optional_secret_for_validation
FIRECRAWL_API_KEY=fc-your-api-key-here
```

---

## Dependencies

- `requests` - HTTP client
- `fastapi` - Webhook endpoint
- `firecrawl-py` - AI readiness analysis
- `pydantic` - Schema validation
- CrewAI Technical SEO Specialist agent

---

## Notes

- Start with 5 competitors, scale gradually
- Use weekly intervals to control costs
- AI readiness checks: ~1 Firecrawl credit per page
- Consider adding llms.txt to own sites for AI crawler guidance
- Reference: https://github.com/firecrawl/ai-ready-website

## AI Readiness Scoring Weights

| Check | Weight | Why |
|-------|--------|-----|
| Readability | 1.5x | Most important for LLM comprehension |
| Headings | 1.4x | Structure helps AI understand hierarchy |
| Metadata | 1.2x | Context for AI summarization |
| Semantic HTML | 1.0x | Baseline structural signal |
| Crawlability | 0.9x | Access requirement |
| llms.txt | 0.3x | Emerging standard, bonus points |
