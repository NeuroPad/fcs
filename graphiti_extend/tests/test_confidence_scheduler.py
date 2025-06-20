"""
Tests for ConfidenceScheduler class.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from graphiti_extend.confidence.scheduler import ConfidenceScheduler
from graphiti_extend.confidence.models import ConfidenceTrigger


class TestConfidenceScheduler:
    """Test ConfidenceScheduler functionality."""
    
    @pytest.fixture
    def mock_driver(self):
        """Create a mock driver for testing."""
        driver = AsyncMock()
        driver.execute_query = AsyncMock()
        return driver
    
    @pytest.fixture
    def scheduler(self):
        """Create a ConfidenceScheduler instance for testing."""
        return ConfidenceScheduler(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            cron_schedule="0 2 * * *",
            group_ids=["test_group"],
            batch_size=50
        )
    
    @pytest.fixture
    def sample_metadata_json(self):
        """Create sample metadata JSON for testing."""
        return json.dumps({
            "origin_type": "user_given",
            "confidence_history": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "value": 0.8,
                    "trigger": "initial_assignment",
                    "reason": "Test",
                    "metadata": None
                }
            ],
            "revisions": 0,
            "last_user_validation": (datetime.now() - timedelta(days=35)).isoformat(),
            "supporting_co_ids": [],
            "contradicting_co_ids": [],
            "contradiction_resolution_status": "unresolved",
            "dormancy_start": None,
            "stability_score": 0.0
        })

    async def test_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler.neo4j_uri == "bolt://localhost:7687"
        assert scheduler.neo4j_user == "neo4j"
        assert scheduler.neo4j_password == "password"
        assert scheduler.cron_schedule == "0 2 * * *"
        assert scheduler.group_ids == ["test_group"]
        assert scheduler.batch_size == 50
        assert scheduler.driver is None
        assert scheduler.confidence_manager is None

    async def test_initialize(self, scheduler):
        """Test scheduler initialization with database connection."""
        with patch('neo4j.AsyncGraphDatabase.driver') as mock_driver_class:
            mock_driver = AsyncMock()
            mock_driver_class.return_value = mock_driver
            
            await scheduler.initialize()
            
            assert scheduler.driver == mock_driver
            assert scheduler.confidence_manager is not None
            mock_driver_class.assert_called_once_with(
                "bolt://localhost:7687",
                auth=("neo4j", "password")
            )

    async def test_cleanup(self, scheduler):
        """Test scheduler cleanup."""
        # Mock driver
        mock_driver = AsyncMock()
        scheduler.driver = mock_driver
        
        await scheduler.cleanup()
        
        mock_driver.close.assert_called_once()
        assert scheduler.driver is None

    async def test_run_decay_cycle_not_initialized(self, scheduler):
        """Test decay cycle when scheduler is not initialized."""
        result = await scheduler.run_decay_cycle()
        
        assert result == {}

    async def test_run_decay_cycle_success(self, scheduler):
        """Test successful decay cycle execution."""
        # Mock confidence manager
        mock_manager = AsyncMock()
        scheduler.confidence_manager = mock_manager
        
        # Mock dormancy decay
        with patch.object(scheduler, '_run_dormancy_decay') as mock_dormancy:
            mock_dormancy.return_value = {
                "processed": 10,
                "dormancy_decay": 5,
                "extended_dormancy": 2,
                "orphaned": 1
            }
            
            result = await scheduler.run_decay_cycle()
            
            assert result["processed"] == 10
            assert result["dormancy_decay"] == 5
            assert result["extended_dormancy"] == 2
            assert result["orphaned"] == 1
            mock_dormancy.assert_called_once()

    async def test_run_decay_cycle_exception(self, scheduler):
        """Test decay cycle with exception handling."""
        # Mock confidence manager
        mock_manager = AsyncMock()
        scheduler.confidence_manager = mock_manager
        
        # Mock dormancy decay to raise exception
        with patch.object(scheduler, '_run_dormancy_decay') as mock_dormancy:
            mock_dormancy.side_effect = Exception("Test error")
            
            result = await scheduler.run_decay_cycle()
            
            assert result == {"error": "Test error"}

    async def test_run_manual_decay_not_initialized(self, scheduler):
        """Test manual decay when scheduler is not initialized."""
        with patch.object(scheduler, 'initialize') as mock_init:
            result = await scheduler.run_manual_decay()
            
            mock_init.assert_called_once()
            assert "processed" in result

    async def test_run_manual_decay_success(self, scheduler):
        """Test successful manual decay execution."""
        # Mock confidence manager
        mock_manager = AsyncMock()
        scheduler.confidence_manager = mock_manager
        
        # Mock dormancy decay
        with patch.object(scheduler, '_run_dormancy_decay') as mock_dormancy:
            mock_dormancy.return_value = {
                "processed": 5,
                "dormancy_decay": 3,
                "extended_dormancy": 1,
                "orphaned": 0
            }
            
            result = await scheduler.run_manual_decay(group_ids=["custom_group"])
            
            assert result["processed"] == 5
            assert result["dormancy_decay"] == 3
            assert result["extended_dormancy"] == 1
            assert result["orphaned"] == 0
            mock_dormancy.assert_called_once_with(["custom_group"])

    async def test_run_manual_decay_exception(self, scheduler):
        """Test manual decay with exception handling."""
        # Mock confidence manager
        mock_manager = AsyncMock()
        scheduler.confidence_manager = mock_manager
        
        # Mock dormancy decay to raise exception
        with patch.object(scheduler, '_run_dormancy_decay') as mock_dormancy:
            mock_dormancy.side_effect = Exception("Manual test error")
            
            result = await scheduler.run_manual_decay()
            
            assert result == {"error": "Manual test error"}

    async def test_run_dormancy_decay_no_group_filter(self, scheduler):
        """Test dormancy decay without group filter."""
        # Mock driver
        mock_driver = AsyncMock()
        scheduler.driver = mock_driver
        
        # Mock query results
        mock_driver.execute_query.return_value = ([], None, None)
        
        result = await scheduler._run_dormancy_decay()
        
        assert result["processed"] == 0
        assert result["dormancy_decay"] == 0
        assert result["extended_dormancy"] == 0
        assert result["orphaned"] == 0

    async def test_run_dormancy_decay_with_group_filter(self, scheduler):
        """Test dormancy decay with group filter."""
        # Mock driver
        mock_driver = AsyncMock()
        scheduler.driver = mock_driver
        
        # Mock query results
        mock_driver.execute_query.return_value = ([], None, None)
        
        result = await scheduler._run_dormancy_decay(group_ids=["test_group"])
        
        assert result["processed"] == 0
        # Verify query was called with group filter
        mock_driver.execute_query.assert_called()

    async def test_run_dormancy_decay_with_nodes(self, scheduler, sample_metadata_json):
        """Test dormancy decay with actual nodes."""
        # Mock driver
        mock_driver = AsyncMock()
        scheduler.driver = mock_driver
        
        # Mock query results with nodes
        mock_driver.execute_query.side_effect = [
            ([{"uuid": "node1", "metadata": sample_metadata_json}], None, None),  # Main query
            ([], None, None)  # Orphaned query
        ]
        
        # Mock confidence manager
        mock_manager = AsyncMock()
        scheduler.confidence_manager = mock_manager
        
        result = await scheduler._run_dormancy_decay()
        
        assert result["processed"] == 1
        assert result["dormancy_decay"] == 1  # 35 days > 30 days
        assert result["extended_dormancy"] == 0  # 35 days < 90 days
        assert result["orphaned"] == 0

    async def test_run_dormancy_decay_extended_dormancy(self, scheduler):
        """Test dormancy decay for extended dormancy (>90 days)."""
        # Mock driver
        mock_driver = AsyncMock()
        scheduler.driver = mock_driver
        
        # Create metadata with very old last_user_validation
        old_metadata = json.dumps({
            "origin_type": "user_given",
            "confidence_history": [],
            "revisions": 0,
            "last_user_validation": (datetime.now() - timedelta(days=100)).isoformat(),
            "supporting_co_ids": [],
            "contradicting_co_ids": [],
            "contradiction_resolution_status": "unresolved",
            "dormancy_start": None,
            "stability_score": 0.0
        })
        
        # Mock query results
        mock_driver.execute_query.side_effect = [
            ([{"uuid": "node1", "metadata": old_metadata}], None, None),  # Main query
            ([], None, None)  # Orphaned query
        ]
        
        # Mock confidence manager
        mock_manager = AsyncMock()
        scheduler.confidence_manager = mock_manager
        
        result = await scheduler._run_dormancy_decay()
        
        assert result["processed"] == 1
        assert result["dormancy_decay"] == 0  # 100 days > 30 days, but > 90 days
        assert result["extended_dormancy"] == 1  # 100 days > 90 days
        assert result["orphaned"] == 0

    async def test_run_dormancy_decay_orphaned_entities(self, scheduler):
        """Test dormancy decay for orphaned entities."""
        # Mock driver
        mock_driver = AsyncMock()
        scheduler.driver = mock_driver
        
        # Mock query results
        mock_driver.execute_query.side_effect = [
            ([], None, None),  # Main query - no nodes
            ([{"uuid": "orphaned1"}, {"uuid": "orphaned2"}], None, None)  # Orphaned query
        ]
        
        # Mock confidence manager
        mock_manager = AsyncMock()
        scheduler.confidence_manager = mock_manager
        
        result = await scheduler._run_dormancy_decay()
        
        assert result["processed"] == 0
        assert result["dormancy_decay"] == 0
        assert result["extended_dormancy"] == 0
        assert result["orphaned"] == 2

    async def test_run_dormancy_decay_invalid_metadata(self, scheduler):
        """Test dormancy decay with invalid metadata."""
        # Mock driver
        mock_driver = AsyncMock()
        scheduler.driver = mock_driver
        
        # Mock query results with invalid JSON
        mock_driver.execute_query.side_effect = [
            ([{"uuid": "node1", "metadata": "invalid json"}], None, None),  # Main query
            ([], None, None)  # Orphaned query
        ]
        
        # Mock confidence manager
        mock_manager = AsyncMock()
        scheduler.confidence_manager = mock_manager
        
        result = await scheduler._run_dormancy_decay()
        
        assert result["processed"] == 1
        assert result["dormancy_decay"] == 0  # Invalid metadata should be skipped
        assert result["extended_dormancy"] == 0
        assert result["orphaned"] == 0

    async def test_run_dormancy_decay_no_last_validation(self, scheduler):
        """Test dormancy decay with no last_user_validation."""
        # Mock driver
        mock_driver = AsyncMock()
        scheduler.driver = mock_driver
        
        # Create metadata without last_user_validation
        metadata_no_validation = json.dumps({
            "origin_type": "user_given",
            "confidence_history": [],
            "revisions": 0,
            "supporting_co_ids": [],
            "contradicting_co_ids": [],
            "contradiction_resolution_status": "unresolved",
            "dormancy_start": None,
            "stability_score": 0.0
        })
        
        # Mock query results
        mock_driver.execute_query.side_effect = [
            ([{"uuid": "node1", "metadata": metadata_no_validation}], None, None),  # Main query
            ([], None, None)  # Orphaned query
        ]
        
        # Mock confidence manager
        mock_manager = AsyncMock()
        scheduler.confidence_manager = mock_manager
        
        result = await scheduler._run_dormancy_decay()
        
        assert result["processed"] == 1
        assert result["dormancy_decay"] == 0  # No last_validation should be skipped
        assert result["extended_dormancy"] == 0
        assert result["orphaned"] == 0

    async def test_run_dormancy_decay_exception_handling(self, scheduler):
        """Test dormancy decay with exception handling."""
        # Mock driver
        mock_driver = AsyncMock()
        scheduler.driver = mock_driver
        
        # Mock query to raise exception
        mock_driver.execute_query.side_effect = Exception("Database error")
        
        result = await scheduler._run_dormancy_decay()
        
        assert result["processed"] == 0
        assert result["dormancy_decay"] == 0
        assert result["extended_dormancy"] == 0
        assert result["orphaned"] == 0

    async def test_setup_scheduler(self, scheduler):
        """Test scheduler setup with FastAPI."""
        # Mock FastAPI app
        mock_app = MagicMock()
        
        # Test setup doesn't raise exceptions
        try:
            scheduler.setup_scheduler(mock_app)
            # Should add event handlers to the app
            assert mock_app.on_event.called
        except Exception as e:
            pytest.fail(f"Setup scheduler raised exception: {e}")

    async def test_batch_size_limits(self, scheduler):
        """Test that batch size limits are respected."""
        # Mock driver
        mock_driver = AsyncMock()
        scheduler.driver = mock_driver
        
        # Mock query results with more nodes than batch size
        many_nodes = [{"uuid": f"node{i}", "metadata": "{}"} for i in range(100)]
        mock_driver.execute_query.side_effect = [
            (many_nodes, None, None),  # Main query
            ([], None, None)  # Orphaned query
        ]
        
        # Mock confidence manager
        mock_manager = AsyncMock()
        scheduler.confidence_manager = mock_manager
        
        result = await scheduler._run_dormancy_decay()
        
        # Should only process up to batch_size nodes
        assert result["processed"] == 50  # batch_size 