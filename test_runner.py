#!/usr/bin/env python3
"""
Test Runner for SEO Multi-Agent System

Provides convenient commands for running different test categories.
Usage: python test_runner.py [command]

Available commands:
    all          - Run all tests
    unit         - Run unit tests only
    integration  - Run integration tests only
    agents       - Run agent tests only
    tools        - Run tool tests only
    fast         - Run fast tests (exclude slow)
    coverage     - Run tests with coverage report
    specific     - Run specific test file
"""

import subprocess
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_command(cmd: str, description: str) -> int:
    """Run a command and return exit code."""
    print(f"\n🚀 {description}")
    print(f"Running: {cmd}")
    print("-" * 60)
    
    result = subprocess.run(cmd, shell=True, cwd=project_root)
    
    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
    else:
        print(f"❌ {description} - FAILED")
    
    return result.returncode

def main():
    """Main test runner."""
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    
    command = sys.argv[1]
    
    # Set environment
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    commands = {
        "all": ("source venv/bin/activate && python -m pytest tests/ -v", "All Tests"),
        "unit": ("source venv/bin/activate && python -m pytest tests/ -m unit -v", "Unit Tests"),
        "integration": ("source venv/bin/activate && python -m pytest tests/ -m integration -v", "Integration Tests"),
        "agents": ("source venv/bin/activate && python -m pytest tests/ -m agents -v", "Agent Tests"),
        "tools": ("source venv/bin/activate && python -m pytest tests/ -m tools -v", "Tool Tests"),
        "fast": ("source venv/bin/activate && python -m pytest tests/ -m 'not slow' -v", "Fast Tests Only"),
        "coverage": ("source venv/bin/activate && python -m pytest tests/ --cov=agents --cov=api --cov=utils --cov-report=html --cov-report=term", "Tests with Coverage"),
    }
    
    if command == "specific" and len(sys.argv) > 2:
        test_file = sys.argv[2]
        # Sanitize: only allow paths with alphanumeric, /, _, -, .
        if not all(c.isalnum() or c in "/_-." for c in test_file):
            print(f"❌ Invalid test file path: {test_file}")
            return 1
        cmd = f"source venv/bin/activate && python -m pytest {test_file} -v"
        desc = f"Specific Test: {test_file}"
        return run_command(cmd, desc)
    
    if command in commands:
        cmd, desc = commands[command]
        return run_command(cmd, desc)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        return 1

if __name__ == "__main__":
    sys.exit(main())