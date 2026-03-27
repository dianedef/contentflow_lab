"""Angle Strategist — generates content angles by crossing creator narrative with customer pain.

This is The Bridge — the core value proposition of the Psychology Engine.
It takes creator identity (voice, positioning, narrative) and customer
persona (pain points, goals, language) and produces strategic content angles.

This agent uses no tools — it reasons purely over the provided context.
"""

from crewai import Agent, Task, Crew


def _build_agent() -> Agent:
    return Agent(
        role="Content Angle Strategist",
        goal=(
            "Generate compelling content angles that authentically connect the "
            "creator's narrative with the customer's pain points. Each angle "
            "should feel personal, strategic, and impossible to replicate."
        ),
        backstory=(
            "You are a content strategist who specializes in personal brand "
            "content. Your superpower is finding the intersection between what "
            "a creator has lived and what their audience needs to hear. You "
            "generate angles that are both authentic (grounded in real creator "
            "experience) and strategic (addressing specific customer pain). "
            "You never suggest generic topics — every angle has a unique spin "
            "that only THIS creator could write."
        ),
        tools=[],
        verbose=False,
    )


def run_angle_generation(
    creator_voice: dict,
    creator_positioning: dict,
    narrative_summary: str | None,
    persona_data: dict,
    content_type: str | None = None,
    count: int = 5,
    seo_signals: list[dict] | None = None,
    trending_signals: list[dict] | None = None,
) -> dict:
    """Run the Angle Strategist to generate content angles.

    Args:
        creator_voice: Creator's voice profile dict
        creator_positioning: Creator's positioning dict
        narrative_summary: Current narrative summary text
        persona_data: Customer persona dict
        content_type: Optional content type filter
        count: Number of angles to generate
        seo_signals: Optional SEO keyword data (volume, difficulty, intent)
        trending_signals: Optional trending topics from research

    Returns:
        Dict with angles list and strategy_note
    """
    import json

    agent = _build_agent()

    content_type_instruction = (
        f"Focus on {content_type} format." if content_type else "Suggest the best format for each angle (article, newsletter, short, social_post)."
    )

    # Build SEO/trending context sections
    seo_section = ""
    if seo_signals:
        seo_section = (
            f"\n## SEO Opportunities\n"
            f"The following keywords have search demand. Use them to inform angle selection, "
            f"especially for article and blog content:\n"
            f"{json.dumps(seo_signals, indent=2)}\n"
        )

    trending_section = ""
    if trending_signals:
        trending_section = (
            f"\n## Trending Signals\n"
            f"These topics are currently trending. Prefer timely angles when relevant, "
            f"especially for short and social_post formats:\n"
            f"{json.dumps(trending_signals, indent=2)}\n"
        )

    scoring_instruction = ""
    if seo_signals or trending_signals:
        scoring_instruction = (
            "\nFor each angle, also provide:\n"
            "8. priority_score: 0-100 computed priority (factor in SEO volume, trending velocity, and confidence)\n"
            "9. seo_keyword: the primary SEO keyword this angle targets (if applicable, null otherwise)\n"
        )

    generation_task = Task(
        description=(
            f"Generate {count} content angles by crossing creator identity with customer persona.\n\n"
            f"## Creator Identity\n"
            f"**Voice**: {json.dumps(creator_voice)}\n"
            f"**Positioning**: {json.dumps(creator_positioning)}\n"
            f"**Current narrative**: {narrative_summary or 'Not available'}\n\n"
            f"## Target Persona\n"
            f"**Name**: {persona_data.get('name', 'Unknown')}\n"
            f"**Pain points**: {json.dumps(persona_data.get('painPoints', []))}\n"
            f"**Goals**: {json.dumps(persona_data.get('goals', []))}\n"
            f"**Language triggers**: {json.dumps(persona_data.get('language', {}).get('triggers', []))}\n"
            f"**Content preferences**: {json.dumps(persona_data.get('contentPreferences', {}))}\n"
            f"{seo_section}"
            f"{trending_section}"
            f"\n## Instructions\n"
            f"{content_type_instruction}\n\n"
            f"For each angle, provide:\n"
            f"1. title: Working title\n"
            f"2. hook: Opening hook/headline\n"
            f"3. angle: The strategic angle (how creator narrative meets customer pain)\n"
            f"4. content_type: article, newsletter, short, or social_post\n"
            f"5. narrative_thread: Which creator story this draws from\n"
            f"6. pain_point_addressed: Which customer pain this solves\n"
            f"7. confidence: 0-100 confidence score\n"
            f"{scoring_instruction}\n"
            f"Return a JSON object with:\n"
            f"- angles: array of angle objects\n"
            f"- strategy_note: high-level rationale for the set of angles"
        ),
        agent=agent,
        expected_output="JSON with angles array and strategy_note",
    )

    crew = Crew(
        agents=[agent],
        tasks=[generation_task],
        verbose=False,
    )

    result = crew.kickoff()
    raw = str(result)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "angles": [],
            "strategy_note": raw,
        }

    return parsed
