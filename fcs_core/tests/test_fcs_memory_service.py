"""
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
