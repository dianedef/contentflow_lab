"""Run history endpoints — expose robot run logs to the dashboard."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from agents.shared.run_history import RunHistory

router = APIRouter(prefix="/runs", tags=["Runs"])


def _get_history() -> RunHistory:
    return RunHistory()


@router.get(
    "",
    summary="List robot runs",
    description="List recent runs across all robots with optional filters.",
)
async def list_runs(
    robot_name: Optional[str] = Query(None, description="Filter by robot name"),
    workflow_type: Optional[str] = Query(None, description="Filter by workflow type"),
    status: Optional[str] = Query(None, description="Filter by status (running, success, error)"),
    limit: int = Query(20, ge=1, le=200, description="Maximum number of runs to return"),
):
    history = _get_history()
    runs = history.get_all_runs(
        robot_name=robot_name,
        workflow_type=workflow_type,
        status=status,
        limit=limit,
    )
    return {"runs": runs, "total": len(runs)}


@router.get(
    "/{run_id}",
    summary="Get run detail",
    description="Return the full record for a single run.",
)
async def get_run(run_id: str):
    history = _get_history()
    run = history.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


@router.get(
    "/stats/{robot_name}",
    summary="Get robot stats",
    description="Aggregate success rate, avg duration, and last run timestamps for a robot.",
)
async def get_robot_stats(robot_name: str):
    history = _get_history()
    return history.get_stats(robot_name)
