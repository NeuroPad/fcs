"""
Custom triplet implementation that extends the functionality of graphiti_core
with support for creating custom edge types.
"""

from datetime import datetime
from uuid import uuid4

from neo4j import AsyncDriver
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge
from graphiti_core.helpers import DEFAULT_DATABASE
from graphiti_extend.custom_edges import (
    CUSTOM_EDGE_TYPES, 
    CUSTOM_EDGE_TYPE_CREATION_QUERY
)

import logging

logger = logging.getLogger(__name__)

async def add_custom_triplet(
    driver: AsyncDriver,
    source_node: EntityNode, 
    edge_type: str,
    target_node: EntityNode,
    fact: str,
    group_id: str = "",
    episodes: list[str] = None,
    valid_at: datetime = None,
    invalid_at: datetime = None,
) -> EntityEdge:
    """
    Create a custom triplet with a specified edge type.
    
    Parameters
    ----------
    driver : AsyncDriver
        The Neo4j async driver
    source_node : EntityNode
        The source node of the triplet
    edge_type : str
        The type of edge to create (e.g., REINFORCES, CONTRADICTS)
    target_node : EntityNode
        The target node of the triplet
    fact : str
        The fact representing the relationship
    group_id : str, optional
        The group ID for the edge, by default ""
    episodes : list[str], optional
        List of episode UUIDs related to this edge, by default None
    valid_at : datetime, optional
        When the fact became valid, by default None
    invalid_at : datetime, optional
        When the fact became invalid, by default None
        
    Returns
    -------
    EntityEdge
        The created edge between the source and target nodes
    
    Raises
    ------
    ValueError
        If the edge_type is not supported
    """
    if edge_type not in CUSTOM_EDGE_TYPES and edge_type != "MENTIONS":
        raise ValueError(f"Unsupported edge type: {edge_type}. Use one of {CUSTOM_EDGE_TYPES + ['MENTIONS']}")
    
    # Create edge UUID
    edge_uuid = str(uuid4())
    
    # Use current time if valid_at is not provided
    if valid_at is None:
        valid_at = datetime.now()
    
    # Ensure episodes is a list
    if episodes is None:
        episodes = []
    
    # Save the edge to the database
    result = await driver.execute_query(
        CUSTOM_EDGE_TYPE_CREATION_QUERY,
        source_node_uuid=source_node.uuid,
        target_node_uuid=target_node.uuid,
        uuid=edge_uuid,
        group_id=group_id or source_node.group_id,
        edge_type=edge_type,
        fact=fact,
        episodes=episodes,
        created_at=datetime.now(),
        valid_at=valid_at,
        invalid_at=invalid_at,
        database_=DEFAULT_DATABASE,
    )
    
    logger.debug(f"Created custom edge of type {edge_type}: {edge_uuid}")
    
    # Create and return an EntityEdge object
    edge = EntityEdge(
        uuid=edge_uuid,
        source_node_uuid=source_node.uuid,
        target_node_uuid=target_node.uuid,
        name=edge_type,
        fact=fact,
        episodes=episodes,
        group_id=group_id or source_node.group_id,
        created_at=datetime.now(),
        valid_at=valid_at,
        invalid_at=invalid_at,
    )
    
    return edge 