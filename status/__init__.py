"""
Unified Status Management System

Tracks content lifecycle from creation to publication across all robots.
"""

from status.service import StatusService, get_status_service
from status.schemas import (
    ContentLifecycleStatus,
    ContentRecord,
    StatusChange,
    WorkDomainRecord,
    ProjectStatus,
    VALID_TRANSITIONS,
)

__all__ = [
    "StatusService",
    "get_status_service",
    "ContentLifecycleStatus",
    "ContentRecord",
    "StatusChange",
    "WorkDomainRecord",
    "ProjectStatus",
    "VALID_TRANSITIONS",
]
