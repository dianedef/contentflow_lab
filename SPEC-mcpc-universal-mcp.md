# TASK: mcpc - Universal MCP Client Integration

> **Robot**: All robots (SEO, Newsletter, Article Generator, Scheduling)
> **Tools**: mcpc CLI + multiple MCP servers (Apify, Composio, Exa, custom)
> **Priority**: Medium

## Objective

Use mcpc as a **centralized configuration hub** for all MCP servers, enabling CrewAI agents to access multiple services (web scraping, app integrations, search) through a single interface.

---

## Why mcpc?

| Problem | mcpc Solution |
|---------|---------------|
| Multiple API keys scattered | Centralized OAuth/credentials in OS keychain |
| Different SDKs per service | One CLI for all MCP servers |
| Hardcoded tool configs | Dynamic tool discovery at runtime |
| Agent credential exposure | Proxy sandboxing for security |

---

## Implementation Checklist

### Phase 1: Installation & Setup

- [ ] **Install mcpc**
  ```bash
  npm install -g @apify/mcpc

  # Linux: install libsecret for credential storage
  sudo apt-get install libsecret-1-0
  ```

- [ ] **Verify Installation**
  ```bash
  mcpc --version
  mcpc --help
  ```

- [ ] **Create Base Config Directory**
  ```bash
  mkdir -p ~/.config/mcpc
  ```

### Phase 2: MCP Server Connections

- [ ] **Apify (Web Scraping)**
  ```bash
  # Authenticate
  mcpc mcp.apify.com login

  # Create persistent session
  mcpc mcp.apify.com connect @apify

  # Test
  mcpc @apify tools-list
  ```

- [ ] **Composio (App Integrations)**
  ```bash
  # Authenticate
  mcpc mcp.composio.dev login

  # Create session
  mcpc mcp.composio.dev connect @composio

  # Test - list available integrations
  mcpc @composio tools-list
  ```

- [ ] **Exa (Search)** *(if MCP server available)*
  ```bash
  mcpc mcp.exa.ai connect @exa
  mcpc @exa tools-list
  ```

- [ ] **Document Active Sessions**
  ```bash
  # List all configured sessions
  mcpc
  ```

### Phase 3: CrewAI Tool Integration

- [ ] **Create Universal MCP Tool Wrapper**

```python
# src/tools/mcp_client.py
import subprocess
import json
from typing import Any
from dataclasses import dataclass

@dataclass
class MCPResult:
    success: bool
    data: Any
    error: str | None = None

class MCPClient:
    """Universal MCP client wrapper using mcpc CLI."""

    def __init__(self):
        self._verify_mcpc()

    def _verify_mcpc(self):
        """Check mcpc is installed."""
        result = subprocess.run(["mcpc", "--version"], capture_output=True)
        if result.returncode != 0:
            raise RuntimeError("mcpc not installed. Run: npm install -g @apify/mcpc")

    def list_tools(self, session: str) -> list[dict]:
        """List available tools for a session."""
        result = subprocess.run(
            ["mcpc", session, "tools-list", "--json"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return json.loads(result.stdout).get("tools", [])
        return []

    def call_tool(
        self,
        session: str,
        tool_name: str,
        **kwargs
    ) -> MCPResult:
        """Call a tool on an MCP session."""
        cmd = ["mcpc", session, "tools-call", tool_name, "--json"]

        # Add arguments
        for key, value in kwargs.items():
            if isinstance(value, (dict, list)):
                cmd.append(f"{key}:={json.dumps(value)}")
            else:
                cmd.append(f"{key}:={value}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return MCPResult(
                success=True,
                data=json.loads(result.stdout) if result.stdout else None
            )
        else:
            return MCPResult(
                success=False,
                data=None,
                error=result.stderr
            )

    def call_apify(self, tool: str, **kwargs) -> MCPResult:
        """Shortcut for Apify session."""
        return self.call_tool("@apify", tool, **kwargs)

    def call_composio(self, tool: str, **kwargs) -> MCPResult:
        """Shortcut for Composio session."""
        return self.call_tool("@composio", tool, **kwargs)
```

- [ ] **Create CrewAI Tools**

```python
# src/tools/mcp_tools.py
from crewai import tool
from src.tools.mcp_client import MCPClient

mcp = MCPClient()

# === APIFY TOOLS (Web Scraping) ===

@tool
def scrape_website(url: str) -> str:
    """Scrape a website using Apify web scraper."""
    result = mcp.call_apify(
        "run-actor",
        actor="apify/web-scraper",
        input={"startUrls": [{"url": url}]}
    )
    return json.dumps(result.data) if result.success else f"Error: {result.error}"

@tool
def search_apify_actors(keywords: str) -> str:
    """Search for specialized Apify actors."""
    result = mcp.call_apify("search-actors", keywords=keywords)
    return json.dumps(result.data) if result.success else f"Error: {result.error}"

# === COMPOSIO TOOLS (App Integrations) ===

@tool
def post_to_slack(channel: str, message: str) -> str:
    """Post a message to Slack via Composio."""
    result = mcp.call_composio(
        "slack_send_message",
        channel=channel,
        text=message
    )
    return "Posted successfully" if result.success else f"Error: {result.error}"

@tool
def create_notion_page(title: str, content: str) -> str:
    """Create a page in Notion via Composio."""
    result = mcp.call_composio(
        "notion_create_page",
        title=title,
        content=content
    )
    return json.dumps(result.data) if result.success else f"Error: {result.error}"

@tool
def add_to_google_sheets(spreadsheet_id: str, data: list) -> str:
    """Append data to Google Sheets via Composio."""
    result = mcp.call_composio(
        "sheets_append_row",
        spreadsheet_id=spreadsheet_id,
        values=data
    )
    return "Added successfully" if result.success else f"Error: {result.error}"
```

