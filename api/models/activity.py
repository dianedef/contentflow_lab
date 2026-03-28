"""Models for activity log endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ActivityLogResponse(BaseModel):
    id: str
    userId: str
    projectId: str | None = None
    action: str
    robotId: str | None = None
    status: str = "started"
    details: dict[str, Any] | None = None
    createdAt: datetime


class ActivityLogCreateRequest(BaseModel):
    projectId: str | None = None
    action: str
    robotId: str | None = None
    status: str | None = None
    details: dict[str, Any] | None = None
