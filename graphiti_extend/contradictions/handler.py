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

import logging
from time import time
from typing import List, Optional, Callable, Any
import uuid

from graphiti_core.edges import EntityEdge
from graphiti_core.llm_client import LLMClient
from graphiti_core.llm_client.config import ModelSize
from graphiti_core.nodes import EntityNode, EpisodicNode
from graphiti_core.utils.datetime_utils import utc_now

# Import CognitiveObject directly to avoid circular imports
# from fcs_core.models import CognitiveObject

# Define CognitiveObject locally to avoid circular import
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class CognitiveObject(BaseModel):
    """Structured representation of user-expressed or system-derived ideas."""
    id: str = Field(..., description="Unique identifier (UUID)")
    content: str = Field(..., description="Natural language text expressed or inferred")
    type: str = Field(..., description="Enum: idea, contradiction, reference, system_note")
    confidence: float = Field(default=0.7, description="Float [0.0 – 1.0] — how sure the system is this idea is currently valid")
    salience: float = Field(default=0.5, description="Float — how central or reinforced this idea is within the session")
    source: str = Field(..., description="One of user, external, or system")
    flags: List[str] = Field(default_factory=list, description="Optional list, e.g. tracked, contradiction, external, unverified, dismissed")
    parent_ids: List[str] = Field(default_factory=list, description="List of UUIDs — COs this idea directly builds on")
    child_ids: List[str] = Field(default_factory=list, description="List of UUIDs — COs derived from this idea")
    match_history: List[str] = Field(default_factory=list, description="Optional list of CO IDs that have semantically reinforced this CO")
    arbitration_score: Optional[float] = Field(None, description="Optional — last known score from arbitration pass")
    linked_refs: List[str] = Field(default_factory=list, description="Optional list of CO.id or source string, e.g., reference DOI or URL")
    generated_from: List[str] = Field(default_factory=list, description="Optional list of CO IDs used to construct this one (for LLM output tracking)")
from graphiti_extend.prompts.contradiction import ContradictionPairs, get_contradiction_pairs_prompt

logger = logging.getLogger(__name__)


def entity_node_to_cognitive_object(entity_node: EntityNode) -> CognitiveObject:
    """
    Convert an EntityNode to a CognitiveObject for FCS processing.
    
    Parameters
    ----------
    entity_node : EntityNode
        The EntityNode to convert
        
    Returns
    -------
    CognitiveObject
        The converted CognitiveObject
    """
    return CognitiveObject(
        id=entity_node.uuid,
        content=entity_node.summary or entity_node.name,
        type="idea",  # Default type for contradiction analysis
        confidence=getattr(entity_node, 'confidence', 0.7),
        salience=getattr(entity_node, 'salience', 0.5),
        source="user",  # Assume user-derived for contradiction analysis
        flags=[],
        parent_ids=[],
        child_ids=[],
        match_history=[],
        arbitration_score=None,
        linked_refs=[],
        generated_from=[]
    )


def cognitive_object_to_entity_node(cognitive_object: CognitiveObject, group_id: str) -> EntityNode:
    """
    Convert a CognitiveObject to an EntityNode for Graphiti integration.
    
    Parameters
    ----------
    cognitive_object : CognitiveObject
        The CognitiveObject to convert
    group_id : str
        Group ID for the EntityNode
        
    Returns
    -------
    EntityNode
        The converted EntityNode
    """
    return EntityNode(
        uuid=cognitive_object.id,
        name=cognitive_object.content[:100],  # Truncate for name field
        group_id=group_id,
        labels=['Entity', 'CognitiveObject'],
        summary=cognitive_object.content,
        created_at=utc_now(),
        attributes={
            'cognitive_object_type': cognitive_object.type,
            'confidence': cognitive_object.confidence,
            'salience': cognitive_object.salience,
            'source': cognitive_object.source,
            'flags': cognitive_object.flags,
        }
    )


