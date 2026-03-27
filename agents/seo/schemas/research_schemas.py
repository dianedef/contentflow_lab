"""
Pydantic schemas for Research Analyst agent outputs.
Validates competitive analysis, SERP data, trends, and keyword gaps.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


class CompetitorResult(BaseModel):
    """Individual competitor in SERP results."""
    position: int = Field(..., ge=1, description="Ranking position")
    url: str = Field(..., description="Page URL")
    title: str = Field(..., description="Page title")
    snippet: str = Field(..., description="Meta description/snippet")
    domain: str = Field(..., description="Root domain")
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class SERPAnalysis(BaseModel):
    """SERP analysis with competitive positioning."""
    keyword: str = Field(..., description="Target keyword analyzed")
    search_intent: str = Field(..., description="Informational, Commercial, Transactional, or Navigational")
    total_results: int = Field(..., ge=0, description="Total number of results")
    top_competitors: List[CompetitorResult] = Field(..., max_items=10, description="Top 10 ranking pages")
    featured_snippet: Optional[Dict[str, str]] = Field(None, description="Featured snippet data if present")
    related_searches: List[str] = Field(default_factory=list, description="Related search queries")
    average_word_count: Optional[int] = Field(None, ge=0, description="Average content length of top results")
    common_topics: List[str] = Field(default_factory=list, description="Topics covered by top rankers")
    competitive_score: float = Field(..., ge=0.0, le=10.0, description="Difficulty score 0-10")
    analysis_timestamp: datetime = Field(default_factory=datetime.now)
    
    @validator('search_intent')
    def validate_intent(cls, v):
        valid_intents = ['Informational', 'Commercial', 'Transactional', 'Navigational']
        if v not in valid_intents:
            raise ValueError(f'Search intent must be one of {valid_intents}')
        return v


class TrendData(BaseModel):
    """Trend data point with temporal information."""
    keyword: str = Field(..., description="Keyword or topic")
    trend_score: float = Field(..., ge=0.0, le=100.0, description="Trend strength 0-100")
    search_volume: Optional[int] = Field(None, ge=0, description="Monthly search volume")
    growth_rate: Optional[float] = Field(None, description="Percentage growth rate")
    seasonality: Optional[str] = Field(None, description="Seasonal pattern if detected")
    related_terms: List[str] = Field(default_factory=list, description="Related trending terms")


class TrendReport(BaseModel):
    """Sector trends and seasonality analysis."""
    sector: str = Field(..., description="Industry or topic sector")
    analysis_period: str = Field(..., description="Time period analyzed")
    emerging_trends: List[TrendData] = Field(..., min_items=1, description="Trending keywords/topics")
    declining_trends: List[TrendData] = Field(default_factory=list, description="Declining keywords/topics")
    seasonal_patterns: Dict[str, str] = Field(default_factory=dict, description="Identified seasonal patterns")
    recommendations: List[str] = Field(..., min_items=1, description="Strategic recommendations")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence 0-1")
    generated_at: datetime = Field(default_factory=datetime.now)


class KeywordGap(BaseModel):
    """Content gap and keyword opportunity."""
    keyword: str = Field(..., description="Gap keyword")
    search_volume: int = Field(..., ge=0, description="Monthly search volume")
    difficulty: float = Field(..., ge=0.0, le=100.0, description="Keyword difficulty 0-100")
    opportunity_score: float = Field(..., ge=0.0, le=10.0, description="Opportunity score 0-10")
    competitors_ranking: List[str] = Field(..., description="Competitors ranking for this keyword")
    content_type_suggested: str = Field(..., description="Suggested content type (blog, guide, tool, etc.)")
    search_intent: str = Field(..., description="Primary search intent")
    related_keywords: List[str] = Field(default_factory=list, description="Related keyword opportunities")
    
    @validator('content_type_suggested')
    def validate_content_type(cls, v):
        valid_types = ['blog', 'guide', 'tutorial', 'tool', 'comparison', 'review', 'listicle', 'case-study']
        if v.lower() not in valid_types:
            raise ValueError(f'Content type must be one of {valid_types}')
        return v.lower()


class KeywordGapAnalysis(BaseModel):
    """Complete keyword gap analysis."""
    target_domain: Optional[str] = Field(None, description="Your domain being analyzed")
    competitor_domains: List[str] = Field(..., min_items=1, description="Competitor domains analyzed")
    gaps_identified: List[KeywordGap] = Field(..., min_items=1, description="Keyword gaps found")
    total_opportunity_value: float = Field(..., ge=0.0, description="Combined opportunity score")
    priority_keywords: List[str] = Field(..., min_items=1, max_items=10, description="Top 10 priority keywords")
    analysis_date: datetime = Field(default_factory=datetime.now)


class RankingFactor(BaseModel):
    """Individual ranking factor extracted from analysis."""
    factor_name: str = Field(..., description="Name of ranking factor")
    importance_score: float = Field(..., ge=0.0, le=10.0, description="Importance score 0-10")
    observation: str = Field(..., description="What was observed")
    actionable_insight: str = Field(..., description="How to apply this factor")


class RankingPattern(BaseModel):
    """Success patterns from top-ranking content."""
    keyword_analyzed: str = Field(..., description="Keyword these patterns relate to")
    content_length_pattern: Dict[str, Any] = Field(..., description="Word count patterns (min, max, avg)")
    structure_patterns: List[str] = Field(..., description="Common content structures (H2/H3 patterns)")
    ranking_factors: List[RankingFactor] = Field(..., min_items=1, description="Key ranking factors identified")
    backlink_profile: Optional[Dict[str, Any]] = Field(None, description="Backlink pattern summary")
    content_freshness: Optional[str] = Field(None, description="Update frequency pattern")
    multimedia_usage: Dict[str, bool] = Field(default_factory=dict, description="Images, videos, infographics usage")
    schema_markup_usage: List[str] = Field(default_factory=list, description="Schema types used by top rankers")
    success_probability: float = Field(..., ge=0.0, le=1.0, description="Probability of ranking with these patterns")
    extracted_at: datetime = Field(default_factory=datetime.now)
