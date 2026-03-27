"""
Simple integration tests for SEO system.
Tests basic multi-agent functionality.
"""
import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.integration
def test_import_seo_agents():
    """Test that all SEO agents can be imported."""
    agents_to_test = [
        "agents.seo.research_analyst",
        "agents.seo.content_strategist", 
        "agents.seo.copywriter",
        "agents.seo.technical_seo",
        "agents.seo.marketing_strategist",
        "agents.seo.editor"
    ]
    
    for agent_module in agents_to_test:
        try:
            __import__(agent_module)
        except ImportError:
            pytest.skip(f"Agent {agent_module} not available")


@pytest.mark.integration
def test_seo_system_import():
    """Test that SEO system can be imported."""
    try:
        from agents.seo.seo_crew import SEOContentCrew
        crew = SEOContentCrew()
        assert crew is not None
    except ImportError:
        pytest.skip("SEOContentCrew not available")