def create_cognitive_object_from_llm_data(node_data: dict[str, Any], group_id: str) -> CognitiveObject:
    """
    Create a CognitiveObject from LLM response data.
    
    Parameters
    ----------
    node_data : dict[str, Any]
        Node data from LLM response
    group_id : str
        Group ID for context
        
    Returns
    -------
    CognitiveObject
        The created CognitiveObject
    """
    return CognitiveObject(
        id=str(uuid.uuid4()),
        content=node_data.get('summary', node_data.get('name', '')),
        type="contradiction",  # Type for contradiction-related cognitive objects
        confidence=0.8,  # High confidence for LLM-detected contradictions
        salience=0.6,  # Medium salience for new contradictions
        source="system",  # System-derived from contradiction detection
        flags=["contradiction", "newly_detected"],
        parent_ids=[],
        child_ids=[],
        match_history=[],
        arbitration_score=None,
        linked_refs=[],
        generated_from=[]
    )


async def detect_contradiction_pairs(
    llm_client: LLMClient,
    episode: EpisodicNode,
    existing_nodes: List[EntityNode],
    previous_episodes: Optional[List[EpisodicNode]] = None,
) -> List[tuple[EntityNode, EntityNode, str]]:
    """
    Detect contradiction pairs as cognitive objects using LLM.
    
    Parameters
    ----------
    llm_client : LLMClient
        The LLM client for generating responses
    episode : EpisodicNode
        Current episode being processed
    existing_nodes : List[EntityNode]
        Existing nodes in the graph to check against
    previous_episodes : Optional[List[EpisodicNode]]
        Previous episodes for context
        
    Returns
    -------
    List[tuple[EntityNode, EntityNode, str]]
        List of (node1, node2, contradiction_reason) tuples
    """
    start = time()
    
    if not existing_nodes:
        logger.debug("No existing nodes to check for contradictions")
        return []
    
    # Prepare context for LLM
    existing_nodes_context = [
        {
            'name': node.name,
            'summary': node.summary or '',
            'labels': node.labels,
            'attributes': node.attributes or {},
        }
        for node in existing_nodes
    ]
    
    context = {
        'episode_content': episode.content,
        'existing_nodes': existing_nodes_context,
        'previous_episodes': [ep.content for ep in previous_episodes] if previous_episodes else [],
    }
    
    try:
        # Use the new contradiction pairs prompt
        llm_response = await llm_client.generate_response(
            get_contradiction_pairs_prompt(context),
            response_model=ContradictionPairs,
            model_size=ModelSize.small,
        )
        
        contradiction_pairs_data = llm_response.get('contradiction_pairs', [])
        contradiction_pairs = []
        
        # Convert LLM response to EntityNode pairs
        for pair_data in contradiction_pairs_data:
            node1_data = pair_data.get('node1', {})
            node2_data = pair_data.get('node2', {})
            reason = pair_data.get('contradiction_reason', 'Contradictory concepts detected')
            
            # Create or find node1
            node1 = _find_or_create_node(node1_data, existing_nodes, episode.group_id)
            
            # Create or find node2
            node2 = _find_or_create_node(node2_data, existing_nodes, episode.group_id)
            
            if node1 and node2 and node1.uuid != node2.uuid:
                contradiction_pairs.append((node1, node2, reason))
                logger.debug(f"Found contradiction pair: {node1.name} <-> {node2.name}")
        
        end = time()
        logger.debug(f'Detected {len(contradiction_pairs)} contradiction pairs in {(end - start) * 1000} ms')
        
        return contradiction_pairs
        
    except Exception as e:
        logger.error(f"Error detecting contradiction pairs: {str(e)}")
        return []


