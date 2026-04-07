"""Scheduler management endpoints for persistent job scheduling."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime

from api.models.status import (
    CreateScheduleJobRequest,
    UpdateScheduleJobRequest,
    ScheduleJobResponse,
    ContentResponse,
)
from api.dependencies.auth import require_current_user
from status.service import get_status_service, ContentNotFoundError

router = APIRouter(
    prefix="/api/scheduler",
    tags=["Scheduler"],
    dependencies=[Depends(require_current_user)],
)


def _job_to_response(job: dict) -> ScheduleJobResponse:
    """Convert a job dict to a ScheduleJobResponse."""
    return ScheduleJobResponse(**job)


# ─── Schedule Jobs CRUD ───────────────────────────────


@router.get(
    "/jobs",
    response_model=List[ScheduleJobResponse],
    summary="List schedule jobs",
    description="List all scheduled jobs with optional filters",
)
async def list_jobs(
    user_id: Optional[str] = Query(None, description="Filter by user"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    enabled_only: bool = Query(False, description="Only enabled jobs"),
):
    """List all scheduled jobs."""
    svc = get_status_service()
    jobs = svc.list_schedule_jobs(
        user_id=user_id,
        project_id=project_id,
        enabled_only=enabled_only,
    )
    return [_job_to_response(j) for j in jobs]


@router.post(
    "/jobs",
    response_model=ScheduleJobResponse,
    status_code=201,
    summary="Create schedule job",
    description="Create a new scheduled job for recurring content generation",
)
async def create_job(request: CreateScheduleJobRequest):
    """Create a new schedule job."""
    svc = get_status_service()
    try:
        job = svc.create_schedule_job(**request.model_dump())
        return _job_to_response(job)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/jobs/{job_id}",
    response_model=ScheduleJobResponse,
    summary="Get schedule job",
    description="Get a single schedule job by ID",
)
async def get_job(job_id: str):
    """Get a schedule job by ID."""
    svc = get_status_service()
    try:
        job = svc.get_schedule_job(job_id)
        return _job_to_response(job)
    except ContentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


@router.patch(
    "/jobs/{job_id}",
    response_model=ScheduleJobResponse,
    summary="Update schedule job",
    description="Update a schedule job (enable/disable, change schedule, etc.)",
)
async def update_job(job_id: str, request: UpdateScheduleJobRequest):
    """Update a schedule job."""
    svc = get_status_service()
    try:
        updates = request.model_dump(exclude_none=True)
        job = svc.update_schedule_job(job_id, **updates)
        return _job_to_response(job)
    except ContentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


@router.delete(
    "/jobs/{job_id}",
    summary="Delete schedule job",
    description="Delete a scheduled job permanently",
)
async def delete_job(job_id: str):
    """Delete a schedule job."""
    svc = get_status_service()
    try:
        svc.delete_schedule_job(job_id)
        return {"status": "deleted", "id": job_id}
    except ContentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


# ─── Calendar View ────────────────────────────────────


@router.get(
    "/calendar",
    summary="Get calendar events",
    description="Get content records and schedule jobs for a date range (for calendar view)",
)
async def get_calendar_events(
    start: str = Query(..., description="Start date (ISO format, e.g. 2026-01-01)"),
    end: str = Query(..., description="End date (ISO format, e.g. 2026-01-31)"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
):
    """
    Aggregate ContentRecords and ScheduleJobs for the calendar view.
    Returns events grouped by date.
    """
    svc = get_status_service()

    # Get content records in range
    all_content = svc.list_content(project_id=project_id, limit=200)

    events = []

    for item in all_content:
        event_date = None
        event_type = "content"

        # Use scheduledFor, publishedAt, or createdAt as the event date
        if item.scheduled_for:
            date_str = item.scheduled_for.isoformat()
            if start <= date_str <= end:
                event_date = date_str
        elif item.published_at:
            date_str = item.published_at.isoformat()
            if start <= date_str <= end:
                event_date = date_str
        elif item.created_at:
            date_str = item.created_at.isoformat()
            if start <= date_str <= end:
                event_date = date_str

        if event_date:
            events.append({
                "id": item.id,
                "title": item.title,
                "date": event_date[:10],  # YYYY-MM-DD
                "datetime": event_date,
                "type": event_type,
                "content_type": item.content_type,
                "source_robot": item.source_robot,
                "status": item.status,
            })

    # Get schedule jobs for the range
    jobs = svc.list_schedule_jobs(enabled_only=True)
    for job in jobs:
        if job.get("next_run_at"):
            next_run = job["next_run_at"]
            if start <= next_run <= end:
                events.append({
                    "id": job["id"],
                    "title": f"[{job['job_type'].upper()}] Scheduled {job['schedule']}",
                    "date": next_run[:10],
                    "datetime": next_run,
                    "type": "schedule",
                    "content_type": job["job_type"],
                    "source_robot": job["job_type"],
                    "status": "scheduled",
                })

    # Sort by date
    events.sort(key=lambda e: e["datetime"])

    return {"events": events, "total": len(events)}
