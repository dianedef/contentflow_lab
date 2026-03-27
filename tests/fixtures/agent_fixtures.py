"""
Enhanced agent fixtures for multi-agent SEO system testing.

This module provides specific fixtures for each SEO agent and their interactions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Generator


@pytest.fixture
def research_agent():
    """
    Research Analyst agent fixture.
    
    Returns:
        ResearchAnalystAgent instance with mocked LLM
    """
    with patch('agents.seo.research_analyst.get_balanced_llm') as mock_llm:
        mock_llm.return_value = MagicMock()
        from agents.seo.research_analyst import ResearchAnalystAgent
        return ResearchAnalystAgent()


@pytest.fixture
def content_strategist():
    """
    Content Strategist agent fixture.
    
    Returns:
        ContentStrategistAgent instance with mocked LLM
    """
    with patch('agents.seo.content_strategist.get_balanced_llm') as mock_llm:
        mock_llm.return_value = MagicMock()
        from agents.seo.content_strategist import ContentStrategistAgent
        return ContentStrategistAgent()


@pytest.fixture
def copywriter():
    """
    Copywriter agent fixture.
    
    Returns:
        CopywriterAgent instance with mocked LLM
    """
    with patch('agents.seo.copywriter.get_balanced_llm') as mock_llm:
        mock_llm.return_value = MagicMock()
        from agents.seo.copywriter import CopywriterAgent
        return CopywriterAgent()


@pytest.fixture
def technical_seo():
    """
    Technical SEO agent fixture.
    
    Returns:
        TechnicalSEOAgent instance with mocked LLM
    """
    with patch('agents.seo.technical_seo.get_balanced_llm') as mock_llm:
        mock_llm.return_value = MagicMock()
        from agents.seo.technical_seo import TechnicalSEOAgent
        return TechnicalSEOAgent()


@pytest.fixture
def marketing_strategist():
    """
    Marketing Strategist agent fixture.
    
    Returns:
        MarketingStrategistAgent instance with mocked LLM
    """
    with patch('agents.seo.marketing_strategist.get_balanced_llm') as mock_llm:
        mock_llm.return_value = MagicMock()
        from agents.seo.marketing_strategist import MarketingStrategistAgent
        return MarketingStrategistAgent()


@pytest.fixture
def editor():
    """
    Editor agent fixture.
    
    Returns:
        EditorAgent instance with mocked LLM
    """
    with patch('agents.seo.editor.get_balanced_llm') as mock_llm:
        mock_llm.return_value = MagicMock()
        from agents.seo.editor import EditorAgent
        return EditorAgent()


@pytest.fixture
def all_agents(research_agent, content_strategist, copywriter, technical_seo, marketing_strategist, editor):
    """
    All 6 SEO agents as a dictionary.
    
    Returns:
        Dictionary mapping agent names to instances
    """
    return {
        "research_analyst": research_agent,
        "content_strategist": content_strategist,
        "copywriter": copywriter,
        "technical_seo": technical_seo,
        "marketing_strategist": marketing_strategist,
        "editor": editor
    }


@pytest.fixture
def mock_crew_workflow():
    """
    Mock CrewAI workflow for testing.
    
    Returns:
        Mocked CrewAI crew with predefined responses
    """
    with patch('crewai.Crew') as mock_crew:
        mock_crew.return_value.kickoff.return_value = {
            "result": "Mock SEO content generated successfully",
            "raw": {
                "research_analysis": {"insights": ["Mock research insight"]},
                "content_strategy": {"plan": "Mock content plan"},
                "copywriting": {"content": "Mock SEO content"},
                "technical_optimization": {"recommendations": ["Mock tech rec"]},
                "marketing_strategy": {"tactics": ["Mock marketing tactic"]},
                "editing": {"final_content": "Mock edited content"}
            },
            "usage": {
                "total_tokens": 1000,
                "cost": 0.05,
                "time": 30.5
            }
        }
        yield mock_crew


@pytest.fixture
def sample_seo_task():
    """
    Sample SEO task for testing agent workflows.
    
    Returns:
        Dictionary containing SEO task parameters
    """
    return {
        "target_keyword": "content marketing automation",
        "business_goals": ["rank", "convert", "inform"],
        "target_audience": "B2B marketers",
        "content_type": "blog_post",
        "competitor_domains": ["hubspot.com", "contentmarketinginstitute.com"],
        "word_count_target": 2000,
        "primary_intent": "informational"
    }


@pytest.fixture
def sample_agent_tasks():
    """
    Sample tasks for each agent type.
    
    Returns:
        Dictionary mapping agent types to sample tasks
    """
    return {
        "research_analyst": {
            "task": "Analyze SERP for 'content marketing automation'",
            "expected_output": {
                "keyword_analysis": {},
                "competitive_insights": [],
                "search_intent": "informational"
            }
        },
        "content_strategist": {
            "task": "Create content strategy for B2B SaaS company",
            "expected_output": {
                "content_pillars": [],
                "topic_clusters": [],
                "content_calendar": {}
            }
        },
        "copywriter": {
            "task": "Write 2000-word blog post about content marketing",
            "expected_output": {
                "title": "Compelling title",
                "content": "SEO-optimized content",
                "metadata": {"word_count": 2000, "readability_score": 70}
            }
        },
        "technical_seo": {
            "task": "Optimize content for search engines",
            "expected_output": {
                "optimizations": [],
                "schema_markup": {},
                "technical_score": 85
            }
        },
        "marketing_strategist": {
            "task": "Develop marketing promotion strategy",
            "expected_output": {
                "distribution_channels": [],
                "promotion_tactics": [],
                "roi_projection": {}
            }
        },
        "editor": {
            "task": "Review and edit content for quality",
            "expected_output": {
                "edited_content": "Polished content",
                "quality_score": 90,
                "improvements": []
            }
        }
    }


@pytest.fixture
def mock_tool_responses():
    """
    Mock responses for agent tools.
    
    Returns:
        Dictionary of mocked tool responses
    """
    return {
        "serp_analysis": {
            "keyword": "content marketing automation",
            "search_intent": "informational",
            "competitive_score": 8,
            "top_competitors": [
                {"domain": "hubspot.com", "position": 1, "title": "Content Marketing Automation Guide"}
            ],
            "related_searches": ["marketing automation tools", "automated content creation"]
        },
        "keyword_gaps": {
            "gaps_identified": [
                {"keyword": "AI content creation", "opportunity_score": 9.2, "difficulty": "medium"}
            ],
            "total_opportunity_value": 45.8,
            "priority_keywords": ["AI content creation", "automated blog writing"]
        },
        "topical_mesh": {
            "main_topic": "Content Marketing Automation",
            "pillar_page": {"title": "Complete Guide to Content Marketing Automation", "authority_score": 85},
            "cluster_pages": [
                {"title": "AI Content Creation Tools", "authority_score": 75},
                {"title": "Marketing Automation Software", "authority_score": 70}
            ],
            "topical_authority_score": 78.5,
            "authority_grade": "B+ (Good)"
        },
        "content_outline": {
            "h1": "Complete Guide to Content Marketing Automation",
            "sections": [
                {"h2": "What is Content Marketing Automation?", "word_count": 300},
                {"h2": "Benefits of Automated Content Marketing", "word_count": 400},
                {"h2": "Top Content Automation Tools", "word_count": 600},
                {"h2": "Implementation Strategy", "word_count": 500},
                {"h2": "Measuring ROI", "word_count": 200}
            ],
            "total_word_count": 2000
        }
    }


# Helper functions for agent testing
def assert_agent_initialized(agent, expected_role: str):
    """
    Assert that an agent is properly initialized.
    
    Args:
        agent: Agent instance to check
        expected_role: Expected role string
    """
    assert agent is not None
    assert hasattr(agent, 'agent')
    assert hasattr(agent, 'llm')
    assert agent.agent.role == expected_role


def assert_agent_tools_loaded(agent, expected_tool_count: int = None):
    """
    Assert that an agent has expected tools loaded.
    
    Args:
        agent: Agent instance to check
        expected_tool_count: Expected number of tools (optional)
    """
    assert hasattr(agent, 'agent')
    assert hasattr(agent.agent, 'tools')
    
    tools = agent.agent.tools or []
    if expected_tool_count:
        assert len(tools) >= expected_tool_count, f"Expected at least {expected_tool_count} tools, got {len(tools)}"
    
    return tools


def assert_task_result_valid(result: Dict[str, Any], required_keys: list = None):
    """
    Assert that a task result from an agent is valid.
    
    Args:
        result: Task result dictionary
        required_keys: List of required keys to check
    """
    assert isinstance(result, dict)
    assert "success" in result or "result" in result or "error" not in result
    
    if required_keys:
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"


# Agent-specific test data
SAMPLE_AGENT_CONFIGS = {
    "research_analyst": {
        "role": "SEO Research Analyst",
        "goal": "Conduct comprehensive competitive intelligence and keyword analysis",
        "backstory": "Expert SEO analyst with 10+ years in digital marketing"
    },
    "content_strategist": {
        "role": "Content Strategist",
        "goal": "Develop comprehensive content strategies and topical authority plans",
        "backstory": "Strategic content planner specializing in SEO and audience engagement"
    },
    "copywriter": {
        "role": "SEO Copywriter",
        "goal": "Create compelling, SEO-optimized content that converts",
        "backstory": "Professional copywriter with expertise in SEO and persuasive writing"
    },
    "technical_seo": {
        "role": "Technical SEO Specialist",
        "goal": "Ensure technical excellence and search engine optimization",
        "backstory": "Technical SEO expert focused on performance and indexing"
    },
    "marketing_strategist": {
        "role": "Marketing Strategist",
        "goal": "Develop marketing strategies that amplify content impact",
        "backstory": "Marketing strategist with data-driven approach to growth"
    },
    "editor": {
        "role": "Content Editor",
        "goal": "Review, refine, and ensure content quality and consistency",
        "backstory": "Experienced editor with keen eye for detail and quality"
    }
}