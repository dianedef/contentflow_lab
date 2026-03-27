"""
Simple tests for SEO tools.
"""
import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.unit
@pytest.mark.tools
def test_import_advertools():
    """Test that advertools can be imported."""
    try:
        import advertools as adv
        assert adv is not None
    except ImportError:
        pytest.skip("advertools not installed")


@pytest.mark.unit
@pytest.mark.tools
def test_import_topical_mesh_tools():
    """Test that topical mesh tools can be imported."""
    try:
        from agents.seo.tools.strategy_tools import TopicalMeshBuilder
        builder = TopicalMeshBuilder()
        assert builder is not None
    except ImportError:
        pytest.skip("Topical mesh tools not available")