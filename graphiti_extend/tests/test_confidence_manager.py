"""
Tests for ConfidenceManager class.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from graphiti_core.nodes import EntityNode
from graphiti_extend.confidence.manager import ConfidenceManager, ConfidenceMetadata
from graphiti_extend.confidence.models import (
    ConfidenceConfig,
    ConfidenceTrigger,
    OriginType,
    ConfidenceHistory
)


class TestConfidenceManager:
    """Test ConfidenceManager functionality."""
    
    @pytest.fixture
    def mock_driver(self):
        """Create a mock driver for testing."""
        driver = AsyncMock()
        driver.execute_query = AsyncMock()
        return driver
    
    @pytest.fixture
    def confidence_manager(self, mock_driver):
        """Create a ConfidenceManager instance for testing."""
        return ConfidenceManager(mock_driver)
    
    @pytest.fixture
    def sample_node(self):
        """Create a sample EntityNode for testing."""
        return EntityNode(
            uuid="test-uuid-123",
            name="Test Node",
            summary="A test node for confidence testing",
            group_id="test_group"
        )
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample confidence metadata."""
        return ConfidenceMetadata(
            origin_type=OriginType.USER_GIVEN,
            confidence_history=[
                ConfidenceHistory(
                    timestamp=datetime.now(),
                    value=0.8,
                    trigger=ConfidenceTrigger.INITIAL_ASSIGNMENT,
                    reason="Initial assignment"
                )
            ],
            revisions=0,
            supporting_co_ids=[],
            contradicting_co_ids=[]
        )

    async def test_assign_initial_confidence_user_given(self, confidence_manager, sample_node):
        """Test initial confidence assignment for user-given origin."""
        with patch.object(confidence_manager, '_store_confidence_metadata') as mock_store:
            confidence = await confidence_manager.assign_initial_confidence(
                sample_node, OriginType.USER_GIVEN, is_duplicate=False
            )
            
            assert confidence == 0.8  # Default user_given confidence
            mock_store.assert_called_once()
            
            # Check that metadata was created correctly
            call_args = mock_store.call_args
            assert call_args[0][0] == sample_node.uuid  # node_uuid
            assert call_args[0][1] == 0.8  # confidence
            metadata = call_args[0][2]  # metadata
            assert metadata.origin_type == OriginType.USER_GIVEN
            assert len(metadata.confidence_history) == 1
            assert metadata.confidence_history[0].trigger == ConfidenceTrigger.INITIAL_ASSIGNMENT

    async def test_assign_initial_confidence_inferred(self, confidence_manager, sample_node):
        """Test initial confidence assignment for inferred origin."""
        with patch.object(confidence_manager, '_store_confidence_metadata') as mock_store:
            confidence = await confidence_manager.assign_initial_confidence(
                sample_node, OriginType.INFERRED, is_duplicate=False
            )
            
            assert confidence == 0.5  # Default inferred confidence
            mock_store.assert_called_once()

    async def test_assign_initial_confidence_system_suggested(self, confidence_manager, sample_node):
        """Test initial confidence assignment for system-suggested origin."""
        with patch.object(confidence_manager, '_store_confidence_metadata') as mock_store:
            confidence = await confidence_manager.assign_initial_confidence(
                sample_node, OriginType.SYSTEM_SUGGESTED, is_duplicate=False
            )
            
            assert confidence == 0.4  # Default system_suggested confidence
            mock_store.assert_called_once()

    async def test_assign_initial_confidence_duplicate(self, confidence_manager, sample_node):
        """Test initial confidence assignment for duplicate (user reaffirmation)."""
        with patch.object(confidence_manager, '_store_confidence_metadata') as mock_store:
            confidence = await confidence_manager.assign_initial_confidence(
                sample_node, OriginType.USER_GIVEN, is_duplicate=True
            )
            
            # Should be user_given + duplicate_found boost
            expected_confidence = 0.8 + 0.1  # 0.9
            assert confidence == expected_confidence
            mock_store.assert_called_once()

    async def test_assign_initial_confidence_bounds(self, confidence_manager, sample_node):
        """Test that confidence is properly bounded between 0.0 and 1.0."""
        # Test with custom config that would exceed bounds
        custom_config = ConfidenceConfig(
            initial_user_given=1.5,  # Would exceed 1.0
            initial_duplicate_found=0.5  # Would make total 2.0
        )
        confidence_manager.config = custom_config
        
        with patch.object(confidence_manager, '_store_confidence_metadata'):
            confidence = await confidence_manager.assign_initial_confidence(
                sample_node, OriginType.USER_GIVEN, is_duplicate=True
            )
            
            assert confidence == 1.0  # Should be capped at 1.0

    async def test_update_confidence_success(self, confidence_manager):
        """Test successful confidence update."""
        node_uuid = "test-uuid"
        old_confidence = 0.5
        
        # Mock getting current confidence
        with patch.object(confidence_manager, '_get_confidence_and_metadata') as mock_get:
            mock_get.return_value = (old_confidence, sample_metadata)
            
            with patch.object(confidence_manager, '_store_confidence_metadata') as mock_store:
                update = await confidence_manager.update_confidence(
                    node_uuid,
                    ConfidenceTrigger.USER_REAFFIRMATION,
                    "User reaffirmed",
                    {"context": "test"}
                )
                
                assert update is not None
                assert update.node_uuid == node_uuid
                assert update.old_value == old_confidence
                assert update.new_value == old_confidence + 0.1  # user_reaffirmation_boost
                assert update.trigger == ConfidenceTrigger.USER_REAFFIRMATION
                assert update.reason == "User reaffirmed"
                assert update.metadata == {"context": "test"}
                
                mock_store.assert_called_once()

    async def test_update_confidence_no_existing_data(self, confidence_manager):
        """Test confidence update when no existing data is found."""
        node_uuid = "test-uuid"
        
        with patch.object(confidence_manager, '_get_confidence_and_metadata') as mock_get:
            mock_get.return_value = (None, None)
            
            update = await confidence_manager.update_confidence(
                node_uuid,
                ConfidenceTrigger.USER_REAFFIRMATION,
                "User reaffirmed"
            )
            
            assert update is None

    async def test_update_confidence_no_change(self, confidence_manager):
        """Test confidence update that results in no change."""
        node_uuid = "test-uuid"
        old_confidence = 0.5
        
        with patch.object(confidence_manager, '_get_confidence_and_metadata') as mock_get:
            mock_get.return_value = (old_confidence, sample_metadata)
            
            # Use a trigger that doesn't change confidence
            update = await confidence_manager.update_confidence(
                node_uuid,
                ConfidenceTrigger.CONSISTENCY_CHECK,  # This trigger might not change confidence
                "No change test"
            )
            
            # Should return None if no change occurred
            assert update is None

    async def test_update_confidence_batch(self, confidence_manager):
        """Test batch confidence updates."""
        updates = [
            ("uuid1", ConfidenceTrigger.USER_REAFFIRMATION, "Test 1", None),
            ("uuid2", ConfidenceTrigger.USER_REFERENCE, "Test 2", {"context": "test"}),
        ]
        
        with patch.object(confidence_manager, 'update_confidence') as mock_update:
            mock_update.return_value = MagicMock()  # Return a mock update object
            
            results = await confidence_manager.update_confidence_batch(updates)
            
            assert len(results) == 2
            assert mock_update.call_count == 2

    async def test_get_confidence(self, confidence_manager):
        """Test getting confidence for a node."""
        node_uuid = "test-uuid"
        expected_confidence = 0.8
        
        with patch.object(confidence_manager, '_get_confidence_and_metadata') as mock_get:
            mock_get.return_value = (expected_confidence, sample_metadata)
            
            confidence = await confidence_manager.get_confidence(node_uuid)
            
            assert confidence == expected_confidence
            mock_get.assert_called_once_with(node_uuid)

    async def test_get_confidence_metadata(self, confidence_manager):
        """Test getting confidence metadata for a node."""
        node_uuid = "test-uuid"
        
        with patch.object(confidence_manager, '_get_confidence_and_metadata') as mock_get:
            mock_get.return_value = (0.8, sample_metadata)
            
            metadata = await confidence_manager.get_confidence_metadata(node_uuid)
            
            assert metadata == sample_metadata
            mock_get.assert_called_once_with(node_uuid)

    async def test_calculate_network_reinforcement(self, confidence_manager):
        """Test network reinforcement calculation."""
        node_uuid = "test-uuid"
        connected_nodes = [
            EntityNode(uuid="connected1", name="Connected 1"),
            EntityNode(uuid="connected2", name="Connected 2"),
        ]
        
        with patch.object(confidence_manager, 'get_confidence') as mock_get_confidence:
            # Mock high confidence for connected nodes
            mock_get_confidence.side_effect = [0.8, 0.9]  # High confidence nodes
            
            boost = await confidence_manager.calculate_network_reinforcement(
                node_uuid, connected_nodes
            )
            
            # Should calculate boost based on connected node confidences
            assert boost > 0
            assert boost <= 0.2  # Should be capped at 0.2

    async def test_detect_origin_type_user_given(self, confidence_manager, sample_node):
        """Test origin type detection for user-given content."""
        episode_content = "I love pizza and I work as a software engineer"
        
        origin_type = await confidence_manager.detect_origin_type(
            sample_node, episode_content, is_duplicate=False
        )
        
        # Should detect user-given patterns
        assert origin_type == OriginType.USER_GIVEN

    async def test_detect_origin_type_inferred(self, confidence_manager, sample_node):
        """Test origin type detection for inferred content."""
        episode_content = "The user mentioned pizza and engineering"
        
        origin_type = await confidence_manager.detect_origin_type(
            sample_node, episode_content, is_duplicate=False
        )
        
        # Should detect inferred patterns
        assert origin_type == OriginType.INFERRED

    async def test_detect_origin_type_duplicate(self, confidence_manager, sample_node):
        """Test origin type detection for duplicate nodes."""
        episode_content = "Some content"
        
        origin_type = await confidence_manager.detect_origin_type(
            sample_node, episode_content, is_duplicate=True
        )
        
        # Duplicates should be treated as user-given (reaffirmation)
        assert origin_type == OriginType.USER_GIVEN

    async def test_apply_contradiction_penalties(self, confidence_manager):
        """Test applying contradiction penalties."""
        contradicted_uuid = "contradicted-uuid"
        contradicting_uuid = "contradicting-uuid"
        
        with patch.object(confidence_manager, 'get_confidence') as mock_get_confidence:
            # Mock high confidence for contradicting node
            mock_get_confidence.side_effect = [0.5, 0.8]  # contradicted, contradicting
            
            with patch.object(confidence_manager, 'update_confidence') as mock_update:
                mock_update.return_value = MagicMock()
                
                result = await confidence_manager.apply_contradiction_penalties(
                    contradicted_uuid, contradicting_uuid, contradiction_strength=1.0
                )
                
                assert result is not None
                mock_update.assert_called_once()

    async def test_apply_contradiction_penalties_low_confidence(self, confidence_manager):
        """Test contradiction penalties when contradicting node has low confidence."""
        contradicted_uuid = "contradicted-uuid"
        contradicting_uuid = "contradicting-uuid"
        
        with patch.object(confidence_manager, 'get_confidence') as mock_get_confidence:
            # Mock low confidence for contradicting node
            mock_get_confidence.side_effect = [0.5, 0.6]  # contradicted, contradicting (below threshold)
            
            result = await confidence_manager.apply_contradiction_penalties(
                contradicted_uuid, contradicting_uuid
            )
            
            # Should return None when contradicting node has low confidence
            assert result is None

    async def test_calculate_confidence_change(self, confidence_manager):
        """Test confidence change calculation for different triggers."""
        # Test user reaffirmation
        change = confidence_manager._calculate_confidence_change(ConfidenceTrigger.USER_REAFFIRMATION)
        assert change == 0.1
        
        # Test contradiction
        change = confidence_manager._calculate_confidence_change(ConfidenceTrigger.CONTRADICTION_DETECTED)
        assert change == -0.3
        
        # Test unknown trigger
        change = confidence_manager._calculate_confidence_change(ConfidenceTrigger.CONSISTENCY_CHECK)
        assert change == 0.02

    async def test_parse_confidence_metadata(self, confidence_manager):
        """Test parsing confidence metadata from JSON."""
        metadata_json = json.dumps({
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
            "revisions": 1,
            "supporting_co_ids": ["uuid1", "uuid2"],
            "contradicting_co_ids": ["uuid3"],
            "contradiction_resolution_status": "unresolved",
            "stability_score": 0.7
        })
        
        metadata = confidence_manager._parse_confidence_metadata(metadata_json)
        
        assert metadata.origin_type == OriginType.USER_GIVEN
        assert len(metadata.confidence_history) == 1
        assert metadata.revisions == 1
        assert metadata.supporting_co_ids == ["uuid1", "uuid2"]
        assert metadata.contradicting_co_ids == ["uuid3"]
        assert metadata.stability_score == 0.7

    async def test_serialize_confidence_metadata(self, confidence_manager, sample_metadata):
        """Test serializing confidence metadata to JSON."""
        json_str = confidence_manager._serialize_confidence_metadata(sample_metadata)
        
        # Should be valid JSON
        data = json.loads(json_str)
        
        assert data["origin_type"] == "user_given"
        assert len(data["confidence_history"]) == 1
        assert data["revisions"] == 0
        assert data["supporting_co_ids"] == []
        assert data["contradicting_co_ids"] == []

    async def test_serialize_confidence_metadata_error_handling(self, confidence_manager):
        """Test error handling in metadata serialization."""
        # Create metadata with non-serializable content
        metadata = ConfidenceMetadata(
            origin_type=OriginType.USER_GIVEN,
            confidence_history=[],
            last_user_validation=datetime.now()
        )
        
        # Should handle serialization errors gracefully
        json_str = confidence_manager._serialize_confidence_metadata(metadata)
        assert json_str == "{}"  # Should return empty object on error 