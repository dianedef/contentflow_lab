"""
Technical Analysis Schemas
Pydantic models for SEO and tech stack analysis
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class IssueSeverity(str, Enum):
    """Issue severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(str, Enum):
    """Technical SEO issue categories"""
    CRAWLABILITY = "crawlability"
    INDEXABILITY = "indexability"
    PERFORMANCE = "performance"
    MOBILE = "mobile"
    SCHEMA = "schema"
    INTERNAL_LINKING = "internal_linking"
    ACCESSIBILITY = "accessibility"
    SECURITY = "security"


class SEOIssue(BaseModel):
    """Individual SEO issue detected"""
    issue_id: str
    category: IssueCategory
    severity: IssueSeverity
    title: str = Field(..., description="Short issue description")
    description: str = Field(..., description="Detailed issue explanation")
    affected_urls: List[str] = Field(default_factory=list)
    recommendation: str = Field(..., description="How to fix")
    auto_fixable: bool = Field(default=False, description="Can be auto-fixed")
    detected_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class CoreWebVitals(BaseModel):
    """Core Web Vitals metrics"""
    lcp: float = Field(..., description="Largest Contentful Paint (seconds)")
    fid: float = Field(..., description="First Input Delay (milliseconds)")
    cls: float = Field(..., description="Cumulative Layout Shift")
    fcp: float = Field(..., description="First Contentful Paint (seconds)")
    ttfb: float = Field(..., description="Time to First Byte (seconds)")
    overall_rating: str = Field(..., description="good, needs-improvement, poor")

    @validator('lcp')
    def validate_lcp(cls, v):
        """LCP should be < 2.5s for good rating"""
        return v

    @validator('cls')
    def validate_cls(cls, v):
        """CLS should be < 0.1 for good rating"""
        return v


class SchemaValidation(BaseModel):
    """Schema.org validation results"""
    valid: bool
    schemas_found: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    coverage: float = Field(ge=0.0, le=100.0, description="Percentage of pages with schema")


class InternalLinkingMetrics(BaseModel):
    """Internal linking structure metrics"""
    total_links: int
    orphan_pages: int = Field(default=0, description="Pages with no internal links")
    broken_links: int = Field(default=0, description="404 internal links")
    redirect_chains: int = Field(default=0, description="Links through redirects")
    average_depth: float = Field(description="Average click depth from homepage")
    link_graph_density: float = Field(ge=0.0, le=1.0, description="Graph connectivity")


class TechnicalSEOScore(BaseModel):
    """
    Comprehensive technical SEO analysis results
    """
    analysis_id: str
    analyzed_at: datetime = Field(default_factory=datetime.now)
    overall_score: float = Field(ge=0.0, le=100.0, description="Overall SEO score")

    # Component scores
    page_speed_score: float = Field(ge=0.0, le=100.0)
    schema_validity_score: float = Field(ge=0.0, le=100.0)
    internal_linking_score: float = Field(ge=0.0, le=100.0)
    mobile_friendly_score: float = Field(ge=0.0, le=100.0)
    accessibility_score: float = Field(ge=0.0, le=100.0)

    # Detailed metrics
    core_web_vitals: CoreWebVitals
    schema_validation: SchemaValidation
    internal_linking: InternalLinkingMetrics

    # Issues and recommendations
    issues: List[SEOIssue] = Field(default_factory=list)
    critical_issues: int = Field(default=0, description="Count of critical issues")
    recommendations: List[str] = Field(default_factory=list)

    # Additional data
    pages_crawled: int = Field(ge=0)
    crawl_errors: List[str] = Field(default_factory=list)
    mobile_friendly: bool = Field(default=True)
    https_enabled: bool = Field(default=True)
    sitemap_valid: bool = Field(default=True)
    robots_txt_valid: bool = Field(default=True)

    @validator('overall_score', always=True)
    def calculate_overall_score(cls, v, values):
        """Calculate weighted overall score"""
        if v is not None:
            return v

        scores = [
            values.get('page_speed_score', 0) * 0.25,
            values.get('schema_validity_score', 0) * 0.15,
            values.get('internal_linking_score', 0) * 0.20,
            values.get('mobile_friendly_score', 0) * 0.20,
            values.get('accessibility_score', 0) * 0.20,
        ]
        return sum(scores)


class Vulnerability(BaseModel):
    """Security vulnerability in dependencies"""
    vuln_id: str
    package_name: str
    installed_version: str
    patched_version: Optional[str]
    severity: IssueSeverity
    title: str
    description: str
    cve: Optional[str] = Field(None, description="CVE identifier if available")
    recommendation: str

    class Config:
        use_enum_values = True


