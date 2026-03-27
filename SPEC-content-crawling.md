# TASK: Content Crawling for Article Generation

> **Robot**: Article Generator Robot
> **Tools**: Firecrawl (crawl/scrape/extract)
> **Priority**: High

## Objective

Implement web crawling capabilities for the Article Generator to analyze competitor content, identify gaps, and generate original articles based on competitive insights.

---

## Implementation Checklist

### Phase 1: Firecrawl Integration

- [ ] **Setup**
  - [ ] Install SDK: `pip install firecrawl-py`
  - [ ] Add `FIRECRAWL_API_KEY` to `.env`
  - [ ] Create `src/articles/tools/firecrawl_tools.py`

- [ ] **Basic Crawling**
  - [ ] Implement site crawl function
  - [ ] Configure depth and page limits
  - [ ] Handle async/webhook for large crawls

```python
# src/articles/tools/firecrawl_tools.py
from firecrawl import Firecrawl
from crewai import tool
import os

@tool
def crawl_site_for_content(url: str, max_pages: int = 20) -> str:
    """
    Crawl a website and return markdown content for analysis.
    Use this to understand competitor content structure and topics.
    """
    client = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

    result = client.crawl(
        url=url,
        limit=max_pages,
        scrape_options={"formats": ["markdown"]}
    )

    pages = []
    for doc in result.data:
        title = doc.get("metadata", {}).get("title", "Untitled")
        markdown = doc.get("markdown", "")
        pages.append(f"## {title}\n\n{markdown}")

    return "\n\n---\n\n".join(pages)
```

### Phase 2: Structured Extraction

- [ ] **Article Analysis Schema**
  - [ ] Define Pydantic model for article structure
  - [ ] Extract key elements (headings, topics, keywords)
  - [ ] Identify content patterns

```python
# src/articles/schemas/article_analysis.py
from pydantic import BaseModel

class ArticleAnalysis(BaseModel):
    title: str
    main_topic: str
    subtopics: list[str]
    target_keywords: list[str]
    word_count: int
    heading_structure: list[str]
    content_type: str  # tutorial, guide, listicle, etc.
    unique_angles: list[str]
    missing_topics: list[str]

class CompetitorContentGap(BaseModel):
    competitor_url: str
    topics_covered: list[str]
    topics_missing: list[str]
    recommended_articles: list[str]
```

- [ ] **JSON Extraction Mode**
  - [ ] Use Firecrawl extract with schema
  - [ ] Validate against Pydantic models

```python
@tool
def extract_article_structure(url: str) -> ArticleAnalysis:
    """
    Extract structured article data from a URL.
    Returns analysis of the article's structure and content.
    """
    client = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

    result = client.scrape(
        url,
        formats=[{
            "type": "json",
            "schema": ArticleAnalysis.model_json_schema()
        }]
    )

    return ArticleAnalysis(**result.data["json"])
```

### Phase 3: Site Mapping

- [ ] **URL Discovery**
  - [ ] Use Firecrawl map endpoint
  - [ ] Filter for content pages (blog, articles)
  - [ ] Build content inventory

```python
@tool
def map_site_content(url: str, search_filter: str = None) -> list[str]:
    """
    Discover all content URLs on a site.
    Use before crawling to identify relevant pages.
    Optionally filter with search_filter for topic-based relevance.
    """
    client = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

    # Include sitemap data and optionally filter by search term
    result = client.map(
        url,
        sitemap="include",
        search=search_filter  # Filter for specific topics/URLs
    )

    # Filter for likely content pages
    content_urls = [
        link["url"] for link in result.links
        if any(p in link["url"] for p in ['/blog/', '/articles/', '/posts/', '/guide/'])
    ]

    return content_urls
```

### Phase 3.5: Web Search Integration

- [ ] **Search Tool for Content Research**
  - [ ] Use Firecrawl search endpoint for topic research
  - [ ] Combine search with scraping for rich content
  - [ ] Filter by time (recent content) and location

```python
@tool
def search_topic_content(query: str, limit: int = 10, scrape: bool = True) -> str:
    """
    Search the web for content on a topic and optionally scrape results.
    Use for competitive research and content gap analysis.
    """
    client = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

    scrape_options = {"formats": ["markdown", "links"]} if scrape else None

    results = client.search(
        query=query,
        limit=limit,
        scrape_options=scrape_options,
        tbs="qdr:m"  # Past month for fresh content
    )

    output = []
    for item in results.data.get("web", []):
        entry = f"## {item.get('title', 'Untitled')}\n"
        entry += f"URL: {item.get('url')}\n"
        if scrape and item.get("markdown"):
            entry += f"\n{item.get('markdown')[:2000]}..."
        else:
            entry += f"\n{item.get('description', '')}"
        output.append(entry)

    return "\n\n---\n\n".join(output)
```

