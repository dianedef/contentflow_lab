"""Authenticated creator profile endpoints."""

from fastapi import APIRouter, Depends, Query

from api.dependencies.auth import CurrentUser, require_current_user
from api.models.user_data import CreatorProfileResponse, CreatorProfileUpdateRequest
from api.services.user_data_store import user_data_store

router = APIRouter(prefix="/api/creator-profile", tags=["Creator Profile"])


@router.get("", response_model=CreatorProfileResponse | None, summary="Get creator profile")
async def get_creator_profile(
    projectId: str | None = Query(default=None),
    current_user: CurrentUser = Depends(require_current_user),
) -> CreatorProfileResponse | None:
    profile = await user_data_store.get_creator_profile(
        current_user.user_id,
        projectId,
    )
    return CreatorProfileResponse(**profile) if profile else None


@router.put("", response_model=CreatorProfileResponse, summary="Upsert creator profile")
async def put_creator_profile(
    request: CreatorProfileUpdateRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> CreatorProfileResponse:
    profile = await user_data_store.upsert_creator_profile(
        current_user.user_id,
        request.model_dump(exclude_unset=True),
    )
    return CreatorProfileResponse(**profile)