### Phase 4: Agent Integration

- [ ] **Add MCP Tools to Agents**

```python
# src/seo/agents/seo_crew.py (example)
from crewai import Agent
from src.tools.mcp_tools import scrape_website, search_apify_actors

research_analyst = Agent(
    role="Research Analyst",
    goal="Analyze competitor websites and market trends",
    tools=[
        scrape_website,        # Via Apify MCP
        search_apify_actors,   # Find specialized scrapers
        # ... existing tools
    ]
)
```

```python
# src/newsletter/agents/newsletter_agent.py (example)
from src.tools.mcp_tools import post_to_slack, create_notion_page

# After newsletter generation, notify team
post_to_slack("#newsletter", "New newsletter generated!")
create_notion_page("Newsletter Archive", newsletter_content)
```

### Phase 5: Session Management

- [ ] **Create Session Health Check Script**

```bash
#!/bin/bash
# scripts/check_mcp_sessions.sh

echo "=== MCP Session Status ==="
mcpc

echo ""
echo "=== Testing Sessions ==="

for session in "@apify" "@composio"; do
    echo -n "$session: "
    if mcpc $session tools-list --json > /dev/null 2>&1; then
        echo "✓ OK"
    else
        echo "✗ FAILED - reconnecting..."
        # Extract server from session name and reconnect
        mcpc $session reconnect
    fi
done
```

- [ ] **Add to Startup/Cron**
  ```bash
  # Check sessions on robot startup
  ./scripts/check_mcp_sessions.sh
  ```

### Phase 6: Proxy for Security (Optional)

- [ ] **Setup MCP Proxy for Agent Sandboxing**

```bash
# Start proxy (agents can't see credentials)
mcpc mcp.apify.com connect @apify-proxy --proxy 8080 --proxy-bearer-token $PROXY_SECRET

# Agents connect to localhost instead
mcpc localhost:8080 tools-list
```

---

## MCP Services to Configure

| Session | Server | Use Case |
|---------|--------|----------|
| `@apify` | mcp.apify.com | Web scraping, data extraction |
| `@composio` | mcp.composio.dev | App integrations (Slack, Notion, Sheets, GitHub) |
| `@exa` | (if available) | Web search |
| `@browserbase` | (if needed) | Browser automation |

---

## Process Flow

```
CrewAI Agent needs external action
          │
          ▼
    ┌─────────────┐
    │ MCP Tool    │  (e.g., scrape_website)
    └─────────────┘
          │
          ▼
    ┌─────────────┐
    │ MCPClient   │  Python wrapper
    └─────────────┘
          │
          ▼
    ┌─────────────┐
    │ mcpc CLI    │  subprocess call
    └─────────────┘
          │
          ▼
    ┌─────────────┐
    │ @session    │  Persistent connection
    └─────────────┘
          │
          ▼
    ┌─────────────┐
    │ MCP Server  │  Apify/Composio/etc
    └─────────────┘
```

---

## Available Integrations via Composio

Once `@composio` is configured, agents can access:

| Category | Tools |
|----------|-------|
| **Communication** | Slack, Discord, Email, Telegram |
| **Productivity** | Notion, Google Docs, Sheets, Calendar |
| **Development** | GitHub, GitLab, Jira, Linear |
| **CRM** | HubSpot, Salesforce |
| **Storage** | Google Drive, Dropbox |
| **Social** | Twitter/X, LinkedIn |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Sessions configured | 3+ (Apify, Composio, +1) |
| Session uptime | > 99% |
| Tool call latency | < 5s |
| Credential exposure | Zero (via proxy) |

---

## Environment Variables

```bash
# .env (optional - mcpc uses OS keychain)
MCP_PROXY_SECRET=your_proxy_bearer_token

# Sessions are stored by mcpc in OS keychain
# No API keys needed in .env!
```

---

## Dependencies

```bash
# System
npm install -g @apify/mcpc
sudo apt-get install libsecret-1-0  # Linux only

# Python (already have)
# No additional deps - uses subprocess
```

---

## Notes

- **Sessions persist** - mcpc maintains connections via bridge process
- **Auto-reconnect** - crashed sessions restart automatically
- **One-time auth** - OAuth tokens stored in OS keychain, no repeated logins
- **Dynamic discovery** - `tools-list` shows available tools without hardcoding
- **JSON mode** - `--json` flag for scripting/parsing
