"""Ownership helpers for project-scoped resources."""

from __future__ import annotations

from fastapi import HTTPException, status

from agents.seo.config.project_store import project_store
from api.dependencies.auth import CurrentUser
from status.schemas import ContentRecord
from status.service import ContentNotFoundError, StatusService


def _database_not_configured(detail: str) -> HTTPException:
    """Normalize backing store configuration failures."""
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=detail,
    )


async def get_owned_project_ids(current_user: CurrentUser) -> list[str]:
    """Return all project ids owned by the current user."""
    try:
        projects = await project_store.get_by_user(current_user.user_id)
    except RuntimeError as exc:
        raise _database_not_configured(str(exc)) from exc

    return [project.id for project in projects]


async def require_owned_project_id(
    project_id: str,
    current_user: CurrentUser,
) -> str:
    """Ensure the project belongs to the current user."""
    try:
        project = await project_store.get_by_id(project_id)
    except RuntimeError as exc:
        raise _database_not_configured(str(exc)) from exc

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    if project.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return project_id


async def resolve_owned_project_ids(
    current_user: CurrentUser,
    project_id: str | None = None,
) -> list[str]:
    """Resolve the project scope for the current user."""
    if project_id is not None:
        return [await require_owned_project_id(project_id, current_user)]
    return await get_owned_project_ids(current_user)


async def require_owned_content_record(
    content_id: str,
    current_user: CurrentUser,
    status_service: StatusService,
) -> ContentRecord:
    """Load a content record and ensure its project belongs to the current user."""
    try:
        record = status_service.get_content(content_id)
    except ContentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content {content_id} not found",
        ) from exc

    if not record.project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Content record is not scoped to a project",
        )

    await require_owned_project_id(record.project_id, current_user)
    return record