def _find_or_create_node(
    node_data: dict[str, Any], 
    existing_nodes: List[EntityNode], 
    group_id: str
) -> Optional[EntityNode]:
    """
    Find an existing node or create a new cognitive object as EntityNode.
    
    This function now follows the Cognitive Object (CO) format as requested,
    creating proper cognitive objects for contradiction detection.
    
    Parameters
    ----------
    node_data : dict[str, Any]
        Node data from LLM response
    existing_nodes : List[EntityNode]
        Existing nodes to search through
    group_id : str
        Group ID for new nodes
        
    Returns
    -------
    Optional[EntityNode]
        Found or created EntityNode (representing a Cognitive Object), or None if invalid data
    """
    try:
        if not node_data or not node_data.get('name'):
            logger.warning("Invalid node data provided to _find_or_create_node")
            return None
        
        node_name = node_data['name'].strip()
        node_summary = node_data.get('summary', '').strip()
        entity_type = node_data.get('entity_type', 'Entity')
        
        if not node_name:
            logger.warning("Empty node name provided to _find_or_create_node")
            return None
        
        # First, try to find existing node by name (exact match)
        for existing_node in existing_nodes:
            if existing_node.name.lower() == node_name.lower():
                logger.debug(f"Found existing cognitive object: {existing_node.name} (UUID: {existing_node.uuid})")
                return existing_node
        
        # If not found, create a new cognitive object using the CO format
        logger.info(f"Creating new cognitive object for contradiction: {node_name}")
        
        # Create the cognitive object first
        cognitive_object = create_cognitive_object_from_llm_data(node_data, group_id)
        
        # Convert to EntityNode for Graphiti integration
        entity_node = cognitive_object_to_entity_node(cognitive_object, group_id)
        
        # Override the name to use the provided name instead of truncated content
        entity_node.name = node_name
        entity_node.summary = node_summary if node_summary else cognitive_object.content
        
        logger.info(f"Created new cognitive object as EntityNode: {entity_node.name} (UUID: {entity_node.uuid})")
        logger.debug(f"Cognitive object details - Type: {cognitive_object.type}, Confidence: {cognitive_object.confidence}, Flags: {cognitive_object.flags}")
        
        return entity_node
        
    except Exception as e:
        logger.error(f"Error in _find_or_create_node: {str(e)}")
        # Log only essential data without embeddings
        essential_data = {
            'name': node_data.get('name', 'unknown') if node_data else 'no_data',
            'entity_type': node_data.get('entity_type', 'unknown') if node_data else 'no_data',
            'summary_length': len(str(node_data.get('summary', ''))) if node_data else 0
        }
        logger.error(f"Essential node data: {essential_data}")
        return None



async def _contradiction_exists(
    driver,
    node1_uuid: str,
    node2_uuid: str,
) -> bool:
    """
    Check if a CONTRADICTS relationship already exists between two nodes.
    
    Parameters
    ----------
    driver
        Neo4j driver instance
    node1_uuid : str
        UUID of first node
    node2_uuid : str
        UUID of second node
        
    Returns
    -------
    bool
        True if contradiction relationship exists in either direction
    """
    query = """
    MATCH (n1:Entity {uuid: $node1_uuid})-[r:CONTRADICTS]-(n2:Entity {uuid: $node2_uuid})
    RETURN count(r) as count
    """
    
    try:
        records, _, _ = await driver.execute_query(
            query, 
            node1_uuid=node1_uuid, 
            node2_uuid=node2_uuid
        )
        
        if records and records[0]["count"] > 0:
            logger.debug(f"Contradiction already exists between {node1_uuid} and {node2_uuid}")
            return True
        return False
        
    except Exception as e:
        logger.error(f"Error checking for existing contradiction: {str(e)}")
        return False


