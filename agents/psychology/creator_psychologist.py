"""Creator Psychologist — synthesizes creator entries into narrative updates.

This agent reads raw ritual entries, detects patterns and evolution,
and produces narrative updates that the creator reviews before merging.
"""

from crewai import Agent, Task, Crew
from agents.psychology.tools.narrative_tools import (
    read_narrative_context,
    analyze_entry_patterns,
    detect_chapter_transition,
    generate_narrative_update,
)


def _build_agent() -> Agent:
    return Agent(
        role="Creator Psychologist",
        goal=(
            "Synthesize the creator's raw entries into a coherent narrative update "
            "that captures voice evolution, positioning shifts, and chapter transitions."
        ),
        backstory=(
            "You are a brand psychologist who specializes in personal branding and "
            "creator identity. You read between the lines of a creator's reflections "
            "to detect shifts in voice, positioning, and narrative arc. You never "
            "fabricate — you surface what's already there."
        ),
        tools=[
            read_narrative_context,
            analyze_entry_patterns,
            detect_chapter_transition,
            generate_narrative_update,
        ],
        verbose=False,
    )


def run_narrative_synthesis(
    profile_id: str,
    entries: list[dict],
    current_voice: dict | None = None,
    current_positioning: dict | None = None,
    chapter_title: str | None = None,
) -> dict:
    """Run the Creator Psychologist crew to synthesize narrative from entries.

    Args:
        profile_id: Creator profile ID
        entries: List of creator entry dicts
        current_voice: Current voice profile dict
        current_positioning: Current positioning dict
        chapter_title: Current narrative chapter title

    Returns:
        Dict with voice_delta, positioning_delta, narrative_summary, chapter_transition
    """
    import json

    agent = _build_agent()

    entries_json = json.dumps(entries)
    voice_json = json.dumps(current_voice or {})
    positioning_json = json.dumps(current_positioning or {})

    synthesis_task = Task(
        description=(
            f"Analyze these creator entries and synthesize a narrative update.\n\n"
            f"Current voice profile: {voice_json}\n"
            f"Current positioning: {positioning_json}\n"
            f"Current chapter: {chapter_title or 'None'}\n\n"
            f"Entries to analyze:\n{entries_json}\n\n"
            f"Steps:\n"
            f"1. Use read_narrative_context to understand current state\n"
            f"2. Use analyze_entry_patterns to find themes and evolution\n"
            f"3. Use detect_chapter_transition to check for narrative shifts\n"
            f"4. Use generate_narrative_update to format the result\n\n"
            f"Return the final JSON from generate_narrative_update."
        ),
        agent=agent,
        expected_output="JSON object with voice_delta, positioning_delta, narrative_summary",
    )

    crew = Crew(
        agents=[agent],
        tasks=[synthesis_task],
        verbose=False,
    )

    result = crew.kickoff()
    raw = str(result)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "voice_delta": {},
            "positioning_delta": {},
            "narrative_summary": raw,
            "chapter_transition": False,
        }

    return parsed
