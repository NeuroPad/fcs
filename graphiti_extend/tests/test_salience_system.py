"""
Copyright 2025, FCS Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge
from graphiti_core.utils.datetime_utils import utc_now

from graphiti_extend.salience.manager import SalienceManager, SalienceConfig


class TestSalienceManager:
    """Test suite for SalienceManager functionality."""
    
    @pytest.fixture
    def mock_driver(self):
        """Create a mock Neo4j driver."""
        driver = AsyncMock()
        return driver
    
    @pytest.fixture
    def salience_config(self):
        """Create a test salience configuration."""
        return SalienceConfig()
    
    @pytest.fixture
    def salience_manager(self, mock_driver, salience_config):
        """Create a SalienceManager instance for testing."""
        return SalienceManager(mock_driver, salience_config)
    
    @pytest.fixture
    def cognitive_object_node(self):
        """Create a test CognitiveObject node."""
        return EntityNode(
            uuid="test-uuid-1",
            name="Test Cognitive Object",
            labels=["Entity", "CognitiveObject"],
            summary="A test cognitive object",
            attributes={
                "confidence": 0.7,
                "salience": 0.5
            },
            group_id="test-group"
        )
    
    @pytest.fixture
    def regular_entity_node(self):
        """Create a test regular Entity node."""
        return EntityNode(
            uuid="test-uuid-2",
            name="Regular Entity",
            labels=["Entity"],
            summary="A regular entity",
            attributes={},
            group_id="test-group"
        )

    @pytest.mark.asyncio
    async def test_direct_salience_update_duplicate_found(self, salience_manager, cognitive_object_node):
        """Test direct salience update for duplicate detection."""
        # Mock the connection count
        salience_manager._get_connection_count = AsyncMock(return_value=2)
        
        initial_salience = cognitive_object_node.attributes['salience']
        
        # Apply duplicate found trigger
        updated_nodes = await salience_manager.update_direct_salience(
            [cognitive_object_node], 'duplicate_found'
        )
        
        # Verify salience increased
        assert len(updated_nodes) == 1
        final_salience = updated_nodes[0].attributes['salience']
        assert final_salience > initial_salience
        
        # Should be approximately initial + (0.25 * multipliers)
        # With confidence 0.7, connectivity 2, recency 1.0:
        # reinforcement = 0.25 * (1 + 2*0.05) * 1.0 * (0.7 + 0.7*0.3) = 0.25 * 1.1 * 1.0 * 0.91 ≈ 0.25
        expected_increase = 0.25 * 1.1 * 1.0 * 0.91  # approximately 0.25
        assert abs(final_salience - (initial_salience + expected_increase)) < 0.05

    @pytest.mark.asyncio
    async def test_direct_salience_update_conversation_mention(self, salience_manager, cognitive_object_node):
        """Test direct salience update for conversation mention."""
        salience_manager._get_connection_count = AsyncMock(return_value=0)
        
        initial_salience = cognitive_object_node.attributes['salience']
        
        updated_nodes = await salience_manager.update_direct_salience(
            [cognitive_object_node], 'conversation_mention'
        )
        
        final_salience = updated_nodes[0].attributes['salience']
        assert final_salience > initial_salience
        
        # Should be approximately initial + (0.3 * multipliers)
        expected_increase = 0.3 * 1.0 * 1.0 * 0.91  # approximately 0.27
        assert abs(final_salience - (initial_salience + expected_increase)) < 0.05

    @pytest.mark.asyncio
    async def test_salience_cap_at_max(self, salience_manager, cognitive_object_node):
        """Test that salience is capped at maximum value."""
        # Set initial salience high
        cognitive_object_node.attributes['salience'] = 0.95
        salience_manager._get_connection_count = AsyncMock(return_value=5)
        
        updated_nodes = await salience_manager.update_direct_salience(
            [cognitive_object_node], 'conversation_mention'
        )
        
        # Should be capped at 1.0
        assert updated_nodes[0].attributes['salience'] == 1.0

    @pytest.mark.asyncio
    async def test_non_cognitive_object_unchanged(self, salience_manager, regular_entity_node):
        """Test that non-CognitiveObject nodes are unchanged."""
        initial_attributes = regular_entity_node.attributes.copy()
        
        updated_nodes = await salience_manager.update_direct_salience(
            [regular_entity_node], 'duplicate_found'
        )
        
        # Attributes should be unchanged
        assert updated_nodes[0].attributes == initial_attributes

    @pytest.mark.asyncio
    async def test_network_reinforcement(self, salience_manager, cognitive_object_node):
        """Test network pathway reinforcement."""
        # Mock finding connected nodes
        connected_nodes = [
            ("connected-uuid-1", 1, 0.8),  # 1 hop, 0.8 confidence
            ("connected-uuid-2", 2, 0.6),  # 2 hops, 0.6 confidence
        ]
        salience_manager._find_connected_cognitive_objects = AsyncMock(return_value=connected_nodes)
        
        # Mock applying reinforcement
        salience_manager._apply_network_reinforcement_batch = AsyncMock()
        
        result_count = await salience_manager.propagate_network_reinforcement([cognitive_object_node])
        
        # Should have processed 2 connected nodes
        assert result_count == 2
        
        # Verify batch reinforcement was called
        salience_manager._apply_network_reinforcement_batch.assert_called_once()
        
        # Check the reinforcement map
        call_args = salience_manager._apply_network_reinforcement_batch.call_args[0][0]
        assert "connected-uuid-1" in call_args
        assert "connected-uuid-2" in call_args
        
        # Verify reinforcement calculations
        node_salience = cognitive_object_node.attributes['salience']  # 0.5
        expected_reinforcement_1 = 0.05 * (1.0 / 1) * 0.8 * node_salience  # 0.02
        expected_reinforcement_2 = 0.05 * (1.0 / 2) * 0.6 * node_salience  # 0.0075
        
        assert abs(call_args["connected-uuid-1"] - expected_reinforcement_1) < 0.001
        assert abs(call_args["connected-uuid-2"] - expected_reinforcement_2) < 0.001

    @pytest.mark.asyncio
    async def test_structural_boost(self, salience_manager, cognitive_object_node):
        """Test structural importance boost."""
        # Mock high-confidence connections (above threshold)
        salience_manager._count_high_confidence_connections = AsyncMock(return_value=4)
        
        initial_salience = cognitive_object_node.attributes['salience']
        
        updated_nodes = await salience_manager.apply_structural_boosts([cognitive_object_node])
        
        # Should have received structural boost
        final_salience = updated_nodes[0].attributes['salience']
        assert final_salience == initial_salience + 0.15  # STRUCTURAL_BOOST

    @pytest.mark.asyncio
    async def test_no_structural_boost_insufficient_connections(self, salience_manager, cognitive_object_node):
        """Test no structural boost for insufficient connections."""
        # Mock low connection count
        salience_manager._count_high_confidence_connections = AsyncMock(return_value=2)
        
        initial_salience = cognitive_object_node.attributes['salience']
        
        updated_nodes = await salience_manager.apply_structural_boosts([cognitive_object_node])
        
        # Should have no change
        final_salience = updated_nodes[0].attributes['salience']
        assert final_salience == initial_salience

    @pytest.mark.asyncio
    async def test_decay_calculation(self, salience_manager):
        """Test decay amount calculation."""
        # Test normal decay
        decay = await salience_manager._calculate_decay_amount(
            current_salience=0.8,
            confidence=0.7,
            days_since_update=7,
            connection_count=3
        )
        
        # Should be base decay with connection resistance
        # Base decay = 0.02, connection resistance = min(0.8, 3 * 0.1) = 0.3
        # Final decay = 0.02 * (1 - 0.3) = 0.014
        expected_decay = 0.02 * (1 - 0.3)
        assert abs(decay - expected_decay) < 0.001

    @pytest.mark.asyncio
    async def test_decay_calculation_orphaned(self, salience_manager):
        """Test decay calculation for orphaned nodes."""
        decay = await salience_manager._calculate_decay_amount(
            current_salience=0.5,
            confidence=0.7,
            days_since_update=20,  # > 14 days
            connection_count=0     # orphaned
        )
        
        # Should have base + no_reference + orphaned decay, no resistance
        # decay = (0.02 + 0.1 + 0.2) * (1 - 0) = 0.32
        expected_decay = (0.02 + 0.1 + 0.2) * 1.0
        assert abs(decay - expected_decay) < 0.001

    @pytest.mark.asyncio
    async def test_should_delete_orphaned_node(self, salience_manager):
        """Test deletion criteria for orphaned nodes."""
        should_delete = await salience_manager._should_delete_node(
            uuid="test-uuid",
            salience=0.05,  # Below threshold
            confidence=0.5,
            connection_count=0,  # Orphaned
            days_since_update=35  # > 30 days
        )
        
        assert should_delete is True

    @pytest.mark.asyncio
    async def test_should_not_delete_well_connected_node(self, salience_manager):
        """Test that well-connected nodes are not deleted."""
        # Mock the dismissed flags check to avoid database call
        salience_manager._check_dismissed_flags = AsyncMock(return_value=False)
        
        should_delete = await salience_manager._should_delete_node(
            uuid="test-uuid",
            salience=0.05,  # Below threshold
            confidence=0.2,
            connection_count=5,  # Well connected
            days_since_update=100
        )
        
        assert should_delete is False

    @pytest.mark.asyncio
    async def test_reinforcement_weight_calculation(self, salience_manager, cognitive_object_node):
        """Test the reinforcement weight calculation with all multipliers."""
        # Mock connection count
        salience_manager._get_connection_count = AsyncMock(return_value=3)
        
        base_increment = 0.25
        current_time = utc_now()
        
        weight = await salience_manager._calculate_reinforcement_weight(
            cognitive_object_node, base_increment, current_time
        )
        
        # Calculate expected weight
        confidence = 0.7
        connectivity_multiplier = 1 + (3 * 0.05)  # 1.15
        recency_multiplier = 1.0  # Normal
        confidence_multiplier = 0.7 + (0.7 * 0.3)  # 0.91
        
        expected_weight = base_increment * connectivity_multiplier * recency_multiplier * confidence_multiplier
        expected_weight = 0.25 * 1.15 * 1.0 * 0.91
        
        assert abs(weight - expected_weight) < 0.001

    @pytest.mark.asyncio
    async def test_run_decay_cycle(self, salience_manager):
        """Test running a complete decay cycle."""
        # Mock getting cognitive objects
        mock_objects = [
            {
                'uuid': 'uuid-1',
                'salience': 0.6,
                'confidence': 0.7,
                'updated_at': utc_now() - timedelta(days=5),
                'created_at': utc_now() - timedelta(days=30),
                'name': 'Test Node 1'
            },
            {
                'uuid': 'uuid-2',
                'salience': 0.1,
                'confidence': 0.2,
                'updated_at': utc_now() - timedelta(days=40),
                'created_at': utc_now() - timedelta(days=80),
                'name': 'Test Node 2'
            }
        ]
        
        # Mock all the database operations
        salience_manager._get_cognitive_objects_batch = AsyncMock()
        salience_manager._get_cognitive_objects_batch.side_effect = [mock_objects, []]  # First call returns objects, second returns empty
        
        salience_manager._get_connection_count = AsyncMock(return_value=2)
        salience_manager._check_dismissed_flags = AsyncMock(return_value=False)
        salience_manager._apply_decay_updates = AsyncMock()
        salience_manager._delete_nodes = AsyncMock()
        
        stats = await salience_manager.run_decay_cycle()
        
        # Should have processed nodes
        assert stats['processed'] >= 2
        
        # Verify methods were called
        salience_manager._apply_decay_updates.assert_called()

    @pytest.mark.asyncio
    async def test_is_cognitive_object(self, salience_manager, cognitive_object_node, regular_entity_node):
        """Test cognitive object identification."""
        assert salience_manager._is_cognitive_object(cognitive_object_node) is True
        assert salience_manager._is_cognitive_object(regular_entity_node) is False

    @pytest.mark.asyncio
    async def test_empty_node_list_handling(self, salience_manager):
        """Test handling of empty node lists."""
        result = await salience_manager.update_direct_salience([], 'duplicate_found')
        assert result == []
        
        result = await salience_manager.propagate_network_reinforcement([])
        assert result == 0
        
        result = await salience_manager.apply_structural_boosts([])
        assert result == []

    @pytest.mark.asyncio
    async def test_multiple_triggers_same_node(self, salience_manager, cognitive_object_node):
        """Test applying multiple triggers to the same node."""
        salience_manager._get_connection_count = AsyncMock(return_value=1)
        
        initial_salience = cognitive_object_node.attributes['salience']
        
        # Apply duplicate found
        nodes = await salience_manager.update_direct_salience(
            [cognitive_object_node], 'duplicate_found'
        )
        intermediate_salience = nodes[0].attributes['salience']
        
        # Apply reasoning usage
        nodes = await salience_manager.update_direct_salience(
            nodes, 'reasoning_usage'
        )
        final_salience = nodes[0].attributes['salience']
        
        # Should have cumulative increases
        assert final_salience > intermediate_salience > initial_salience


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 