async def create_contradiction_edges_from_pairs(
    contradiction_pairs: List[tuple[EntityNode, EntityNode, str]],
    episode: EpisodicNode,
    add_triplet_func: Callable[[EntityNode, EntityEdge, EntityNode], Any],
    driver = None,
) -> List[EntityEdge]:
    """
    Create CONTRADICTS edges from contradiction pairs using add_triplet.
    Only creates edges if they don't already exist.
    
    Parameters
    ----------
    contradiction_pairs : List[tuple[EntityNode, EntityNode, str]]
        List of contradiction pairs with reasons
    episode : EpisodicNode
        Current episode
    add_triplet_func : Callable
        Function to add triplet (source_node, edge, target_node)
    driver : optional
        Neo4j driver for checking existing relationships
        
    Returns
    -------
    List[EntityEdge]
        List of created contradiction edges
    """
    contradiction_edges = []
    now = utc_now()
    
    for node1, node2, reason in contradiction_pairs:
        try:
            # Check if contradiction already exists between these nodes
            if driver and await _contradiction_exists(driver, node1.uuid, node2.uuid):
                logger.info(f'Contradiction already exists between {node1.name} and {node2.name}, skipping creation')
                continue
            
            # Create contradiction edge
            contradiction_edge = EntityEdge(
                source_node_uuid=node1.uuid,
                target_node_uuid=node2.uuid,
                name='CONTRADICTS',
                group_id=episode.group_id,
                fact=f'{node1.name} contradicts {node2.name}: {reason}',
                episodes=[episode.uuid],
                created_at=now,
                valid_at=episode.valid_at,
                attributes={
                    'contradiction_reason': reason,
                    'detected_in_episode': episode.uuid,
                }
            )
            
            # Use add_triplet to create the relationship
            await add_triplet_func(node1, contradiction_edge, node2)
            
            contradiction_edges.append(contradiction_edge)
            logger.info(f'Created CONTRADICTS edge: {node1.name} -> {node2.name} ({reason})')
            
        except Exception as e:
            logger.error(f"Error creating contradiction edge between {node1.name} and {node2.name}: {str(e)}")
    
    return contradiction_edges


async def detect_and_create_node_contradictions(
    llm_client: LLMClient,
    episode: EpisodicNode,
    existing_nodes: List[EntityNode],
    add_triplet_func: Callable[[EntityNode, EntityEdge, EntityNode], Any],
    previous_episodes: Optional[List[EpisodicNode]] = None,
    driver = None,
) -> List[EntityEdge]:
    """
    Main function to detect contradictions and create contradiction edges.
    
    This is the new main entry point that replaces the old contradiction detection logic.
    
    Parameters
    ----------
    llm_client : LLMClient
        The LLM client for generating responses
    episode : EpisodicNode
        Current episode being processed
    existing_nodes : List[EntityNode]
        Existing nodes in the graph to check against
    add_triplet_func : Callable
        Function to add triplet (source_node, edge, target_node)
    previous_episodes : Optional[List[EpisodicNode]]
        Previous episodes for context
        
    Returns
    -------
    List[EntityEdge]
        List of created contradiction edges
    """
    try:
        # Step 1: Detect contradiction pairs as cognitive objects
        contradiction_pairs = await detect_contradiction_pairs(
            llm_client, episode, existing_nodes, previous_episodes
        )
        
        if not contradiction_pairs:
            logger.debug("No contradiction pairs detected")
            return []
        
        # Step 2: Create contradiction edges for normal flow (with deduplication)
        contradiction_nodes, contradiction_edges = await detect_node_contradictions_for_flow(
            llm_client, episode, existing_nodes, previous_episodes, driver
        )
        
        # Return the edges for normal flow processing
        return contradiction_edges
        
        logger.info(f"Successfully created {len(contradiction_edges)} contradiction edges")
        return contradiction_edges
        
    except Exception as e:
        logger.error(f"Error in detect_and_create_node_contradictions: {str(e)}")
        return []


