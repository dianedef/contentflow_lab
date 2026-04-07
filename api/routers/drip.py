"""
Content Drip Router — Progressive content publication.

Endpoints:
  POST   /api/drip/plans              Create a drip plan
  GET    /api/drip/plans              List drip plans
  GET    /api/drip/plans/{id}         Get a drip plan
  PATCH  /api/drip/plans/{id}         Update a drip plan
  DELETE /api/drip/plans/{id}         Delete a drip plan
  GET    /api/drip/plans/{id}/items   List plan items (ContentRecords)
  GET    /api/drip/plans/{id}/stats   Get plan statistics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from api.dependencies.auth import CurrentUser, require_current_user

from api.models.drip import (
    CreateDripPlanRequest,
    UpdateDripPlanRequest,
    DripPlanResponse,
    DripPlanListResponse,
    DripStatsResponse,
)
from api.models.status import ContentResponse
from api.services.drip_service import DripService, DripPlanNotFoundError
from status.service import get_status_service

router = APIRouter(
    prefix="/api/drip",
    tags=["Content Drip"],
    dependencies=[Depends(require_current_user)],
)


def _get_drip_service() -> DripService:
    return DripService(get_status_service())


# ─── Plans CRUD ──────────────────────────────────────


@router.post(
    "/plans",
    response_model=DripPlanResponse,
    status_code=201,
    summary="Create a drip plan",
)
async def create_plan(
    request: CreateDripPlanRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Create a new progressive content publication plan."""
    svc = _get_drip_service()
    plan = svc.create_plan(
        name=request.name,
        user_id=current_user.user_id,
        cadence_config=request.cadence.model_dump(),
        cluster_strategy=request.cluster_strategy.model_dump(),
        ssg_config=request.ssg_config.model_dump(),
        gsc_config=request.gsc_config.model_dump() if request.gsc_config else None,
        project_id=request.project_id,
    )
    return DripPlanResponse(**plan)


@router.get(
    "/plans",
    response_model=DripPlanListResponse,
    summary="List drip plans",
)
async def list_plans(
    user_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """List all drip plans with optional filters."""
    svc = _get_drip_service()
    plans = svc.list_plans(user_id=user_id, project_id=project_id, status=status)
    return DripPlanListResponse(
        items=[DripPlanResponse(**p) for p in plans],
        total=len(plans),
    )


@router.get(
    "/plans/{plan_id}",
    response_model=DripPlanResponse,
    summary="Get a drip plan",
)
async def get_plan(plan_id: str):
    """Get a drip plan by ID."""
    svc = _get_drip_service()
    try:
        plan = svc.get_plan(plan_id)
        return DripPlanResponse(**plan)
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")


@router.patch(
    "/plans/{plan_id}",
    response_model=DripPlanResponse,
    summary="Update a drip plan",
)
async def update_plan(plan_id: str, request: UpdateDripPlanRequest):
    """Update a drip plan's configuration."""
    svc = _get_drip_service()
    try:
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.cadence is not None:
            updates["cadence_config"] = request.cadence.model_dump()
        if request.cluster_strategy is not None:
            updates["cluster_strategy"] = request.cluster_strategy.model_dump()
        if request.ssg_config is not None:
            updates["ssg_config"] = request.ssg_config.model_dump()
        if request.gsc_config is not None:
            updates["gsc_config"] = request.gsc_config.model_dump()

        plan = svc.update_plan(plan_id, **updates)
        return DripPlanResponse(**plan)
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")


@router.delete(
    "/plans/{plan_id}",
    summary="Delete a drip plan",
)
async def delete_plan(plan_id: str):
    """Delete a drip plan and its associated content records."""
    svc = _get_drip_service()
    try:
        svc.delete_plan(plan_id)
        return {"status": "deleted", "id": plan_id}
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")


# ─── Plan Items ──────────────────────────────────────


@router.get(
    "/plans/{plan_id}/items",
    response_model=List[ContentResponse],
    summary="List plan items",
)
async def list_plan_items(
    plan_id: str,
    status: Optional[str] = Query(None, description="Filter by content status"),
):
    """List all ContentRecords belonging to a drip plan."""
    svc = _get_drip_service()
    try:
        svc.get_plan(plan_id)  # Ensure plan exists
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")

    items = svc.get_plan_items(plan_id, status=status)
    return [
        ContentResponse(
            id=item.id,
            title=item.title,
            content_type=item.content_type,
            source_robot=item.source_robot,
            status=item.status,
            project_id=item.project_id,
            user_id=item.user_id,
            content_path=item.content_path,
            content_preview=item.content_preview,
            content_hash=item.content_hash,
            priority=item.priority,
            tags=item.tags,
            metadata=item.metadata,
            target_url=item.target_url,
            reviewer_note=item.reviewer_note,
            reviewed_by=item.reviewed_by,
            created_at=item.created_at,
            updated_at=item.updated_at,
            scheduled_for=item.scheduled_for,
            published_at=item.published_at,
            synced_at=item.synced_at,
        )
        for item in items
    ]


# ─── Plan Stats ──────────────────────────────────────


@router.get(
    "/plans/{plan_id}/stats",
    response_model=DripStatsResponse,
    summary="Get plan statistics",
)
async def get_plan_stats(plan_id: str):
    """Get statistics for a drip plan (items by status, clusters breakdown)."""
    svc = _get_drip_service()
    try:
        svc.get_plan(plan_id)  # Ensure plan exists
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")

    stats = svc.get_plan_stats(plan_id)
    return DripStatsResponse(**stats)


# ─── Import & Clustering ────────────────────────────


@router.post(
    "/plans/{plan_id}/import",
    summary="Import content from a directory",
)
async def import_content(
    plan_id: str,
    directory: str = Query(..., description="Absolute path to content directory"),
    exclude_drafts: bool = Query(True, description="Skip files with draft: true"),
):
    """Scan a directory for Markdown files and create ContentRecords for the plan."""
    svc = _get_drip_service()
    try:
        svc.get_plan(plan_id)
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")

    try:
        count = svc.import_from_directory(plan_id, directory, exclude_drafts=exclude_drafts)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "imported", "items_imported": count, "plan_id": plan_id}


