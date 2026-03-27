"""Audience Analyst — refines customer personas using behavioral data and analytics.

This agent takes existing persona definitions and enriches them with
analytics data, content performance correlations, and gap analysis.
"""

from crewai import Agent, Task, Crew
from agents.psychology.tools.persona_tools import (
    read_persona_profile,
    analyze_persona_gaps,
    merge_behavioral_data,
    update_persona_confidence,
)
from agents.psychology.tools.analytics_tools import (
    correlate_content_performance,
)


def _build_agent() -> Agent:
    return Agent(
        role="Audience Analyst",
        goal=(
            "Refine customer personas using behavioral data, analytics, and content "
            "performance to increase persona accuracy and confidence."
        ),
        backstory=(
            "You are a customer research specialist who builds detailed audience "
            "segment models. You combine qualitative persona definitions with "
            "quantitative behavioral data. You identify gaps, suggest enrichments, "
            "and update confidence scores based on evidence."
        ),
        tools=[
            read_persona_profile,
            analyze_persona_gaps,
            merge_behavioral_data,
            update_persona_confidence,
            correlate_content_performance,
        ],
        verbose=False,
    )


def run_persona_refinement(
    persona: dict,
    analytics_data: dict | None = None,
    content_performance: list[dict] | None = None,
) -> dict:
    """Run the Audience Analyst crew to refine a persona.

    Args:
        persona: Current persona dict
        analytics_data: Optional analytics data dict
        content_performance: Optional list of content performance records

    Returns:
        Dict with updated persona fields and new confidence score
    """
    import json

    agent = _build_agent()

    persona_json = json.dumps(persona)
    analytics_json = json.dumps(analytics_data or {})
    content_json = json.dumps(content_performance or [])

    refinement_task = Task(
        description=(
            f"Refine this customer persona using available data.\n\n"
            f"Current persona: {persona_json}\n\n"
            f"Analytics data: {analytics_json}\n\n"
            f"Content performance: {content_json}\n\n"
            f"Steps:\n"
            f"1. Use read_persona_profile to understand current state\n"
            f"2. Use analyze_persona_gaps to find missing data\n"
            f"3. If analytics data is available, use merge_behavioral_data\n"
            f"4. If content performance data is available, use correlate_content_performance\n"
            f"5. Use update_persona_confidence to recalculate confidence\n\n"
            f"Return a JSON object with:\n"
            f"- suggested_updates: dict of fields to update\n"
            f"- new_confidence: number 0-100\n"
            f"- gaps: list of remaining gaps\n"
            f"- insights: list of key findings"
        ),
        agent=agent,
        expected_output="JSON with suggested_updates, new_confidence, gaps, insights",
    )

    crew = Crew(
        agents=[agent],
        tasks=[refinement_task],
        verbose=False,
    )

    result = crew.kickoff()
    raw = str(result)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "suggested_updates": {},
            "new_confidence": persona.get("confidence", 50),
            "gaps": [],
            "insights": [raw],
        }

    return parsed
