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
    get_node_contradictions,
    create_contradiction_edges,
    detect_and_create_node_contradictions,
)
from graphiti_extend.prompts.contradiction import ContradictedNodes


class TestNodeOperations:
    """Test cases for node contradiction detection operations."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = AsyncMock(spec=LLMClient)
        return client

    @pytest.fixture
    def sample_nodes(self):
        """Create sample nodes for testing."""
        now = utc_now()
        
        node1 = EntityNode(
            name="vanilla ice cream",
            group_id="user123",
            labels=["Entity"],
            summary="User's favorite ice cream flavor",
            created_at=now,
            attributes={"preference": "positive"}
        )
        
        node2 = EntityNode(
            name="chocolate ice cream", 
            group_id="user123",
            labels=["Entity"],
            summary="Alternative ice cream flavor",
            created_at=now,
            attributes={"preference": "neutral"}
        )
        
        return node1, node2

    @pytest.fixture
    def sample_episode(self):
        """Create a sample episode for testing."""
        return EpisodicNode(
            name="Test Episode",
            group_id="user123",
            labels=[],
            source=EpisodeType.message,
            content="I hate vanilla ice cream now",
            source_description="User statement",
            created_at=utc_now(),
            valid_at=utc_now(),
        )

    @pytest.mark.asyncio
    async def test_get_node_contradictions_no_existing_nodes(self, mock_llm_client, sample_nodes, sample_episode):
        """Test contradiction detection with no existing nodes."""
        new_node, _ = sample_nodes
        existing_nodes = []
        
        result = await get_node_contradictions(
            mock_llm_client, new_node, existing_nodes, sample_episode
        )
        
        assert result == []
        mock_llm_client.generate_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_node_contradictions_with_contradictions(self, mock_llm_client, sample_nodes, sample_episode):
        """Test contradiction detection when contradictions exist."""
        new_node, existing_node = sample_nodes
        existing_nodes = [existing_node]
        
        # Mock LLM response indicating contradiction
        mock_llm_client.generate_response.return_value = {
            'contradicted_nodes': [0]  # Index of contradicted node
        }
        
        result = await get_node_contradictions(
            mock_llm_client, new_node, existing_nodes, sample_episode
        )
        
        assert len(result) == 1
        assert result[0] == existing_node
        mock_llm_client.generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_node_contradictions_no_contradictions(self, mock_llm_client, sample_nodes, sample_episode):
        """Test contradiction detection when no contradictions exist."""
        new_node, existing_node = sample_nodes
        existing_nodes = [existing_node]
        
        # Mock LLM response indicating no contradictions
        mock_llm_client.generate_response.return_value = {
            'contradicted_nodes': []
        }
        
        result = await get_node_contradictions(
            mock_llm_client, new_node, existing_nodes, sample_episode
        )
        
        assert result == []
        mock_llm_client.generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_contradiction_edges(self, sample_nodes, sample_episode):
        """Test creation of contradiction edges."""
        new_node, contradicted_node = sample_nodes
        contradicted_nodes = [contradicted_node]
        
        result = await create_contradiction_edges(
            new_node, contradicted_nodes, sample_episode
        )
        
        assert len(result) == 1
        edge = result[0]
        assert isinstance(edge, EntityEdge)
        assert edge.source_node_uuid == new_node.uuid
        assert edge.target_node_uuid == contradicted_node.uuid
        assert edge.name == 'CONTRADICTS'
        assert edge.group_id == new_node.group_id
        assert sample_episode.uuid in edge.episodes
        assert edge.fact == f'{new_node.name} contradicts {contradicted_node.name}'

    @pytest.mark.asyncio
    async def test_create_contradiction_edges_multiple_nodes(self, sample_nodes, sample_episode):
        """Test creation of contradiction edges with multiple contradicted nodes."""
        new_node, existing_node = sample_nodes
        
        # Create another contradicted node
        another_node = EntityNode(
            name="strawberry ice cream",
            group_id="user123", 
            labels=["Entity"],
            summary="Another ice cream flavor",
            created_at=utc_now(),
        )
        
        contradicted_nodes = [existing_node, another_node]
        
        result = await create_contradiction_edges(
            new_node, contradicted_nodes, sample_episode
        )
        
        assert len(result) == 2
        
        # Check first edge
        edge1 = result[0]
        assert edge1.source_node_uuid == new_node.uuid
        assert edge1.target_node_uuid == existing_node.uuid
        assert edge1.name == 'CONTRADICTS'
        
        # Check second edge
        edge2 = result[1]
        assert edge2.source_node_uuid == new_node.uuid
        assert edge2.target_node_uuid == another_node.uuid
        assert edge2.name == 'CONTRADICTS'

    @pytest.mark.asyncio
    async def test_detect_and_create_node_contradictions_full_flow(self, mock_llm_client, sample_nodes, sample_episode):
        """Test the complete contradiction detection and edge creation flow."""
        new_node, existing_node = sample_nodes
        existing_nodes = [existing_node]
        
        # Mock LLM response indicating contradiction
        mock_llm_client.generate_response.return_value = {
            'contradicted_nodes': [0]
        }
        
        result = await detect_and_create_node_contradictions(
            mock_llm_client, new_node, existing_nodes, sample_episode
        )
        
        assert len(result) == 1
        edge = result[0]
        assert isinstance(edge, EntityEdge)
        assert edge.name == 'CONTRADICTS'
        assert edge.source_node_uuid == new_node.uuid
        assert edge.target_node_uuid == existing_node.uuid

    @pytest.mark.asyncio
    async def test_detect_and_create_node_contradictions_no_contradictions(self, mock_llm_client, sample_nodes, sample_episode):
        """Test the flow when no contradictions are detected."""
        new_node, existing_node = sample_nodes
        existing_nodes = [existing_node]
        
        # Mock LLM response indicating no contradictions
        mock_llm_client.generate_response.return_value = {
            'contradicted_nodes': []
        }
        
        result = await detect_and_create_node_contradictions(
            mock_llm_client, new_node, existing_nodes, sample_episode
        )
        
        assert result == []

    def test_contradiction_edge_properties(self, sample_nodes, sample_episode):
        """Test that contradiction edges have the correct properties."""
        new_node, contradicted_node = sample_nodes
        
        # Create edge manually to test properties
        edge = EntityEdge(
            source_node_uuid=new_node.uuid,
            target_node_uuid=contradicted_node.uuid,
            name='CONTRADICTS',
            group_id=new_node.group_id,
            fact=f'{new_node.name} contradicts {contradicted_node.name}',
            episodes=[sample_episode.uuid],
            created_at=utc_now(),
            valid_at=sample_episode.valid_at,
        )
        
        assert edge.name == 'CONTRADICTS'
        assert edge.source_node_uuid == new_node.uuid
        assert edge.target_node_uuid == contradicted_node.uuid
        assert edge.group_id == new_node.group_id
        assert sample_episode.uuid in edge.episodes
        assert 'contradicts' in edge.fact.lower()

    @pytest.mark.asyncio
    async def test_llm_context_structure(self, mock_llm_client, sample_nodes, sample_episode):
        """Test that the LLM is called with the correct context structure."""
        new_node, existing_node = sample_nodes
        existing_nodes = [existing_node]
        previous_episodes = [sample_episode]
        
        mock_llm_client.generate_response.return_value = {
            'contradicted_nodes': []
        }
        
        await get_node_contradictions(
            mock_llm_client, new_node, existing_nodes, sample_episode, previous_episodes
        )
        
        # Verify the LLM was called
        assert mock_llm_client.generate_response.called
        
        # Get the call arguments
        call_args = mock_llm_client.generate_response.call_args
        prompt_messages = call_args[0][0]  # First positional argument
        response_model = call_args[1]['response_model']  # Keyword argument
        
        # Verify response model
        assert response_model == ContradictedNodes
        
        # Verify prompt structure (basic check)
        assert len(prompt_messages) >= 1
        assert any('contradict' in msg.content.lower() for msg in prompt_messages) 