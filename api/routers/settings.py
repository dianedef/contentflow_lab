"""Authenticated user settings endpoints."""

from fastapi import APIRouter, Depends

from api.dependencies.auth import CurrentUser, require_current_user
from api.models.user_data import UserSettingsResponse, UserSettingsUpdateRequest
from api.services.user_data_store import user_data_store

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("", response_model=UserSettingsResponse, summary="Get user settings")
async def get_settings(
    current_user: CurrentUser = Depends(require_current_user),
) -> UserSettingsResponse:
    settings = await user_data_store.get_user_settings(current_user.user_id)
    return UserSettingsResponse(**settings)


@router.patch("", response_model=UserSettingsResponse, summary="Update user settings")
async def patch_settings(
    request: UserSettingsUpdateRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> UserSettingsResponse:
    settings = await user_data_store.update_user_settings(
        current_user.user_id,
        request.model_dump(exclude_unset=True),
    )
    return UserSettingsResponse(**settings)
