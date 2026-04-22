"""Models for async persona draft generation from repo understanding."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ExistingCreatorProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    display_name: str | None = None
    voice: dict[str, Any] | None = None
    positioning: dict[str, Any] | None = None
    values: list[str] = Field(default_factory=list)


class PersonaDraftRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("project_id", "projectId"),
        serialization_alias="projectId",
    )
    repo_source: Literal["project_repo", "connected_github", "manual_url"]
    repo_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("repo_url", "repoUrl"),
        serialization_alias="repoUrl",
    )
    manual_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("manual_url", "manualUrl"),
        serialization_alias="manualUrl",
    )
    mode: Literal["blank_form", "suggest_from_repo", "refresh_from_repo"] = "suggest_from_repo"
    existing_creator_profile: ExistingCreatorProfile | None = Field(
        default=None,
        validation_alias=AliasChoices("existing_creator_profile", "existingCreatorProfile"),
        serialization_alias="existingCreatorProfile",
    )


class EvidenceItem(BaseModel):
    source: str
    location: str | None = None
    snippet: str


class RepoUnderstandingResult(BaseModel):
    project_summary: str = ""
    target_audiences: list[str] = Field(default_factory=list)
    icp_hypotheses: list[str] = Field(default_factory=list)
    personal_story_signals: list[str] = Field(default_factory=list)
    positioning_hypotheses: list[str] = Field(default_factory=list)
    persona_candidates: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class PersonaDraftResult(BaseModel):
    persona_draft: dict[str, Any]
    repo_understanding: RepoUnderstandingResult
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: int = Field(default=50, ge=0, le=100)


class PersonaDraftJobResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str
    job_type: str = Field(default="personas.draft", serialization_alias="jobType")
    status: str
    progress: int = 0
    message: str | None = None
    user_id: str = Field(serialization_alias="userId")
    result: PersonaDraftResult | None = None
    error: str | None = None
    created_at: datetime | None = Field(default=None, serialization_alias="createdAt")
    updated_at: datetime | None = Field(default=None, serialization_alias="updatedAt")