@router.post(
    "/plans/{plan_id}/cluster",
    summary="Cluster plan items",
)
async def cluster_items(
    plan_id: str,
    mode: str = Query("directory", description="Clustering mode: directory, tags, or auto"),
    repo_url: Optional[str] = Query(None, description="GitHub repo URL (for auto mode)"),
    local_repo_path: Optional[str] = Query(None, description="Local repo path (for auto mode)"),
):
    """Group imported items into clusters.

    Modes:
    - **directory**: group by file directory structure (default)
    - **tags**: group by primary frontmatter tag
    - **auto**: use Topical Mesh Architect AI to detect semantic cocoons
    """
    svc = _get_drip_service()
    try:
        svc.get_plan(plan_id)
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")

    if mode == "tags":
        result = svc.cluster_by_tags(plan_id)
    elif mode == "auto":
        result = svc.cluster_auto(plan_id, repo_url=repo_url, local_repo_path=local_repo_path)
    else:
        result = svc.cluster_by_directory(plan_id)

    result["mode"] = mode
    return result


# ─── Scheduling ──────────────────────────────────────


@router.post(
    "/plans/{plan_id}/schedule",
    summary="Generate publication schedule",
)
async def generate_schedule(plan_id: str):
    """Assign scheduled_for dates to all items based on cadence and cluster order."""
    svc = _get_drip_service()
    try:
        svc.get_plan(plan_id)
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")

    schedule = svc.generate_schedule(plan_id, dry_run=False)
    return {"status": "scheduled", "total_items": len(schedule), "schedule": schedule}


@router.get(
    "/plans/{plan_id}/preview",
    summary="Preview schedule (dry-run)",
)
async def preview_schedule(plan_id: str):
    """Preview the publication schedule without writing to the database."""
    svc = _get_drip_service()
    try:
        svc.get_plan(plan_id)
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")

    schedule = svc.generate_schedule(plan_id, dry_run=True)
    days = len(set(e["scheduled_date"] for e in schedule))
    return {
        "total_items": len(schedule),
        "total_days": days,
        "first_date": schedule[0]["scheduled_date"] if schedule else None,
        "last_date": schedule[-1]["scheduled_date"] if schedule else None,
        "schedule": schedule,
    }


# ─── Plan Lifecycle ──────────────────────────────────


