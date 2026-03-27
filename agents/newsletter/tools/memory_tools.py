"""
Memory Tools - CrewAI @tool functions for accessing the project brain.

Provides newsletter agents with access to persistent memory for:
- Recalling past newsletters (deduplication)
- Loading brand voice guidelines
- Searching project context

All tools use lazy imports with graceful degradation — if Mem0 isn't
installed, they return "Memory unavailable" instead of crashing.
"""

from crewai.tools import tool

# Lazy import flag — checked on first tool call
_memory_checked = False
_memory_service = None


def _get_memory():
    """Lazy-load memory service with graceful fallback."""
    global _memory_checked, _memory_service
    if not _memory_checked:
        _memory_checked = True
        try:
            from memory import get_memory_service
            _memory_service = get_memory_service()
        except (ImportError, Exception) as e:
            print(f"Memory tools: Memory unavailable ({e})")
            _memory_service = None
    return _memory_service


@tool
def recall_project_context(query: str) -> str:
    """Search the project brain for relevant context about a topic.

    Use this to recall what you know about a specific topic, past decisions,
    content strategy, or any project knowledge before starting work.

    Args:
        query: Natural language search query (e.g. "AI agent trends",
               "content strategy for newsletters")

    Returns:
        Relevant project memories formatted as context, or a message
        if memory is unavailable.
    """
    memory = _get_memory()
    if memory is None:
        return "Memory unavailable — proceeding without project context."

    try:
        context = memory.load_context(query, limit=10)
        if not context:
            return f"No memories found for: {query}"
        return context
    except Exception as e:
        return f"Memory search failed: {e}"


@tool
def recall_past_newsletters(limit: int = 10) -> str:
    """Recall past newsletter topics to avoid duplication.

    Use this before planning newsletter content to see what topics
    were already covered in previous newsletters.

    Args:
        limit: Maximum number of past newsletters to recall (default 10)

    Returns:
        Summary of past newsletter topics and dates, or a message
        if memory is unavailable.
    """
    memory = _get_memory()
    if memory is None:
        return "Memory unavailable — no past newsletter history accessible."

    try:
        entries = memory.search(
            "past newsletter generation topics covered",
            limit=limit,
            agent_id="newsletter",
        )
        if not entries:
            return "No past newsletters found in memory — this may be the first run."

        lines = [f"=== Past Newsletters ({len(entries)} found) ==="]
        for i, entry in enumerate(entries, 1):
            lines.append(f"\n[{i}] {entry.memory}")
        lines.append("\n=== End Past Newsletters ===")
        return "\n".join(lines)
    except Exception as e:
        return f"Memory search failed: {e}"


@tool
def recall_brand_voice() -> str:
    """Recall brand voice guidelines and writing style from memory.

    Use this before writing content to ensure consistent tone, style,
    and terminology across all newsletters.

    Returns:
        Brand voice guidelines and style notes, or a message
        if memory is unavailable.
    """
    memory = _get_memory()
    if memory is None:
        return "Memory unavailable — using default writing style."

    try:
        context = memory.load_context(
            "brand voice writing style tone guidelines",
            limit=10,
        )
        if not context:
            return "No brand voice guidelines found in memory — using default style."
        return context
    except Exception as e:
        return f"Memory search failed: {e}"
