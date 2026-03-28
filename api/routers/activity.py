"""Authenticated activity log endpoints."""

from fastapi import APIRouter, Depends, Query

from api.dependencies.auth import CurrentUser, require_current_user
from api.models.activity import (
    ActivityLogCreateRequest,
    ActivityLogResponse,
)
from api.services.user_data_store import user_data_store

router = APIRouter(prefix="/api/activity", tags=["Activity"])


@router.get("", response_model=list[ActivityLogResponse], summary="List activity")
async def list_activity(
    projectId: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_current_user),
) -> list[ActivityLogResponse]:
    activities = await user_data_store.list_activity(current_user.user_id, projectId, limit)
    return [ActivityLogResponse(**a) for a in activities]


@router.post("", response_model=ActivityLogResponse, status_code=201, summary="Log activity")
async def create_activity(
    request: ActivityLogCreateRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> ActivityLogResponse:
    activity = await user_data_store.create_activity(
        current_user.user_id,
        request.model_dump(exclude_unset=True),
    )
    return ActivityLogResponse(**activity)