@router.post(
    "/plans/{plan_id}/activate",
    response_model=DripPlanResponse,
    summary="Activate a plan",
)
async def activate_plan(plan_id: str):
    """Activate a draft/paused plan — creates the cron job and starts dripping."""
    svc = _get_drip_service()
    try:
        plan = svc.activate_plan(plan_id)
        return DripPlanResponse(**plan)
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/plans/{plan_id}/pause",
    response_model=DripPlanResponse,
    summary="Pause an active plan",
)
async def pause_plan(plan_id: str):
    """Pause an active plan — stops dripping but preserves schedule."""
    svc = _get_drip_service()
    try:
        plan = svc.pause_plan(plan_id)
        return DripPlanResponse(**plan)
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/plans/{plan_id}/resume",
    response_model=DripPlanResponse,
    summary="Resume a paused plan",
)
async def resume_plan(plan_id: str):
    """Resume a paused plan."""
    svc = _get_drip_service()
    try:
        plan = svc.resume_plan(plan_id)
        return DripPlanResponse(**plan)
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/plans/{plan_id}/cancel",
    response_model=DripPlanResponse,
    summary="Cancel a plan",
)
async def cancel_plan(plan_id: str):
    """Cancel a plan — no more drips will execute."""
    svc = _get_drip_service()
    try:
        plan = svc.cancel_plan(plan_id)
        return DripPlanResponse(**plan)
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Execution ───────────────────────────────────────


@router.post(
    "/plans/{plan_id}/execute-tick",
    summary="Execute drip tick (publish due items)",
)
async def execute_tick(plan_id: str):
    """Publish items that are due today, update their frontmatter, and trigger rebuild."""
    from api.services.rebuild_trigger import trigger_rebuild

    svc = _get_drip_service()
    try:
        plan = svc.get_plan(plan_id)
    except DripPlanNotFoundError:
        raise HTTPException(status_code=404, detail=f"Drip plan {plan_id} not found")

    # Execute the drip tick (update frontmatter + transition records)
    result = svc.execute_drip_tick(plan_id)

    # Trigger SSG rebuild if items were published
    rebuild_result = None
    if result["published"] > 0:
        ssg_config = plan.get("ssg_config", {})
        rebuild_result = await trigger_rebuild(ssg_config)

        # Submit URLs to GSC if configured
        gsc_config = plan.get("gsc_config")
        if gsc_config and gsc_config.get("enabled") and gsc_config.get("submit_urls"):
            try:
                from api.services.gsc_client import get_gsc_client
                gsc = get_gsc_client()
                if gsc.available:
                    site_url = gsc_config["site_url"].rstrip("/")
                    urls = [f"{site_url}/{item['content_path'].replace('.md', '')}" for item in result.get("items", [])]
                    gsc_result = gsc.submit_urls_batch(urls, max_per_day=gsc_config.get("max_submissions_per_day", 200))
                    result["gsc"] = gsc_result
            except Exception as e:
                result["gsc"] = {"error": str(e)}

    result["rebuild"] = rebuild_result
    return result


# ─── GSC ─────────────────────────────────────────────


@router.post(
    "/gsc/submit-urls",
    summary="Submit URLs to Google Search Console",
)
async def gsc_submit_urls(
    urls: List[str],
    max_per_day: int = Query(200, description="Max submissions per day"),
):
    """Submit URLs for indexing via the Google Indexing API."""
    try:
        from api.services.gsc_client import get_gsc_client
        gsc = get_gsc_client()
        if not gsc.available:
            raise HTTPException(status_code=503, detail="Google API libraries not installed")
        return gsc.submit_urls_batch(urls, max_per_day=max_per_day)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get(
    "/gsc/indexation-status",
    summary="Check URL indexation status",
)
async def gsc_check_indexation(
    site_url: str = Query(..., description="GSC property URL"),
    urls: List[str] = Query(..., description="Page URLs to check"),
):
    """Check indexation status for URLs via the URL Inspection API."""
    try:
        from api.services.gsc_client import get_gsc_client
        gsc = get_gsc_client()
        if not gsc.available:
            raise HTTPException(status_code=503, detail="Google API libraries not installed")
        return gsc.check_indexation_batch(site_url, urls)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
