"""Pydantic models for Topical Mesh endpoints"""

from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Literal


# ─────────────────────────────────────────────────
# Request Models
# ─────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """Request to analyze existing website mesh"""
    repo_url: HttpUrl = Field(
        ...,
        description="GitHub repository URL (e.g., https://github.com/user/repo)",
        examples=["https://github.com/example/marketing-site"]
    )
    local_repo_path: Optional[str] = Field(
        default=None,
        description="Absolute local path to an already-cloned repo. Skips git clone entirely."
    )
    include_visualization: bool = Field(
        default=True,
        description="Generate mesh visualization (PNG/Mermaid/JSON)"
    )
    clone_depth: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Git clone depth (1=latest commit, 10=full history)"
    )


class BuildMeshRequest(BaseModel):
    """Request to build new topical mesh from scratch"""
    main_topic: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Main pillar topic",
        examples=["Digital Marketing Strategies"]
    )
    subtopics: list[str] = Field(
        ...,
        min_length=2,
        max_length=20,
        description="Cluster topics (2-20 topics)",
        examples=[["SEO Basics", "Social Media", "Email Marketing"]]
    )
    business_goals: list[Literal["rank", "convert", "engage", "educate"]] = Field(
        default=["rank", "convert"],
        description="Business objectives"
    )
    target_pages: int = Field(
        default=10,
        ge=3,
        le=50,
        description="Target number of pages (3-50)"
    )
    target_authority: int = Field(
        default=85,
        ge=50,
        le=100,
        description="Target authority score (50-100)"
    )


class ImproveMeshRequest(BaseModel):
    """Request to improve existing mesh"""
    repo_url: HttpUrl = Field(
        ...,
        description="GitHub repository URL to improve"
    )
    new_topics: list[str] = Field(
        default=[],
        description="New topics to add"
    )
    competitor_topics: list[str] = Field(
        default=[],
        description="Topics found in competitor analysis"
    )
    target_authority: int = Field(
        default=85,
        ge=50,
        le=100,
        description="Target authority score"
    )


class CompareRequest(BaseModel):
    """Request to compare current vs ideal mesh"""
    repo_url: HttpUrl = Field(
        ...,
        description="Current website repository"
    )
    ideal_main_topic: str = Field(
        ...,
        description="Ideal pillar topic"
    )
    ideal_subtopics: list[str] = Field(
        ...,
        description="Ideal cluster topics"
    )


# ─────────────────────────────────────────────────
# Response Models
# ─────────────────────────────────────────────────

class PageInfo(BaseModel):
    """Information about a single page in the mesh"""
    id: str
    title: str
    authority: int = Field(ge=0, le=100)
    word_count: int = Field(ge=0)
    inbound_links: int = Field(ge=0)
    outbound_links: int = Field(ge=0)
    is_pillar: bool = False
    is_orphan: bool = False


class MeshIssue(BaseModel):
    """Detected issue in the mesh"""
    severity: Literal["high", "medium", "low"]
    category: Literal["orphan", "weak_pillar", "low_density", "missing_content"]
    description: str
    affected_pages: list[str]
    impact: str


class Recommendation(BaseModel):
    """Action recommendation with effort/impact"""
    priority: Literal["high", "medium", "low"]
    action: str
    description: str
    estimated_effort: str  # e.g., "30 minutes", "2 hours"
    estimated_impact: int = Field(ge=0, le=100, description="Authority points gain")
    affected_pages: list[str]


class AnalyzeResponse(BaseModel):
    """Response from mesh analysis"""
    authority_score: int = Field(ge=0, le=100)
    grade: Literal["A", "B", "C", "D", "F"]
    total_pages: int = Field(ge=0)
    total_links: int = Field(ge=0)
    mesh_density: float = Field(ge=0, le=1)
    
    pillar: Optional[PageInfo] = None
    clusters: list[PageInfo] = []
    orphans: list[PageInfo] = []
    
    issues: list[MeshIssue] = []
    recommendations: list[Recommendation] = []
    
    visualization_url: Optional[str] = None
    mermaid_diagram: Optional[str] = None
    
    analysis_timestamp: str
    processing_time_seconds: float


class BuildMeshResponse(BaseModel):
    """Response from building new mesh"""
    mesh_id: str
    main_topic: str
    authority_score: int = Field(ge=0, le=100)
    grade: Literal["A", "B", "C", "D", "F"]
    
    pillar: PageInfo
    clusters: list[PageInfo]
    
    total_pages: int
    total_links: int
    mesh_density: float
    
    linking_strategy: dict
    visualization_url: Optional[str] = None
    mermaid_diagram: Optional[str] = None
    
    created_at: str


class ImprovementPhase(BaseModel):
    """Single phase in improvement plan"""
    phase_number: int
    name: str
    description: str
    actions: list[Recommendation]
    estimated_duration: str
    authority_gain: int
    cumulative_authority: int


class ImproveMeshResponse(BaseModel):
    """Response from improvement plan generation"""
    current_authority: int
    target_authority: int
    authority_gap: int
    
    quick_wins: list[Recommendation]
    phases: list[ImprovementPhase]
    
    total_estimated_time: str
    final_projection: int
    success_probability: float = Field(ge=0, le=1)


class CompareResponse(BaseModel):
    """Response from current vs ideal comparison"""
    current_mesh: AnalyzeResponse
    ideal_mesh: BuildMeshResponse
    
    authority_gap: int
    missing_topics: list[str]
    underperforming_pages: list[str]
    
    gap_analysis: dict
    recommendations: list[Recommendation]
