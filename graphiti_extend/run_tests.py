#!/usr/bin/env python3
"""
Test runner for the graphiti_extend module.

This script sets up the Python path and runs the tests for the graphiti_extend module.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import pytest
    
    # Run tests with verbose output
    test_dir = Path(__file__).parent / "tests"
    exit_code = pytest.main([
        str(test_dir),
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])
    
    sys.exit(exit_code) 