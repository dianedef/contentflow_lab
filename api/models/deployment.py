"""Pydantic models for SEO deployment endpoints"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ScheduleType(str, Enum):
    """Schedule frequency types"""
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class DeploymentRunRequest(BaseModel):
    """Request model for single topic deployment"""
    topic: str = Field(..., description="Topic to generate content for")
    dry_run: bool = Field(default=False, description="Preview without executing changes")
    no_deploy: bool = Field(default=False, description="Generate content but skip deployment")
    target_repo: Optional[str] = Field(default=None, description="Target repository URL")


class BatchRunRequest(BaseModel):
    """Request model for batch deployment"""
    topics: List[str] = Field(..., min_length=1, description="List of topics to process")
    delay_seconds: int = Field(default=60, ge=30, le=600, description="Delay between topics")
    auto_deploy: bool = Field(default=True, description="Auto-deploy after generation")


class ScheduleRequest(BaseModel):
    """Request model for creating/updating schedules"""
    schedule_type: ScheduleType = Field(..., description="Schedule frequency type")
    cron_expression: Optional[str] = Field(default=None, description="Custom cron expression")
    topics: List[str] = Field(..., min_length=1, description="Topics to process on schedule")
    enabled: bool = Field(default=True, description="Whether schedule is active")


class StepStatus(BaseModel):
    """Status of a pipeline step"""
    name: str
    status: str = Field(..., description="pending, running, completed, error")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


class BatchProgress(BaseModel):
    """Progress information for batch processing"""
    completed: int = 0
    total: int = 0
    current_topic: Optional[str] = None


class DeploymentStatus(BaseModel):
    """Current deployment status"""
    running: bool = False
    job_id: Optional[str] = None
    job_type: Optional[str] = Field(default=None, description="single or batch")
    topic: Optional[str] = None
    current_step: Optional[str] = None
    progress: int = Field(default=0, ge=0, le=100)
    steps: List[StepStatus] = Field(default_factory=list)
    batch_progress: Optional[BatchProgress] = None
    error: Optional[str] = None


class LogEntry(BaseModel):
    """Log entry from deployment"""
    timestamp: datetime
    level: str = Field(..., description="info, warning, error")
    step: Optional[str] = None
    message: str


class Schedule(BaseModel):
    """Deployment schedule configuration"""
    id: str
    schedule_type: ScheduleType
    cron_expression: str
    topics: List[str]
    enabled: bool = True
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None


class DeploymentRunResponse(BaseModel):
    """Response for single run request"""
    job_id: str
    status: str
    topic: str


class BatchRunResponse(BaseModel):
    """Response for batch run request"""
    batch_id: str
    total_topics: int
    status: str


class StopResponse(BaseModel):
    """Response for stop request"""
    status: str


class DeleteResponse(BaseModel):
    """Response for delete request"""
    status: str
