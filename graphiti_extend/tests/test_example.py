"""
Test cases for the example.py functionality.

This module tests the core functionality demonstrated in example.py,
including contradiction detection, enhanced search, and summary features.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Mock the graphiti_extend import since we're testing the functionality
from unittest.mock import Mock


class MockContradictionResult:
    """Mock contradiction result object."""
    def __init__(self, contradictions_found=False, contradiction_message="", 
                 contradiction_edges=None, contradicting_nodes=None, contradicted_nodes=None):
        self.contradictions_found = contradictions_found
        self.contradiction_message = contradiction_message
        self.contradiction_edges = contradiction_edges or []
        self.contradicting_nodes = contradicting_nodes or []
        self.contradicted_nodes = contradicted_nodes or []


class MockEpisodeResult:
    """Mock episode result object."""
    def __init__(self, nodes=None, edges=None, contradiction_result=None):
        self.nodes = nodes or []
        self.edges = edges or []
        self.contradiction_result = contradiction_result or MockContradictionResult()


class MockNode:
    """Mock node object."""
    def __init__(self, name, uuid=None, attributes=None):
        self.name = name
        self.uuid = uuid or f"uuid-{name}"
        self.attributes = attributes or {}


class MockEdge:
    """Mock edge object."""
    def __init__(self, name, fact="", source_node_uuid="", target_node_uuid=""):
        self.name = name
        self.fact = fact
        self.source_node_uuid = source_node_uuid
        self.target_node_uuid = target_node_uuid


class MockSearchResult:
    """Mock search result object."""
    def __init__(self, nodes=None, edges=None, contradiction_edges=None, 
                 contradicted_nodes_map=None, contradicting_nodes_map=None):
        self.nodes = nodes or []
        self.edges = edges or []
        self.contradiction_edges = contradiction_edges or []
        self.contradicted_nodes_map = contradicted_nodes_map or {}
        self.contradicting_nodes_map = contradicting_nodes_map or {}


class MockExtendedGraphiti:
    """Mock ExtendedGraphiti class for testing."""
    
    def __init__(self, uri="", user="", password="", 
                 enable_contradiction_detection=True, contradiction_threshold=0.7):
        self.uri = uri
        self.user = user
        self.password = password
        self.enable_contradiction_detection = enable_contradiction_detection
        self.contradiction_threshold = contradiction_threshold
        self._closed = False
    
    async def build_indices_and_constraints(self):
        """Mock building indices and constraints."""
        pass
    
    async def add_episode_with_contradictions(self, name, episode_body, 
                                            source_description, reference_time, group_id):
        """Mock adding episode with contradiction detection."""
        # Simulate different scenarios based on episode content
        if "love vanilla" in episode_body:
            # First episode - no contradictions
            return MockEpisodeResult(
                nodes=[MockNode("Vanilla Preference", attributes={"preference": "positive"})],
                edges=[MockEdge("LIKES", "User likes vanilla ice cream")],
                contradiction_result=MockContradictionResult(contradictions_found=False)
            )
        elif "hate vanilla" in episode_body:
            # Second episode - contradiction detected
            contradiction_result = MockContradictionResult(
                contradictions_found=True,
                contradiction_message="Contradiction detected: User previously liked vanilla ice cream",
                contradiction_edges=[MockEdge("CONTRADICTS", "User likes vanilla vs User hates vanilla")],
                contradicting_nodes=[MockNode("New Vanilla Dislike")],
                contradicted_nodes=[MockNode("Previous Vanilla Like")]
            )
            return MockEpisodeResult(
                nodes=[MockNode("Vanilla Dislike", attributes={"preference": "negative"})],
                edges=[MockEdge("DISLIKES", "User hates vanilla ice cream")],
                contradiction_result=contradiction_result
            )
        else:
            # Clarification episode
            return MockEpisodeResult(
                nodes=[MockNode("Preference Clarification")],
                edges=[MockEdge("CLARIFIES", "User clarifies ice cream preference change")],
                contradiction_result=MockContradictionResult(contradictions_found=False)
            )
    
    async def contradiction_aware_search(self, query, group_ids, include_contradictions=True):
        """Mock contradiction-aware search."""
        nodes = [
            MockNode("Vanilla Preference", attributes={"has_contradictions": True, 
                                                     "contradicted_nodes": ["Previous Like"],
                                                     "contradicting_nodes": ["Current Dislike"]}),
            MockNode("Chocolate Preference", attributes={"has_contradictions": False})
        ]
        edges = [
            MockEdge("LIKES", "User likes vanilla ice cream"),
            MockEdge("DISLIKES", "User hates vanilla ice cream"),
            MockEdge("CONTRADICTS", "Vanilla preference contradiction")
        ]
        return MockSearchResult(nodes=nodes, edges=edges)
    
    async def get_contradiction_summary(self, group_ids):
        """Mock getting contradiction summary."""
        return {
            "total_contradictions": 2,
            "nodes_with_contradictions": 1,
            "recent_contradictions": [
                MockEdge("CONTRADICTS", "User ice cream preference contradiction")
            ]
        }
    
    async def enhanced_contradiction_search(self, query, group_ids):
        """Mock enhanced contradiction search."""
        return MockSearchResult(
            nodes=[MockNode("Ice Cream Node")],
            edges=[MockEdge("RELATES", "Ice cream relation")],
            contradiction_edges=[MockEdge("CONTRADICTS", "Ice cream contradiction")],
            contradicted_nodes_map={"node1": ["contradicted_node1"]},
            contradicting_nodes_map={"node1": ["contradicting_node1"]}
        )
    
    async def close(self):
        """Mock closing the connection."""
        self._closed = True


@pytest.fixture
def mock_graphiti():
    """Fixture providing a mock ExtendedGraphiti instance."""
    return MockExtendedGraphiti()


class TestExampleFunctionality:
    """Test cases for example.py functionality."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_graphiti):
        """Test ExtendedGraphiti initialization."""
        assert mock_graphiti.enable_contradiction_detection is True
        assert mock_graphiti.contradiction_threshold == 0.7
        assert mock_graphiti.uri == ""
        assert mock_graphiti.user == ""
        assert mock_graphiti.password == ""
    
    @pytest.mark.asyncio
    async def test_build_indices_and_constraints(self, mock_graphiti):
        """Test building indices and constraints."""
        # Should not raise any exceptions
        await mock_graphiti.build_indices_and_constraints()
    
    @pytest.mark.asyncio
    async def test_first_episode_no_contradictions(self, mock_graphiti):
        """Test adding first episode with no contradictions."""
        result = await mock_graphiti.add_episode_with_contradictions(
            name="Ice Cream Preference 1",
            episode_body="I absolutely love vanilla ice cream. It's my favorite flavor.",
            source_description="User preference statement",
            reference_time=datetime.now(),
            group_id="user123"
        )
        
        assert len(result.nodes) == 1
        assert len(result.edges) == 1
        assert not result.contradiction_result.contradictions_found
        assert result.nodes[0].name == "Vanilla Preference"
        assert result.edges[0].name == "LIKES"
    
    @pytest.mark.asyncio
    async def test_second_episode_with_contradictions(self, mock_graphiti):
        """Test adding second episode that creates contradictions."""
        result = await mock_graphiti.add_episode_with_contradictions(
            name="Ice Cream Preference 2",
            episode_body="I hate vanilla ice cream. It's so boring and tasteless.",
            source_description="User preference statement",
            reference_time=datetime.now(),
            group_id="user123"
        )
        
        assert len(result.nodes) == 1
        assert len(result.edges) == 1
        assert result.contradiction_result.contradictions_found
        assert len(result.contradiction_result.contradiction_edges) == 1
        assert len(result.contradiction_result.contradicting_nodes) == 1
        assert len(result.contradiction_result.contradicted_nodes) == 1
        assert "Contradiction detected" in result.contradiction_result.contradiction_message
    
    @pytest.mark.asyncio
    async def test_clarification_episode(self, mock_graphiti):
        """Test adding clarification episode."""
        result = await mock_graphiti.add_episode_with_contradictions(
            name="Ice Cream Clarification",
            episode_body="Actually, I used to like vanilla but my taste has changed.",
            source_description="User clarification",
            reference_time=datetime.now(),
            group_id="user123"
        )
        
        assert len(result.nodes) == 1
        assert not result.contradiction_result.contradictions_found
        assert result.nodes[0].name == "Preference Clarification"
    
    @pytest.mark.asyncio
    async def test_contradiction_aware_search(self, mock_graphiti):
        """Test contradiction-aware search functionality."""
        result = await mock_graphiti.contradiction_aware_search(
            query="ice cream preferences",
            group_ids=["user123"],
            include_contradictions=True
        )
        
        assert len(result.nodes) == 2
        assert len(result.edges) == 3
        
        # Check for contradiction metadata
        vanilla_node = next(n for n in result.nodes if n.name == "Vanilla Preference")
        assert vanilla_node.attributes.get('has_contradictions') is True
        assert 'contradicted_nodes' in vanilla_node.attributes
        assert 'contradicting_nodes' in vanilla_node.attributes
        
        # Check for contradiction edges
        contradiction_edges = [e for e in result.edges if e.name == 'CONTRADICTS']
        regular_edges = [e for e in result.edges if e.name != 'CONTRADICTS']
        assert len(contradiction_edges) == 1
        assert len(regular_edges) == 2
    
    @pytest.mark.asyncio
    async def test_contradiction_summary(self, mock_graphiti):
        """Test getting contradiction summary."""
        summary = await mock_graphiti.get_contradiction_summary(group_ids=["user123"])
        
        assert summary['total_contradictions'] == 2
        assert summary['nodes_with_contradictions'] == 1
        assert len(summary['recent_contradictions']) == 1
        assert summary['recent_contradictions'][0].name == 'CONTRADICTS'
    
    @pytest.mark.asyncio
    async def test_enhanced_contradiction_search(self, mock_graphiti):
        """Test enhanced contradiction search functionality."""
        result = await mock_graphiti.enhanced_contradiction_search(
            query="ice cream",
            group_ids=["user123"]
        )
        
        assert len(result.nodes) == 1
        assert len(result.edges) == 1
        assert len(result.contradiction_edges) == 1
        assert len(result.contradicted_nodes_map) == 1
        assert len(result.contradicting_nodes_map) == 1
    
    @pytest.mark.asyncio
    async def test_close_connection(self, mock_graphiti):
        """Test closing the connection."""
        await mock_graphiti.close()
        assert mock_graphiti._closed is True