### Phase 4: CrewAI Integration

- [ ] **Add Tools to Article Generator Agent**
  - [ ] Register Firecrawl tools
  - [ ] Create content analysis task
  - [ ] Define gap analysis workflow

```python
# src/articles/agents/article_generator.py
from crewai import Agent, Task
from src.articles.tools.firecrawl_tools import (
    crawl_site_for_content,
    extract_article_structure,
    map_site_content,
    search_topic_content
)

article_researcher = Agent(
    role="Content Researcher",
    goal="Analyze competitor content to identify gaps and opportunities",
    backstory="Expert at understanding content strategies and finding unique angles",
    tools=[crawl_site_for_content, extract_article_structure, map_site_content, search_topic_content]
)

content_analysis_task = Task(
    description="""
    1. Map the competitor site to find all content URLs
    2. Crawl the top 10 most relevant pages
    3. Extract article structure from each
    4. Identify topics they cover well
    5. Find gaps where we can create unique content
    """,
    agent=article_researcher,
    expected_output="Content gap analysis with 5 recommended article topics"
)
```

### Phase 5: Caching & Optimization

- [ ] **Response Caching**
  - [ ] Cache crawl results (24h TTL)
  - [ ] Implement cache invalidation
  - [ ] Reduce API costs

```python
# src/articles/tools/cache.py
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

CACHE_DIR = Path("cache/firecrawl")
CACHE_TTL = timedelta(hours=24)

def get_cache_key(url: str, operation: str) -> str:
    return hashlib.md5(f"{url}:{operation}".encode()).hexdigest()

def get_cached(url: str, operation: str) -> dict | None:
    cache_file = CACHE_DIR / f"{get_cache_key(url, operation)}.json"
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        cached_at = datetime.fromisoformat(data["cached_at"])
        if datetime.now() - cached_at < CACHE_TTL:
            return data["result"]
    return None

def set_cached(url: str, operation: str, result: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{get_cache_key(url, operation)}.json"
    cache_file.write_text(json.dumps({
        "cached_at": datetime.now().isoformat(),
        "result": result
    }))
```

---

## Process Flow

```
1. Target Identification
   └── Define competitor URLs
   └── Identify content topics to analyze

2. Web Search (Firecrawl search)
   └── Search for topic-specific content
   └── Get recent competitive landscape
   └── Scrape search results for analysis

3. Site Mapping (Firecrawl map)
   └── Discover all content URLs
   └── Include sitemap data
   └── Filter by search relevance

4. Content Crawling (Firecrawl crawl)
   └── Crawl prioritized pages
   └── Convert to clean markdown
   └── Store for analysis

5. Structure Extraction (Firecrawl scrape + JSON)
   └── Extract article metadata
   └── Identify patterns and structures
   └── Validate against Pydantic schemas

6. Gap Analysis (CrewAI Agent)
   └── Compare with own content
   └── Identify missing topics
   └── Generate article recommendations

7. Article Generation
   └── Use insights for original content
   └── Maintain topical flow
   └── Validate uniqueness
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Crawl accuracy | > 95% |
| Extraction success | > 90% |
| Cache hit rate | > 70% |
| Cost per analysis | < $0.50 |
| Article generation time | < 15 min |

---

## Environment Variables

```bash
# .env
FIRECRAWL_API_KEY=fc-your-api-key-here
```

---

## Dependencies

- `firecrawl-py` - Firecrawl SDK
- `pydantic` - Schema validation
- CrewAI framework for agent orchestration

---

## Alternative: MCP Server Integration

For local development or Claude Desktop/Cursor integration, use the Firecrawl MCP server:

```bash
# Run with npx
env FIRECRAWL_API_KEY=fc-YOUR_API_KEY npx -y firecrawl-mcp

# Or install globally
npm install -g firecrawl-mcp
```

**Available MCP tools:**
| Tool | Description |
|------|-------------|
| `firecrawl_scrape` | Single page content extraction |
| `firecrawl_batch_scrape` | Multiple known URLs |
| `firecrawl_map` | Discover URLs on a site |
| `firecrawl_crawl` | Multi-page extraction |
| `firecrawl_search` | Web search with optional scraping |
| `firecrawl_extract` | Structured data extraction (LLM-powered) |

**Claude Desktop config** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "firecrawl": {
      "command": "npx",
      "args": ["-y", "firecrawl-mcp"],
      "env": {
        "FIRECRAWL_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

See: https://github.com/firecrawl/firecrawl-mcp-server

---

## Notes

- Respect robots.txt (Firecrawl handles automatically)
- Start with 10-page limit per site to control costs
- Use map before crawl to target specific content
- Cache aggressively to reduce API calls
- Search costs: 2 credits per 10 results + scraping credits
- Use `tbs` param in search for time filtering (qdr:d=day, qdr:w=week, qdr:m=month)
