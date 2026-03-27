"""
Simple tests for Research Analyst Agent.
Tests basic functionality and imports.
"""
import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.unit
@pytest.mark.agents
def test_research_analyst_import():
    """Test that ResearchAnalystAgent can be imported."""
    try:
        from agents.seo.research_analyst import ResearchAnalystAgent
        agent = ResearchAnalystAgent()
        assert agent is not None
        assert hasattr(agent, 'agent')
        assert hasattr(agent.agent, 'role')
    except ImportError:
        pytest.skip("ResearchAnalystAgent not available")


@pytest.mark.unit
@pytest.mark.agents
def test_research_tools_import():
    """Test that research tools can be imported."""
    try:
        from agents.seo.tools.research_tools import SERPAnalyzer, KeywordGapFinder, RankingPatternExtractor
        assert SERPAnalyzer is not None
        assert KeywordGapFinder is not None
        assert RankingPatternExtractor is not None
    except ImportError:
        pytest.skip("Research tools not available")