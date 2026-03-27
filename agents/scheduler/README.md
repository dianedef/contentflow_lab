# 📅 Scheduling Robot - Intelligent Content Publishing & Analysis System

A multi-agent CrewAI system that automates content scheduling, publishing, and performs continuous technical analysis of your site's SEO and infrastructure health.

## 🎯 Overview

The Scheduling Robot consists of **4 specialized AI agents** working together to:

1. **Schedule content** at optimal times for maximum engagement
2. **Publish content** to production with Google integration
3. **Audit technical SEO** and site health continuously
4. **Analyze infrastructure** for vulnerabilities and optimization opportunities

### Key Features

- **Intelligent Scheduling**: ML-based optimal time prediction using historical data
- **Automated Publishing**: Git deployment + Google Search Console + Indexing API
- **SEO Monitoring**: Continuous crawling, schema validation, performance audits
- **Tech Health**: Dependency tracking, vulnerability scanning, cost monitoring
- **Self-Analysis**: The robot audits itself for technical debt and improvements

---

## 🤖 Agent Architecture

### 1. Calendar Manager Agent
**Role:** Content scheduling and queue management

**Capabilities:**
- Analyze publishing history to identify patterns
- Calculate optimal publishing times based on engagement data
- Manage content queue with priority-based scheduling
- Detect and resolve scheduling conflicts
- Generate visual calendar views

**Tools:** `CalendarAnalyzer`, `QueueManager`, `TimeOptimizer`

---

### 2. Publishing Agent
**Role:** Content deployment and platform integration

**Capabilities:**
- Deploy content via Git commit/push
- Update sitemap.xml automatically
- Submit URLs to Google Search Console
- Trigger Google Indexing API for instant indexing
- Monitor deployment health and rollback on failure
- Track deployment history and analytics

**Tools:** `GitDeployer`, `GoogleIntegration`, `DeploymentMonitor`

---

### 3. Site Health Monitor Agent
**Role:** Site-wide health monitoring and SEO auditing

**Capabilities:**
- Crawl site structure and analyze architecture (100+ pages)
- Monitor page speed and Core Web Vitals across all pages
- Audit internal linking graph site-wide
- Detect broken links and redirect chains
- Generate comprehensive health reports
- **Uses On-Page SEO tools** from the SEO Robot for individual page validation

**Tools:** `SiteCrawler`, `PerformanceAnalyzer`, `LinkAnalyzer`
**Shared Tools:** Imports `SchemaGenerator`, `MetadataValidator` from `agents.seo.tools.technical_tools`

**Note:** This agent demonstrates **tool sharing** - it reuses the SEO Robot's On-Page Technical SEO tools instead of duplicating them!

---

### 4. Tech Stack Analyzer Agent
**Role:** Infrastructure and dependency analysis

**Capabilities:**
- Analyze project dependencies (npm/pip)
- Scan for security vulnerabilities
- Monitor build performance and bundle sizes
- Track API costs and forecast monthly spend
- Detect outdated packages
- Generate tech health scorecards

**Tools:** `DependencyAnalyzer`, `VulnerabilityScanner`, `BuildAnalyzer`, `CostTracker`

---

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install crewai langchain-groq pydantic requests beautifulsoup4 networkx pyyaml

# Set environment variables
export GROQ_API_KEY="your_groq_api_key"
export GOOGLE_SEARCH_CONSOLE_CREDENTIALS="path/to/credentials.json"
export GOOGLE_INDEXING_API_KEY="your_api_key"
export GITHUB_TOKEN="your_github_token"
```

### Basic Usage

```python
from agents.scheduler.scheduler_crew import create_scheduler_crew

# Create scheduler crew
crew = create_scheduler_crew(
    llm_model="mixtral-8x7b-32768",
    base_url="https://yoursite.com",
    project_path="/path/to/project"
)

# Publish content workflow
result = crew.publish_content_workflow(
    content_path="src/content/blog/new-article.md",
    title="My New Article",
    content_type="article",
    priority=4  # High priority
)

# Weekly analysis workflow
report = crew.weekly_analysis_workflow(
    max_pages=100,
    include_build_analysis=True
)

# Quick health check
health = crew.quick_health_check()
print(f"Overall Status: {health['overall_status']}")
```

---

## 📊 Workflows

### Publishing Workflow
```
Content Created → Add to Queue → Calculate Optimal Time →
Schedule → Deploy to Git → Update Sitemap →
Submit to Google → Monitor Health → Log Analytics
```

### Weekly Analysis Workflow
```
Trigger → Crawl Site → Analyze SEO →
Analyze Tech Stack → Build Performance →
Generate Report → Identify Action Items → Notify Team
```

### Emergency Rollback Workflow
```
Detect Failure → Halt Deployment → Rollback Git →
Restore Previous Version → Notify → Generate Incident Report
```

---

## 🔧 Configuration

### Environment Variables

```bash
# LLM Configuration
SCHEDULER_LLM_MODEL=mixtral-8x7b-32768
GROQ_API_KEY=your_api_key

