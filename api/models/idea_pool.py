"""Pydantic models for the Idea Pool — central staging area for content ideas."""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class IdeaSource(str, Enum):
    NEWSLETTER_INBOX = "newsletter_inbox"
    SEO_KEYWORDS = "seo_keywords"
    WEEKLY_RITUAL = "weekly_ritual"
    COMPETITOR_WATCH = "competitor_watch"
    MANUAL = "manual"


class IdeaStatus(str, Enum):
    RAW = "raw"
    ENRICHED = "enriched"
    USED = "used"
    DISMISSED = "dismissed"


class IdeaRecord(BaseModel):
    id: str
    source: str
    title: str
    raw_data: dict[str, Any] = Field(default_factory=dict)
    seo_signals: Optional[dict[str, Any]] = None
    trending_signals: Optional[dict[str, Any]] = None
    tags: list[str] = Field(default_factory=list)
    priority_score: Optional[float] = None
    status: str = "raw"
    project_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CreateIdeaRequest(BaseModel):
    source: str = Field(..., description="Source: newsletter_inbox, seo_keywords, weekly_ritual, competitor_watch, manual")
    title: str = Field(..., description="Idea title or topic")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Source-specific payload")
    seo_signals: Optional[dict[str, Any]] = Field(None, description="SEO keyword data")
    trending_signals: Optional[dict[str, Any]] = Field(None, description="Trending/recency signals")
    tags: list[str] = Field(default_factory=list)
    project_id: Optional[str] = None


class UpdateIdeaRequest(BaseModel):
    title: Optional[str] = None
    seo_signals: Optional[dict[str, Any]] = None
    trending_signals: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    priority_score: Optional[float] = None
    status: Optional[str] = None


class BulkIngestRequest(BaseModel):
    source: str = Field(..., description="Source type for all items")
    items: list[dict[str, Any]] = Field(..., description="List of idea dicts with at least 'title'")
    project_id: Optional[str] = None


class IdeaListResponse(BaseModel):
    items: list[IdeaRecord]
    total: int
