"""Pydantic models for Image Robot API endpoints"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Literal
from datetime import datetime


# ─────────────────────────────────────────────────
# Request Models
# ─────────────────────────────────────────────────

class GenerateImagesRequest(BaseModel):
    """Request to generate images for an article"""
    project_id: Optional[str] = Field(
        default=None,
        description="Optional project ID for project-scoped history and settings"
    )
    article_content: str = Field(
        ...,
        min_length=100,
        description="Markdown content of the article",
        examples=["# My Article\n\nThis is the content..."]
    )
    article_title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Title of the article",
        examples=["Getting Started with AI Agents"]
    )
    article_slug: str = Field(
        ...,
        min_length=3,
        max_length=200,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL slug for the article",
        examples=["getting-started-ai-agents"]
    )
    strategy_type: Literal["minimal", "standard", "hero+sections", "rich"] = Field(
        default="standard",
        description="Image strategy type: minimal (hero only), standard (hero + OG), hero+sections (hero + section images), rich (all types)"
    )
    style_guide: str = Field(
        default="brand_primary",
        description="Style guide to use for branding consistency"
    )
    generate_responsive: bool = Field(
        default=True,
        description="Whether to generate responsive image variants"
    )
    path_type: Literal["articles", "newsletter", "social", "thumbnails"] = Field(
        default="articles",
        description="CDN path type for organizing images"
    )


class UploadImageRequest(BaseModel):
    """Request to upload a single image to CDN"""
    source_url: HttpUrl = Field(
        ...,
        description="URL of the source image to upload"
    )
    file_name: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="SEO-friendly filename for the image"
    )
    alt_text: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Alt text for accessibility and SEO"
    )
    image_type: Literal["hero", "section", "thumbnail", "og"] = Field(
        default="hero",
        description="Type of image being uploaded"
    )
    path_type: Literal["articles", "newsletter", "social", "thumbnails"] = Field(
        default="articles",
        description="CDN path type for organizing images"
    )


class ImageProfileData(BaseModel):
    """Image generation profile configuration"""
    profile_id: str = Field(
        ...,
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="Unique profile identifier"
    )
    name: str = Field(..., min_length=2, max_length=120, description="Display name")
    description: str = Field(default="", max_length=300, description="Profile description")
    image_type: Literal["hero_image", "section_image", "og_card", "thumbnail"] = Field(
        ...,
        description="Generated image type"
    )
    image_provider: Literal["robolly", "openai"] = Field(
        default="robolly",
        description="Image generation provider"
    )
    style_guide: str = Field(
        default="brand_primary",
        description="Default style guide for this profile"
    )
    path_type: Literal["articles", "newsletter", "social", "thumbnails"] = Field(
        default="articles",
        description="Default CDN path for generated images"
    )
    template_id: Optional[str] = Field(
        default=None,
        max_length=120,
        description="Optional explicit Robolly template ID override"
    )
    default_alt_text: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Default alt text prefix for images generated with this profile"
    )
    base_prompt: Optional[str] = Field(
        default=None,
        max_length=1200,
        description="Base visual prompt used by AI providers"
    )
    tags: List[str] = Field(default_factory=list, description="Profile tags")
    is_system: bool = Field(default=False, description="Whether profile is built-in")


class CreateImageProfileRequest(BaseModel):
    """Request to create/update a custom image profile"""
    profile_id: str = Field(
        ...,
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="Custom profile ID"
    )
    name: str = Field(..., min_length=2, max_length=120, description="Display name")
    description: str = Field(default="", max_length=300, description="Profile description")
    image_type: Literal["hero_image", "section_image", "og_card", "thumbnail"] = Field(
        ...,
        description="Generated image type"
    )
    image_provider: Literal["robolly", "openai"] = Field(
        default="robolly",
        description="Image generation provider"
    )
    style_guide: str = Field(
        default="brand_primary",
        description="Default style guide for this profile"
    )
    path_type: Literal["articles", "newsletter", "social", "thumbnails"] = Field(
        default="articles",
        description="Default CDN path for generated images"
    )
    template_id: Optional[str] = Field(
        default=None,
        max_length=120,
        description="Optional explicit Robolly template ID override"
    )
    default_alt_text: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Default alt text prefix"
    )
    base_prompt: Optional[str] = Field(
        default=None,
        max_length=1200,
        description="Base visual prompt for AI providers"
    )
    tags: List[str] = Field(default_factory=list, description="Custom tags")


class ListImageProfilesResponse(BaseModel):
    """Response with all available image generation profiles"""
    items: List[ImageProfileData] = Field(default_factory=list, description="Available profiles")
    total_count: int = Field(default=0, description="Total profiles count")


class GenerateImageFromProfileRequest(BaseModel):
    """Generate one image on the fly using a saved profile"""
    project_id: str = Field(
        ...,
        min_length=2,
        max_length=120,
        description="Project ID used to scope profile storage"
    )
    profile_id: str = Field(
        ...,
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="Profile ID to use for generation"
    )
    title_text: str = Field(
        ...,
        min_length=2,
        max_length=160,
        description="Primary title/overlay text"
    )
    subtitle_text: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional secondary text"
    )
    file_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=200,
        description="Optional filename override (without path)"
    )
    alt_text: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional alt text override"
    )
    custom_prompt: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional explicit prompt (AI providers only)"
    )
    provider_override: Optional[Literal["robolly", "openai"]] = Field(
        default=None,
        description="Optional provider override for this generation"
    )
    style_guide_override: Optional[str] = Field(
        default=None,
        description="Optional style guide override"
    )
    path_type_override: Optional[Literal["articles", "newsletter", "social", "thumbnails"]] = Field(
        default=None,
        description="Optional CDN path override"
    )
    template_id_override: Optional[str] = Field(
        default=None,
        max_length=120,
        description="Optional Robolly template ID override"
    )


class GenerateImageFromProfileResponse(BaseModel):
    """Response for on-demand profile-based generation"""
    success: bool = Field(..., description="Whether generation succeeded")
    profile: Optional[ImageProfileData] = Field(default=None, description="Resolved generation profile")
    image_type: Optional[str] = Field(default=None, description="Generated image type")
    source_image_url: Optional[str] = Field(default=None, description="Raw generated image URL")
    cdn_url: Optional[str] = Field(default=None, description="Stored CDN original URL")
    primary_url: Optional[str] = Field(default=None, description="Primary optimized URL")
    responsive_urls: Dict[str, str] = Field(
        default_factory=dict,
        description="Responsive URLs from Bunny optimizer"
    )
    render_id: Optional[str] = Field(default=None, description="Robolly render ID")
    file_name: Optional[str] = Field(default=None, description="Stored file name")
    alt_text: Optional[str] = Field(default=None, description="Resolved alt text")
    provider_used: Optional[str] = Field(default=None, description="Provider used for generation")
    prompt_used: Optional[str] = Field(default=None, description="Resolved prompt for AI generation")
    style_guide_used: Optional[str] = Field(default=None, description="Final style guide")
    path_type_used: Optional[str] = Field(default=None, description="Final CDN path")
    storage_path: Optional[str] = Field(default=None, description="Path in storage zone")
    generation_time_ms: Optional[int] = Field(default=None, description="Image generation time")
    upload_time_ms: Optional[int] = Field(default=None, description="Upload + optimizer prep time")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class VerifyOptimizerRequest(BaseModel):
    """Request to verify Bunny Optimizer status"""
    test_url: Optional[str] = Field(
        default=None,
        description="Optional URL to test optimizer transformation"
    )


# ─────────────────────────────────────────────────
# Response Models
# ─────────────────────────────────────────────────

class GeneratedImageResponse(BaseModel):
    """Response for a single generated image"""
    success: bool = Field(..., description="Whether image generation succeeded")
    image_type: str = Field(..., description="Type of image (hero, section, og, etc.)")
    primary_url: Optional[str] = Field(None, description="Primary CDN URL")
    responsive_urls: Dict[str, str] = Field(
        default_factory=dict,
        description="Responsive variant URLs keyed by width"
    )
    alt_text: str = Field(default="", description="Generated alt text")
    file_name: str = Field(default="", description="SEO-friendly filename")
    file_size_kb: Optional[float] = Field(None, description="File size in KB")
    error: Optional[str] = Field(None, description="Error message if failed")


class GenerateImagesResponse(BaseModel):
    """Response from image generation endpoint"""
    success: bool = Field(..., description="Overall success status")
    total_images: int = Field(default=0, description="Total images attempted")
    successful_images: int = Field(default=0, description="Successfully generated images")
    failed_images: int = Field(default=0, description="Failed image generations")
    images: List[GeneratedImageResponse] = Field(
        default_factory=list,
        description="Individual image results"
    )
    markdown_with_images: str = Field(
        default="",
        description="Article markdown with images inserted"
    )
    og_image_url: Optional[str] = Field(
        None,
        description="OG image URL for social sharing"
    )
    total_cdn_size_kb: float = Field(
        default=0,
        description="Total CDN storage used in KB"
    )
    processing_time_ms: int = Field(
        default=0,
        description="Total processing time in milliseconds"
    )
    strategy_used: str = Field(
        default="standard",
        description="Strategy type that was used"
    )


class UploadImageResponse(BaseModel):
    """Response from single image upload"""
    success: bool = Field(..., description="Whether upload succeeded")
    cdn_url: Optional[str] = Field(None, description="CDN URL of uploaded image")
    optimizer_url: Optional[str] = Field(
        None,
        description="Bunny Optimizer URL with transformation params"
    )
    responsive_urls: Dict[str, str] = Field(
        default_factory=dict,
        description="Responsive variant URLs"
    )
    file_size_kb: Optional[float] = Field(None, description="File size in KB")
    content_type: Optional[str] = Field(None, description="MIME content type")
    storage_path: Optional[str] = Field(None, description="Path in CDN storage")
    error: Optional[str] = Field(None, description="Error message if failed")


class OptimizerStatusResponse(BaseModel):
    """Response from optimizer status check"""
    enabled: bool = Field(..., description="Whether optimizer is enabled in config")
    config_enabled: bool = Field(
        ...,
        description="Whether optimizer is enabled in Bunny dashboard"
    )
    verified: Optional[bool] = Field(
        None,
        description="Whether optimizer transformation was verified"
    )
    hostname: Optional[str] = Field(None, description="CDN hostname")
    test_url: Optional[str] = Field(
        None,
        description="Test URL used for verification"
    )
    transformed_url: Optional[str] = Field(
        None,
        description="Transformed URL from test"
    )
    message: str = Field(..., description="Human-readable status message")
    supported_formats: List[str] = Field(
        default_factory=lambda: ["webp", "avif", "jpeg", "png"],
        description="Supported output formats"
    )
    default_quality: int = Field(default=85, description="Default quality setting")


class ImageRobotHistoryItem(BaseModel):
    """Single item in image generation history"""
    workflow_id: str
    timestamp: str
    article_title: str
    article_slug: str
    total_images: int
    successful_images: int
    failed_images: int
    processing_time_ms: int
    cdn_urls_count: int
    total_cdn_size_kb: float


class ImageRobotHistoryResponse(BaseModel):
    """Response containing generation history"""
    items: List[ImageRobotHistoryItem] = Field(
        default_factory=list,
        description="Recent generation history"
    )
    total_count: int = Field(default=0, description="Total history items")
