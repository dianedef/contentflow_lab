"""Tools for the Creator Psychologist agent — narrative analysis and synthesis"""

from crewai import tool


@tool("read_narrative_context")
def read_narrative_context(
    voice_profile: str,
    positioning: str,
    chapter_title: str,
) -> str:
    """Read the creator's current narrative context (voice, positioning, chapter).
    Returns a formatted summary for the agent to reason over.

    Args:
        voice_profile: JSON string of the creator's voice profile
        positioning: JSON string of the creator's positioning
        chapter_title: Title of the current narrative chapter
    """
    import json

    voice = json.loads(voice_profile) if voice_profile else {}
    pos = json.loads(positioning) if positioning else {}

    parts = [f"## Current Chapter: {chapter_title or 'Untitled'}"]

    if voice:
        parts.append(f"**Tone**: {voice.get('tone', 'not defined')}")
        if voice.get("vocabulary"):
            parts.append(f"**Key vocabulary**: {', '.join(voice['vocabulary'][:10])}")
        if voice.get("rhetoricalDevices"):
            parts.append(f"**Rhetorical devices**: {', '.join(voice['rhetoricalDevices'])}")

    if pos:
        parts.append(f"**Niche**: {pos.get('niche', 'not defined')}")
        parts.append(f"**Unique angle**: {pos.get('uniqueAngle', 'not defined')}")
        if pos.get("differentiators"):
            parts.append(f"**Differentiators**: {', '.join(pos['differentiators'])}")

    return "\n".join(parts)


@tool("analyze_entry_patterns")
def analyze_entry_patterns(entries_json: str) -> str:
    """Analyze a batch of creator entries to detect patterns in themes, emotions, and evolution.

    Args:
        entries_json: JSON array of creator entries with content and entryType fields
    """
    import json

    entries = json.loads(entries_json)

    type_counts: dict[str, int] = {}
    all_tags: list[str] = []

    for entry in entries:
        t = entry.get("entryType", "reflection")
        type_counts[t] = type_counts.get(t, 0) + 1
        all_tags.extend(entry.get("tags", []))

    tag_freq: dict[str, int] = {}
    for tag in all_tags:
        tag_freq[tag] = tag_freq.get(tag, 0) + 1
    top_tags = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:5]

    report = [
        f"## Entry Analysis ({len(entries)} entries)",
        f"**Type distribution**: {type_counts}",
        f"**Top themes**: {[t[0] for t in top_tags]}",
        "",
        "### Entry summaries:",
    ]

    for i, entry in enumerate(entries[:10], 1):
        content_preview = entry["content"][:200]
        report.append(f"{i}. [{entry.get('entryType', 'reflection')}] {content_preview}...")

    return "\n".join(report)


@tool("detect_chapter_transition")
def detect_chapter_transition(
    entries_json: str,
    current_chapter_title: str,
) -> str:
    """Analyze recent entries for signals that a narrative chapter transition is happening.
    Look for pivots, major wins, identity shifts, or new directions.

    Args:
        entries_json: JSON array of recent creator entries
        current_chapter_title: Title of the current chapter
    """
    import json

    entries = json.loads(entries_json)

    pivot_count = sum(1 for e in entries if e.get("entryType") == "pivot")
    has_pivots = pivot_count > 0

    pivot_content = [e["content"] for e in entries if e.get("entryType") == "pivot"]

    report = [
        f"## Chapter Transition Analysis",
        f"**Current chapter**: {current_chapter_title}",
        f"**Pivot entries**: {pivot_count} out of {len(entries)}",
        f"**Transition signal**: {'STRONG' if pivot_count >= 2 else 'MODERATE' if has_pivots else 'NONE'}",
    ]

    if pivot_content:
        report.append("\n### Pivot entry content:")
        for i, content in enumerate(pivot_content, 1):
            report.append(f"{i}. {content[:300]}...")

    return "\n".join(report)


@tool("generate_narrative_update")
def generate_narrative_update(
    voice_delta_json: str,
    positioning_delta_json: str,
    narrative_summary: str,
) -> str:
    """Format the synthesized narrative update for storage.

    Args:
        voice_delta_json: JSON of proposed voice changes
        positioning_delta_json: JSON of proposed positioning changes
        narrative_summary: Human-readable summary of what changed
    """
    import json

    voice_delta = json.loads(voice_delta_json) if voice_delta_json else {}
    positioning_delta = json.loads(positioning_delta_json) if positioning_delta_json else {}

    result = {
        "voice_delta": voice_delta,
        "positioning_delta": positioning_delta,
        "narrative_summary": narrative_summary,
    }

    return json.dumps(result, indent=2)
