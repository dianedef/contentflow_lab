# TASK: Workflow Visualization & Process Costing

> **Robot**: Dashboard (Chatbot Admin)
> **Inspiration**: [Puzzle App](https://www.puzzleapp.io)
> **Priority**: High

## Objective

Implement visual workflow representation and cost tracking for robot executions, providing transparency on agent pipelines and ROI justification for API costs.

---

## Implementation Checklist

### Phase 1: Cost Tracking Infrastructure

- [ ] **Cost Configuration**
  - [ ] Create `src/config/api_costs.py` with pricing per API
  - [ ] Define cost structure for each tool/service
  - [ ] Support for token-based and credit-based pricing

```python
# src/config/api_costs.py
from pydantic import BaseModel
from typing import Literal

class APICost(BaseModel):
    service: str
    unit: Literal["credit", "token", "request", "email"]
    cost_per_unit: float
    currency: str = "USD"

API_COSTS = {
    "firecrawl_scrape": APICost(service="Firecrawl", unit="credit", cost_per_unit=0.01),
    "firecrawl_crawl": APICost(service="Firecrawl", unit="credit", cost_per_unit=0.01),
    "firecrawl_search": APICost(service="Firecrawl", unit="credit", cost_per_unit=0.002),  # 2 credits/10 results
    "firecrawl_map": APICost(service="Firecrawl", unit="credit", cost_per_unit=0.005),
    "hexowatch_check": APICost(service="Hexowatch", unit="credit", cost_per_unit=0.01),
    "paced_email_send": APICost(service="Paced Email", unit="email", cost_per_unit=0.001),
    "exa_search": APICost(service="Exa AI", unit="request", cost_per_unit=0.02),
    "openai_gpt4": APICost(service="OpenAI", unit="token", cost_per_unit=0.00003),  # per 1K tokens
    "anthropic_claude": APICost(service="Anthropic", unit="token", cost_per_unit=0.000015),
}

def calculate_cost(service: str, units: int) -> float:
    """Calculate cost for a service usage."""
    if service not in API_COSTS:
        return 0.0
    return API_COSTS[service].cost_per_unit * units
```

- [ ] **Usage Tracker**
  - [ ] Create `src/tracking/usage_tracker.py`
  - [ ] Track API calls per robot execution
  - [ ] Aggregate costs per agent, per run, per day

```python
# src/tracking/usage_tracker.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import json
from pathlib import Path

class UsageEvent(BaseModel):
    timestamp: datetime
    robot_id: str
    run_id: str
    agent: str
    service: str
    units: int
    cost: float
    metadata: Optional[dict] = None

class UsageTracker:
    """Track API usage and costs for robot executions."""

    def __init__(self, storage_path: str = "data/usage"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.current_run: list[UsageEvent] = []

    def track(
        self,
        robot_id: str,
        run_id: str,
        agent: str,
        service: str,
        units: int
    ) -> UsageEvent:
        """Track a single API usage event."""
        from src.config.api_costs import calculate_cost

        event = UsageEvent(
            timestamp=datetime.now(),
            robot_id=robot_id,
            run_id=run_id,
            agent=agent,
            service=service,
            units=units,
            cost=calculate_cost(service, units)
        )
        self.current_run.append(event)
        self._persist(event)
        return event

    def get_run_summary(self, run_id: str) -> dict:
        """Get cost summary for a specific run."""
        events = [e for e in self.current_run if e.run_id == run_id]

        by_agent = {}
        by_service = {}
        total_cost = 0.0

        for event in events:
            by_agent[event.agent] = by_agent.get(event.agent, 0) + event.cost
            by_service[event.service] = by_service.get(event.service, 0) + event.cost
            total_cost += event.cost

        return {
            "run_id": run_id,
            "total_cost": round(total_cost, 4),
            "by_agent": by_agent,
            "by_service": by_service,
            "event_count": len(events)
        }

    def _persist(self, event: UsageEvent):
        """Save event to storage."""
        date_str = event.timestamp.strftime("%Y-%m-%d")
        file_path = self.storage_path / f"{date_str}.jsonl"
        with open(file_path, "a") as f:
            f.write(event.model_dump_json() + "\n")
```

- [ ] **Decorator for Auto-Tracking**
  - [ ] Create `@track_cost` decorator for tool functions
  - [ ] Automatic cost calculation on tool execution

```python
# src/tracking/decorators.py
from functools import wraps
from src.tracking.usage_tracker import UsageTracker

_tracker = UsageTracker()

def track_cost(service: str, units_fn=lambda *args, **kwargs: 1):
    """Decorator to automatically track API costs."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get context from current execution
            robot_id = kwargs.get("_robot_id", "unknown")
            run_id = kwargs.get("_run_id", "unknown")
            agent = kwargs.get("_agent", "unknown")

            # Execute function
            result = func(*args, **kwargs)

            # Calculate units and track
            units = units_fn(*args, **kwargs, result=result)
            _tracker.track(robot_id, run_id, agent, service, units)

            return result
        return wrapper
    return decorator

# Usage example:
# @track_cost("firecrawl_crawl", units_fn=lambda **kw: kw.get("max_pages", 10))
# def crawl_site_for_content(url: str, max_pages: int = 20) -> str:
#     ...
```

### Phase 2: Workflow State Management

- [ ] **Workflow Schema**
  - [ ] Define workflow step model
  - [ ] Track status transitions
  - [ ] Store execution history

```python
# src/workflows/models.py
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime

StepStatus = Literal["pending", "running", "completed", "failed", "skipped"]

class WorkflowStep(BaseModel):
    id: str
    agent: str
    description: str
    tools: list[str]
    status: StepStatus = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cost: float = 0.0
    output_preview: Optional[str] = None
    error: Optional[str] = None

class WorkflowExecution(BaseModel):
    id: str
    robot_id: str
    robot_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: StepStatus = "running"
    steps: list[WorkflowStep]
    total_cost: float = 0.0

    def get_current_step(self) -> Optional[WorkflowStep]:
        """Get the currently running step."""
        for step in self.steps:
            if step.status == "running":
                return step
        return None

    def get_progress(self) -> dict:
        """Get execution progress."""
        completed = sum(1 for s in self.steps if s.status == "completed")
        return {
            "completed": completed,
            "total": len(self.steps),
            "percentage": round(completed / len(self.steps) * 100)
        }
```

- [ ] **Workflow Definitions**
  - [ ] Define workflow templates for each robot
  - [ ] Map CrewAI agents to visual steps

```python
# src/workflows/definitions.py
from src.workflows.models import WorkflowStep

SEO_ROBOT_WORKFLOW = [
    WorkflowStep(
        id="research",
        agent="Research Analyst",
        description="Analyze competitors and market",
        tools=["exa_search", "firecrawl_crawl"]
    ),
    WorkflowStep(
        id="strategy",
        agent="Content Strategist",
        description="Identify content gaps and opportunities",
        tools=["firecrawl_map", "firecrawl_extract"]
    ),
    WorkflowStep(
        id="marketing",
        agent="Marketing Strategist",
        description="Prioritize by business impact",
        tools=[]
    ),
    WorkflowStep(
        id="writing",
        agent="Copywriter",
        description="Generate optimized content",
        tools=["openai_gpt4"]
    ),
    WorkflowStep(
        id="technical",
        agent="Technical SEO Specialist",
        description="Add schema markup and optimize",
        tools=["firecrawl_scrape"]
    ),
    WorkflowStep(
        id="editing",
        agent="Editor",
        description="Final review and formatting",
        tools=["anthropic_claude"]
    ),
]

NEWSLETTER_ROBOT_WORKFLOW = [
    WorkflowStep(
        id="collect",
        agent="Content Collector",
        description="Gather content from sources",
        tools=["exa_search", "firecrawl_scrape"]
    ),
    WorkflowStep(
        id="curate",
        agent="Content Curator",
        description="Filter and organize content",
        tools=["anthropic_claude"]
    ),
    WorkflowStep(
        id="generate",
        agent="Newsletter Writer",
        description="Generate newsletter content",
        tools=["openai_gpt4"]
    ),
    WorkflowStep(
        id="send",
        agent="Email Sender",
        description="Deliver to subscribers",
        tools=["paced_email_send"]
    ),
]

ARTICLE_GENERATOR_WORKFLOW = [
    WorkflowStep(
        id="map",
        agent="Site Mapper",
        description="Discover competitor URLs",
        tools=["firecrawl_map"]
    ),
    WorkflowStep(
        id="crawl",
        agent="Content Crawler",
        description="Extract competitor content",
        tools=["firecrawl_crawl"]
    ),
    WorkflowStep(
        id="analyze",
        agent="Content Researcher",
        description="Analyze structure and gaps",
        tools=["firecrawl_extract"]
    ),
    WorkflowStep(
        id="generate",
        agent="Article Writer",
        description="Generate original article",
        tools=["anthropic_claude"]
    ),
]

WORKFLOWS = {
    "seo-robot": SEO_ROBOT_WORKFLOW,
    "newsletter-robot": NEWSLETTER_ROBOT_WORKFLOW,
    "article-generator": ARTICLE_GENERATOR_WORKFLOW,
}
```

### Phase 3: Dashboard Components (React/Next.js)

- [ ] **WorkflowVisualizer Component**
  - [ ] Visual step-by-step representation
  - [ ] Real-time status updates
  - [ ] Cost display per step

```typescript
// chatbot/components/dashboard/workflow-visualizer.tsx
import { cn } from "@/lib/utils";

interface WorkflowStep {
  id: string;
  agent: string;
  description: string;
  tools: string[];
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  cost: number;
  duration?: number;
}

interface WorkflowVisualizerProps {
  robotName: string;
  steps: WorkflowStep[];
  showCosts?: boolean;
  orientation?: "horizontal" | "vertical";
}

const statusColors = {
  pending: "bg-gray-200 border-gray-300",
  running: "bg-yellow-100 border-yellow-400 animate-pulse",
  completed: "bg-green-100 border-green-400",
  failed: "bg-red-100 border-red-400",
  skipped: "bg-gray-100 border-gray-200 opacity-50",
};

const statusIcons = {
  pending: "⚪",
  running: "🟡",
  completed: "🟢",
  failed: "🔴",
  skipped: "⏭️",
};

export function WorkflowVisualizer({
  robotName,
  steps,
  showCosts = true,
  orientation = "horizontal",
}: WorkflowVisualizerProps) {
  const totalCost = steps.reduce((sum, step) => sum + step.cost, 0);
  const completedSteps = steps.filter((s) => s.status === "completed").length;
  const progress = Math.round((completedSteps / steps.length) * 100);

  return (
    <div className="p-4 bg-white rounded-lg border">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-lg">{robotName}</h3>
        <div className="flex gap-4 text-sm">
          <span className="text-gray-500">
            Progress: {completedSteps}/{steps.length} ({progress}%)
          </span>
          {showCosts && (
            <span className="font-mono text-green-600">
              ${totalCost.toFixed(4)}
            </span>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2 bg-gray-200 rounded-full mb-6">
        <div
          className="h-full bg-green-500 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Steps */}
      <div
        className={cn(
          "flex gap-2",
          orientation === "vertical" ? "flex-col" : "flex-row overflow-x-auto"
        )}
      >
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center gap-2">
            {/* Step Card */}
            <div
              className={cn(
                "p-3 rounded-lg border-2 min-w-[180px]",
                statusColors[step.status]
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                <span>{statusIcons[step.status]}</span>
                <span className="font-medium text-sm">{step.agent}</span>
              </div>
              <p className="text-xs text-gray-600 mb-2">{step.description}</p>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-400">
                  {step.tools.length > 0 ? step.tools[0] : "—"}
                </span>
                {showCosts && step.cost > 0 && (
                  <span className="font-mono text-green-600">
                    ${step.cost.toFixed(4)}
                  </span>
                )}
              </div>
            </div>

            {/* Connector Arrow */}
            {index < steps.length - 1 && orientation === "horizontal" && (
              <div className="text-gray-300 text-xl">→</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **CostSummary Component**
  - [ ] Breakdown by agent
  - [ ] Breakdown by service
  - [ ] Time saved estimation

```typescript
// chatbot/components/dashboard/cost-summary.tsx
interface CostBreakdown {
  totalCost: number;
  byAgent: Record<string, number>;
  byService: Record<string, number>;
  timeSavedMinutes: number;
}

interface CostSummaryProps {
  data: CostBreakdown;
  hourlyRate?: number; // For ROI calculation
}

export function CostSummary({ data, hourlyRate = 50 }: CostSummaryProps) {
  const timeSavedHours = data.timeSavedMinutes / 60;
  const moneySaved = timeSavedHours * hourlyRate;
  const roi = moneySaved / data.totalCost;

  return (
    <div className="p-4 bg-white rounded-lg border">
      <h3 className="font-semibold mb-4">Cost Analysis</h3>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="p-3 bg-blue-50 rounded-lg">
          <p className="text-xs text-gray-500">Total Cost</p>
          <p className="text-xl font-mono font-bold text-blue-600">
            ${data.totalCost.toFixed(2)}
          </p>
        </div>
        <div className="p-3 bg-green-50 rounded-lg">
          <p className="text-xs text-gray-500">Time Saved</p>
          <p className="text-xl font-bold text-green-600">
            {Math.round(data.timeSavedMinutes)} min
          </p>
        </div>
        <div className="p-3 bg-purple-50 rounded-lg">
          <p className="text-xs text-gray-500">ROI</p>
          <p className="text-xl font-bold text-purple-600">{roi.toFixed(0)}x</p>
        </div>
      </div>

      {/* Breakdown Tables */}
      <div className="grid grid-cols-2 gap-4">
        {/* By Agent */}
        <div>
          <h4 className="text-sm font-medium mb-2">By Agent</h4>
          <table className="w-full text-sm">
            <tbody>
              {Object.entries(data.byAgent).map(([agent, cost]) => (
                <tr key={agent} className="border-b">
                  <td className="py-1">{agent}</td>
                  <td className="py-1 text-right font-mono">
                    ${cost.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* By Service */}
        <div>
          <h4 className="text-sm font-medium mb-2">By Service</h4>
          <table className="w-full text-sm">
            <tbody>
              {Object.entries(data.byService).map(([service, cost]) => (
                <tr key={service} className="border-b">
                  <td className="py-1">{service}</td>
                  <td className="py-1 text-right font-mono">
                    ${cost.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **ROI Calculator Component**
  - [ ] Input: manual time estimate
  - [ ] Output: cost savings visualization

```typescript
// chatbot/components/dashboard/roi-calculator.tsx
"use client";

import { useState } from "react";

interface ROICalculatorProps {
  robotCost: number;
  defaultManualHours?: number;
}

export function ROICalculator({
  robotCost,
  defaultManualHours = 3,
}: ROICalculatorProps) {
  const [manualHours, setManualHours] = useState(defaultManualHours);
  const [hourlyRate, setHourlyRate] = useState(50);

  const manualCost = manualHours * hourlyRate;
  const savings = manualCost - robotCost;
  const savingsPercent = ((savings / manualCost) * 100).toFixed(0);

  return (
    <div className="p-4 bg-gradient-to-br from-green-50 to-blue-50 rounded-lg border">
      <h3 className="font-semibold mb-4">ROI Calculator</h3>

      {/* Inputs */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="text-xs text-gray-500">Manual time (hours)</label>
          <input
            type="number"
            value={manualHours}
            onChange={(e) => setManualHours(Number(e.target.value))}
            className="w-full p-2 border rounded"
            min={0.5}
            step={0.5}
          />
        </div>
        <div>
          <label className="text-xs text-gray-500">Hourly rate ($)</label>
          <input
            type="number"
            value={hourlyRate}
            onChange={(e) => setHourlyRate(Number(e.target.value))}
            className="w-full p-2 border rounded"
            min={10}
          />
        </div>
      </div>

      {/* Comparison */}
      <div className="flex items-center justify-between p-3 bg-white rounded-lg">
        <div className="text-center">
          <p className="text-xs text-gray-500">Manual</p>
          <p className="text-lg font-bold text-red-500">
            ${manualCost.toFixed(2)}
          </p>
        </div>
        <div className="text-2xl">→</div>
        <div className="text-center">
          <p className="text-xs text-gray-500">Robot</p>
          <p className="text-lg font-bold text-green-500">
            ${robotCost.toFixed(2)}
          </p>
        </div>
        <div className="text-center px-4 py-2 bg-green-100 rounded-lg">
          <p className="text-xs text-gray-500">Savings</p>
          <p className="text-lg font-bold text-green-600">{savingsPercent}%</p>
        </div>
      </div>
    </div>
  );
}
```

### Phase 4: API Endpoints

- [ ] **Workflow Status API**
  - [ ] GET `/api/workflows/:runId` - Get execution status
  - [ ] WebSocket for real-time updates
  - [ ] Cost aggregation endpoint

```typescript
// chatbot/app/api/workflows/[runId]/route.ts
import { NextRequest, NextResponse } from "next/server";

export async function GET(
  request: NextRequest,
  { params }: { params: { runId: string } }
) {
  const { runId } = params;

  // Fetch from your backend/database
  const execution = await getWorkflowExecution(runId);

  if (!execution) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  return NextResponse.json({
    id: execution.id,
    robotName: execution.robot_name,
    status: execution.status,
    progress: execution.get_progress(),
    steps: execution.steps,
    totalCost: execution.total_cost,
    startedAt: execution.started_at,
    completedAt: execution.completed_at,
  });
}
```

- [ ] **Cost Analytics API**
  - [ ] GET `/api/analytics/costs` - Daily/weekly/monthly costs
  - [ ] GET `/api/analytics/costs/by-robot` - Per robot breakdown

```typescript
// chatbot/app/api/analytics/costs/route.ts
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const period = searchParams.get("period") || "week"; // day, week, month
  const robotId = searchParams.get("robotId");

  const costs = await getCostAnalytics(period, robotId);

  return NextResponse.json({
    period,
    totalCost: costs.total,
    byDay: costs.byDay,
    byRobot: costs.byRobot,
    byService: costs.byService,
    trend: costs.trend, // +5% vs last period
  });
}
```

### Phase 5: Integration with Existing Robots

- [ ] **CrewAI Callback Integration**
  - [ ] Add callbacks to track agent execution
  - [ ] Emit events for workflow updates

```python
# src/tracking/crewai_callbacks.py
from crewai import Agent, Task, Crew
from src.tracking.usage_tracker import UsageTracker
from src.workflows.models import WorkflowExecution, WorkflowStep
from datetime import datetime
import uuid

class WorkflowTrackingCallback:
    """Callback to track CrewAI execution for visualization."""

    def __init__(self, robot_id: str, workflow_steps: list[WorkflowStep]):
        self.robot_id = robot_id
        self.run_id = str(uuid.uuid4())
        self.tracker = UsageTracker()
        self.execution = WorkflowExecution(
            id=self.run_id,
            robot_id=robot_id,
            robot_name=robot_id.replace("-", " ").title(),
            started_at=datetime.now(),
            steps=workflow_steps
        )

    def on_agent_start(self, agent: Agent):
        """Called when an agent starts execution."""
        for step in self.execution.steps:
            if step.agent.lower() == agent.role.lower():
                step.status = "running"
                step.started_at = datetime.now()
                self._emit_update()
                break

    def on_agent_end(self, agent: Agent, output: str):
        """Called when an agent completes execution."""
        for step in self.execution.steps:
            if step.agent.lower() == agent.role.lower():
                step.status = "completed"
                step.completed_at = datetime.now()
                step.output_preview = output[:200] if output else None

                # Get costs for this agent
                summary = self.tracker.get_run_summary(self.run_id)
                step.cost = summary["by_agent"].get(agent.role, 0)

                self._emit_update()
                break

    def on_agent_error(self, agent: Agent, error: str):
        """Called when an agent fails."""
        for step in self.execution.steps:
            if step.agent.lower() == agent.role.lower():
                step.status = "failed"
                step.completed_at = datetime.now()
                step.error = error
                self._emit_update()
                break

    def on_crew_complete(self):
        """Called when the entire crew completes."""
        self.execution.completed_at = datetime.now()
        self.execution.status = "completed"
        self.execution.total_cost = sum(s.cost for s in self.execution.steps)
        self._emit_update()

    def _emit_update(self):
        """Emit workflow update (WebSocket, file, etc.)."""
        # Store to file for API to read
        import json
        from pathlib import Path

        output_dir = Path("data/executions")
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / f"{self.run_id}.json", "w") as f:
            f.write(self.execution.model_dump_json(indent=2))
```

- [ ] **Update Robot Implementations**
  - [ ] Add tracking to SEO Robot
  - [ ] Add tracking to Newsletter Robot
  - [ ] Add tracking to Article Generator

```python
# Example: src/seo/workflows/seo_crew.py (updated)
from crewai import Crew
from src.tracking.crewai_callbacks import WorkflowTrackingCallback
from src.workflows.definitions import SEO_ROBOT_WORKFLOW

def run_seo_robot(target_url: str):
    """Run SEO Robot with workflow tracking."""

    # Initialize tracking
    callback = WorkflowTrackingCallback(
        robot_id="seo-robot",
        workflow_steps=SEO_ROBOT_WORKFLOW
    )

    # Create crew with callback
    crew = Crew(
        agents=[research_analyst, content_strategist, ...],
        tasks=[research_task, strategy_task, ...],
        callbacks=[callback]  # Add tracking
    )

    result = crew.kickoff()
    callback.on_crew_complete()

    return result, callback.execution
```

### Phase 6: Dashboard Integration

- [ ] **Add to Robot Card**
  - [ ] Show mini workflow progress
  - [ ] Display last run cost

- [ ] **Execution History Page**
  - [ ] List past executions
  - [ ] Filter by robot, date, cost
  - [ ] Export cost reports

- [ ] **Real-time Updates**
  - [ ] WebSocket connection for live updates
  - [ ] Toast notifications on completion

---

## Process Flow

```
1. Robot Execution Starts
   └── Create WorkflowExecution record
   └── Initialize cost tracking
   └── Emit "started" event

2. For Each Agent Step
   └── Update step status to "running"
   └── Track API calls via @track_cost decorator
   └── On completion, update step with cost
   └── Emit "step_updated" event

3. On Completion/Error
   └── Calculate total cost
   └── Store execution record
   └── Emit "completed" event
   └── Update dashboard via WebSocket

4. Dashboard Display
   └── Fetch execution status via API
   └── Render WorkflowVisualizer component
   └── Show CostSummary and ROI
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Cost tracking accuracy | > 99% |
| Dashboard update latency | < 500ms |
| User understands workflow | > 80% (survey) |
| ROI visibility | 100% of executions |

---

## Environment Variables

```bash
# .env (no new vars needed, uses existing API keys)
# Cost tracking uses configured API pricing
```

---

## Dependencies

- `pydantic` - Schema validation
- React components (existing Next.js setup)
- WebSocket library (optional, for real-time)
- Chart library (recharts/chart.js) for cost visualization

---

## Notes

- Start with file-based storage for executions, migrate to DB later
- Cost estimates are approximations, adjust based on actual invoices
- Consider caching cost summaries for dashboard performance
- Future: Add budget alerts when costs exceed threshold

---

## References

- Inspiration: [Puzzle App](https://www.puzzleapp.io)
- CrewAI Callbacks: [CrewAI Docs](https://docs.crewai.com)
- Firecrawl Pricing: [Firecrawl](https://firecrawl.dev/pricing)
