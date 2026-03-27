"""
Shared fixtures and configuration for pytest test suite.

This module provides common test fixtures, mocks, and utilities
for testing the SEO multi-agent system.
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Generator

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """
    Configure pytest with custom markers.
    
    Args:
        config: pytest config object
    """
    # Custom marker descriptions are already in pytest.ini
    pass


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers based on test location.
    
    Args:
        config: pytest config object
        items: List of test items
    """
    for item in items:
        # Add markers based on test file location
        if "agents/" in str(item.fspath):
            item.add_marker(pytest.mark.agents)
            item.add_marker(pytest.mark.unit)
        elif "tools/" in str(item.fspath):
            item.add_marker(pytest.mark.tools)
            item.add_marker(pytest.mark.unit)
        elif "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "utils/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add markers for specific test types
        if "storm" in item.name.lower():
            item.add_marker(pytest.mark.storm)
        if "integration" in item.name.lower():
            item.add_marker(pytest.mark.integration)


# Helper functions for testing
def assert_valid_seo_result(result: Dict[str, Any], required_keys: list = None) -> None:
    """
    Helper to assert valid SEO analysis result.
    
    Args:
        result: SEO analysis result dictionary
        required_keys: List of required keys (optional)
    """
    assert isinstance(result, dict)
    assert "success" in result or "error" not in result
    
    if required_keys:
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"


def assert_agent_response(response: Any) -> None:
    """
    Helper to assert valid agent response.
    
    Args:
        response: Agent response object
    """
    assert response is not None
    if hasattr(response, 'raw'):
        assert response.raw is not None
    if isinstance(response, dict):
        assert "success" in response or "result" in response or "error" not in response

@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent / "fixtures"

@pytest.fixture(scope="session")
def mock_llm():
    """Mock LLM for testing agent functionality."""
    llm = MagicMock()
    llm.invoke.return_value = "Mock LLM response"
    llm.ainvoke = AsyncMock(return_value="Mock async LLM response")
    return llm

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables and cleanup after."""
    # Set test mode
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    # Mock API keys for testing
    test_keys = {
        "OPENROUTER_API_KEY": "test-openrouter-key",
        "GROQ_API_KEY": "test-groq-key",
        "SERP_API_KEY": "test-serp-key",
        "EXA_API_KEY": "test-exa-key",
        "YDC_API_KEY": "test-ydc-key"
    }
    
    original_keys = {}
    for key, value in test_keys.items():
        original_keys[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment
    os.environ.pop("TESTING", None)
    os.environ.pop("LOG_LEVEL", None)
    for key, original_value in original_keys.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value

@pytest.fixture
def sample_serp_data():
    """Sample SERP analysis data for testing."""
    return {
        "keyword": "python tutorial",
        "search_intent": "informational",
        "competitive_score": 7,
        "top_competitors": [
            {"url": "https://docs.python.org", "title": "Python Documentation"},
            {"url": "https://realpython.com", "title": "Real Python"}
        ],
        "search_results": [
            {
                "position": 1,
                "title": "Python Tutorial - W3Schools",
                "snippet": "Learn Python programming...",
                "url": "https://www.w3schools.com/python/"
            }
        ]
    }

@pytest.fixture
def sample_topical_mesh():
    """Sample topical mesh data for testing."""
    return {
        "main_topic": "Digital Marketing",
        "clusters": [
            {
                "name": "SEO Basics",
                "keywords": ["keyword research", "on-page seo", "meta tags"],
                "authority_score": 0.8
            },
            {
                "name": "Content Strategy",
                "keywords": ["blogging", "content calendar", "topic clusters"],
                "authority_score": 0.7
            }
        ],
        "connections": [
            {"from": "SEO Basics", "to": "Content Strategy", "weight": 0.9}
        ]
    }

@pytest.fixture
def mock_serp_api():
    """Mock SERP API responses."""
    api = MagicMock()
    api.search.return_value = {
        "organic_results": [
            {
                "position": 1,
                "title": "Python Tutorial",
                "snippet": "Learn Python programming",
                "link": "https://example.com/python"
            }
        ]
    }
    return api

@pytest.fixture
def sample_agent_config():
    """Sample agent configuration for testing."""
    return {
        "role": "Test Agent",
        "goal": "Test goal for agent",
        "backstory": "Test backstory",
        "verbose": False,
        "allow_delegation": False,
        "llm": "mock_llm"
    }