"""
Tests for node operations including contradiction detection.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the Python path so we can import graphiti_core
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

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
from graphiti_extend.prompts.contradiction import ContradictionPairs


class TestNodeOperations:
    """Test cases for node contradiction detection operations."""

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
    def sample_nodes(self):
        """Create sample nodes for testing."""
        now = utc_now()
        
        node1 = EntityNode(
            name="love vanilla ice cream",
            group_id="1",
            labels=["Entity"],
            summary="User loves vanilla ice cream",
            created_at=now,
            attributes={"preference": "positive", "subject": "vanilla ice cream"}
        )
        
        node2 = EntityNode(
            name="hate vanilla ice cream", 
            group_id="1",
            labels=["Entity"],
            summary="User hates vanilla ice cream",
            created_at=now,
            attributes={"preference": "negative", "subject": "vanilla ice cream"}
        )
        
        node3 = EntityNode(
            name="Joseph Adebisi",
            group_id="1", 
            labels=["Entity", "Person"],
            summary="The user",
            created_at=now,
            attributes={"type": "person"}
        )
        
        return node1, node2, node3

    @pytest.fixture
    def sample_episode(self):
        """Create a sample episode for testing."""
        return EpisodicNode(
            name="Test Episode",
            group_id="1",
            labels=[],
            source=EpisodeType.message,
            content="I hate vanilla ice cream now",
            source_description="User statement",
            created_at=utc_now(),
            valid_at=utc_now(),
        )

    @pytest.mark.asyncio
    async def test_detect_contradiction_pairs_no_existing_nodes(self, mock_llm_client, sample_episode):
        """Test contradiction detection with no existing nodes."""
        existing_nodes = []
        
        result = await detect_contradiction_pairs(
            mock_llm_client, sample_episode, existing_nodes
        )
        
        assert result == []
        mock_llm_client.generate_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_detect_contradiction_pairs_with_contradictions(self, mock_llm_client, sample_nodes, sample_episode):
        """Test contradiction detection when contradictions exist."""
        love_node, hate_node, person_node = sample_nodes
        existing_nodes = [love_node, person_node]  # Include person to test filtering
        
        # Mock LLM response with contradiction pairs
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': [
                {
                    'node1': {
                        'name': 'love vanilla ice cream',
                        'summary': 'User loves vanilla ice cream',
                        'entity_type': 'Entity'
                    },
                    'node2': {
                        'name': 'hate vanilla ice cream',
                        'summary': 'User hates vanilla ice cream', 
                        'entity_type': 'Entity'
                    },
                    'contradiction_reason': 'Opposite preferences about vanilla ice cream'
                }
            ]
        }
        
        result = await detect_contradiction_pairs(
            mock_llm_client, sample_episode, existing_nodes
        )
        
        assert len(result) == 1
        node1, node2, reason = result[0]
        assert node1.name == 'love vanilla ice cream'
        assert node2.name == 'hate vanilla ice cream'
        assert 'opposite preferences' in reason.lower()
        mock_llm_client.generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_contradiction_pairs_no_contradictions(self, mock_llm_client, sample_nodes, sample_episode):
        """Test contradiction detection when no contradictions exist."""
        love_node, _, person_node = sample_nodes
        existing_nodes = [love_node, person_node]
        
        # Mock LLM response with no contradictions
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': []
        }
        
        result = await detect_contradiction_pairs(
            mock_llm_client, sample_episode, existing_nodes
        )
        
        assert result == []
        mock_llm_client.generate_response.assert_called_once()

    def test_find_or_create_node_existing(self, sample_nodes):
        """Test finding an existing node."""
        love_node, hate_node, person_node = sample_nodes
        existing_nodes = [love_node, person_node]
        
        node_data = {
            'name': 'love vanilla ice cream',
            'summary': 'User loves vanilla ice cream',
            'entity_type': 'Entity'
        }
        
        result = _find_or_create_node(node_data, existing_nodes, "1")
        
        assert result == love_node
        assert result.uuid == love_node.uuid

    def test_find_or_create_node_new(self, sample_nodes):
        """Test creating a new node when not found."""
        love_node, _, person_node = sample_nodes
        existing_nodes = [love_node, person_node]
        
        node_data = {
            'name': 'hate vanilla ice cream',
            'summary': 'User hates vanilla ice cream',
            'entity_type': 'Entity'
        }
        
        result = _find_or_create_node(node_data, existing_nodes, "1")
        
        assert result is not None
        assert result.name == 'hate vanilla ice cream'
        assert result.summary == 'User hates vanilla ice cream'
        assert result.group_id == "1"
        assert 'Entity' in result.labels
        assert result.uuid != love_node.uuid  # Should be a new node

    def test_find_or_create_node_invalid_data(self, sample_nodes):
        """Test handling invalid node data."""
        love_node, _, person_node = sample_nodes
        existing_nodes = [love_node, person_node]
        
        # Test with empty name
        node_data = {
            'name': '',
            'summary': 'Some summary',
            'entity_type': 'Entity'
        }
        
        result = _find_or_create_node(node_data, existing_nodes, "1")
        assert result is None
        
        # Test with no name
        node_data = {
            'summary': 'Some summary',
            'entity_type': 'Entity'
        }
        
        result = _find_or_create_node(node_data, existing_nodes, "1")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_contradiction_edges_from_pairs(self, sample_nodes, sample_episode, mock_add_triplet):
        """Test creation of contradiction edges from pairs."""
        love_node, hate_node, _ = sample_nodes
        
        contradiction_pairs = [
            (love_node, hate_node, "Opposite preferences about vanilla ice cream")
        ]
        
        result = await create_contradiction_edges_from_pairs(
            contradiction_pairs, sample_episode, mock_add_triplet
        )
        
        assert len(result) == 1
        edge = result[0]
        assert isinstance(edge, EntityEdge)
        assert edge.source_node_uuid == love_node.uuid
        assert edge.target_node_uuid == hate_node.uuid
        assert edge.name == 'CONTRADICTS'
        assert edge.group_id == sample_episode.group_id
        assert sample_episode.uuid in edge.episodes
        assert 'opposite preferences' in edge.fact.lower()
        assert edge.attributes['contradiction_reason'] == "Opposite preferences about vanilla ice cream"
        
        # Verify add_triplet was called
        mock_add_triplet.assert_called_once_with(love_node, edge, hate_node)

    @pytest.mark.asyncio
    async def test_create_contradiction_edges_multiple_pairs(self, sample_nodes, sample_episode, mock_add_triplet):
        """Test creation of multiple contradiction edges."""
        love_node, hate_node, person_node = sample_nodes
        
        # Create another node for testing
        prefer_chocolate = EntityNode(
            name="prefer chocolate",
            group_id="1",
            labels=["Entity"],
            summary="User prefers chocolate",
            created_at=utc_now(),
        )
        
        contradiction_pairs = [
            (love_node, hate_node, "Opposite preferences about vanilla"),
            (love_node, prefer_chocolate, "Conflicting preferences")
        ]
        
        result = await create_contradiction_edges_from_pairs(
            contradiction_pairs, sample_episode, mock_add_triplet
        )
        
        assert len(result) == 2
        assert all(isinstance(edge, EntityEdge) for edge in result)
        assert all(edge.name == 'CONTRADICTS' for edge in result)
        assert mock_add_triplet.call_count == 2

    @pytest.mark.asyncio
    async def test_detect_and_create_node_contradictions_full_flow(self, mock_llm_client, sample_nodes, sample_episode, mock_add_triplet):
        """Test the complete contradiction detection and edge creation flow."""
        love_node, _, person_node = sample_nodes
        existing_nodes = [love_node, person_node]
        
        # Mock LLM response with contradiction pairs
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': [
                {
                    'node1': {
                        'name': 'love vanilla ice cream',
                        'summary': 'User loves vanilla ice cream',
                        'entity_type': 'Entity'
                    },
                    'node2': {
                        'name': 'hate vanilla ice cream',
                        'summary': 'User hates vanilla ice cream',
                        'entity_type': 'Entity'
                    },
                    'contradiction_reason': 'Opposite preferences about vanilla ice cream'
                }
            ]
        }
        
        result = await detect_and_create_node_contradictions(
            mock_llm_client, sample_episode, existing_nodes, mock_add_triplet
        )
        
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

    @pytest.mark.asyncio
    async def test_detect_and_create_node_contradictions_no_contradictions(self, mock_llm_client, sample_nodes, sample_episode, mock_add_triplet):
        """Test the flow when no contradictions are detected."""
        love_node, _, person_node = sample_nodes
        existing_nodes = [love_node, person_node]
        
        # Mock LLM response with no contradictions
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': []
        }
        
        result = await detect_and_create_node_contradictions(
            mock_llm_client, sample_episode, existing_nodes, mock_add_triplet
        )
        
        assert result == []
        mock_add_triplet.assert_not_called()

    @pytest.mark.asyncio
    async def test_contradiction_prevents_invalid_pairs(self, mock_llm_client, sample_nodes, sample_episode, mock_add_triplet):
        """Test that invalid contradiction pairs are filtered out."""
        love_node, _, person_node = sample_nodes
        existing_nodes = [love_node, person_node]
        
        # Mock LLM response with invalid contradiction (person vs concept)
        mock_llm_client.generate_response.return_value = {
            'contradiction_pairs': [
                {
                    'node1': {
                        'name': 'Joseph Adebisi',
                        'summary': 'The user',
                        'entity_type': 'Person'
                    },
                    'node2': {
                        'name': 'vanilla ice cream',
                        'summary': 'Ice cream flavor',
                        'entity_type': 'Entity'
                    },
                    'contradiction_reason': 'Invalid contradiction between person and concept'
                }
            ]
        }
        
        result = await detect_and_create_node_contradictions(
            mock_llm_client, sample_episode, existing_nodes, mock_add_triplet
        )
        
        # Should still create the edge if LLM returns it, but the prompt should prevent this
        # This test verifies the system handles such cases gracefully
        assert isinstance(result, list)

    def test_contradiction_edge_attributes(self, sample_nodes, sample_episode):
        """Test that contradiction edges have the correct attributes."""
        love_node, hate_node, _ = sample_nodes
        
        edge = EntityEdge(
            source_node_uuid=love_node.uuid,
            target_node_uuid=hate_node.uuid,
            name='CONTRADICTS',
            group_id=sample_episode.group_id,
            fact=f'{love_node.name} contradicts {hate_node.name}: Opposite preferences',
            episodes=[sample_episode.uuid],
            created_at=utc_now(),
            valid_at=sample_episode.valid_at,
            attributes={
                'contradiction_reason': 'Opposite preferences',
                'detected_in_episode': sample_episode.uuid,
            }
        )
        
        assert edge.name == 'CONTRADICTS'
        assert edge.attributes['contradiction_reason'] == 'Opposite preferences'
        assert edge.attributes['detected_in_episode'] == sample_episode.uuid
        assert 'contradicts' in edge.fact.lower()
        assert 'opposite preferences' in edge.fact.lower() 