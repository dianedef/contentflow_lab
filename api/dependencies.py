"""
FastAPI Dependency Injection for SEO Agents

Provides singleton instances of Python agents for use in API endpoints.
Uses lazy initialization to avoid startup delays.
"""

from functools import lru_cache
from typing import Optional


@lru_cache(maxsize=1)
def get_mesh_architect():
    """
    Get singleton TopicalMeshArchitect instance.

    Uses lru_cache for lazy singleton pattern -
    agent is only initialized on first request.
    """
    from agents.seo.topical_mesh_architect import TopicalMeshArchitect
    return TopicalMeshArchitect()


@lru_cache(maxsize=1)
def get_research_analyst():
    """
    Get singleton ResearchAnalystAgent instance.
    """
    from agents.seo.research_analyst import ResearchAnalystAgent
    return ResearchAnalystAgent()


@lru_cache(maxsize=1)
def get_content_strategist():
    """
    Get singleton ContentStrategistAgent instance.
    """
    from agents.seo.content_strategist import ContentStrategistAgent
    return ContentStrategistAgent()


# Optional: Clear cache for testing or reloading
def clear_agent_cache():
    """Clear all cached agent instances (useful for testing)"""
    get_mesh_architect.cache_clear()
    get_research_analyst.cache_clear()
    get_content_strategist.cache_clear()
