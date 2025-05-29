#!/usr/bin/env python3
"""
Test runner for the fcs_core module.

This script sets up the Python path and runs tests for the fcs_core module.
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
    
    # Create tests directory if it doesn't exist
    test_dir.mkdir(exist_ok=True)
    
    # Check if there are any test files
    test_files = list(test_dir.glob("test_*.py"))
    
    if not test_files:
        print("No test files found in fcs_core/tests/")
        print("Creating a basic test structure...")
        
        # Create a basic test file
        basic_test = test_dir / "test_fcs_memory_service.py"
        basic_test.write_text('''"""
Basic tests for FCS Memory Service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

def test_fcs_memory_service_import():
    """Test that we can import the FCS Memory Service."""
    from fcs_core import FCSMemoryService
    assert FCSMemoryService is not None

def test_models_import():
    """Test that we can import the models."""
    from fcs_core import Message, ContradictionAlert, CognitiveObject
    assert Message is not None
    assert ContradictionAlert is not None
    assert CognitiveObject is not None

def test_async_worker_import():
    """Test that we can import the async worker."""
    from fcs_core import AsyncWorker
    assert AsyncWorker is not None

@pytest.mark.asyncio
async def test_fcs_memory_service_initialization():
    """Test FCS Memory Service initialization."""
    from fcs_core import FCSMemoryService
    
    # This test requires actual Neo4j connection, so we'll just test instantiation
    try:
        service = FCSMemoryService(
            enable_contradiction_detection=True,
            contradiction_threshold=0.7
        )
        assert service is not None
        assert service.graphiti is not None
    except Exception as e:
        # Expected if Neo4j is not available
        assert "Failed to establish connection" in str(e) or "Connection refused" in str(e)
''')
        print(f"Created basic test file: {basic_test}")
    
    exit_code = pytest.main([
        str(test_dir),
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])
    
    sys.exit(exit_code) 