@pytest.mark.asyncio
async def test_complete_example_workflow():
    """Test the complete workflow from example.py."""
    mock_graphiti = MockExtendedGraphiti(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password",
        enable_contradiction_detection=True,
        contradiction_threshold=0.7
    )
    
    try:
        # Build indices
        await mock_graphiti.build_indices_and_constraints()
        
        user_id = "user123"
        
        # Episode 1: Like vanilla
        result1 = await mock_graphiti.add_episode_with_contradictions(
            name="Ice Cream Preference 1", 
            episode_body="I absolutely love vanilla ice cream.",
            source_description="User preference statement",
            reference_time=datetime.now(),
            group_id=user_id
        )
        assert not result1.contradiction_result.contradictions_found
        
        # Episode 2: Hate vanilla (contradiction)
        result2 = await mock_graphiti.add_episode_with_contradictions(
            name="Ice Cream Preference 2",
            episode_body="I hate vanilla ice cream.",
            source_description="User preference statement", 
            reference_time=datetime.now(),
            group_id=user_id
        )
        assert result2.contradiction_result.contradictions_found
        
        # Episode 3: Clarification
        result3 = await mock_graphiti.add_episode_with_contradictions(
            name="Ice Cream Clarification",
            episode_body="Actually, I used to like vanilla but my taste has changed.",
            source_description="User clarification",
            reference_time=datetime.now(),
            group_id=user_id
        )
        assert not result3.contradiction_result.contradictions_found
        
        # Test searches
        search_result = await mock_graphiti.contradiction_aware_search(
            query="ice cream preferences",
            group_ids=[user_id],
            include_contradictions=True
        )
        assert len(search_result.nodes) > 0
        assert len(search_result.edges) > 0
        
        # Test summary
        summary = await mock_graphiti.get_contradiction_summary(group_ids=[user_id])
        assert summary['total_contradictions'] > 0
        
        # Test enhanced search
        enhanced_result = await mock_graphiti.enhanced_contradiction_search(
            query="ice cream",
            group_ids=[user_id]
        )
        assert len(enhanced_result.nodes) > 0
        
    finally:
        await mock_graphiti.close()
        assert mock_graphiti._closed is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 