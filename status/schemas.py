"""
Status Management Schemas

Pydantic models for the unified content lifecycle tracking system.
Reuses ContentType and SourceRobot from publishing_schemas.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from agents.scheduler.schemas.publishing_schemas import ContentType, SourceRobot


class ContentLifecycleStatus(str, Enum):
    """
    Unified content lifecycle status.
    Replaces PublishingStatus with a complete lifecycle from creation to archival.
    """
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    GENERATED = "generated"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    ARCHIVED = "archived"


class ProjectStatus(str, Enum):
    """Project lifecycle status"""
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


# Valid state transitions matrix
VALID_TRANSITIONS: Dict[ContentLifecycleStatus, List[ContentLifecycleStatus]] = {
    ContentLifecycleStatus.TODO: [
        ContentLifecycleStatus.IN_PROGRESS,
        ContentLifecycleStatus.ARCHIVED,
    ],
    ContentLifecycleStatus.IN_PROGRESS: [
        ContentLifecycleStatus.GENERATED,
        ContentLifecycleStatus.FAILED,
    ],
    ContentLifecycleStatus.GENERATED: [
        ContentLifecycleStatus.PENDING_REVIEW,
        ContentLifecycleStatus.IN_PROGRESS,  # re-generation
    ],
    ContentLifecycleStatus.PENDING_REVIEW: [
        ContentLifecycleStatus.APPROVED,
        ContentLifecycleStatus.REJECTED,
        ContentLifecycleStatus.IN_PROGRESS,  # re-generation
    ],
    ContentLifecycleStatus.APPROVED: [
        ContentLifecycleStatus.SCHEDULED,
        ContentLifecycleStatus.PUBLISHING,
        ContentLifecycleStatus.ARCHIVED,
    ],
    ContentLifecycleStatus.REJECTED: [
        ContentLifecycleStatus.TODO,
        ContentLifecycleStatus.IN_PROGRESS,
        ContentLifecycleStatus.ARCHIVED,
    ],
    ContentLifecycleStatus.SCHEDULED: [
        ContentLifecycleStatus.PUBLISHING,
        ContentLifecycleStatus.APPROVED,
    ],
    ContentLifecycleStatus.PUBLISHING: [
        ContentLifecycleStatus.PUBLISHED,
        ContentLifecycleStatus.FAILED,
    ],
    ContentLifecycleStatus.PUBLISHED: [
        ContentLifecycleStatus.ARCHIVED,
    ],
    ContentLifecycleStatus.FAILED: [
        ContentLifecycleStatus.TODO,
        ContentLifecycleStatus.IN_PROGRESS,
        ContentLifecycleStatus.ARCHIVED,
    ],
    ContentLifecycleStatus.ARCHIVED: [
        ContentLifecycleStatus.TODO,
    ],
}


class ContentRecord(BaseModel):
    """
    Unified content record tracking a piece of content through its lifecycle.
    Evolves from ContentItem with additional review and sync fields.
    """
    id: str = Field(..., description="Unique content identifier")
    title: str = Field(..., description="Content title")
    content_type: ContentType = Field(..., description="Type of content")
    source_robot: SourceRobot = Field(..., description="Robot that created this content")
    status: ContentLifecycleStatus = Field(
        default=ContentLifecycleStatus.TODO,
        description="Current lifecycle status",
    )
    project_id: Optional[str] = Field(None, description="Associated project ID")
    user_id: Optional[str] = Field(None, description="Owner user ID from Clerk auth")
    content_path: Optional[str] = Field(None, description="File system path to content")
    content_preview: Optional[str] = Field(None, description="Short preview of the content (first ~500 chars)")
    content_hash: Optional[str] = Field(None, description="SHA-256 hash of content for deduplication")
    priority: int = Field(default=3, ge=1, le=5, description="Priority (1=lowest, 5=highest)")
    tags: List[str] = Field(default_factory=list, description="Content tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    target_url: Optional[str] = Field(None, description="Target URL after publishing")
    reviewer_note: Optional[str] = Field(None, description="Note from the reviewer")
    reviewed_by: Optional[str] = Field(None, description="Who reviewed this content")
    current_version: int = Field(default=0, description="Current content body version")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled publish time")
    published_at: Optional[datetime] = Field(None, description="Actual publish time")
    synced_at: Optional[datetime] = Field(None, description="Last sync to Turso timestamp")

    @validator("priority")
    def validate_priority(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("Priority must be between 1 and 5")
        return v

    class Config:
        use_enum_values = True


class StatusChange(BaseModel):
    """Audit trail entry for a status transition."""
    id: str = Field(..., description="Unique change identifier")
    content_id: str = Field(..., description="Content record ID")
    from_status: ContentLifecycleStatus = Field(..., description="Previous status")
    to_status: ContentLifecycleStatus = Field(..., description="New status")
    changed_by: str = Field(..., description="Who triggered the change (robot name or user)")
    reason: Optional[str] = Field(None, description="Reason for the transition")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the change occurred")

    class Config:
        use_enum_values = True


class WorkDomainRecord(BaseModel):
    """Tracks the state of a work domain (SEO, Newsletter, etc.) for a project."""
    id: str = Field(..., description="Unique record identifier")
    project_id: str = Field(..., description="Associated project ID")
    domain: str = Field(..., description="Work domain name (seo, newsletter, images, scheduler)")
    status: str = Field(default="idle", description="Domain status (idle, running, paused, error)")
    last_run_at: Optional[datetime] = Field(None, description="Last execution timestamp")
    last_run_status: Optional[str] = Field(None, description="Last execution result")
    items_pending: int = Field(default=0, description="Items waiting to be processed")
    items_completed: int = Field(default=0, description="Items completed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional domain metadata")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        use_enum_values = True
