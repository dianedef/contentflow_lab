# TASK: Crawlee Hybrid Crawling (Cost Optimization)

> **Robot**: Article Generator + SEO Robot
> **Tools**: Crawlee (primary) + Firecrawl (fallback)
> **Priority**: Low (implement when scaling needed)

## When to Implement

**Trigger this task when:**
- [ ] Crawling > 500 pages/month consistently
- [ ] Firecrawl costs exceed $50/month
- [ ] Need custom extraction logic Firecrawl doesn't support

**Skip if:** Current volume is low and Firecrawl costs are acceptable.

---

## Objective

Replace direct Firecrawl usage with Crawlee as primary crawler, falling back to Firecrawl only for sites that block or require advanced anti-bot. Reduces costs by 60-80% at scale.

---

## Implementation Checklist

### Phase 1: Crawlee Setup

- [ ] **Install Dependencies**
  ```bash
  pip install crawlee[playwright]
  playwright install chromium
  ```

- [ ] **Create Base Crawler Module**
  - [ ] Create `src/tools/crawlee_client.py`
  - [ ] Implement basic HTTP and browser crawlers
  - [ ] Add markdown conversion (match Firecrawl output)

```python
# src/tools/crawlee_client.py
from crawlee.playwright_crawler import PlaywrightCrawler, PlaywrightCrawlingContext
from crawlee.http_crawler import HttpCrawler, HttpCrawlingContext
import html2text
from dataclasses import dataclass

@dataclass
class CrawlResult:
    url: str
    title: str
    markdown: str
    success: bool
    error: str | None = None

class CrawleeClient:
    """Crawlee-based crawler with Firecrawl-compatible output."""

    def __init__(self):
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = False

    async def crawl_simple(self, urls: list[str]) -> list[CrawlResult]:
        """Fast HTTP crawl for simple sites (no JS rendering)."""
        results = []

        crawler = HttpCrawler(
            max_requests_per_crawl=len(urls),
            request_handler=self._http_handler(results)
        )

        await crawler.run(urls)
        return results

    async def crawl_browser(self, urls: list[str]) -> list[CrawlResult]:
        """Browser crawl for JS-heavy sites."""
        results = []

        crawler = PlaywrightCrawler(
            max_requests_per_crawl=len(urls),
            headless=True,
            request_handler=self._browser_handler(results)
        )

        await crawler.run(urls)
        return results

    def _http_handler(self, results: list):
        async def handler(context: HttpCrawlingContext):
            try:
                html = context.http_response.read().decode()
                markdown = self.h2t.handle(html)
                results.append(CrawlResult(
                    url=str(context.request.url),
                    title=self._extract_title(html),
                    markdown=markdown,
                    success=True
                ))
            except Exception as e:
                results.append(CrawlResult(
                    url=str(context.request.url),
                    title="",
                    markdown="",
                    success=False,
                    error=str(e)
                ))
        return handler

    def _browser_handler(self, results: list):
        async def handler(context: PlaywrightCrawlingContext):
            try:
                html = await context.page.content()
                title = await context.page.title()
                markdown = self.h2t.handle(html)
                results.append(CrawlResult(
                    url=str(context.request.url),
                    title=title,
                    markdown=markdown,
                    success=True
                ))
            except Exception as e:
                results.append(CrawlResult(
                    url=str(context.request.url),
                    title="",
                    markdown="",
                    success=False,
                    error=str(e)
                ))
        return handler

    def _extract_title(self, html: str) -> str:
        import re
        match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        return match.group(1) if match else ""
```

### Phase 2: Hybrid Fallback Logic

- [ ] **Create Hybrid Crawler**
  - [ ] Try Crawlee first
  - [ ] Detect failures/blocks
  - [ ] Fallback to Firecrawl on failure

```python
# src/tools/hybrid_crawler.py
from src.tools.crawlee_client import CrawleeClient, CrawlResult
from firecrawl import Firecrawl
import os
import logging

logger = logging.getLogger(__name__)

class HybridCrawler:
    """Crawlee primary, Firecrawl fallback."""

    def __init__(self):
        self.crawlee = CrawleeClient()
        self.firecrawl = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

        # Sites known to need Firecrawl (learned over time)
        self.firecrawl_domains: set[str] = set()

    async def crawl(self, urls: list[str], use_browser: bool = False) -> list[CrawlResult]:
        """
        Crawl URLs with automatic fallback.

        1. Check if domain is in firecrawl_domains -> use Firecrawl directly
        2. Try Crawlee
        3. On failure -> retry with Firecrawl, add domain to blocklist
        """
        results = []
        crawlee_urls = []
        firecrawl_urls = []

        # Split URLs by known difficulty
        for url in urls:
            domain = self._get_domain(url)
            if domain in self.firecrawl_domains:
                firecrawl_urls.append(url)
            else:
                crawlee_urls.append(url)

        # Crawlee batch
        if crawlee_urls:
            if use_browser:
                crawlee_results = await self.crawlee.crawl_browser(crawlee_urls)
            else:
                crawlee_results = await self.crawlee.crawl_simple(crawlee_urls)

            for result in crawlee_results:
                if result.success:
                    results.append(result)
                else:
                    # Retry with Firecrawl
                    logger.info(f"Crawlee failed for {result.url}, trying Firecrawl")
                    firecrawl_urls.append(result.url)
                    self.firecrawl_domains.add(self._get_domain(result.url))

        # Firecrawl batch (known hard + failed)
        if firecrawl_urls:
            for url in firecrawl_urls:
                fc_result = self._crawl_with_firecrawl(url)
                results.append(fc_result)

        return results

    def _crawl_with_firecrawl(self, url: str) -> CrawlResult:
        """Single URL crawl via Firecrawl."""
        try:
            result = self.firecrawl.scrape(url, formats=["markdown"])
            return CrawlResult(
                url=url,
                title=result.metadata.get("title", ""),
                markdown=result.markdown,
                success=True
            )
        except Exception as e:
            return CrawlResult(
                url=url,
                title="",
                markdown="",
                success=False,
                error=str(e)
            )

    def _get_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc
```

