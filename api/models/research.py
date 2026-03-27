"""Pydantic models for Research endpoints"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional


class CompetitorAnalysisRequest(BaseModel):
    """Request for competitor analysis"""
    keywords: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Keywords to analyze (1-10)",
        examples=[["SEO tools", "content marketing"]]
    )
    num_competitors: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of competitors to analyze"
    )
    include_serp_data: bool = Field(
        default=True,
        description="Include SERP rankings data"
    )
    use_consensus_ai: bool = Field(
        default=False,
        description="Use Consensus AI for scientific/academic research"
    )


class CompetitorInfo(BaseModel):
    """Information about a single competitor"""
    domain: str
    url: HttpUrl
    authority_score: Optional[int] = None
    backlinks: Optional[int] = None
    topics_covered: list[str] = []
    content_gaps: list[str] = []
    strengths: list[str] = []
    weaknesses: list[str] = []


class CompetitorAnalysisResponse(BaseModel):
    """Response from competitor analysis"""
    keywords: list[str]
    competitors: list[CompetitorInfo]
    
    common_topics: list[str]
    content_opportunities: list[str]
    recommended_topics: list[str]
    
    analysis_timestamp: str
    processing_time_seconds: float