async def detect_node_contradictions_for_flow(
    llm_client: LLMClient,
    episode: EpisodicNode,
    existing_nodes: List[EntityNode],
    previous_episodes: Optional[List[EpisodicNode]] = None,
    driver = None,
) -> tuple[List[EntityNode], List[EntityEdge]]:
    """
    Detect contradictions and return nodes and edges for normal flow integration.
    
    This function detects contradictions and returns the data to be processed
    through the normal node and edge flow, ensuring proper deduplication.
    
    Parameters
    ----------
    llm_client : LLMClient
        The LLM client for generating responses
    episode : EpisodicNode
        Current episode being processed
    existing_nodes : List[EntityNode]
        Existing nodes in the graph to check against
    previous_episodes : Optional[List[EpisodicNode]]
        Previous episodes for context
    driver : optional
        Neo4j driver for checking existing relationships
        
    Returns
    -------
    tuple[List[EntityNode], List[EntityEdge]]
        Tuple of (contradiction_nodes, contradiction_edges) to be added to normal flow
    """
    try:
        # Step 1: Detect contradiction pairs as cognitive objects
        contradiction_pairs = await detect_contradiction_pairs(
            llm_client, episode, existing_nodes, previous_episodes
        )
        
        if not contradiction_pairs:
            logger.debug("No contradiction pairs detected")
            return [], []
        
        # Step 2: Extract nodes and create edges for normal flow
        contradiction_nodes = []
        contradiction_edges = []
        now = utc_now()
        
        for node1, node2, reason in contradiction_pairs:
            try:
                # Check if contradiction already exists between these nodes
                if driver and await _contradiction_exists(driver, node1.uuid, node2.uuid):
                    logger.info(f'Contradiction already exists between {node1.name} and {node2.name}, skipping creation')
                    continue
                
                # Add nodes to the list (deduplication will be handled by normal flow)
                if node1 not in contradiction_nodes:
                    contradiction_nodes.append(node1)
                if node2 not in contradiction_nodes:
                    contradiction_nodes.append(node2)
                
                # Create contradiction edge for normal flow
                contradiction_edge = EntityEdge(
                    source_node_uuid=node1.uuid,
                    target_node_uuid=node2.uuid,
                    name='CONTRADICTS',
                    group_id=episode.group_id,
                    fact=f'{node1.name} contradicts {node2.name}: {reason}',
                    episodes=[episode.uuid],
                    created_at=now,
                    valid_at=episode.valid_at,
                    attributes={
                        'contradiction_reason': reason,
                        'detected_in_episode': episode.uuid,
                        'type': 'contradiction',  # Add type for easier identification
                    }
                )
                
                contradiction_edges.append(contradiction_edge)
                logger.debug(f'Prepared contradiction edge for normal flow: {node1.name} -> {node2.name}')
                
            except Exception as e:
                logger.error(f"Error preparing contradiction data for {node1.name} and {node2.name}: {str(e)}")
        
        logger.info(f"Prepared {len(contradiction_nodes)} contradiction nodes and {len(contradiction_edges)} contradiction edges for normal flow")
        return contradiction_nodes, contradiction_edges
        
    except Exception as e:
        logger.error(f"Error in detect_node_contradictions_for_flow: {str(e)}")
        return [], []


# Legacy functions for backward compatibility (can be removed later)
async def get_node_contradictions(
    llm_client: LLMClient,
    new_node: EntityNode,
    existing_nodes: list[EntityNode],
    episode: EpisodicNode | None = None,
    previous_episodes: list[EpisodicNode] | None = None,
) -> list[EntityNode]:
    """Legacy function - use detect_and_create_node_contradictions instead."""
    logger.warning("Using legacy get_node_contradictions function. Consider upgrading to new API.")
    return []


async def create_contradiction_edges(
    new_node: EntityNode,
    contradicted_nodes: list[EntityNode],
    episode: EpisodicNode,
) -> list[EntityEdge]:
    """Legacy function - use detect_and_create_node_contradictions instead."""
    logger.warning("Using legacy create_contradiction_edges function. Consider upgrading to new API.")
    return []
