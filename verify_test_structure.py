#!/usr/bin/env python3
"""
Simple test to verify our new test structure works
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_import_fixtures():
    """Test that fixtures can be imported."""
    try:
        from tests.fixtures.sample_data import SAMPLE_KEYWORDS
        from tests.fixtures.mock_responses import MockSERPResponse
        print("✅ Fixtures import successfully")
        return True
    except ImportError as e:
        print(f"❌ Fixture import failed: {e}")
        return False

def test_test_discovery():
    """Test that pytest can discover our tests."""
    test_files = []
    tests_dir = project_root / "tests"
    
    if not tests_dir.exists():
        print("❌ tests directory not found")
        return False
    
    for root, dirs, files in os.walk(tests_dir):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                test_files.append(str(Path(root) / file))
    
    print(f"📁 Discovered {len(test_files)} test files:")
    for test_file in sorted(test_files):
        rel_path = str(Path(test_file).relative_to(project_root))
        print(f"   - {rel_path}")
    
    return len(test_files) > 0

def test_marker_configuration():
    """Test that our pytest configuration is valid."""
    try:
        import configparser
    except ImportError:
        print("❌ configparser not available")
        return False
    
    config_path = project_root / "pytest.ini"
    if not config_path.exists():
        print("❌ pytest.ini not found")
        return False
    
    config = configparser.ConfigParser()
    try:
        config.read(config_path)
    except Exception as e:
        print(f"❌ pytest.ini parsing failed: {e}")
        return False
    
    markers = config.get("tool:pytest", "markers", fallback="")
    expected_markers = ["unit", "integration", "e2e", "slow", "external", "agents", "tools"]
    
    missing_markers = []
    for marker in expected_markers:
        if marker not in markers:
            missing_markers.append(marker)
    
    if missing_markers:
        print(f"❌ Missing markers: {missing_markers}")
        return False
    else:
        print("✅ All expected markers configured")
        return True

def main():
    """Run all verification tests."""
    print("🔍 Verifying test structure...")
    
    tests = [
        ("Import Fixtures", test_import_fixtures),
        ("Test Discovery", test_test_discovery),
        ("Marker Configuration", test_marker_configuration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 40)
        if test_func():
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 Test structure is properly configured!")
        return 0
    else:
        print("⚠️  Some issues found - please address them")
        return 1

if __name__ == "__main__":
    sys.exit(main())