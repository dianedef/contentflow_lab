"""
Publishing and Calendar Management Schemas
Pydantic models for content scheduling and deployment
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ContentType(str, Enum):
    """Content type enumeration"""
    ARTICLE = "article"
    NEWSLETTER = "newsletter"
    SEO_CONTENT = "seo-content"
    IMAGE = "image"
    MANUAL = "manual"
    VIDEO_SCRIPT = "video_script"
    SHORT = "short"
    SOCIAL_POST = "social_post"


class SourceRobot(str, Enum):
    """Source robot enumeration"""
    SEO = "seo"
    NEWSLETTER = "newsletter"
    ARTICLE = "article"
    IMAGES = "images"
    MANUAL = "manual"
    SHORT = "short"
    SOCIAL = "social"


class PublishingStatus(str, Enum):
    """Publishing status enumeration"""
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ContentItem(BaseModel):
    """
    Represents a single content item in the publishing queue
    """
    id: str = Field(..., description="Unique content identifier")
    title: str = Field(..., description="Content title")
    content_path: str = Field(..., description="File system path to content")
    content_type: ContentType = Field(..., description="Type of content")
    priority: int = Field(default=3, ge=1, le=5, description="Priority (1=lowest, 5=highest)")
    source_robot: SourceRobot = Field(..., description="Robot that created this content")
    status: PublishingStatus = Field(default=PublishingStatus.QUEUED, description="Current status")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled publish time")
    published_at: Optional[datetime] = Field(None, description="Actual publish time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: List[str] = Field(default_factory=list, description="Content tags")
    target_url: Optional[str] = Field(None, description="Target URL after publishing")

    @validator('priority')
    def validate_priority(cls, v):
        if not 1 <= v <= 5:
            raise ValueError('Priority must be between 1 and 5')
        return v

    @validator('scheduled_for')
    def validate_schedule(cls, v, values):
        if v and 'created_at' in values and v < values['created_at']:
            raise ValueError('Scheduled time cannot be before creation time')
        return v

    class Config:
        use_enum_values = True


class SchedulingConflict(BaseModel):
    """Represents a scheduling conflict between content items"""
    conflict_id: str
    items: List[str] = Field(..., description="Conflicting content IDs")
    reason: str = Field(..., description="Reason for conflict")
    severity: str = Field(..., description="low, medium, high")
    resolution: Optional[str] = Field(None, description="Suggested resolution")


class OptimalTime(BaseModel):
    """Optimal publishing time recommendation"""
    content_id: str
    recommended_time: datetime
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    reasoning: str = Field(..., description="Why this time is optimal")
    alternative_times: List[datetime] = Field(default_factory=list)


class PublishingSchedule(BaseModel):
    """
    Complete publishing schedule with items, optimal times, and conflicts
    """
    schedule_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    items: List[ContentItem] = Field(..., description="All content items")
    optimal_times: List[OptimalTime] = Field(default_factory=list)
    conflicts: List[SchedulingConflict] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    calendar_view: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Date -> Content IDs mapping"
    )

    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('Schedule must contain at least one item')
        return v


class GoogleIndexingStatus(BaseModel):
    """Google Indexing API status"""
    url: str
    status: str = Field(..., description="pending, indexed, error")
    submitted_at: datetime
    indexed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class DeploymentResult(BaseModel):
    """
    Result of a content deployment operation
    """
    success: bool = Field(..., description="Whether deployment succeeded")
    deployment_id: str = Field(..., description="Unique deployment identifier")
    content_id: str = Field(..., description="Content item ID")
    commit_sha: Optional[str] = Field(None, description="Git commit SHA")
    published_at: datetime = Field(default_factory=datetime.now)
    urls: List[str] = Field(default_factory=list, description="Published URLs")
    indexing_status: List[GoogleIndexingStatus] = Field(
        default_factory=list,
        description="Google indexing status for each URL"
    )
    errors: List[str] = Field(default_factory=list, description="Error messages if any")
    rollback_available: bool = Field(default=False, description="Whether rollback is possible")
    deployment_time_seconds: Optional[float] = Field(None, description="Time taken to deploy")

    @validator('urls')
    def validate_urls(cls, v, values):
        if values.get('success') and not v:
            raise ValueError('Successful deployment must have at least one URL')
        return v


class CalendarEvent(BaseModel):
    """Calendar event for visualization"""
    event_id: str
    date: datetime
    title: str
    content_type: ContentType
    status: PublishingStatus
    priority: int = Field(ge=1, le=5)
    description: Optional[str] = None
    url: Optional[str] = None

    class Config:
        use_enum_values = True


class CalendarView(BaseModel):
    """Complete calendar view for a date range"""
    start_date: datetime
    end_date: datetime
    events: List[CalendarEvent]
    statistics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Calendar statistics (counts, trends, etc.)"
    )
