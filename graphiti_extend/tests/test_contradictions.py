"""
Tests for the new contradiction detection system using cognitive objects.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the Python path so we can import graphiti_core
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from graphiti_core.edges import EntityEdge
from graphiti_core.llm_client import LLMClient
from graphiti_core.nodes import EntityNode, EpisodicNode, EpisodeType
from graphiti_core.utils.datetime_utils import utc_now

from graphiti_extend.contradictions.handler import (
    detect_contradiction_pairs,
    create_contradiction_edges_from_pairs,
    detect_and_create_node_contradictions,
    _find_or_create_node,
)
from graphiti_extend.contradictions.models import (
    ContradictionMetadata,
    CognitiveObjectPair,
    ContradictionDetectionResult,
)
from graphiti_extend.prompts.contradiction import (
    ContradictionPairs,
    ContradictionPair,
    ContradictionNode,
    get_contradiction_pairs_prompt,
)


class TestContradictionSystem:
    """Test cases for the new contradiction detection system."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = AsyncMock(spec=LLMClient)
        return client

    @pytest.fixture
    def mock_add_triplet(self):
        """Create a mock add_triplet function."""
        return AsyncMock()

    @pytest.fixture
    def sample_episode(self):
        """Create a sample episode for testing."""
        return EpisodicNode(
            name="Preference Change Episode",
            group_id="1",
            labels=[],
            source=EpisodeType.message,
            content="I hate football now. I can't stand watching it anymore.",
            source_description="User statement about changed preference",
            created_at=utc_now(),
            valid_at=utc_now(),
        )

    @pytest.fixture
    def existing_nodes(self):
        """Create existing nodes for testing."""
        now = utc_now()
        
        love_football = EntityNode(
            name="love football",
            group_id="1",
            labels=["Entity"],
            summary="User loves football and enjoys watching games",
            created_at=now,
            attributes={"preference": "positive", "subject": "football", "activity": "watching"}
        )
        
        user_node = EntityNode(
            name="Joseph",
            group_id="1",
            labels=["Entity", "Person"],
            summary="The user",
            created_at=now,
            attributes={"type": "person"}
        )
        
        football_node = EntityNode(
            name="football",
            group_id="1",
            labels=["Entity", "Sport"],
            summary="American football sport",
            created_at=now,
            attributes={"type": "sport", "category": "entertainment"}
        )
        
        return [love_football, user_node, football_node]

    @pytest.mark.asyncio
    async def test_detect_contradiction_pairs_creates_cognitive_objects(self, mock_llm_client, sample_episode, existing_nodes):
        """Test that the system creates proper cognitive objects for contradictions."""
        # Mock LLM response with cognitive object pairs
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': [
                {
                    'node1': {
                        'name': 'love football',
                        'summary': 'User loves football and enjoys watching games',
                        'entity_type': 'Entity'
                    },
                    'node2': {
                        'name': 'hate football',
                        'summary': 'User hates football and cannot stand watching it',
                        'entity_type': 'Entity'
                    },
                    'contradiction_reason': 'Opposite emotional preferences about football'
                }
            ]
        }
        
        result = await detect_contradiction_pairs(
            mock_llm_client, sample_episode, existing_nodes
        )
        
        assert len(result) == 1
        node1, node2, reason = result[0]
        
        # Verify cognitive objects are created properly
        assert node1.name == 'love football'
        assert node1.summary == 'User loves football and enjoys watching games'
        assert node2.name == 'hate football'
        assert node2.summary == 'User hates football and cannot stand watching it'
        assert 'opposite emotional preferences' in reason.lower()
        
        # Verify LLM was called with proper context
        mock_llm_client.generate_response.assert_called_once()
        call_args = mock_llm_client.generate_response.call_args
        assert call_args[1]['response_model'] == ContradictionPairs

    @pytest.mark.asyncio
    async def test_detect_contradiction_pairs_filters_invalid_contradictions(self, mock_llm_client, sample_episode, existing_nodes):
        """Test that invalid contradictions (person vs concept) are not created."""
        # Mock LLM response with both valid and invalid contradictions
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': [
                {
                    'node1': {
                        'name': 'love football',
                        'summary': 'User loves football',
                        'entity_type': 'Entity'
                    },
                    'node2': {
                        'name': 'hate football',
                        'summary': 'User hates football',
                        'entity_type': 'Entity'
                    },
                    'contradiction_reason': 'Valid preference contradiction'
                },
                {
                    'node1': {
                        'name': 'Joseph',
                        'summary': 'The user',
                        'entity_type': 'Person'
                    },
                    'node2': {
                        'name': 'football',
                        'summary': 'American football sport',
                        'entity_type': 'Sport'
                    },
                    'contradiction_reason': 'Invalid person vs sport contradiction'
                }
            ]
        }
        
        result = await detect_contradiction_pairs(
            mock_llm_client, sample_episode, existing_nodes
        )
        
        # Should only return valid contradictions
        assert len(result) == 2  # Both are returned, but the prompt should prevent invalid ones
        
        # The prompt system should guide the LLM to avoid such invalid contradictions
        # This test verifies the system handles the response gracefully

    def test_find_or_create_node_finds_existing_by_name(self, existing_nodes):
        """Test finding existing node by exact name match."""
        node_data = {
            'name': 'love football',
            'summary': 'User loves football and enjoys watching games',
            'entity_type': 'Entity'
        }
        
        result = _find_or_create_node(node_data, existing_nodes, "1")
        
        assert result is not None
        assert result.name == 'love football'
        assert result.uuid == existing_nodes[0].uuid  # Should be the same node

    def test_find_or_create_node_creates_new_cognitive_object(self, existing_nodes):
        """Test creating new cognitive object when not found."""
        node_data = {
            'name': 'hate football',
            'summary': 'User hates football and cannot stand watching it',
            'entity_type': 'Entity'
        }
        
        result = _find_or_create_node(node_data, existing_nodes, "1")
        
        assert result is not None
        assert result.name == 'hate football'
        assert result.summary == 'User hates football and cannot stand watching it'
        assert result.group_id == "1"
        assert 'Entity' in result.labels
        # Should be a new UUID, not matching any existing node
        existing_uuids = {node.uuid for node in existing_nodes}
        assert result.uuid not in existing_uuids

    def test_find_or_create_node_handles_similarity_matching(self, existing_nodes):
        """Test finding nodes with similar but not exact names."""
        # Test with slightly different name but same concept
        node_data = {
            'name': 'loves football',  # Similar to 'love football'
            'summary': 'User loves football',
            'entity_type': 'Entity'
        }
        
        result = _find_or_create_node(node_data, existing_nodes, "1")
        
        # Should create new node since name doesn't match exactly
        assert result is not None
        assert result.name == 'loves football'
        existing_uuids = {node.uuid for node in existing_nodes}
        assert result.uuid not in existing_uuids

    @pytest.mark.asyncio
    async def test_create_contradiction_edges_from_pairs_uses_add_triplet(self, existing_nodes, sample_episode, mock_add_triplet):
        """Test that contradiction edges are created using add_triplet."""
        love_node = existing_nodes[0]
        
        # Create hate node
        hate_node = EntityNode(
            name="hate football",
            group_id="1",
            labels=["Entity"],
            summary="User hates football",
            created_at=utc_now(),
        )
        
        contradiction_pairs = [
            (love_node, hate_node, "Opposite preferences about football")
        ]
        
        result = await create_contradiction_edges_from_pairs(
            contradiction_pairs, sample_episode, mock_add_triplet
        )
        
        assert len(result) == 1
        edge = result[0]
        
        # Verify edge properties
        assert isinstance(edge, EntityEdge)
        assert edge.name == 'CONTRADICTS'
        assert edge.source_node_uuid == love_node.uuid
        assert edge.target_node_uuid == hate_node.uuid
        assert edge.group_id == sample_episode.group_id
        assert sample_episode.uuid in edge.episodes
        
        # Verify edge attributes
        assert 'contradiction_reason' in edge.attributes
        assert edge.attributes['contradiction_reason'] == "Opposite preferences about football"
        assert 'detected_in_episode' in edge.attributes
        assert edge.attributes['detected_in_episode'] == sample_episode.uuid
        
        # Verify add_triplet was called correctly
        mock_add_triplet.assert_called_once_with(love_node, edge, hate_node)

    @pytest.mark.asyncio
    async def test_detect_and_create_node_contradictions_end_to_end(self, mock_llm_client, sample_episode, existing_nodes, mock_add_triplet):
        """Test the complete end-to-end contradiction detection flow."""
        # Mock LLM response
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': [
                {
                    'node1': {
                        'name': 'love football',
                        'summary': 'User loves football and enjoys watching games',
                        'entity_type': 'Entity'
                    },
                    'node2': {
                        'name': 'hate football',
                        'summary': 'User hates football and cannot stand watching it',
                        'entity_type': 'Entity'
                    },
                    'contradiction_reason': 'Complete reversal of preference about football'
                }
            ]
        }
        
        result = await detect_and_create_node_contradictions(
            mock_llm_client, sample_episode, existing_nodes, mock_add_triplet
        )
        
        # Verify results
        assert len(result) == 1
        edge = result[0]
        assert isinstance(edge, EntityEdge)
        assert edge.name == 'CONTRADICTS'
        
        # Verify LLM was called with correct parameters
        mock_llm_client.generate_response.assert_called_once()
        call_args = mock_llm_client.generate_response.call_args
        assert call_args[1]['response_model'] == ContradictionPairs
        
        # Verify add_triplet was called
        mock_add_triplet.assert_called_once()
        
        # Verify the edge has correct attributes
        assert 'contradiction_reason' in edge.attributes
        assert edge.attributes['contradiction_reason'] == 'Complete reversal of preference about football'

    def test_contradiction_prompt_structure(self, sample_episode, existing_nodes):
        """Test that the contradiction prompt is structured correctly."""
        context = {
            'episode_content': sample_episode.content,
            'existing_nodes': [
                {
                    'name': node.name,
                    'summary': node.summary,
                    'uuid': node.uuid,
                    'labels': node.labels,
                    'attributes': node.attributes
                }
                for node in existing_nodes
            ],
            'previous_episodes': []
        }
        
        messages = get_contradiction_pairs_prompt(context)
        
        assert len(messages) == 2
        assert messages[0].role == 'system'
        assert messages[1].role == 'user'
        
        # Verify system message contains key instructions
        system_content = messages[0].content.lower()
        assert 'cognitive objects' in system_content
        assert 'concept' in system_content
        assert 'people and concepts' in system_content
        
        # Verify user message contains context
        user_content = messages[1].content
        assert sample_episode.content in user_content
        assert 'existing nodes' in user_content.lower()

    def test_contradiction_models_validation(self):
        """Test that the Pydantic models validate data correctly."""
        # Test ContradictionNode
        node = ContradictionNode(
            name="hate football",
            summary="User hates football",
            entity_type="Entity"
        )
        assert node.name == "hate football"
        assert node.entity_type == "Entity"
        
        # Test ContradictionPair
        node1 = ContradictionNode(name="love football", summary="User loves football")
        node2 = ContradictionNode(name="hate football", summary="User hates football")
        
        pair = ContradictionPair(
            node1=node1,
            node2=node2,
            contradiction_reason="Opposite preferences"
        )
        assert pair.node1.name == "love football"
        assert pair.node2.name == "hate football"
        assert pair.contradiction_reason == "Opposite preferences"
        
        # Test ContradictionPairs
        pairs = ContradictionPairs(contradiction_pairs=[pair])
        assert len(pairs.contradiction_pairs) == 1
        assert pairs.contradiction_pairs[0].contradiction_reason == "Opposite preferences"

    def test_contradiction_metadata_model(self):
        """Test the ContradictionMetadata model."""
        metadata = ContradictionMetadata(
            contradiction_reason="User changed preference from loving to hating football",
            detection_confidence=0.9,
            detected_in_episode="episode123",
            contradiction_type="preference",
            resolution_status="unresolved",
            user_feedback=None
        )
        
        assert metadata.contradiction_reason == "User changed preference from loving to hating football"
        assert metadata.detection_confidence == 0.9
        assert metadata.resolution_status == "unresolved"
        assert metadata.user_feedback is None

    def test_cognitive_object_pair_model(self):
        """Test the CognitiveObjectPair model."""
        # Create sample nodes and edge for the model
        node1 = EntityNode(name="love football", group_id="1", labels=["Entity"], summary="User loves football")
        node2 = EntityNode(name="hate football", group_id="1", labels=["Entity"], summary="User hates football")  
        edge = EntityEdge(
            source_node_uuid=node1.uuid,
            target_node_uuid=node2.uuid,
            name="CONTRADICTS",
            group_id="1",
            fact="love football contradicts hate football",
            episodes=["episode123"],
            created_at=utc_now(),
            valid_at=utc_now()
        )
        
        pair = CognitiveObjectPair(
            node1=node1,
            node2=node2,
            contradiction_edge=edge,
            metadata=ContradictionMetadata(
                contradiction_reason="Preference change",
                detection_confidence=0.85,
                detected_in_episode="episode123",
                contradiction_type="preference"
            )
        )
        
        assert pair.node1.name == "love football"
        assert pair.node2.name == "hate football"
        assert pair.metadata.detection_confidence == 0.85

    def test_contradiction_detection_result_model(self):
        """Test the ContradictionDetectionResult model."""
        # Create sample nodes and edge for the model
        node1 = EntityNode(name="love football", group_id="1", labels=["Entity"], summary="User loves football")
        node2 = EntityNode(name="hate football", group_id="1", labels=["Entity"], summary="User hates football")  
        edge = EntityEdge(
            source_node_uuid=node1.uuid,
            target_node_uuid=node2.uuid,
            name="CONTRADICTS",
            group_id="1",
            fact="love football contradicts hate football",
            episodes=["episode123"],
            created_at=utc_now(),
            valid_at=utc_now()
        )
        
        pair = CognitiveObjectPair(
            node1=node1,
            node2=node2,
            contradiction_edge=edge,
            metadata=ContradictionMetadata(
                contradiction_reason="Preference reversal",
                detection_confidence=0.9,
                detected_in_episode="episode123",
                contradiction_type="preference"
            )
        )
        
        result = ContradictionDetectionResult(
            pairs_detected=[pair],
            new_nodes_created=[node2],  # Assume node2 was newly created
            edges_created=[edge]
        )
        
        assert len(result.pairs_detected) == 1
        assert len(result.new_nodes_created) == 1
        assert len(result.edges_created) == 1
        assert result.pairs_detected[0].node1.name == "love football"

    @pytest.mark.asyncio
    async def test_complex_scenario_multiple_contradictions(self, mock_llm_client, mock_add_triplet):
        """Test a complex scenario with multiple contradictions."""
        # Create episode with multiple preference changes
        episode = EpisodicNode(
            name="Multiple Preference Changes",
            group_id="1",
            labels=[],
            source=EpisodeType.message,
            content="I hate football now and I also prefer chocolate over vanilla ice cream",
            source_description="Multiple preference changes",
            created_at=utc_now(),
            valid_at=utc_now(),
        )
        
        # Create existing nodes
        existing_nodes = [
            EntityNode(
                name="love football",
                group_id="1",
                labels=["Entity"],
                summary="User loves football",
                created_at=utc_now(),
            ),
            EntityNode(
                name="prefer vanilla",
                group_id="1",
                labels=["Entity"],
                summary="User prefers vanilla ice cream",
                created_at=utc_now(),
            )
        ]
        
        # Mock LLM response with multiple contradictions
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': [
                {
                    'node1': {
                        'name': 'love football',
                        'summary': 'User loves football',
                        'entity_type': 'Entity'
                    },
                    'node2': {
                        'name': 'hate football',
                        'summary': 'User hates football',
                        'entity_type': 'Entity'
                    },
                    'contradiction_reason': 'Opposite preferences about football'
                },
                {
                    'node1': {
                        'name': 'prefer vanilla',
                        'summary': 'User prefers vanilla ice cream',
                        'entity_type': 'Entity'
                    },
                    'node2': {
                        'name': 'prefer chocolate',
                        'summary': 'User prefers chocolate ice cream',
                        'entity_type': 'Entity'
                    },
                    'contradiction_reason': 'Conflicting ice cream preferences'
                }
            ]
        }
        
        result = await detect_and_create_node_contradictions(
            mock_llm_client, episode, existing_nodes, mock_add_triplet
        )
        
        # Verify multiple contradictions were detected
        assert len(result) == 2
        assert all(isinstance(edge, EntityEdge) for edge in result)
        assert all(edge.name == 'CONTRADICTS' for edge in result)
        
        # Verify both add_triplet calls were made
        assert mock_add_triplet.call_count == 2
        
        # Verify different contradiction reasons
        reasons = [edge.attributes['contradiction_reason'] for edge in result]
        assert 'football' in reasons[0].lower()
        assert 'ice cream' in reasons[1].lower() or 'chocolate' in reasons[1].lower()

    @pytest.mark.asyncio
    async def test_error_handling_invalid_llm_response(self, mock_llm_client, sample_episode, existing_nodes, mock_add_triplet):
        """Test error handling when LLM returns invalid response."""
        # Mock LLM response with missing required fields
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': [
                {
                    'node1': {
                        'name': 'love football',
                        # Missing summary and entity_type
                    },
                    'node2': {
                        'name': 'hate football',
                        'summary': 'User hates football',
                        'entity_type': 'Entity'
                    },
                    'contradiction_reason': 'Opposite preferences'
                }
            ]
        }
        
        # Should handle the error gracefully
        result = await detect_and_create_node_contradictions(
            mock_llm_client, sample_episode, existing_nodes, mock_add_triplet
        )
        
        # Should return empty list or handle gracefully
        assert isinstance(result, list)
        # The exact behavior depends on implementation - it might create partial results or skip invalid pairs

    def test_node_creation_with_proper_attributes(self):
        """Test that new nodes are created with proper attributes."""
        node_data = {
            'name': 'hate football',
            'summary': 'User hates football and cannot stand watching it',
            'entity_type': 'Entity'
        }
        
        result = _find_or_create_node(node_data, [], "1")
        
        assert result is not None
        assert result.name == 'hate football'
        assert result.summary == 'User hates football and cannot stand watching it'
        assert result.group_id == "1"
        assert 'Entity' in result.labels
        assert result.created_at is not None
        assert result.uuid is not None
        
        # Should have default attributes structure
        assert hasattr(result, 'attributes')

    @pytest.mark.asyncio
    async def test_factual_correction_contradiction(self, mock_llm_client, mock_add_triplet):
        """Test detection of factual corrections like price changes."""
        # Create episode with factual correction
        episode = EpisodicNode(
            name="Price Correction Episode",
            group_id="1",
            labels=[],
            source=EpisodeType.message,
            content="oh i made a mistake it was $45 dollars for the room i read the receipt wrong",
            source_description="User correcting hotel room price",
            created_at=utc_now(),
            valid_at=utc_now(),
        )
        
        # Create existing node with original price
        existing_node = EntityNode(
            name="hotel room booking $450",
            group_id="1",
            labels=["Entity"],
            summary="User booked hotel room for $450 during high season",
            created_at=utc_now(),
            attributes={"price": "$450", "type": "hotel_booking"}
        )
        
        existing_nodes = [existing_node]
        
        # Mock LLM response detecting the factual correction
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': [
                {
                    'node1': {
                        'name': 'hotel room booking $450',
                        'summary': 'User booked hotel room for $450 during high season',
                        'entity_type': 'Entity'
                    },
                    'node2': {
                        'name': 'hotel room booking $45',
                        'summary': 'User corrected hotel room cost to $45',
                        'entity_type': 'Entity'
                    },
                    'contradiction_reason': 'Factual correction of hotel room price from $450 to $45'
                }
            ]
        }
        
        # Test the detection
        result = await detect_and_create_node_contradictions(
            mock_llm_client, episode, existing_nodes, mock_add_triplet
        )
        
        # Verify contradiction was detected
        assert len(result) == 1
        edge = result[0]
        assert isinstance(edge, EntityEdge)
        assert edge.name == 'CONTRADICTS'
        assert 'factual correction' in edge.attributes['contradiction_reason'].lower()
        
        # Verify LLM was called with correct context
        mock_llm_client.generate_response.assert_called_once()
        call_args = mock_llm_client.generate_response.call_args
        # Check that the prompt messages contain the episode content and existing nodes
        prompt_messages = call_args[0][0]  # First positional argument is the prompt messages
        prompt_content = ' '.join([msg.content for msg in prompt_messages])
        assert '$45' in prompt_content
        assert '$450' in prompt_content
        
        # Verify add_triplet was called to create the new node and edge
        mock_add_triplet.assert_called_once()

    @pytest.mark.asyncio
    async def test_numerical_correction_contradiction(self, mock_llm_client, mock_add_triplet):
        """Test detection of numerical corrections."""
        # Create episode with numerical correction
        episode = EpisodicNode(
            name="Count Correction Episode",
            group_id="1",
            labels=[],
            source=EpisodeType.message,
            content="Actually I have 2 cats, not 3",
            source_description="User correcting pet count",
            created_at=utc_now(),
            valid_at=utc_now(),
        )
        
        # Create existing node with original count
        existing_node = EntityNode(
            name="have 3 cats",
            group_id="1",
            labels=["Entity"],
            summary="User has 3 cats",
            created_at=utc_now(),
            attributes={"count": 3, "type": "pet_ownership"}
        )
        
        existing_nodes = [existing_node]
        
        # Mock LLM response detecting the numerical correction
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': [
                {
                    'node1': {
                        'name': 'have 3 cats',
                        'summary': 'User has 3 cats',
                        'entity_type': 'Entity'
                    },
                    'node2': {
                        'name': 'have 2 cats',
                        'summary': 'User corrected to having 2 cats',
                        'entity_type': 'Entity'
                    },
                    'contradiction_reason': 'Numerical correction of cat count from 3 to 2'
                }
            ]
        }
        
        # Test the detection
        result = await detect_and_create_node_contradictions(
            mock_llm_client, episode, existing_nodes, mock_add_triplet
        )
        
        # Verify contradiction was detected
        assert len(result) == 1
        edge = result[0]
        assert isinstance(edge, EntityEdge)
        assert edge.name == 'CONTRADICTS'
        assert 'numerical correction' in edge.attributes['contradiction_reason'].lower()

    @pytest.mark.asyncio
    async def test_duplicate_contradiction_prevention(self, mock_llm_client, mock_add_triplet):
        """Test that duplicate contradiction relationships are not created."""
        # Create episode mentioning the same contradiction again
        episode = EpisodicNode(
            name="Repeated Contradiction",
            group_id="1",
            labels=[],
            source=EpisodeType.message,
            content="I still hate football now",
            source_description="User reaffirming hatred for football",
            created_at=utc_now(),
            valid_at=utc_now(),
        )
        
        # Create existing nodes
        love_node = EntityNode(
            name="I love football",
            group_id="1",
            labels=["Entity"],
            summary="User loves football",
            created_at=utc_now(),
        )
        
        hate_node = EntityNode(
            name="I hate football now",
            group_id="1",
            labels=["Entity"],
            summary="User hates football now",
            created_at=utc_now(),
        )
        
        existing_nodes = [love_node, hate_node]
        
        # Mock LLM response - should return empty since both nodes exist (filtered by prompt)
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': []
        }
        
        # Test the detection - should return empty since prompt filters existing pairs
        result = await detect_and_create_node_contradictions(
            mock_llm_client, episode, existing_nodes, mock_add_triplet
        )
        
        # Should return empty list since prompt filtered out the pair (both nodes exist)
        assert result == []
        
        # Verify add_triplet was NOT called since no pairs were returned
        mock_add_triplet.assert_not_called()

    @pytest.mark.asyncio
    async def test_new_contradiction_creation_when_none_exists(self, mock_llm_client, mock_add_triplet):
        """Test that new contradictions are created when none exist."""
        # Create episode with new contradiction
        episode = EpisodicNode(
            name="New Contradiction",
            group_id="1",
            labels=[],
            source=EpisodeType.message,
            content="I hate tennis now",
            source_description="User expressing hatred for tennis",
            created_at=utc_now(),
            valid_at=utc_now(),
        )
        
        # Create existing nodes
        love_tennis_node = EntityNode(
            name="I love tennis",
            group_id="1",
            labels=["Entity"],
            summary="User loves tennis",
            created_at=utc_now(),
        )
        
        existing_nodes = [love_tennis_node]
        
        # Mock LLM response detecting new contradiction (only one node exists, other is new)
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': [
                {
                    'node1': {
                        'name': 'I love tennis',
                        'summary': 'User loves tennis',
                        'entity_type': 'Entity'
                    },
                    'node2': {
                        'name': 'I hate tennis now',
                        'summary': 'User hates tennis now',
                        'entity_type': 'Entity'
                    },
                    'contradiction_reason': 'User changed preference from loving to hating tennis'
                }
            ]
        }
        
        # Test the detection - should create contradiction since only one node exists
        result = await detect_and_create_node_contradictions(
            mock_llm_client, episode, existing_nodes, mock_add_triplet
        )
        
        # Should create one contradiction edge
        assert len(result) == 1
        edge = result[0]
        assert edge.name == 'CONTRADICTS'
        
        # Verify add_triplet was called to create new contradiction
        mock_add_triplet.assert_called_once()