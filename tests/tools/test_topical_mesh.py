"""
Simple tests for topical mesh functionality.
"""
import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.unit
@pytest.mark.tools
def test_topical_mesh_builder_import():
    """Test that TopicalMeshBuilder can be imported."""
    try:
        from agents.seo.tools.strategy_tools import TopicalMeshBuilder
        builder = TopicalMeshBuilder()
        assert builder is not None
    except ImportError:
        pytest.skip("TopicalMeshBuilder not available")


@pytest.mark.unit
@pytest.mark.tools  
def test_topical_mesh_creation():
    """Test basic topical mesh creation."""
    try:
        from agents.seo.tools.strategy_tools import TopicalMeshBuilder
        builder = TopicalMeshBuilder()
        
        mesh = builder.build_semantic_cocoon(
            main_topic="Test Topic",
            subtopics=["Subtopic 1", "Subtopic 2"],
            business_goals=["rank"]
        )
        
        assert mesh is not None
        assert "main_topic" in mesh
        assert mesh["main_topic"] == "Test Topic"
        
    except ImportError:
        pytest.skip("TopicalMeshBuilder not available")
    except Exception as e:
        pytest.fail(f"Topical mesh creation failed: {e}")