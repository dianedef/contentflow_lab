"""Request/Response models for content template endpoints."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class GeneratePromptRequest(BaseModel):
    """Request to generate an AI prompt for a template section."""
    template_name: str = Field(..., description="Name of the parent template")
    content_type: str = Field(..., description="Content type (article, newsletter, video_script, seo_brief)")
    section_name: str = Field(..., description="Section identifier")
    section_label: str = Field(..., description="Human-readable section label")
    section_field_type: str = Field(..., description="Field type (text, markdown, list, number, url, tags)")
    section_description: Optional[str] = Field(None, description="Section description for context")
    other_sections: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Sibling sections for context: [{name, label, fieldType}]"
    )


class GeneratePromptResponse(BaseModel):
    """Response with AI-generated prompt."""
    prompt: str = Field(..., description="Generated prompt text")
    reasoning: str = Field(..., description="Why this prompt was generated")


class GenerateContentRequest(BaseModel):
    """Request to generate content using a template."""
    template: Dict[str, Any] = Field(..., description="Full template with sections")
    project_id: Optional[str] = Field(None, description="Associated project ID")
    user_inputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="User-provided values per section (skips AI for those)"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Generation context: topic, audience, tone, keywords, etc."
    )


class GenerateContentResponse(BaseModel):
    """Response with generated content sections."""
    sections: Dict[str, Any] = Field(..., description="Generated content per section name")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Generation metadata")
    content_record_id: Optional[str] = Field(None, description="ID of created content record")


class TemplateSectionData(BaseModel):
    """Section data within a default template."""
    name: str
    label: str
    field_type: str
    required: bool = True
    order: int
    description: Optional[str] = None
    placeholder: Optional[str] = None
    default_prompt: Optional[str] = None
    prompt_strategy: str = "auto_generate"


class DefaultTemplateData(BaseModel):
    """A default system template."""
    name: str
    slug: str
    content_type: str
    description: str
    sections: List[TemplateSectionData]
