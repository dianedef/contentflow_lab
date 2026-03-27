"""Models for authenticated bootstrap endpoints."""

from pydantic import BaseModel


class MeResponse(BaseModel):
    """Authenticated user payload returned to clients."""

    user_id: str
    email: str | None = None
    workspace_exists: bool
    default_project_id: str | None = None


class BootstrapResponse(BaseModel):
    """Startup payload used by clients to route between auth/onboarding/app."""

    user: MeResponse
    projects_count: int
    default_project_id: str | None = None
    workspace_status: str
