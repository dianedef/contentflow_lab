"""Content status management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List

from api.dependencies.auth import CurrentUser, require_current_user
from api.dependencies.ownership import (
    require_owned_content_record,
    require_owned_project_id,
    resolve_owned_project_ids,
)
from api.models.status import (
    CreateContentRequest,
    UpdateContentRequest,
    TransitionRequest,
    ContentResponse,
    StatusChangeResponse,
    StatsResponse,
    ContentListResponse,
    WorkDomainResponse,
    UpdateDomainRequest,
    SaveContentBodyRequest,
    ContentBodyResponse,
    ContentEditResponse,
    RegenerateRequest,
    ScheduleContentRequest,
)
from agents.seo.config.project_store import project_store
from status.service import (
    get_status_service,
    InvalidTransitionError,
    ContentNotFoundError,
)

router = APIRouter(prefix="/api/status", tags=["Status"])


def _record_to_response(record) -> ContentResponse:
    """Convert a ContentRecord to a ContentResponse."""
    return ContentResponse(
        id=record.id,
        title=record.title,
        content_type=record.content_type,
        source_robot=record.source_robot,
        status=record.status,
        project_id=record.project_id,
        content_path=record.content_path,
        content_preview=record.content_preview,
        content_hash=record.content_hash,
        priority=record.priority,
        tags=record.tags,
        metadata=record.metadata,
        target_url=record.target_url,
        reviewer_note=record.reviewer_note,
        reviewed_by=record.reviewed_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
        scheduled_for=record.scheduled_for,
        published_at=record.published_at,
        synced_at=record.synced_at,
    )


# ─── Content CRUD ─────────────────────────────────────


@router.get(
    "/content",
    response_model=ContentListResponse,
    summary="List content records",
    description="List content records with optional filters by status, type, robot, and project",
)
async def list_content(
    status: Optional[str] = Query(None, description="Filter by status"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    source_robot: Optional[str] = Query(None, description="Filter by source robot"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: CurrentUser = Depends(require_current_user),
):
    """List content records with filters."""
    svc = get_status_service()
    owned_project_ids = await resolve_owned_project_ids(current_user, project_id)
    items = svc.list_content(
        status=status,
        content_type=content_type,
        source_robot=source_robot,
        project_ids=owned_project_ids,
        limit=limit,
        offset=offset,
    )
    return ContentListResponse(
        items=[_record_to_response(r) for r in items],
        total=len(items),
    )


@router.post(
    "/content",
    response_model=ContentResponse,
    status_code=201,
    summary="Create content record",
    description="Create a new content record to track through the lifecycle",
)
async def create_content(
    request: CreateContentRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Create a new content record."""
    if not request.project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    await require_owned_project_id(request.project_id, current_user)
    svc = get_status_service()
    try:
        record = svc.create_content(
            title=request.title,
            content_type=request.content_type,
            source_robot=request.source_robot,
            status=request.status,
            project_id=request.project_id,
            content_path=request.content_path,
            content_preview=request.content_preview,
            priority=request.priority,
            tags=request.tags,
            metadata=request.metadata,
            target_url=request.target_url,
        )
        return _record_to_response(record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/content/{content_id}",
    response_model=ContentResponse,
    summary="Get content record",
    description="Get a single content record by ID",
)
async def get_content(
    content_id: str,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Get a content record by ID."""
    svc = get_status_service()
    record = await require_owned_content_record(content_id, current_user, svc)
    return _record_to_response(record)


@router.patch(
    "/content/{content_id}",
    response_model=ContentResponse,
    summary="Update content record",
    description="Update content record fields (use /transition for status changes)",
)
async def update_content(
    content_id: str,
    request: UpdateContentRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Update a content record's metadata."""
    svc = get_status_service()
    await require_owned_content_record(content_id, current_user, svc)

    if request.project_id is not None:
        await require_owned_project_id(request.project_id, current_user)

    try:
        updates = request.model_dump(exclude_none=True)
        if "reviewed_by" in updates:
            updates["reviewed_by"] = current_user.user_id
        record = svc.update_content(content_id, **updates)
        return _record_to_response(record)
    except ContentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Content {content_id} not found")


# ─── Status Transitions ───────────────────────────────


@router.post(
    "/content/{content_id}/transition",
    response_model=ContentResponse,
    summary="Transition content status",
    description="Change content status with validation and audit trail",
)
async def transition_content(
    content_id: str,
    request: TransitionRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Transition a content record to a new status."""
    svc = get_status_service()
    await require_owned_content_record(content_id, current_user, svc)
    try:
        record = svc.transition(
            content_id=content_id,
            to_status=request.to_status,
            changed_by=current_user.user_id,
            reason=request.reason,
        )
        return _record_to_response(record)
    except ContentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Content {content_id} not found")
    except InvalidTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/content/{content_id}/history",
    response_model=List[StatusChangeResponse],
    summary="Get content history",
    description="Get the full audit trail of status changes for a content record",
)
async def get_content_history(
    content_id: str,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Get the audit trail for a content record."""
    svc = get_status_service()
    await require_owned_content_record(content_id, current_user, svc)

    history = svc.get_history(content_id)
    return [
        StatusChangeResponse(
            id=h.id,
            content_id=h.content_id,
            from_status=h.from_status,
            to_status=h.to_status,
            changed_by=h.changed_by,
            reason=h.reason,
            timestamp=h.timestamp,
        )
        for h in history
    ]


# ─── Statistics ────────────────────────────────────────


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get content statistics",
    description="Get content counts grouped by status",
)
async def get_stats(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    current_user: CurrentUser = Depends(require_current_user),
):
    """Get content statistics."""
    svc = get_status_service()
    owned_project_ids = await resolve_owned_project_ids(current_user, project_id)
    return svc.get_stats(project_ids=owned_project_ids)


# ─── Work Domains ──────────────────────────────────────


@router.get(
    "/domains",
    response_model=List[WorkDomainResponse],
    summary="Get work domains",
    description="Get work domain states, optionally filtered by project",
)
async def get_domains(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    current_user: CurrentUser = Depends(require_current_user),
):
    """Get work domain records."""
    svc = get_status_service()
    owned_project_ids = await resolve_owned_project_ids(current_user, project_id)
    domains = svc.get_domains(project_ids=owned_project_ids)
    return [
        WorkDomainResponse(
            id=d.id,
            project_id=d.project_id,
            domain=d.domain,
            status=d.status,
            last_run_at=d.last_run_at,
            last_run_status=d.last_run_status,
            items_pending=d.items_pending,
            items_completed=d.items_completed,
            metadata=d.metadata,
            updated_at=d.updated_at,
        )
        for d in domains
    ]


@router.patch(
    "/domains/{project_id}/{domain}",
    response_model=WorkDomainResponse,
    summary="Update work domain",
    description="Create or update a work domain record for a project",
)
async def update_domain(
    project_id: str,
    domain: str,
    request: UpdateDomainRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Update a work domain record."""
    await require_owned_project_id(project_id, current_user)
    svc = get_status_service()
    updates = request.model_dump(exclude_none=True)
    record = svc.upsert_domain(project_id=project_id, domain=domain, **updates)
    return WorkDomainResponse(
        id=record.id,
        project_id=record.project_id,
        domain=record.domain,
        status=record.status,
        last_run_at=record.last_run_at,
        last_run_status=record.last_run_status,
        items_pending=record.items_pending,
        items_completed=record.items_completed,
        metadata=record.metadata,
        updated_at=record.updated_at,
    )


# ─── Content Body ─────────────────────────────────────


@router.get(
    "/content/{content_id}/body",
    response_model=ContentBodyResponse,
    summary="Get content body",
    description="Get the full content body (latest version or specific version)",
)
async def get_content_body(
    content_id: str,
    version: Optional[int] = Query(None, description="Specific version number"),
    current_user: CurrentUser = Depends(require_current_user),
):
    """Get content body for a content record."""
    svc = get_status_service()
    await require_owned_content_record(content_id, current_user, svc)
    try:
        body = svc.get_content_body(content_id, version=version)
        if not body:
            raise HTTPException(status_code=404, detail="No content body found")
        return ContentBodyResponse(**body)
    except ContentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Content {content_id} not found")


@router.put(
    "/content/{content_id}/body",
    response_model=ContentBodyResponse,
    summary="Save content body",
    description="Save a new version of the content body with edit tracking",
)
async def save_content_body(
    content_id: str,
    request: SaveContentBodyRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Save or update content body (creates a new version)."""
    svc = get_status_service()
    await require_owned_content_record(content_id, current_user, svc)
    try:
        result = svc.save_content_body(
            content_id=content_id,
            body=request.body,
            edited_by=current_user.user_id,
            edit_note=request.edit_note,
        )
        return ContentBodyResponse(**result)
    except ContentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Content {content_id} not found")


@router.get(
    "/content/{content_id}/body/history",
    response_model=List[ContentEditResponse],
    summary="Get content edit history",
    description="Get the edit history for a content record",
)
async def get_edit_history(
    content_id: str,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Get edit history for a content record."""
    svc = get_status_service()
    await require_owned_content_record(content_id, current_user, svc)
    try:
        history = svc.get_edit_history(content_id)
        return [ContentEditResponse(**h) for h in history]
    except ContentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Content {content_id} not found")


@router.post(
    "/content/{content_id}/regenerate",
    response_model=ContentResponse,
    summary="Send content for re-generation",
    description="Transition content back to in_progress with instructions for the robot",
)
async def regenerate_content(
    content_id: str,
    request: RegenerateRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Send content back to the robot for re-generation."""
    svc = get_status_service()
    await require_owned_content_record(content_id, current_user, svc)
    try:
        # Store instructions in metadata
        if request.instructions:
            record = svc.get_content(content_id)
            metadata = record.metadata or {}
            metadata["regenerate_instructions"] = request.instructions
            svc.update_content(content_id, metadata=metadata)

        # Transition to in_progress
        record = svc.transition(
            content_id=content_id,
            to_status="in_progress",
            changed_by=current_user.user_id,
            reason=f"Re-generation requested: {request.instructions or 'No instructions'}",
        )
        return _record_to_response(record)
    except ContentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Content {content_id} not found")
    except InvalidTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/content/{content_id}/schedule",
    response_model=ContentResponse,
    summary="Schedule content for publishing",
    description="Set scheduledFor datetime and transition to scheduled status",
)
async def schedule_content(
    content_id: str,
    request: ScheduleContentRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Schedule content for publishing at a specific time."""
    svc = get_status_service()
    await require_owned_content_record(content_id, current_user, svc)
    try:
        # Set scheduled_for date
        svc.update_content(content_id, scheduled_for=request.scheduled_for)

        # Transition to scheduled
        record = svc.transition(
            content_id=content_id,
            to_status="scheduled",
            changed_by=current_user.user_id,
            reason=f"Scheduled for {request.scheduled_for}",
        )
        return _record_to_response(record)
    except ContentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Content {content_id} not found")
    except InvalidTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Sync ──────────────────────────────────────────────


@router.post(
    "/sync/push",
    summary="Trigger manual sync push",
    description="Manually push unsynced records to Turso",
)
async def trigger_sync_push(
    current_user: CurrentUser = Depends(require_current_user),
):
    """Manually trigger a sync push to Turso."""
    try:
        from status.sync import get_sync_service
        sync_svc = get_sync_service()
        result = await sync_svc.push()
        return result
    except ImportError:
        raise HTTPException(status_code=500, detail="Sync service not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post(
    "/sync/pull",
    summary="Trigger manual sync pull",
    description="Manually pull review actions from Turso",
)
async def trigger_sync_pull(
    current_user: CurrentUser = Depends(require_current_user),
):
    """Manually trigger a sync pull from Turso."""
    try:
        from status.sync import get_sync_service
        sync_svc = get_sync_service()
        result = await sync_svc.pull()
        return result
    except ImportError:
        raise HTTPException(status_code=500, detail="Sync service not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


# ─── Migration ─────────────────────────────────────────


@router.post(
    "/migrate/newsletter-history",
    summary="Migrate newsletter localStorage history",
    description="Import newsletter history items as ContentRecord with status PUBLISHED",
)
async def migrate_newsletter_history(
    items: list,
    current_user: CurrentUser = Depends(require_current_user),
):
    """
    Migrate newsletter history from localStorage to ContentRecord.
    Expects a list of items with: subject_line, word_count, created_at, preview_text.
    """
    svc = get_status_service()
    migrated = 0
    default_project_id = None

    try:
        default_project = await project_store.get_default_project(current_user.user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if default_project:
        default_project_id = default_project.id

    for item in items:
        try:
            record = svc.create_content(
                title=item.get("subject_line", "Untitled Newsletter"),
                content_type="newsletter",
                source_robot="newsletter",
                status="todo",
                project_id=default_project_id,
                metadata={
                    "word_count": item.get("word_count", 0),
                    "preview_text": item.get("preview_text", ""),
                    "migrated_from": "localStorage",
                    "original_id": item.get("id"),
                    "migrated_by_user_id": current_user.user_id,
                },
                content_preview=item.get("preview_text"),
            )
            # Fast-track through the lifecycle to published
            svc.transition(record.id, "in_progress", current_user.user_id)
            svc.transition(record.id, "generated", current_user.user_id)
            svc.transition(record.id, "pending_review", current_user.user_id)
            svc.transition(record.id, "approved", current_user.user_id, reason="Auto-approved: migrated from history")
            svc.transition(record.id, "publishing", current_user.user_id)
            svc.transition(record.id, "published", current_user.user_id, reason="Migrated from localStorage")
            migrated += 1
        except Exception as e:
            print(f"Failed to migrate item: {e}")

    return {"migrated": migrated, "total": len(items)}
