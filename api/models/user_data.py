"""Models for authenticated user data endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SafeApiKeys(BaseModel):
    """Masked API keys returned to clients."""

    exa: str | None = None
    firecrawl: str | None = None
    serper: str | None = None
    openrouter: str | None = None
    bunnyStorage: str | None = None
    bunnyCdn: str | None = None
    bunnyCdnHostname: str | None = None
    consensus: str | None = None
    tavily: str | None = None
    groq: str | None = None


class DashboardLayout(BaseModel):
    defaultTab: str | None = None
    collapsedSections: list[str] = Field(default_factory=list)
    refreshInterval: int | None = None


class ContentFrequencyConfig(BaseModel):
    """How many content pieces the user wants generated per time period."""

    blog_posts_per_month: int = Field(default=0, ge=0, le=30)
    newsletters_per_week: int = Field(default=0, ge=0, le=7)
    shorts_per_day: int = Field(default=0, ge=0, le=10)
    social_posts_per_day: int = Field(default=0, ge=0, le=20)


class RobotSettings(BaseModel):
    autoRun: bool | None = None
    schedules: dict[str, str] = Field(default_factory=dict)
    notifications: dict[str, bool] = Field(default_factory=dict)
    contentFrequency: ContentFrequencyConfig | None = None
    ideaPoolEnabled: bool | None = None


class UserSettingsResponse(BaseModel):
    id: str
    userId: str
    theme: str
    language: str | None = None
    emailNotifications: bool
    webhookUrl: str | None = None
    apiKeys: SafeApiKeys | None = None
    defaultProjectId: str | None = None
    dashboardLayout: DashboardLayout | None = None
    robotSettings: RobotSettings | None = None
    createdAt: datetime
    updatedAt: datetime


class UserSettingsUpdateRequest(BaseModel):
    theme: str | None = None
    language: str | None = None
    emailNotifications: bool | None = None
    webhookUrl: str | None = None
    defaultProjectId: str | None = None
    dashboardLayout: dict[str, Any] | None = None
    robotSettings: dict[str, Any] | None = None


class CreatorProfileResponse(BaseModel):
    id: str
    userId: str
    projectId: str | None = None
    displayName: str | None = None
    voice: dict[str, Any] | None = None
    positioning: dict[str, Any] | None = None
    values: list[str] = Field(default_factory=list)
    currentChapterId: str | None = None
    createdAt: datetime
    updatedAt: datetime


class CreatorProfileUpdateRequest(BaseModel):
    projectId: str | None = None
    displayName: str | None = None
    voice: dict[str, Any] | None = None
    positioning: dict[str, Any] | None = None
    values: list[str] | None = None
    currentChapterId: str | None = None


class PersonaResponse(BaseModel):
    id: str
    userId: str
    projectId: str | None = None
    name: str
    avatar: str | None = None
    demographics: dict[str, Any] | None = None
    painPoints: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    language: dict[str, Any] | None = None
    contentPreferences: dict[str, Any] | None = None
    confidence: int = 50
    createdAt: datetime
    updatedAt: datetime


class PersonaCreateRequest(BaseModel):
    projectId: str | None = None
    name: str
    avatar: str | None = None
    demographics: dict[str, Any] | None = None
    painPoints: list[str] | None = None
    goals: list[str] | None = None
    language: dict[str, Any] | None = None
    contentPreferences: dict[str, Any] | None = None
    confidence: int | None = None


class PersonaUpdateRequest(BaseModel):
    name: str | None = None
    avatar: str | None = None
    demographics: dict[str, Any] | None = None
    painPoints: list[str] | None = None
    goals: list[str] | None = None
    language: dict[str, Any] | None = None
    contentPreferences: dict[str, Any] | None = None
    confidence: int | None = None
