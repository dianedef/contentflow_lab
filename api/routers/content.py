"""Content validation endpoints — approve, reject, and list pending articles."""

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies.auth import CurrentUser, require_current_user
from api.dependencies.ownership import (
    require_owned_content_record,
    resolve_owned_project_ids,
)
from status.schemas import ContentLifecycleStatus
from status.service import get_status_service, ContentNotFoundError

router = APIRouter(prefix="/api/content", tags=["Content Validation"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _record_to_dict(r) -> dict:
    meta = r.metadata or {}
    return {
        "id": r.id,
        "title": r.title,
        "cluster": meta.get("cluster", ""),
        "project_id": r.project_id or "",
        "project_name": meta.get("project_name", ""),
        "content_path": r.content_path or "",
        "scheduled_pub_date": meta.get("scheduled_pub_date"),
        "tags": r.tags or [],
        "preview": (r.content_preview or "")[:300],
    }


# ─── Pending Validations ──────────────────────────────────────────────────────

@router.get(
    "/pending-validations",
    summary="Articles pending manual validation",
    description="""
    Returns articles with status `pending_review` that have a `scheduled_pub_date`
    within the next N days — i.e., articles the user should validate soon.

    If no `scheduled_pub_date` is set, the article is included regardless (it needs
    a date assigned first).
    """,
)
async def get_pending_validations(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    days_ahead: int = Query(7, ge=1, le=90, description="Days ahead to look"),
    current_user: CurrentUser = Depends(require_current_user),
):
    svc = get_status_service()
    owned_project_ids = await resolve_owned_project_ids(current_user, project_id)
    records = svc.list_content(
        status=ContentLifecycleStatus.PENDING_REVIEW,
        project_ids=owned_project_ids,
        limit=200,
    )

    cutoff = (date.today() + timedelta(days=days_ahead)).isoformat()
    today = date.today().isoformat()

    filtered = []
    for r in records:
        meta = r.metadata or {}
        pub_date = meta.get("scheduled_pub_date")

        # Include if: no pub_date yet (needs scheduling) OR pub_date is within window
        if pub_date is None or (today <= pub_date <= cutoff):
            filtered.append(r)

    # Sort by scheduled_pub_date asc (None last)
    filtered.sort(key=lambda r: (r.metadata or {}).get("scheduled_pub_date") or "9999")

    return {
        "total": len(filtered),
        "articles": [_record_to_dict(r) for r in filtered],
    }


# ─── Approve ─────────────────────────────────────────────────────────────────

@router.post(
    "/{content_id}/approve",
    summary="Approve an article for publishing",
    description="""
    Transitions the article from `pending_review` → `approved`.
    The Publishing Agent will pick it up and push it to the repo on schedule.
    """,
)
async def approve_content(
    content_id: str,
    current_user: CurrentUser = Depends(require_current_user),
):
    svc = get_status_service()
    await require_owned_content_record(content_id, current_user, svc)
    try:
        svc.transition(content_id, ContentLifecycleStatus.APPROVED, current_user.user_id)
        return {"success": True, "id": content_id, "status": "approved"}
    except ContentNotFoundError:
        raise HTTPException(status_code=404, detail="Article not found")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ─── Reject ──────────────────────────────────────────────────────────────────

@router.post(
    "/{content_id}/reject",
    summary="Reject an article",
    description="Transitions the article to `rejected`. It can be re-queued later.",
)
async def reject_content(
    content_id: str,
    reason: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_current_user),
):
    svc = get_status_service()
    await require_owned_content_record(content_id, current_user, svc)
    try:
        svc.transition(
            content_id,
            ContentLifecycleStatus.REJECTED,
            current_user.user_id,
            reason=reason,
        )
        return {"success": True, "id": content_id, "status": "rejected"}
    except ContentNotFoundError:
        raise HTTPException(status_code=404, detail="Article not found")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ─── Get article content ──────────────────────────────────────────────────────

@router.get(
    "/{content_id}",
    summary="Get article details and full content",
)
async def get_content(
    content_id: str,
    current_user: CurrentUser = Depends(require_current_user),
):
    svc = get_status_service()
    record = await require_owned_content_record(content_id, current_user, svc)

    result = _record_to_dict(record)

    # Try to read the actual file from disk
    if record.content_path and (record.metadata or {}).get("project_name"):
        from pathlib import Path
        from agents.seo.config.project_store import ProjectStore

        try:
            store = ProjectStore()
            # We don't have project_id in path lookup, use project_id from record
            if record.project_id:
                project = await store.get_by_id(record.project_id)
                if project and project.settings and project.settings.local_repo_path:
                    file_path = Path(project.settings.local_repo_path) / record.content_path
                    if file_path.exists():
                        result["full_content"] = file_path.read_text(encoding="utf-8")
        except Exception:
            pass

    return result
