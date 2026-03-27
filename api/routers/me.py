"""Authenticated account bootstrap endpoints."""

from fastapi import APIRouter, Depends

from agents.seo.config.project_store import project_store
from api.dependencies.auth import CurrentUser, require_current_user
from api.models.bootstrap import BootstrapResponse, MeResponse

router = APIRouter(prefix="/api", tags=["Auth"])


@router.get("/me", response_model=MeResponse, summary="Get current authenticated user")
async def get_me(
    current_user: CurrentUser = Depends(require_current_user),
) -> MeResponse:
    """Return the current authenticated user and basic workspace presence."""
    projects = await project_store.get_by_user(current_user.user_id)
    default_project = await project_store.get_default_project(current_user.user_id)

    return MeResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        workspace_exists=bool(projects),
        default_project_id=default_project.id if default_project else None,
    )


@router.get(
    "/bootstrap",
    response_model=BootstrapResponse,
    summary="Get bootstrap state for app routing",
)
async def get_bootstrap(
    current_user: CurrentUser = Depends(require_current_user),
) -> BootstrapResponse:
    """Return the minimum authenticated bootstrap state needed by Flutter."""
    projects = await project_store.get_by_user(current_user.user_id)
    default_project = await project_store.get_default_project(current_user.user_id)

    user = MeResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        workspace_exists=bool(projects),
        default_project_id=default_project.id if default_project else None,
    )

    return BootstrapResponse(
        user=user,
        projects_count=len(projects),
        default_project_id=default_project.id if default_project else None,
        workspace_status="ready" if projects else "empty",
    )
