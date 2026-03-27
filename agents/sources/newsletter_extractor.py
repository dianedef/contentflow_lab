"""Newsletter idea extraction — LLM-powered content analysis + persona/niche scoring.

Reads full newsletter text, extracts multiple actionable content ideas per email,
and scores them by relevance to the creator's niche and customer personas.

Uses utils/llm_simple.chat() directly (no CrewAI overhead).
"""

import json
import re
from typing import Optional


def _html_to_text(html: str) -> str:
    """Convert HTML to plain text, stripping tags and scripts."""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "head"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except ImportError:
        # Fallback: naive tag stripping
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", text).strip()


def _get_email_text(email) -> str:
    """Extract plain text from an EmailMessage, preferring .text over .html."""
    if email.text and email.text.strip():
        return email.text.strip()
    if email.html and email.html.strip():
        return _html_to_text(email.html)
    return ""


def format_persona_context(
    personas: list[dict],
    creator_profile: Optional[dict] = None,
) -> str:
    """Format persona + creator niche data into a compact LLM prompt section.

    Args:
        personas: List of CustomerPersona dicts from user_data_store.
        creator_profile: CreatorProfile dict with positioning/voice.

    Returns:
        Formatted text block, or empty string if no data.
    """
    parts = []

    # Creator niche / positioning
    if creator_profile:
        positioning = creator_profile.get("positioning") or {}
        if isinstance(positioning, str):
            try:
                positioning = json.loads(positioning)
            except (json.JSONDecodeError, TypeError):
                positioning = {}

        niche = positioning.get("niche", "")
        unique_angle = positioning.get("uniqueAngle", "")
        target_audience = positioning.get("targetAudience", "")

        if niche or unique_angle or target_audience:
            parts.append("## Creator Niche")
            if niche:
                parts.append(f"Niche: {niche}")
            if unique_angle:
                parts.append(f"Unique angle: {unique_angle}")
            if target_audience:
                parts.append(f"Target audience: {target_audience}")

    # Personas
    if personas:
        parts.append("\n## Customer Personas")
        for p in personas[:3]:  # max 3 personas to keep prompt short
            name = p.get("name", "Unknown")
            pain_points = p.get("painPoints") or []
            if isinstance(pain_points, str):
                try:
                    pain_points = json.loads(pain_points)
                except (json.JSONDecodeError, TypeError):
                    pain_points = []

            goals = p.get("goals") or []
            if isinstance(goals, str):
                try:
                    goals = json.loads(goals)
                except (json.JSONDecodeError, TypeError):
                    goals = []

            language = p.get("language") or {}
            if isinstance(language, str):
                try:
                    language = json.loads(language)
                except (json.JSONDecodeError, TypeError):
                    language = {}

            triggers = language.get("triggers", [])

            parts.append(f"\n**{name}**")
            if pain_points:
                parts.append(f"- Pain points: {', '.join(pain_points[:3])}")
            if goals:
                parts.append(f"- Goals: {', '.join(goals[:3])}")
            if triggers:
                parts.append(f"- Language triggers: {', '.join(triggers[:5])}")

    return "\n".join(parts)


SYSTEM_PROMPT = """You are a content strategist assistant. Your job is to extract concrete, actionable content ideas from newsletter emails.

For each newsletter, identify the most valuable topics, angles, trends, data points, or quotable insights that could be turned into original content.

If creator niche and persona context is provided, score each idea's relevance to that context. If no context is provided, score based on general content value (novelty, actionability, shareability).

Return ONLY valid JSON. No markdown fences, no explanation outside the JSON."""


def _build_user_prompt(
    emails: list,
    persona_context: str,
    max_ideas_per_email: int,
) -> str:
    """Build the user prompt with batched newsletter content + persona context."""
    parts = []

    if persona_context:
        parts.append(persona_context)

    parts.append("\n## Newsletters to Analyze\n")

    for i, email in enumerate(emails, 1):
        text = _get_email_text(email)
        # Truncate to ~2000 chars
        if len(text) > 2000:
            text = text[:2000] + "..."

        from_label = email.from_name or email.from_email or "Unknown"
        parts.append(f"### Newsletter {i}: \"{email.subject}\" (from {from_label})")
        parts.append(text if text else "(empty content)")
        parts.append("")

    parts.append(f"""## Instructions
For each newsletter, extract up to {max_ideas_per_email} content ideas. Each idea should be a concrete topic or angle that could become an article, video, newsletter, or social post.

For each idea, return:
- title: A working title for the content idea (max 120 chars)
- angle: The specific angle or hook (1-2 sentences)
- relevance_score: 0-100 score based on alignment with the creator's niche and personas' pain points/goals (or general content value if no context)
- source_newsletter: The subject line of the source newsletter
- tags: List of 2-4 relevant topic tags

Return JSON: {{"ideas": [...]}}""")

    return "\n".join(parts)


def _parse_llm_response(raw: str) -> list[dict]:
    """Parse JSON from LLM response, handling markdown fences."""
    raw = raw.strip()

    # Try direct parse
    try:
        data = json.loads(raw)
        return data.get("ideas", [])
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fences
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            return data.get("ideas", [])
        except json.JSONDecodeError:
            pass

    # Try finding JSON object in the response
    match = re.search(r"\{.*\"ideas\".*\}", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return data.get("ideas", [])
        except json.JSONDecodeError:
            pass

    return []


def extract_ideas_from_newsletters(
    emails: list,
    persona_context: str = "",
    max_ideas_per_email: int = 5,
    batch_size: int = 5,
) -> list[dict]:
    """Extract content ideas from newsletter emails using LLM.

    Args:
        emails: List of EmailMessage objects from imap_tools.
        persona_context: Formatted persona/niche context string.
        max_ideas_per_email: Max ideas to extract per email.
        batch_size: Number of emails per LLM call.

    Returns:
        List of idea dicts with title, angle, relevance_score, source_newsletter, tags.
    """
    from utils.llm_simple import chat, MODELS

    if not emails:
        return []

    all_ideas = []

    # Process in batches
    for i in range(0, len(emails), batch_size):
        batch = emails[i : i + batch_size]

        user_prompt = _build_user_prompt(batch, persona_context, max_ideas_per_email)

        try:
            response = chat(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                tier="fast",
                temperature=0.4,
                max_tokens=4096,
            )

            raw_text = response.choices[0].message.content or ""
            ideas = _parse_llm_response(raw_text)

            # Enrich each idea with source email metadata
            email_lookup = {e.subject: e for e in batch}
            for idea in ideas:
                source_subject = idea.get("source_newsletter", "")
                source_email_obj = email_lookup.get(source_subject)

                if source_email_obj:
                    idea["source_email"] = source_email_obj.from_email
                    idea["source_name"] = source_email_obj.from_name
                    idea["source_date"] = (
                        source_email_obj.date.isoformat()
                        if source_email_obj.date
                        else None
                    )
                    idea["source_uid"] = source_email_obj.uid

                # Clamp relevance_score to 0-100
                score = idea.get("relevance_score")
                if isinstance(score, (int, float)):
                    idea["relevance_score"] = max(0, min(100, score))

                all_ideas.append(idea)

            print(f"  Batch {i // batch_size + 1}: extracted {len(ideas)} ideas from {len(batch)} emails")

        except Exception as e:
            print(f"  ⚠ Batch {i // batch_size + 1} extraction failed: {e}")
            continue

    return all_ideas