# Google APIs
GOOGLE_SEARCH_CONSOLE_CREDENTIALS=/path/to/credentials.json
GOOGLE_INDEXING_API_KEY=your_indexing_api_key

# GitHub (for deployment)
GITHUB_TOKEN=your_github_token
GITHUB_REPO=username/repo

# Site Configuration
SCHEDULER_BASE_URL=http://localhost:3000
SCHEDULER_PRODUCTION_URL=https://yoursite.com

# Audit Settings
SCHEDULER_AUDIT_FREQUENCY=weekly  # daily, weekly, monthly
SCHEDULER_AUTO_FIX=false  # Enable auto-fix for simple issues

# Publishing Settings
PUBLISH_AUTO_DEPLOY=true
PUBLISH_REQUIRE_APPROVAL=false
PUBLISH_TIMEZONE=America/New_York

# Notifications
SCHEDULER_NOTIFY_EMAIL=team@example.com
SCHEDULER_NOTIFY_ON_CRITICAL=true

# Performance Thresholds
SCHEDULER_PERF_PAGE_SPEED=90
SCHEDULER_PERF_SEO_SCORE=85
SCHEDULER_PERF_BUILD_TIME=120

# Cost Tracking
SCHEDULER_COST_WARNING=100.0  # USD/month
SCHEDULER_COST_CRITICAL=500.0  # USD/month
```

### Calendar Rules (calendar_rules.yaml)

```yaml
publishing_rules:
  - name: "Peak Weekday Hours"
    days: ["Monday", "Tuesday", "Wednesday", "Thursday"]
    times: ["09:00", "14:00", "18:00"]
    timezone: "America/New_York"

content_rules:
  - type: "newsletter"
    frequency: "weekly"
    preferred_day: "Friday"
    preferred_time: "09:00"

  - type: "article"
    frequency: "2x/week"
    minimum_spacing_hours: 72
```

---

## 📈 Metrics & Monitoring

### Publishing Metrics
- **Success Rate:** >99% deployment success
- **Time to Publish:** <2 hours from queue to live
- **Time to Index:** <24 hours average (Google)
- **Conflict Rate:** <5% scheduling conflicts

### SEO Metrics
- **Overall Score:** 0-100 (target: >90)
- **Page Speed:** Lighthouse score (target: >90)
- **Schema Coverage:** % of pages with structured data (target: >80%)
- **Internal Linking:** Orphan pages, average depth
- **Core Web Vitals:** LCP, FID, CLS ratings

### Tech Health Metrics
- **Overall Health:** 0-100 (deductions for vulns and outdated deps)
- **Vulnerabilities:** Critical/High/Medium/Low counts
- **Build Time:** Seconds (target: <120s)
- **Bundle Size:** MB (target: <10MB)
- **API Costs:** Monthly forecast (USD)

---

## 🎯 Example Use Cases

### 1. Schedule Newsletter
```python
crew.publish_content_workflow(
    content_path="newsletters/weekly-2026-01-17.md",
    title="Weekly Newsletter - January 17, 2026",
    content_type="newsletter",
    priority=5,  # Highest priority
    urls=["https://site.com/newsletter/2026-01-17"]
)
```

### 2. Run Daily SEO Audit
```python
# Quick health check (no full crawl)
health = crew.technical_seo.quick_health_check()

if health['overall_health'] != 'healthy':
    # Trigger full audit
    audit = crew.technical_seo.run_full_audit(max_pages=100)
    print(f"SEO Score: {audit['overall_score']}")
    print(f"Issues: {audit['critical_issues']} critical")
```

### 3. Check Security Vulnerabilities
```python
security = crew.tech_stack.quick_security_check()

if security['critical_vulnerabilities'] > 0:
    print(f"CRITICAL: {security['critical_vulnerabilities']} vulnerabilities found!")
    # Alert team
```

### 4. Track API Costs
```python
# Log API usage
crew.tech_stack.track_api_usage(
    api_name="OpenAI",
    requests=150,
    cost=2.50
)

# Get cost forecast
costs = crew.tech_stack.get_cost_forecast(days=30)
print(f"Forecasted monthly cost: ${costs['forecast_monthly_usd']:.2f}")
```

### 5. Get Calendar View
```python
calendar = crew.calendar_manager.get_calendar(days=14)

for date, events in calendar['calendar'].items():
    print(f"{date}: {len(events)} posts scheduled")
```

---

## 🧪 Testing

### Run Health Check
```bash
python -c "
from agents.scheduler.scheduler_crew import create_scheduler_crew
crew = create_scheduler_crew()
health = crew.quick_health_check()
print(health)
"
```

### Validate Configuration
```python
from agents.scheduler.config.scheduler_config import SchedulerConfig

validation = SchedulerConfig.validate_config()
if not validation['valid']:
    print("Configuration issues:", validation['issues'])