class BuildMetrics(BaseModel):
    """Build performance metrics"""
    build_time_seconds: float
    bundle_size_mb: float
    asset_count: int
    cache_hit_rate: float = Field(ge=0.0, le=1.0)
    deployment_time_seconds: Optional[float] = None
    build_trend: str = Field(..., description="improving, stable, degrading")


class APICosts(BaseModel):
    """API usage and cost tracking"""
    api_name: str
    requests_count: int
    cost_usd: float
    quota_used_percent: float = Field(ge=0.0, le=100.0)
    forecast_monthly_cost: float
    period_start: datetime
    period_end: datetime


class DependencyInfo(BaseModel):
    """Information about a project dependency"""
    name: str
    current_version: str
    latest_version: str
    is_outdated: bool
    major_version_behind: int = Field(default=0)
    has_vulnerabilities: bool = Field(default=False)
    last_updated: Optional[datetime] = None


class TechStackHealth(BaseModel):
    """
    Comprehensive tech stack and infrastructure health analysis
    """
    analysis_id: str
    analyzed_at: datetime = Field(default_factory=datetime.now)
    overall_health: float = Field(ge=0.0, le=100.0, description="Overall health score")

    # Dependencies
    total_dependencies: int
    outdated_dependencies: int
    dependencies: List[DependencyInfo] = Field(default_factory=list)

    # Security
    vulnerabilities: List[Vulnerability] = Field(default_factory=list)
    critical_vulnerabilities: int = Field(default=0)
    high_vulnerabilities: int = Field(default=0)

    # Performance
    build_metrics: BuildMetrics

    # API Costs
    api_costs: List[APICosts] = Field(default_factory=list)
    total_monthly_cost_forecast: float = Field(default=0.0)

    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)

    # Additional metrics
    ci_cd_performance: Dict[str, Any] = Field(default_factory=dict)
    cache_efficiency: float = Field(ge=0.0, le=1.0, default=0.0)
    code_quality_score: Optional[float] = Field(None, ge=0.0, le=100.0)

    @validator('overall_health', always=True)
    def calculate_health_score(cls, v, values):
        """Calculate overall health score"""
        if v is not None:
            return v

        # Health decreases with vulnerabilities and outdated deps
        vuln_penalty = values.get('critical_vulnerabilities', 0) * 20
        vuln_penalty += values.get('high_vulnerabilities', 0) * 10
        outdated_penalty = min(values.get('outdated_dependencies', 0) * 2, 30)

        base_score = 100
        return max(0, base_score - vuln_penalty - outdated_penalty)


class PublishingStats(BaseModel):
    """Publishing statistics for a time period"""
    period_start: datetime
    period_end: datetime
    total_publishes: int
    successful_publishes: int
    failed_publishes: int
    average_time_to_publish_hours: float
    average_time_to_index_hours: float
    publishes_by_type: Dict[str, int] = Field(default_factory=dict)
    publishes_by_day: Dict[str, int] = Field(default_factory=dict)


class CalendarOverview(BaseModel):
    """Editorial calendar overview"""
    total_items_queued: int
    total_items_scheduled: int
    total_items_published: int
    upcoming_publishes: List[str] = Field(default_factory=list)
    conflicts_count: int
    next_available_slot: Optional[datetime] = None


class SchedulerReport(BaseModel):
    """
    Comprehensive Scheduler Robot report combining all analyses
    """
    report_id: str
    generated_at: datetime = Field(default_factory=datetime.now)

    # Analysis results
    seo_analysis: TechnicalSEOScore
    tech_analysis: TechStackHealth

    # Publishing metrics
    publishing_stats: PublishingStats
    calendar_overview: CalendarOverview

    # Summary
    overall_status: str = Field(..., description="healthy, warning, critical")
    action_items: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list, description="Recent wins")

    # Trends
    trends: Dict[str, str] = Field(
        default_factory=dict,
        description="Trend indicators (improving, stable, degrading)"
    )

    @validator('overall_status', always=True)
    def determine_status(cls, v, values):
        """Determine overall status from analyses"""
        if v is not None:
            return v

        seo = values.get('seo_analysis')
        tech = values.get('tech_analysis')

        if not seo or not tech:
            return "unknown"

        if seo.critical_issues > 0 or tech.critical_vulnerabilities > 0:
            return "critical"

        if seo.overall_score < 70 or tech.overall_health < 70:
            return "warning"

        return "healthy"