### Phase 3: CrewAI Tool Integration

- [ ] **Update Tools to Use Hybrid Crawler**
  - [ ] Replace Firecrawl-only tools
  - [ ] Maintain same interface for agents

```python
# src/articles/tools/crawl_tools.py (updated)
from crewai import tool
from src.tools.hybrid_crawler import HybridCrawler
import asyncio

crawler = HybridCrawler()

@tool
def crawl_site_for_content(url: str, max_pages: int = 20) -> str:
    """
    Crawl a website and return markdown content for analysis.
    Uses cost-optimized hybrid approach (Crawlee + Firecrawl fallback).
    """
    # For now, single URL - extend to site crawl later
    results = asyncio.run(crawler.crawl([url]))

    if results and results[0].success:
        return f"## {results[0].title}\n\n{results[0].markdown}"
    else:
        return f"Failed to crawl {url}: {results[0].error if results else 'Unknown error'}"
```

### Phase 4: Bright Data Integration (Optional)

- [ ] **Add Only If Needed**
  - [ ] When Crawlee fails on many sites
  - [ ] When you need geo-specific crawling

```python
# src/tools/crawlee_client.py (with Bright Data)
from crawlee.playwright_crawler import PlaywrightCrawler
from crawlee.proxy_configuration import ProxyConfiguration

# Only add if you're hitting blocks
BRIGHT_DATA_PROXY = "http://user:pass@brd.superproxy.io:22225"

async def crawl_with_proxy(self, urls: list[str]) -> list[CrawlResult]:
    """Browser crawl with Bright Data proxy (expensive, use sparingly)."""
    proxy_config = ProxyConfiguration(
        proxy_urls=[BRIGHT_DATA_PROXY]
    )

    crawler = PlaywrightCrawler(
        proxy_configuration=proxy_config,
        max_requests_per_crawl=len(urls),
        request_handler=self._browser_handler([])
    )

    await crawler.run(urls)
```

---

## Process Flow

```
URL to crawl
    │
    ▼
┌─────────────────────────┐
│ Domain in blocklist?    │
└─────────────────────────┘
    │ No              │ Yes
    ▼                 ▼
┌─────────┐    ┌─────────────┐
│ Crawlee │    │ Firecrawl   │
│ (free)  │    │ (paid)      │
└─────────┘    └─────────────┘
    │
    ▼
┌─────────────────────────┐
│ Success?                │
└─────────────────────────┘
    │ Yes             │ No
    ▼                 ▼
  Return        ┌─────────────┐
  result        │ Add to      │
                │ blocklist   │
                │ + Firecrawl │
                └─────────────┘
```

---

## Cost Comparison

| Scenario | Firecrawl Only | Hybrid |
|----------|----------------|--------|
| 100 pages/month | ~$1 | ~$0.20 |
| 500 pages/month | ~$5 | ~$1 |
| 2000 pages/month | ~$20 | ~$4 |
| 10000 pages/month | ~$100 | ~$15-20 |

*Assumes 80% of sites work with Crawlee, 20% need Firecrawl fallback.*

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Crawlee success rate | > 80% |
| Fallback rate | < 20% |
| Cost reduction | > 60% |
| Crawl quality (vs Firecrawl) | Equivalent |

---

## Environment Variables

```bash
# .env
FIRECRAWL_API_KEY=fc-xxx          # Still needed for fallback

# Optional - only if adding Bright Data
BRIGHT_DATA_USER=xxx
BRIGHT_DATA_PASS=xxx
```

---

## Dependencies

```bash
pip install crawlee[playwright] html2text firecrawl-py
playwright install chromium
```

---

## Notes

- **Start without Bright Data** - Crawlee's defaults handle most sites
- **Track blocklist** - Persist `firecrawl_domains` to file/db over time
- **Monitor costs** - Compare before/after to validate savings
- **Browser crawl is slower** - Use HTTP crawler when possible