```

---

## 📁 Project Structure

```
agents/scheduler/
├── __init__.py
├── README.md                    # This file
├── scheduler_crew.py            # Main workflow orchestration
├── calendar_manager.py          # Agent 1: Scheduling
├── publishing_agent.py          # Agent 2: Publishing
├── site_health_monitor.py       # Agent 3: Site-wide health monitoring
├── tech_stack_analyzer.py       # Agent 4: Tech analysis
├── config/
│   ├── __init__.py
│   ├── calendar_rules.yaml      # Scheduling rules
│   └── scheduler_config.py      # Central configuration
├── schemas/
│   ├── __init__.py
│   ├── publishing_schemas.py    # Publishing data models
│   └── analysis_schemas.py      # Analysis data models
├── tools/
│   ├── __init__.py
│   ├── calendar_tools.py        # Calendar management tools
│   ├── publishing_tools.py      # Publishing tools
│   ├── seo_audit_tools.py       # SEO audit tools
│   └── tech_audit_tools.py      # Tech audit tools
└── validation/
    └── (validation utilities)
```

---

## 🔗 Integration Points

### Input Sources
- **SEO Robot** → Content queue (optimized articles)
- **Newsletter Agent** → Content queue (newsletters)
- **Article Generator** → Content queue (competitor analysis articles)
- **Manual Submissions** → Priority queue (urgent content)

### Output Destinations
- **GitHub** → Git commits and pushes
- **Google Search Console** → URL submissions
- **Google Indexing API** → Instant indexing requests
- **Astro Build** → Static site generation
- **Analytics Dashboard** → Performance metrics

---

## 🛠️ Maintenance

### Weekly Tasks
- Review analysis reports
- Address critical SEO/security issues
- Update outdated dependencies
- Optimize publishing schedule based on learnings

### Monthly Tasks
- Full technical audit (max pages)
- Build performance review
- API cost optimization
- Update calendar rules based on seasonal trends

### Quarterly Tasks
- Review and update thresholds
- A/B test publishing times
- Evaluate new integrations
- Update documentation

---

## 🚨 Troubleshooting

### Common Issues

**Publishing fails with Git error:**
- Check `GITHUB_TOKEN` is set correctly
- Verify repository permissions
- Ensure Git is configured: `git config --global user.email "you@example.com"`

**Google Indexing API not working:**
- Verify `GOOGLE_INDEXING_API_KEY` is set
- Check API quota limits
- Ensure service account has proper permissions

**SEO audit timeout:**
- Reduce `max_pages` parameter
- Check site is accessible
- Increase timeout in `seo_audit_tools.py`

**Dependency analysis fails:**
- Ensure `package.json` or `requirements.txt` exists
- Install `npm` or `pip` if missing
- Check file permissions

---

## 📚 Advanced Topics

### Custom Calendar Rules
Edit `config/calendar_rules.yaml` to customize:
- Publishing times and days
- Content-type specific rules
- Blackout dates
- Minimum spacing requirements

### Extending with New Agents
```python
from crewai import Agent
from agents.scheduler.scheduler_crew import SchedulerCrew

class CustomAgent:
    def __init__(self):
        self.agent = Agent(
            role="Custom Role",
            goal="Custom goal",
            tools=[...]
        )

# Add to crew
crew = SchedulerCrew()
crew.custom_agent = CustomAgent()
```

### Webhook Integrations
Trigger workflows via webhooks:
```python
from flask import Flask, request
app = Flask(__name__)

@app.route('/webhook/publish', methods=['POST'])
def webhook_publish():
    data = request.json
    crew.publish_content_workflow(**data)
    return {"status": "queued"}
```

---

## 🎓 Learn More

### 📚 Complete Documentation
All comprehensive documentation is now in **`/docs/robots/scheduler/`**:

- **[Architecture Specs](../../docs/robots/scheduler/architecture-specs.md)** - Complete technical specifications
- **[Final Architecture](../../docs/robots/scheduler/final-architecture.md)** - System architecture and design
- **[Implementation Summary](../../docs/robots/scheduler/implementation-summary.md)** - What was built and delivered
- **[Refactoring Decisions](../../docs/robots/scheduler/refactoring-decisions.md)** - Why agents were renamed
- **[Changelog](../../docs/robots/scheduler/changelog.md)** - Version history and migration guides

### 🔗 Related Docs
- **All Robots Overview:** `/docs/ROBOT_ARCHITECTURE_OVERVIEW.md`
- **Agent Specs (All Robots):** `/AGENTS.md`
- **Project Overview:** `/CLAUDE.md`

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional SEO audit checks
- More publishing platforms (Medium, Dev.to)
- Enhanced ML-based time optimization
- Real-time analytics dashboard
- Mobile app for monitoring

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

Built with:
- **CrewAI** - Multi-agent orchestration
- **Groq** - Fast LLM inference
- **Pydantic** - Data validation
- **Google APIs** - Search Console and Indexing
- **NetworkX** - Graph analysis for internal linking

---

**Version:** 1.0.0
**Last Updated:** 2026-01-17
**Maintained by:** Scheduler Robot Team
