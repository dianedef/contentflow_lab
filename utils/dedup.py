"""Content deduplication utilities.

Checks for similar existing content before generation to avoid duplicates.
Uses SQL LIKE matching on title words — no ML required.
"""

from typing import Any, Optional


def check_content_duplicate(
    title: str,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> dict[str, Any] | None:
    """Check if content with a similar title already exists.

    Returns the first matching record as a dict, or None if no duplicate found.
    Only checks content in active statuses (approved, published, in_progress, etc.).
    """
    from status import get_status_service

    svc = get_status_service()
    active_statuses = [
        "approved", "scheduled", "publishing", "published",
        "in_progress", "generated", "pending_review",
    ]

    matches = svc.find_similar_content(
        title=title,
        user_id=user_id,
        project_id=project_id,
        statuses=active_statuses,
    )

    if matches:
        m = matches[0]
        return {
            "id": m.id,
            "title": m.title,
            "status": m.status,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
    return None
