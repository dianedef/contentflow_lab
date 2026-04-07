"""
SEO Deployment API Router

Provides endpoints for managing SEO content deployment:
- Single topic runs
- Batch processing
- Schedule management
- Log viewing
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from typing import List, Optional
import uuid
import asyncio
from datetime import datetime

from api.dependencies.auth import require_current_user

from api.models.deployment import (
    DeploymentRunRequest,
    BatchRunRequest,
    ScheduleRequest,
    DeploymentStatus,
    LogEntry,
    Schedule,
    StepStatus,
    BatchProgress,
    ScheduleType,
    DeploymentRunResponse,
    BatchRunResponse,
    StopResponse,
    DeleteResponse,
)

router = APIRouter(
    prefix="/api/deployment",
    tags=["SEO Deployment"],
    dependencies=[Depends(require_current_user)],
)

# In-memory state (replace with Redis/DB for production)
_current_job: Optional[dict] = None
_logs: List[LogEntry] = []
_schedules: dict[str, Schedule] = {}

# Pipeline steps for progress tracking
PIPELINE_STEPS = [
    "research",
    "strategy",
    "content",
    "technical_seo",
    "editing",
    "deployment",
]


def _add_log(level: str, step: Optional[str], message: str) -> None:
    """Add a log entry"""
    _logs.append(
        LogEntry(
            timestamp=datetime.now(),
            level=level,
            step=step,
            message=message,
        )
    )
    # Keep only last 1000 logs
    if len(_logs) > 1000:
        _logs.pop(0)


def _get_default_cron(schedule_type: ScheduleType) -> str:
    """Get default cron expression for schedule type"""
    defaults = {
        ScheduleType.DAILY: "0 9 * * *",  # 9 AM daily
        ScheduleType.WEEKLY: "0 9 * * 1",  # 9 AM Monday
        ScheduleType.CUSTOM: "0 9 * * *",  # Default to daily
    }
    return defaults.get(schedule_type, "0 9 * * *")


def _initialize_steps() -> List[StepStatus]:
    """Initialize pipeline steps with pending status"""
    return [
        StepStatus(name=step, status="pending")
        for step in PIPELINE_STEPS
    ]


async def execute_pipeline(
    topic: str,
    dry_run: bool,
    auto_deploy: bool,
    target_repo: Optional[str],
) -> None:
    """Execute SEO pipeline (background task)"""
    global _current_job

    if _current_job is None:
        return

    _current_job["steps"] = _initialize_steps()

    try:
        # Research phase
        _current_job["current_step"] = "research"
        _current_job["progress"] = 10
        _update_step_status("research", "running")
        _add_log("info", "research", f"Starting research for topic: {topic}")

        # Simulate research (replace with actual agent call)
        await asyncio.sleep(2)
        _update_step_status("research", "completed")
        _add_log("info", "research", "Research phase completed")

        if not _current_job.get("running"):
            _add_log("warning", "research", "Pipeline stopped by user")
            return

        # Strategy phase
        _current_job["current_step"] = "strategy"
        _current_job["progress"] = 25
        _update_step_status("strategy", "running")
        _add_log("info", "strategy", "Developing content strategy")

        await asyncio.sleep(2)
        _update_step_status("strategy", "completed")
        _add_log("info", "strategy", "Strategy phase completed")

        if not _current_job.get("running"):
            return

        # Content generation phase
        _current_job["current_step"] = "content"
        _current_job["progress"] = 45
        _update_step_status("content", "running")
        _add_log("info", "content", "Generating content")

        await asyncio.sleep(3)
        _update_step_status("content", "completed")
        _add_log("info", "content", "Content generation completed")

        if not _current_job.get("running"):
            return

        # Technical SEO phase
        _current_job["current_step"] = "technical_seo"
        _current_job["progress"] = 65
        _update_step_status("technical_seo", "running")
        _add_log("info", "technical_seo", "Applying technical SEO optimizations")

        await asyncio.sleep(2)
        _update_step_status("technical_seo", "completed")
        _add_log("info", "technical_seo", "Technical SEO completed")

        if not _current_job.get("running"):
            return

        # Editing phase
        _current_job["current_step"] = "editing"
        _current_job["progress"] = 80
        _update_step_status("editing", "running")
        _add_log("info", "editing", "Final editing and quality check")

        await asyncio.sleep(2)
        _update_step_status("editing", "completed")
        _add_log("info", "editing", "Editing completed")

        if not _current_job.get("running"):
            return

        # Deployment phase
        if auto_deploy and not dry_run:
            _current_job["current_step"] = "deployment"
            _current_job["progress"] = 90
            _update_step_status("deployment", "running")
            _add_log("info", "deployment", f"Deploying to {target_repo or 'default repository'}")

            await asyncio.sleep(2)
            _update_step_status("deployment", "completed")
            _add_log("info", "deployment", "Deployment completed successfully")
        else:
            _update_step_status("deployment", "completed")
            if dry_run:
                _add_log("info", "deployment", "Dry run - skipping deployment")
            else:
                _add_log("info", "deployment", "No-deploy flag set - skipping deployment")

        _current_job["progress"] = 100
        _current_job["current_step"] = None
        _add_log("info", "complete", f"Pipeline completed successfully for: {topic}")

    except Exception as e:
        error_msg = str(e)
        _current_job["error"] = error_msg
        _add_log("error", _current_job.get("current_step"), f"Pipeline failed: {error_msg}")

        # Mark current step as error
        if _current_job.get("current_step"):
            _update_step_status(_current_job["current_step"], "error")

    finally:
        _current_job["running"] = False


def _update_step_status(step_name: str, status: str) -> None:
    """Update status of a pipeline step"""
    global _current_job
    if _current_job and "steps" in _current_job:
        for step in _current_job["steps"]:
            if step.name == step_name:
                step.status = status
                if status == "running":
                    step.started_at = datetime.now()
                elif status in ("completed", "error"):
                    step.completed_at = datetime.now()
                    if step.started_at:
                        step.duration_seconds = (
                            step.completed_at - step.started_at
                        ).total_seconds()
                break


async def execute_batch(
    topics: List[str],
    delay: int,
    auto_deploy: bool,
) -> None:
    """Execute batch deployment"""
    global _current_job

    for i, topic in enumerate(topics):
        if _current_job is None or not _current_job.get("running"):
            _add_log("warning", "batch", "Batch processing stopped")
            break

        _current_job["topic"] = topic
        _current_job["batch_progress"] = BatchProgress(
            completed=i,
            total=len(topics),
            current_topic=topic,
        )
        _add_log("info", "batch", f"Processing topic {i + 1}/{len(topics)}: {topic}")

        # Execute pipeline for this topic
        await execute_pipeline(topic, False, auto_deploy, None)

        _current_job["batch_progress"].completed = i + 1

        # Delay between topics (except for last one)
        if i < len(topics) - 1 and _current_job.get("running"):
            _add_log("info", "batch", f"Waiting {delay}s before next topic...")
            await asyncio.sleep(delay)

    if _current_job:
        _current_job["running"] = False
        _add_log("info", "batch", "Batch processing completed")


@router.post("/run", response_model=DeploymentRunResponse)
async def run_deployment(
    request: DeploymentRunRequest,
    background_tasks: BackgroundTasks,
) -> DeploymentRunResponse:
    """
    Start single topic deployment

    Initiates the SEO content generation pipeline for a single topic.
    The pipeline runs in the background and progress can be monitored
    via the /status endpoint.
    """
    global _current_job

    if _current_job and _current_job.get("running"):
        raise HTTPException(
            status_code=400,
            detail="Deployment already running. Stop it first or wait for completion.",
        )

    job_id = str(uuid.uuid4())
    _current_job = {
        "job_id": job_id,
        "running": True,
        "job_type": "single",
        "topic": request.topic,
        "current_step": None,
        "progress": 0,
        "steps": _initialize_steps(),
        "started_at": datetime.now(),
    }

    _add_log("info", None, f"Starting deployment for topic: {request.topic}")

    background_tasks.add_task(
        execute_pipeline,
        request.topic,
        request.dry_run,
        not request.no_deploy,
        request.target_repo,
    )

    return DeploymentRunResponse(
        job_id=job_id,
        status="started",
        topic=request.topic,
    )


@router.post("/batch", response_model=BatchRunResponse)
async def run_batch(
    request: BatchRunRequest,
    background_tasks: BackgroundTasks,
) -> BatchRunResponse:
    """
    Start batch deployment

    Processes multiple topics sequentially with configurable delay between them.
    """
    global _current_job

    if _current_job and _current_job.get("running"):
        raise HTTPException(
            status_code=400,
            detail="Deployment already running. Stop it first or wait for completion.",
        )

    job_id = str(uuid.uuid4())
    _current_job = {
        "job_id": job_id,
        "running": True,
        "job_type": "batch",
        "topics": request.topics,
        "topic": request.topics[0] if request.topics else None,
        "current_step": None,
        "progress": 0,
        "steps": _initialize_steps(),
        "batch_progress": BatchProgress(
            completed=0,
            total=len(request.topics),
            current_topic=request.topics[0] if request.topics else None,
        ),
        "started_at": datetime.now(),
    }

    _add_log("info", None, f"Starting batch deployment for {len(request.topics)} topics")

    background_tasks.add_task(
        execute_batch,
        request.topics,
        request.delay_seconds,
        request.auto_deploy,
    )

    return BatchRunResponse(
        batch_id=job_id,
        total_topics=len(request.topics),
        status="started",
    )


@router.get("/status", response_model=DeploymentStatus)
async def get_status() -> DeploymentStatus:
    """
    Get current deployment status

    Returns the current state of any running deployment including
    progress, current step, and any errors.
    """
    if not _current_job:
        return DeploymentStatus(running=False)

    return DeploymentStatus(
        running=_current_job.get("running", False),
        job_id=_current_job.get("job_id"),
        job_type=_current_job.get("job_type"),
        topic=_current_job.get("topic"),
        current_step=_current_job.get("current_step"),
        progress=_current_job.get("progress", 0),
        steps=_current_job.get("steps", []),
        batch_progress=_current_job.get("batch_progress"),
        error=_current_job.get("error"),
    )


@router.post("/stop", response_model=StopResponse)
async def stop_deployment() -> StopResponse:
    """
    Stop running deployment

    Gracefully stops the current deployment at the next checkpoint.
    """
    global _current_job

    if _current_job:
        _current_job["running"] = False
        _current_job["stopped"] = True
        _add_log("warning", None, "Deployment stopped by user")

    return StopResponse(status="stopped")


@router.get("/logs", response_model=List[LogEntry])
async def get_logs(
    level: Optional[str] = Query(default=None, description="Filter by log level"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max logs to return"),
    since: Optional[str] = Query(default=None, description="ISO timestamp to filter from"),
) -> List[LogEntry]:
    """
    Get deployment logs

    Returns recent log entries with optional filtering by level and time.
    """
    logs = _logs

    # Filter by level
    if level:
        logs = [log for log in logs if log.level == level]

    # Filter by timestamp
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            logs = [log for log in logs if log.timestamp >= since_dt]
        except ValueError:
            pass

    return logs[-limit:]


@router.get("/schedules", response_model=List[Schedule])
async def list_schedules() -> List[Schedule]:
    """
    List all schedules

    Returns all configured deployment schedules.
    """
    return list(_schedules.values())


@router.post("/schedules", response_model=Schedule)
async def create_schedule(request: ScheduleRequest) -> Schedule:
    """
    Create or update schedule

    Creates a new deployment schedule with the specified configuration.
    """
    schedule_id = str(uuid.uuid4())
    cron = request.cron_expression or _get_default_cron(request.schedule_type)

    schedule = Schedule(
        id=schedule_id,
        schedule_type=request.schedule_type,
        cron_expression=cron,
        topics=request.topics,
        enabled=request.enabled,
    )
    _schedules[schedule_id] = schedule

    _add_log(
        "info",
        None,
        f"Created schedule {schedule_id}: {request.schedule_type.value} for {len(request.topics)} topics",
    )

    return schedule


@router.patch("/schedules/{schedule_id}", response_model=Schedule)
async def update_schedule(
    schedule_id: str,
    enabled: Optional[bool] = Query(default=None),
) -> Schedule:
    """
    Update schedule

    Updates an existing schedule's configuration.
    """
    if schedule_id not in _schedules:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule = _schedules[schedule_id]

    if enabled is not None:
        schedule.enabled = enabled
        _add_log(
            "info",
            None,
            f"Schedule {schedule_id} {'enabled' if enabled else 'disabled'}",
        )

    return schedule


@router.delete("/schedules/{schedule_id}", response_model=DeleteResponse)
async def delete_schedule(schedule_id: str) -> DeleteResponse:
    """
    Delete schedule

    Removes a deployment schedule.
    """
    if schedule_id in _schedules:
        del _schedules[schedule_id]
        _add_log("info", None, f"Deleted schedule {schedule_id}")

    return DeleteResponse(status="deleted")
