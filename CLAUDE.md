# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains an intelligent automation system with four main components:
1. **SEO Robot** - Multi-agent CrewAI system for SEO optimization
2. **Newsletter Agent** - PydanticAI-based automated newsletter generation with Exa AI
3. **Article Generator** - CrewAI agent using Firecrawl for competitor analysis and content generation
4. **Scheduling Robot** - Multi-agent system for content scheduling, publishing, and technical analysis


## Common Commands



### Python Development (when implemented)
```bash
# Install dependencies (when requirements.txt is created)
pip install -r requirements.txt

# Run SEO robot agents (future)
python -m src.seo.workflows.seo_crew

# Run newsletter generation (future)
python -m src.newsletter.agents.newsletter_agent

# Run article generator (future)
python -m src.articles.agents.article_generator

# Run scheduling robot
python -m agents.scheduler.scheduler_crew

# Run tests (when created)
pytest tests/
```

### Git Workflow
```bash
# This repo uses main branch for development
git checkout main
git pull origin main
```

## High-Level Architecture

### Multi-Agent System Design

The project implements a **hierarchical multi-agent architecture** where specialized AI agents collaborate to achieve complex tasks:

#### SEO Robot (CrewAI - 6 Agents)
Agents work in **hierarchical orchestration**:
1. **Research Analyst** - Competitive analysis, SERP monitoring, keyword research
2. **Content Strategist** - Pillar pages, topic clusters, topical flow optimization
3. **Marketing Strategist** - Business priorities, ROI analysis, strategic recommendations
4. **Copywriter** - SEO-optimized content creation, metadata generation
5. **Technical SEO Specialist** - Schema.org markup, on-page optimization, technical validation
6. **Editor** - Final quality control, consistency validation, markdown formatting

**Key Pattern**: Sequential workflow where each agent builds on previous outputs, with the editor providing final harmonization.

#### Newsletter Agent (PydanticAI)
Single **structured agent** with strict validation:
- **Exa AI Integration** - Uses `/search` and `/contents` APIs for web data collection
- **Pydantic Schemas** - Enforces strict data validation and structure
- **Quality Filtering** - Content relevance scores >0.7, automated retry on validation failures
- **Template System** - Responsive email templates with dynamic content

**Key Pattern**: Linear pipeline (collect → filter → structure → validate → send) with strict schema enforcement at each stage.

#### Article Generator (CrewAI + Firecrawl)
Agent specialized in **competitor analysis and content creation**:
- **Firecrawl Integration** - Crawls competitor sites, extracts clean markdown
- **Analysis Pipeline** - Identifies content gaps, SEO opportunities, key topics
- **Content Generation** - Creates original articles based on competitive insights
- **SEO Integration** - Coordinates with SEO Robot for topical consistency

**Key Pattern**: Extract-Analyze-Generate workflow with Pydantic schema validation (ArticleAnalysis, GeneratedArticle).

#### Scheduling Robot (CrewAI - 4 Agents)
Multi-agent system for **content publishing and technical analysis**:
1. **Calendar Manager** - Analyzes publishing history, optimizes scheduling times, manages content queue
2. **Publishing Agent** - Git deployment, Google Search Console/Indexing API integration, rollback handling
3. **Technical SEO Analyzer** - Site crawling, schema validation, page speed, Core Web Vitals, internal linking
4. **Tech Stack Analyzer** - Dependency analysis, vulnerability scanning, build performance, API cost tracking

**Key Pattern**: Parallel workflows (publish + analyze) with self-analysis capabilities. The robot audits itself for technical SEO and infrastructure health.

**Link validation strategy (local-first → HTTP fallback)**:
- `SiteCrawler.detect_broken_links(local_repo_path=...)` — uses `LocalLinkChecker` against source files when repo is available (pre-deploy, no HTTP required)
- Fallback to HTTP crawl when no local repo path is provided (original behaviour)
- `LocalLinkChecker` lives in `agents/seo/tools/local_link_checker.py` and is also available to `InternalLinkingSpecialistAgent`

### Topical Flow and Content Architecture

This system emphasizes **topical SEO** strategies:
- **Topical Flow** - Logical content progression between pillar and cluster pages
- **Topic Mesh** - Network visualization of semantic relationships between content
- **Entity Mapping** - Graph-based analysis of relationships (see `agents/seo_topic_agent.py`)
- **Content Gaps** - Automated identification of missing topics vs competitors

The `SEOTopicAgent` class uses NetworkX for graph-based topic modeling and matplotlib for visualizations.

### Integration Points

#### External APIs
- **Exa AI** - Search, content extraction, research endpoints for newsletter curation
- **Firecrawl** - Website crawling with markdown output for article generation
- **EmailIt/Paced Email/Encharge.io** - Email delivery and analytics
- **LLM APIs** - OpenAI/Anthropic for agent reasoning and content generation

#### Infrastructure
- **Astro** - Static site generator for final content deployment
- **GitHub Pages** - Hosting for generated content
- **GitHub Actions + Blacksmith** - CI/CD with 2x speed improvement, 75% cost reduction
  - 3,000 free minutes/month on Blacksmith
  - Optimized Docker layer caching
  - LLM dependency caching for faster builds
