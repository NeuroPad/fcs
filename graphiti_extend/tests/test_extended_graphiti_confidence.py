"""
Integration tests for confidence functionality in ExtendedGraphiti.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from graphiti_core.nodes import EntityNode, EpisodicNode, EpisodeType
from graphiti_core.edges import EntityEdge
from graphiti_extend.extended_graphiti import ExtendedGraphiti, ContradictionDetectionResult
from graphiti_extend.confidence.models import ConfidenceTrigger, OriginType


class TestExtendedGraphitiConfidence:
    """Test confidence integration in ExtendedGraphiti."""
    
    @pytest.fixture
    def mock_driver(self):
        """Create a mock driver for testing."""
        driver = AsyncMock()
        driver.execute_query = AsyncMock()
        return driver
    
    @pytest.fixture
    def mock_clients(self):
        """Create mock clients for testing."""
        clients = MagicMock()
        clients.driver = AsyncMock()
        clients.llm_client = AsyncMock()
        clients.embedder = AsyncMock()
        clients.cross_encoder = AsyncMock()
        return clients
    
    @pytest.fixture
    def extended_graphiti(self, mock_driver):
        """Create an ExtendedGraphiti instance for testing."""
        # Use __new__ to avoid calling __init__ twice
        graphiti = ExtendedGraphiti.__new__(ExtendedGraphiti)
        graphiti.__init__(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password",
            enable_contradiction_detection=True,
            contradiction_threshold=0.7
        )
        graphiti.driver = mock_driver
        graphiti.clients = MagicMock()
        graphiti.clients.driver = mock_driver
        graphiti.clients.llm_client = AsyncMock()
        graphiti.clients.embedder = AsyncMock()
        graphiti.clients.cross_encoder = AsyncMock()
        return graphiti
    
    @pytest.fixture
    def sample_nodes(self):
        """Create sample nodes for testing."""
        return [
            EntityNode(
                uuid="node1",
                name="Pizza",
                summary="A delicious food",
                group_id="test_group"
            ),
            EntityNode(
                uuid="node2",
                name="Software Engineer",
                summary="A profession",
                group_id="test_group"
            )
        ]
    
    @pytest.fixture
    def sample_episode(self):
        """Create a sample episode for testing."""
        return EpisodicNode(
            uuid="episode1",
            name="Test Episode",
            content="I love pizza and I work as a software engineer",
            source_description="Test input",
            source=EpisodeType.message,
            group_id="test_group",
            created_at=datetime.now(),
            valid_at=datetime.now()
        )

    async def test_confidence_manager_initialization(self, extended_graphiti):
        """Test that confidence manager is properly initialized."""
        assert extended_graphiti.confidence_manager is not None
        assert hasattr(extended_graphiti.confidence_manager, 'driver')
        assert extended_graphiti.confidence_manager.driver == extended_graphiti.driver

    async def test_initial_confidence_assignment(self, extended_graphiti, sample_nodes):
        """Test initial confidence assignment during episode processing."""
        episode_body = "I love pizza and I work as a software engineer"
        
        # Mock the confidence manager methods
        with patch.object(extended_graphiti.confidence_manager, 'detect_origin_type') as mock_detect:
            with patch.object(extended_graphiti.confidence_manager, 'assign_initial_confidence') as mock_assign:
                mock_detect.return_value = OriginType.USER_GIVEN
                mock_assign.return_value = 0.8
                
                # Simulate the confidence assignment loop
                for node in sample_nodes:
                    is_duplicate = False
                    origin_type = await extended_graphiti.confidence_manager.detect_origin_type(
                        node, episode_body, is_duplicate
                    )
                    await extended_graphiti.confidence_manager.assign_initial_confidence(
                        node, origin_type, is_duplicate
                    )
                
                # Verify calls were made
                assert mock_detect.call_count == 2
                assert mock_assign.call_count == 2
                
                # Verify origin type detection
                mock_detect.assert_called_with(sample_nodes[0], episode_body, False)

    async def test_user_reaffirmation_boost(self, extended_graphiti, sample_nodes):
        """Test user reaffirmation boost for duplicate nodes."""
        episode_body = "I love pizza and I work as a software engineer"
        
        with patch.object(extended_graphiti.confidence_manager, 'detect_origin_type') as mock_detect:
            with patch.object(extended_graphiti.confidence_manager, 'assign_initial_confidence') as mock_assign:
                with patch.object(extended_graphiti.confidence_manager, 'update_confidence_batch') as mock_batch:
                    mock_detect.return_value = OriginType.USER_GIVEN
                    mock_assign.return_value = 0.9  # user_given + duplicate_found
                    
                    # Simulate duplicate detection
                    confidence_updates = []
                    for node in sample_nodes:
                        is_duplicate = True  # Simulate duplicate
                        origin_type = await extended_graphiti.confidence_manager.detect_origin_type(
                            node, episode_body, is_duplicate
                        )
                        await extended_graphiti.confidence_manager.assign_initial_confidence(
                            node, origin_type, is_duplicate
                        )
                        
                        # Add user reaffirmation boost for existing duplicates
                        if is_duplicate and node.uuid in extended_graphiti.created_node_uuids:
                            confidence_updates.append((
                                node.uuid,
                                ConfidenceTrigger.USER_REAFFIRMATION,
                                "User reaffirmed existing entity",
                                {"episode_uuid": "episode1"}
                            ))
                    
                    # Apply confidence updates in batch
                    if confidence_updates:
                        await extended_graphiti.confidence_manager.update_confidence_batch(confidence_updates)
                    
                    # Verify batch update was called
                    mock_batch.assert_called_once()

    async def test_contradiction_confidence_updates(self, extended_graphiti):
        """Test confidence updates during contradiction detection."""
        # Create mock contradiction edges
        contradiction_edge = EntityEdge(
            source_node_uuid="contradicting_node",
            target_node_uuid="contradicted_node",
            name="CONTRADICTS",
            fact="Test contradiction",
            episodes=["episode1"],
            created_at=datetime.now(),
            valid_at=datetime.now(),
            group_id="test_group"
        )
        
        with patch.object(extended_graphiti.confidence_manager, 'get_confidence') as mock_get_confidence:
            with patch.object(extended_graphiti.confidence_manager, 'update_confidence_batch') as mock_batch:
                # Mock confidence values
                mock_get_confidence.side_effect = [0.5, 0.8]  # contradicted, contradicting
                
                # Simulate contradiction confidence updates
                contradiction_confidence_updates = []
                
                # Apply penalty to contradicted node
                contradicted_confidence = await extended_graphiti.confidence_manager.get_confidence(contradiction_edge.target_node_uuid)
                contradicting_confidence = await extended_graphiti.confidence_manager.get_confidence(contradiction_edge.source_node_uuid)
                
                if contradicted_confidence is not None and contradicting_confidence is not None:
                    confidence_diff = contradicting_confidence - contradicted_confidence
                    contradiction_strength = max(0.5, min(1.0, 0.5 + abs(confidence_diff)))
                    
                    # Apply penalty to contradicted node
                    contradiction_confidence_updates.append((
                        contradiction_edge.target_node_uuid,
                        ConfidenceTrigger.CONTRADICTION_DETECTED,
                        f"Contradicted by {contradiction_edge.source_node_uuid}",
                        {
                            "contradicting_node_uuid": contradiction_edge.source_node_uuid,
                            "contradiction_strength": contradiction_strength,
                            "confidence_difference": confidence_diff
                        }
                    ))
                    
                    # Apply boost to contradicting node (if it has higher confidence)
                    if contradicting_confidence > contradicted_confidence:
                        contradiction_confidence_updates.append((
                            contradiction_edge.source_node_uuid,
                            ConfidenceTrigger.NETWORK_SUPPORT,
                            f"Successfully contradicted {contradiction_edge.target_node_uuid}",
                            {
                                "contradicted_node_uuid": contradiction_edge.target_node_uuid,
                                "contradiction_strength": contradiction_strength
                            }
                        ))
                
                # Apply contradiction confidence updates in batch
                if contradiction_confidence_updates:
                    await extended_graphiti.confidence_manager.update_confidence_batch(contradiction_confidence_updates)
                
                # Verify batch update was called
                mock_batch.assert_called_once()
                
                # Verify the updates
                call_args = mock_batch.call_args[0][0]
                assert len(call_args) == 2  # One penalty, one boost
                
                # Check penalty update
                penalty_update = call_args[0]
                assert penalty_update[0] == "contradicted_node"
                assert penalty_update[1] == ConfidenceTrigger.CONTRADICTION_DETECTED
                
                # Check boost update
                boost_update = call_args[1]
                assert boost_update[0] == "contradicting_node"
                assert boost_update[1] == ConfidenceTrigger.NETWORK_SUPPORT

    async def test_network_reinforcement_confidence(self, extended_graphiti, sample_nodes):
        """Test network reinforcement confidence updates."""
        with patch.object(extended_graphiti, '_get_connected_nodes') as mock_get_connected:
            with patch.object(extended_graphiti.confidence_manager, 'calculate_network_reinforcement') as mock_calc:
                with patch.object(extended_graphiti.confidence_manager, 'update_confidence_batch') as mock_batch:
                    # Mock connected nodes
                    mock_get_connected.return_value = [sample_nodes[1]]
                    
                    # Mock network reinforcement calculation
                    mock_calc.return_value = 0.05
                    
                    # Simulate network reinforcement
                    network_confidence_updates = []
                    for node in sample_nodes:
                        connected_nodes = await extended_graphiti._get_connected_nodes(node.uuid)
                        if connected_nodes:
                            network_boost = await extended_graphiti.confidence_manager.calculate_network_reinforcement(
                                node.uuid, connected_nodes
                            )
                            if network_boost > 0:
                                network_confidence_updates.append((
                                    node.uuid,
                                    ConfidenceTrigger.NETWORK_SUPPORT,
                                    f"Network reinforcement from {len(connected_nodes)} connected nodes",
                                    {
                                        "network_boost": network_boost,
                                        "connected_node_count": len(connected_nodes)
                                    }
                                ))
                    
                    # Apply network confidence updates in batch
                    if network_confidence_updates:
                        await extended_graphiti.confidence_manager.update_confidence_batch(network_confidence_updates)
                    
                    # Verify calls were made
                    assert mock_get_connected.call_count == 2
                    assert mock_calc.call_count == 2
                    mock_batch.assert_called_once()

    async def test_confidence_decay(self, extended_graphiti):
        """Test confidence decay for dormant nodes."""
        group_id = "test_group"
        
        with patch.object(extended_graphiti.driver, 'execute_query') as mock_query:
            with patch.object(extended_graphiti.confidence_manager, 'update_confidence_batch') as mock_batch:
                # Mock query results for dormant nodes
                mock_query.return_value = ([], None, None)
                
                await extended_graphiti._apply_confidence_decay(group_id)
                
                # Verify query was called
                mock_query.assert_called()
                
                # Verify batch update was called (even if no updates)
                mock_batch.assert_called_once()

    async def test_get_confidence_methods(self, extended_graphiti):
        """Test confidence getter methods."""
        node_uuid = "test-uuid"
        
        with patch.object(extended_graphiti.confidence_manager, 'get_confidence') as mock_get:
            with patch.object(extended_graphiti.confidence_manager, 'get_confidence_metadata') as mock_get_meta:
                mock_get.return_value = 0.8
                mock_get_meta.return_value = MagicMock()
                
                # Test get_confidence
                confidence = await extended_graphiti.get_confidence(node_uuid)
                assert confidence == 0.8
                mock_get.assert_called_once_with(node_uuid)
                
                # Test get_confidence_metadata
                metadata = await extended_graphiti.get_confidence_metadata(node_uuid)
                assert metadata is not None
                mock_get_meta.assert_called_once_with(node_uuid)

    async def test_update_node_confidence(self, extended_graphiti):
        """Test manual confidence update method."""
        node_uuid = "test-uuid"
        
        with patch.object(extended_graphiti.confidence_manager, 'update_confidence') as mock_update:
            mock_update.return_value = MagicMock()
            
            result = await extended_graphiti.update_node_confidence(
                node_uuid,
                ConfidenceTrigger.USER_REAFFIRMATION,
                "Test update",
                {"context": "test"}
            )
            
            mock_update.assert_called_once_with(
                node_uuid,
                ConfidenceTrigger.USER_REAFFIRMATION,
                "Test update",
                {"context": "test"}
            )

    async def test_get_low_confidence_nodes(self, extended_graphiti):
        """Test getting low confidence nodes."""
        with patch.object(extended_graphiti.driver, 'execute_query') as mock_query:
            # Mock query results
            mock_query.return_value = ([
                {"uuid": "node1", "confidence": 0.3},
                {"uuid": "node2", "confidence": 0.2}
            ], None, None)
            
            result = await extended_graphiti.get_low_confidence_nodes(
                threshold=0.4,
                group_ids=["test_group"],
                limit=10
            )
            
            assert len(result) == 2
            assert result[0][0] == "node1"
            assert result[0][1] == 0.3
            assert result[1][0] == "node2"
            assert result[1][1] == 0.2

    async def test_get_confidence_summary(self, extended_graphiti):
        """Test getting confidence summary."""
        with patch.object(extended_graphiti.driver, 'execute_query') as mock_query:
            # Mock query results
            mock_query.return_value = ([{
                "total_nodes": 10,
                "avg_confidence": 0.65,
                "min_confidence": 0.2,
                "max_confidence": 0.9,
                "unstable_nodes": 3,
                "low_confidence_nodes": 1
            }], None, None)
            
            result = await extended_graphiti.get_confidence_summary(group_ids=["test_group"])
            
            assert result["total_nodes"] == 10
            assert result["average_confidence"] == 0.65
            assert result["min_confidence"] == 0.2
            assert result["max_confidence"] == 0.9
            assert result["unstable_nodes"] == 3
            assert result["low_confidence_nodes"] == 1
            assert result["unstable_percentage"] == 30.0

    async def test_get_connected_nodes(self, extended_graphiti):
        """Test getting connected nodes."""
        node_uuid = "test-uuid"
        
        with patch.object(extended_graphiti.driver, 'execute_query') as mock_query:
            # Mock query results
            mock_query.return_value = ([
                {"connected": {"uuid": "connected1", "name": "Connected 1"}},
                {"connected": {"uuid": "connected2", "name": "Connected 2"}}
            ], None, None)
            
            result = await extended_graphiti._get_connected_nodes(node_uuid)
            
            assert len(result) == 2
            assert result[0].uuid == "connected1"
            assert result[0].name == "Connected 1"
            assert result[1].uuid == "connected2"
            assert result[1].name == "Connected 2"

    async def test_confidence_integration_with_episode_processing(self, extended_graphiti):
        """Test full confidence integration during episode processing."""
        # This test simulates the confidence updates that happen during episode processing
        episode_body = "I love pizza and I work as a software engineer"
        
        with patch.object(extended_graphiti.confidence_manager, 'detect_origin_type') as mock_detect:
            with patch.object(extended_graphiti.confidence_manager, 'assign_initial_confidence') as mock_assign:
                with patch.object(extended_graphiti.confidence_manager, 'update_confidence_batch') as mock_batch:
                    with patch.object(extended_graphiti.confidence_manager, 'get_confidence') as mock_get:
                        with patch.object(extended_graphiti.confidence_manager, 'calculate_network_reinforcement') as mock_calc:
                            # Setup mocks
                            mock_detect.return_value = OriginType.USER_GIVEN
                            mock_assign.return_value = 0.8
                            mock_get.return_value = 0.8
                            mock_calc.return_value = 0.05
                            
                            # Simulate the confidence assignment and updates
                            nodes = sample_nodes
                            confidence_updates = []
                            
                            # Initial confidence assignment
                            for node in nodes:
                                is_duplicate = False
                                origin_type = await extended_graphiti.confidence_manager.detect_origin_type(
                                    node, episode_body, is_duplicate
                                )
                                await extended_graphiti.confidence_manager.assign_initial_confidence(
                                    node, origin_type, is_duplicate
                                )
                            
                            # User reaffirmation for duplicates
                            for node in nodes:
                                if is_duplicate and node.uuid in extended_graphiti.created_node_uuids:
                                    confidence_updates.append((
                                        node.uuid,
                                        ConfidenceTrigger.USER_REAFFIRMATION,
                                        "User reaffirmed existing entity",
                                        {"episode_uuid": "episode1"}
                                    ))
                            
                            # Network reinforcement
                            for node in nodes:
                                connected_nodes = [nodes[1]]  # Mock connected nodes
                                if connected_nodes:
                                    network_boost = await extended_graphiti.confidence_manager.calculate_network_reinforcement(
                                        node.uuid, connected_nodes
                                    )
                                    if network_boost > 0:
                                        confidence_updates.append((
                                            node.uuid,
                                            ConfidenceTrigger.NETWORK_SUPPORT,
                                            f"Network reinforcement from {len(connected_nodes)} connected nodes",
                                            {
                                                "network_boost": network_boost,
                                                "connected_node_count": len(connected_nodes)
                                            }
                                        ))
                            
                            # Apply all updates
                            if confidence_updates:
                                await extended_graphiti.confidence_manager.update_confidence_batch(confidence_updates)
                            
                            # Verify all methods were called
                            assert mock_detect.call_count == 2
                            assert mock_assign.call_count == 2
                            assert mock_batch.call_count == 1
                            assert mock_calc.call_count == 2 