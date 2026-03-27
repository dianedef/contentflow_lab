"""
Pydantic schemas for Internal Linking Specialist

Comprehensive validation schemas for internal linking data structures,
API requests/responses, and configuration management.
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class LinkType(str, Enum):
    """Types of internal links."""
    PILLAR_TO_CLUSTER = "pillar_to_cluster"
    CLUSTER_TO_PILLAR = "cluster_to_pillar"
    CONVERSION = "conversion"
    PERSONALIZED = "personalized"
    FUNNEL_TRANSITION = "funnel_transition"
    HYBRID_OBJECTIVE = "hybrid_objective"


class ConversionObjective(str, Enum):
    """Business conversion objectives."""
    LEAD_GENERATION = "lead_generation"
    DEMO_REQUEST = "demo_request"
    TRIAL_SIGNUP = "trial_signup"
    PURCHASE = "purchase"
    CONSULTATION = "consultation"
    WEBINAR_REGISTRATION = "webinar_registration"


class FunnelStage(str, Enum):
    """Marketing funnel stages."""
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    DECISION = "decision"
    RETENTION = "retention"
    ADVOCACY = "advocacy"


# Core Data Models
class InternalLink(BaseModel):
    """Individual internal link recommendation."""
    source_url: str = Field(..., description="Source page URL")
    target_url: str = Field(..., description="Target page URL")
    anchor_text: str = Field(..., min_length=2, max_length=200, description="Optimized anchor text")
    link_type: LinkType = Field(..., description="Type of internal link")
    seo_value: float = Field(..., ge=0.0, le=10.0, description="SEO value score 0-10")
    conversion_value: float = Field(..., ge=0.0, le=10.0, description="Conversion value score 0-10")
    conversion_objective: Optional[ConversionObjective] = Field(None, description="Primary conversion goal")
    personalization_rules: Optional[List[Dict[str, Any]]] = Field(None, description="Personalization conditions")
    priority_score: float = Field(..., ge=0.0, le=100.0, description="Overall priority score")
    implementation_effort: Literal["low", "medium", "high"] = Field(..., description="Implementation effort")
    is_new_opportunity: bool = Field(..., description="True for new links, False for existing optimization")
    
    class Config:
        use_enum_values = True


class LinkingStrategy(BaseModel):
    """Complete internal linking strategy."""
    strategy_id: str = Field(..., description="Unique strategy identifier")
    created_at: datetime = Field(default_factory=datetime.now)
    business_goals: List[str] = Field(..., min_items=1, description="Business objectives")
    conversion_objectives: List[ConversionObjective] = Field(..., min_items=1, description="Conversion goals")
    
    # 50/50 Split
    new_opportunities: List[InternalLink] = Field(..., description="New link opportunities (50%)")
    existing_optimizations: List[InternalLink] = Field(..., description="Existing link optimizations (50%)")
    
    # Conversion Focus (70% weight)
    conversion_focus_weight: float = Field(0.7, ge=0.3, le=0.9, description="Conversion vs SEO focus")
    
    # Personalization
    personalization_enabled: bool = Field(True, description="Enable personalization")
    personalization_rules: List[Dict[str, Any]] = Field(default_factory=list, description="Personalization rules")
    
    # Business Integration
    business_objective_links: Dict[str, List[InternalLink]] = Field(..., description="Links by business objective")
    
    # Metrics
    balance_score: float = Field(..., ge=0.0, le=100.0, description="New vs existing balance score")
    personalization_score: float = Field(..., ge=0.0, le=100.0, description="Personalization maturity score")
    
    @validator('new_opportunities', 'existing_optimizations')
    def validate_opportunities_list(cls, v):
        """Validate opportunities lists are not excessively long."""
        if len(v) > 1000:
            raise ValueError("Too many opportunities (max 1000)")
        return v
    
    class Config:
        use_enum_values = True


class UserProfile(BaseModel):
    """Progressive user profile for personalization."""
    user_id: str = Field(..., description="Unique user identifier")
    
    # Demographics
    demographics: Dict[str, Any] = Field(default_factory=dict, description="Demographic information")
    
    # Business Context
    business_context: Optional[Dict[str, Any]] = Field(None, description="Business context")
    
    # Progressive Profiling
    profile_maturity: float = Field(default=0.0, ge=0.0, le=1.0, description="Profile completeness")
    
    # Behavioral
    pages_viewed: List[str] = Field(default_factory=list, description="Pages viewed in session")
    links_clicked: List[str] = Field(default_factory=list, description="Links clicked")
    
    # Inferred Business Objectives
    inferred_objectives: List[str] = Field(default_factory=list, description="Inferred business objectives")
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


class LinkInsertionReport(BaseModel):
    """Comprehensive report from automated link insertion."""
    report_id: str = Field(..., description="Unique report identifier")
    generated_at: datetime = Field(default_factory=datetime.now)
    insertion_mode: Literal["preview", "apply", "report"] = Field(..., description="Operation mode")
    
    # Results
    files_processed: int = Field(..., ge=0, description="Number of files processed")
    links_inserted: int = Field(..., ge=0, description="Total links inserted")
    new_links_added: int = Field(..., ge=0, description="New opportunity links added")
    existing_links_optimized: int = Field(..., ge=0, description="Existing links optimized")
    
    # Validation
    balance_achieved: float = Field(..., ge=0.0, le=100.0, description="50/50 balance achievement")
    conversion_focus_achieved: float = Field(..., ge=0.0, le=1.0, description="70% conversion focus achieved")
    quality_score: float = Field(..., ge=0.0, le=100.0, description="Overall insertion quality score")
    
    # Impact Analysis
    seo_impact_score: float = Field(..., ge=0.0, le=100.0, description="SEO impact score")
    conversion_impact_score: float = Field(..., ge=0.0, le=100.0, description="Conversion impact score")
    personalization_coverage: float = Field(..., ge=0.0, le=100.0, description="Personalization coverage")
    
    # Issues and Recommendations
    issues_found: List[Dict[str, Any]] = Field(default_factory=list, description="Issues found")
    recommendations: List[str] = Field(default_factory=list, description="Further optimization suggestions")
    
    class Config:
        use_enum_values = True


class ConversionPath(BaseModel):
    """Conversion path through funnel stages."""
    path_name: str = Field(..., description="Path identifier")
    stages: List[FunnelStage] = Field(..., min_items=1, description="Funnel stages in path")
    primary_links: List[InternalLink] = Field(default_factory=list, description="Primary conversion links")
    supporting_links: List[InternalLink] = Field(default_factory=list, description="Supporting links")
    conversion_points: List[Dict[str, Any]] = Field(default_factory=list, description="Conversion touchpoints")
    effectiveness_score: float = Field(..., ge=0.0, le=1.0, description="Path effectiveness")
    
    class Config:
        use_enum_values = True


class FunnelIntegration(BaseModel):
    """Marketing funnel integration for internal linking."""
    stage_mapping: Dict[str, List[Dict[str, Any]]] = Field(..., description="Content mapped to funnel stages")
    transition_links: List[Dict[str, Any]] = Field(..., description="Stage transition links")
    touchpoint_map: Dict[str, Any] = Field(..., description="Conversion touchpoints")
    funnel_effectiveness: float = Field(..., ge=0.0, le=100.0, description="Funnel effectiveness score")
    
    class Config:
        use_enum_values = True


class PersonalizationStrategy(BaseModel):
    """Personalization strategy configuration."""
    personalization_level: Literal["basic", "intermediate", "advanced", "full"] = Field(
        ..., description="Personalization maturity level"
    )
    profile_structure: Dict[str, Any] = Field(..., description="User profile structure")
    data_collection: Dict[str, Any] = Field(..., description="Data collection strategy")
    profile_enrichment: Dict[str, Any] = Field(..., description="Profile enrichment rules")
    real_time_personalization: Dict[str, Any] = Field(..., description="Real-time personalization rules")
    progressive_profiling_triggers: List[Dict[str, Any]] = Field(..., description="Profiling triggers")
    
    class Config:
        use_enum_values = True


# API Request/Response Models
class LinkingStrategyRequest(BaseModel):
    """Request for internal linking strategy analysis."""
    content_inventory: List[Dict[str, Any]] = Field(..., description="Content inventory with metadata")
    business_goals: List[str] = Field(..., min_items=1, description="Business objectives")
    conversion_objectives: List[str] = Field(..., min_items=1, description="Conversion objectives")
    target_audience: str = Field(..., description="Target audience description")
    scope: Literal["new_content_only", "include_existing", "full_site"] = Field(
        ..., description="Analysis scope"
    )
    personalization_level: Literal["basic", "intermediate", "advanced", "full"] = Field(
        "intermediate", description="Personalization level"
    )
    conversion_focus: float = Field(0.7, ge=0.3, le=0.9, description="Conversion vs SEO focus (0.3-0.9)")
    existing_links_data: Optional[List[Dict[str, Any]]] = Field(None, description="Existing internal links data")
    
    @validator('content_inventory')
    def validate_content_inventory(cls, v):
        """Validate content inventory has required fields."""
        if not v:
            raise ValueError("Content inventory cannot be empty")
        return v
    
    class Config:
        use_enum_values = True


class LinkingStrategyResponse(BaseModel):
    """Response with comprehensive linking strategy."""
    strategy: Dict[str, Any] = Field(..., description="Complete linking strategy")
    analysis_metadata: Dict[str, Any] = Field(..., description="Analysis metadata")
    
    class Config:
        use_enum_values = True


class PersonalizationRequest(BaseModel):
    """Request for personalized linking."""
    base_strategy: Dict[str, Any] = Field(..., description="Base linking strategy")
    user_context: Dict[str, Any] = Field(..., description="User context and profile")
    behavioral_signals: List[Dict[str, Any]] = Field(..., description="User behavioral data")
    session_data: Optional[Dict[str, Any]] = Field(None, description="Session-specific data")
    
    class Config:
        use_enum_values = True


class PersonalizationResponse(BaseModel):
    """Response with personalized linking recommendations."""
    personalized_links: List[Dict[str, Any]] = Field(..., description="Personalized link recommendations")
    user_profile: Dict[str, Any] = Field(..., description="Enhanced user profile")
    next_actions: List[str] = Field(..., description="Recommended next actions")
    
    class Config:
        use_enum_values = True


class AutomatedInsertionRequest(BaseModel):
    """Request for automated link insertion."""
    linking_strategy: Dict[str, Any] = Field(..., description="Complete linking strategy")
    content_files: List[str] = Field(..., min_items=1, description="Content file paths")
    insertion_mode: Literal["preview", "apply", "report"] = Field("preview", description="Operation mode")
    validation_level: Literal["strict", "moderate", "lenient"] = Field(
        "moderate", description="Validation strictness"
    )
    
    @validator('content_files')
    def validate_content_files(cls, v):
        """Validate content files list."""
        if not v:
            raise ValueError("Content files list cannot be empty")
        return v
    
    class Config:
        use_enum_values = True


class AutomatedInsertionResponse(BaseModel):
    """Response from automated link insertion."""
    insertion_report: Dict[str, Any] = Field(..., description="Comprehensive insertion report")
    validation_results: Dict[str, Any] = Field(..., description="Validation results")
    recommendations: List[str] = Field(..., description="Optimization recommendations")
    next_steps: List[str] = Field(..., description="Recommended next steps")
    
    class Config:
        use_enum_values = True


class LinkPerformanceRequest(BaseModel):
    """Request for link performance analysis."""
    links: List[Dict[str, Any]] = Field(..., description="Links to analyze")
    time_period: str = Field(..., description="Analysis time period")
    metrics: List[str] = Field(..., description="Metrics to track")
    
    class Config:
        use_enum_values = True


class LinkPerformanceResponse(BaseModel):
    """Response with link performance data."""
    performance_data: Dict[str, Any] = Field(..., description="Performance metrics")
    trends: Dict[str, Any] = Field(..., description="Performance trends")
    insights: List[str] = Field(..., description="Performance insights")
    optimization_opportunities: List[Dict[str, Any]] = Field(..., description="Opportunities for improvement")
    
    class Config:
        use_enum_values = True


# Configuration Schemas
class ConfigurationUpdate(BaseModel):
    """Update configuration settings."""
    scope: Optional[Literal["new_content_only", "include_existing", "full_site"]] = Field(
        None, description="Analysis scope"
    )
    personalization_level: Optional[Literal["basic", "intermediate", "advanced", "full"]] = Field(
        None, description="Personalization level"
    )
    conversion_focus: Optional[float] = Field(None, ge=0.3, le=0.9, description="Conversion focus")
    business_objective_weights: Optional[Dict[str, float]] = Field(None, description="Business objective weights")
    auto_insert_links: Optional[bool] = Field(None, description="Enable auto-insertion")
    
    class Config:
        use_enum_values = True


class ConfigurationResponse(BaseModel):
    """Response with current configuration."""
    configuration: Dict[str, Any] = Field(..., description="Current configuration")
    available_templates: List[str] = Field(..., description="Available configuration templates")
    
    class Config:
        use_enum_values = True


# Health & Maintenance Schemas
class LinkHealthReport(BaseModel):
    """Link health audit report."""
    total_links: int = Field(..., ge=0, description="Total links analyzed")
    broken_links: int = Field(..., ge=0, description="Broken links count")
    outdated_anchors: int = Field(..., ge=0, description="Outdated anchor count")
    low_performance_links: int = Field(..., ge=0, description="Low-performing links")
    healthy_links: int = Field(..., ge=0, description="Healthy links count")
    overall_health_score: float = Field(..., ge=0.0, le=100.0, description="Overall health score")
    maintenance_needs: List[Dict[str, Any]] = Field(..., description="Required maintenance actions")
    
    class Config:
        use_enum_values = True


class MaintenanceStrategy(BaseModel):
    """Ongoing maintenance strategy."""
    maintenance_frequency: str = Field(..., description="How often to run maintenance")
    monitoring_metrics: List[str] = Field(..., description="Metrics to monitor")
    automated_tasks: List[str] = Field(..., description="Automated maintenance tasks")
    manual_review_triggers: List[str] = Field(..., description="When manual review is needed")
    
    class Config:
        use_enum_values = True


# Validation helpers
def validate_linking_strategy(data: Dict[str, Any]) -> LinkingStrategy:
    """Validate linking strategy data."""
    return LinkingStrategy(**data)


def validate_insertion_report(data: Dict[str, Any]) -> LinkInsertionReport:
    """Validate insertion report data."""
    return LinkInsertionReport(**data)


def validate_user_profile(data: Dict[str, Any]) -> UserProfile:
    """Validate user profile data."""
    return UserProfile(**data)