- **Monitoring** - Performance metrics, cost tracking, quality analytics

### Data Flow Pattern

```
Input (User/Scheduled) → Agent(s) Process → Validation Layer → Output (Markdown/Email)
                            ↓
                    External APIs (Exa/Firecrawl/LLM)
                            ↓
                    Schema Validation (Pydantic)
                            ↓
                    Quality Checks (Retry Logic)
```

## Project Structure Insights

### Key Architecture Files
- **docs/plan.md** - Overall vision, strategic objectives, integration specifications
- **AGENTS.md** - Detailed agent specifications, workflows, quality metrics
- **docs/phases.md** - Development roadmap with 6 phases (Infrastructure → SEO → Newsletter → Tests → Articles → Future)

### Agent Implementation Pattern
- Located in `agents/` (current) or future `src/{seo,newsletter,articles}/agents/`
- Each agent has dedicated tools in `tools/` subdirectory
- Configuration in `config/` subdirectory
- Pydantic schemas in `schemas/` for data validation

### Workflow Orchestration
- SEO: Hierarchical CrewAI workflow (sequential with collaboration)
- Newsletter: Linear pipeline with validation gates
- Articles: Extract-Analyze-Generate pattern

## Development Guidelines

### Agent Development
When creating or modifying agents:
1. Define clear **role, goal, and backstory** for CrewAI agents
2. Create **Pydantic schemas** for all structured data
3. Implement **retry logic** for API failures
4. Add **quality metrics** (relevance scores, performance targets)
5. Use **tools pattern** - each agent has dedicated tool functions decorated with `@tool`

### Content Generation
- Output format: **Markdown** for articles and site content
- Metadata: Generate schema.org structured data
- SEO: Maintain topical flow and internal linking consistency
- Validation: All content must pass Pydantic schema validation

### Integration with Blacksmith
- Workflows configured for Blacksmith runners (2x faster than GitHub Actions)
- Use Docker layer caching for dependencies
- Cache LLM responses where appropriate (24h for newsletter Exa calls)
- Monitor via Blacksmith dashboard for performance tracking

### Quality Standards
- Newsletter: Relevance >0.8, automated validation
- Articles: Uniqueness >90%, relevance >0.85, generation time <15min
- SEO: Natural keyword integration, coherent topical flow
- All outputs validated against Pydantic schemas before publication

## Key Technical Patterns

### CrewAI Agent Pattern
```python
from crewai import Agent, Task

agent = Agent(
    role='Role Name',
    goal='Specific objective',
    backstory='Context and expertise',
    tools=[tool1, tool2]  # Custom @tool decorated functions
)

task = Task(
    description='Task description',
    agent=agent,
    expected_output='Output format'
)
```

### PydanticAI Validation Pattern
All structured data uses Pydantic models for validation:
- Newsletter schemas in `schemas/newsletter_schema.py`
- Article schemas include ArticleAnalysis and GeneratedArticle
- Metadata schemas for SEO validation

### Exa AI Integration Pattern
```python
# Search for relevant content
results = exa.search(query, num_results=10, type="neural")

# Extract clean content
contents = exa.get_contents(ids, text=True)

# Filter by relevance score (>0.7 threshold)
filtered = [r for r in results if r.score > 0.7]
```

## Documentation References

For detailed information:
- Architecture overview: `docs/plan.md`
- Agent specifications: `AGENTS.md`
- Development phases: `docs/phases.md`
- Robot documentation: `docs/robots/README.md`
- Environment setup: `docs/ENVIRONMENT_SETUP.md`
- LLM configuration: `docs/LLM_PROVIDER_SETUP.md`


## Future Marketplace
Phase 6+ includes evaluation for publishing robots on [CrewAI Marketplace](https://marketplace.crewai.com/) for enterprise distribution and potential revenue.

## Context MCP — Token-Saving Protocol

This project uses a local codebase MCP server for efficient context management. Follow this order strictly:

### Every turn:
1. **Call `context_continue` FIRST** — before any Read, Grep, Glob, or file exploration. This returns files already in memory and avoids re-reading.
2. **If you need more files**, call `context_retrieve` with your query BEFORE using Grep/Glob. It ranks files by relevance.
3. **Use `context_read`** instead of the Read tool when exploring code. It excerpts only relevant portions and tracks your token budget (18K chars/turn).
4. **After editing files**, always call `context_register_edit` with a one-sentence summary.
5. **Store key decisions** with `context_decide` (e.g., "using Vue for interactive islands").

### Rules:
- Do NOT use Read/Grep/Glob for broad exploration before calling `context_continue`
- Do NOT re-read files that `context_continue` says are already in memory
- Prefer `context_read` over Read for all code exploration (Read is fine for files you need in full)
- Do NOT exceed the turn read budget — if `context_read` says budget exhausted, stop reading and work with what you have
- After edits, ALWAYS call `context_register_edit` — this invalidates stale cache
- For large files: call `list_symbols` first, then `context_read "file::symbol"` to read just the function you need
- Call `count_tokens(text)` before reading any file > 200 lines to decide if it's worth the budget
- When user says "done", "bye", or "wrap up" — call `session_wrap` to save context for next session
