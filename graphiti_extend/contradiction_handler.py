"""
Contradiction handler that extends graphiti_core's contradiction detection
by adding explicit CONTRADICTS relationships between contradicting nodes.
"""

import logging
from typing import List, Tuple, Optional
from datetime import datetime

from neo4j import AsyncDriver
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge
from graphiti_core.utils.maintenance.edge_operations import (
    get_edge_contradictions,
    resolve_edge_contradictions
)
from graphiti_core.utils.datetime_utils import utc_now
from graphiti_core.llm_client import LLMClient

from graphiti_extend.custom_edges import CONTRADICTS
from graphiti_extend.custom_triplet import add_custom_triplet

logger = logging.getLogger(__name__)

async def detect_and_connect_contradictions(
    driver: AsyncDriver,
    llm_client: LLMClient,
    new_edge: EntityEdge,
    existing_edges: List[EntityEdge],
    group_id: str = ""
) -> Tuple[List[EntityEdge], List[EntityEdge]]:
    """
    Detect contradictions between a new edge and existing edges, then create
    explicit CONTRADICTS relationships between contradicting nodes.
    
    This extends graphiti_core's contradiction detection by adding explicit
    relationships between contradicting facts, making contradictions queryable.
    
    Parameters
    ----------
    driver : AsyncDriver
        The Neo4j async driver
    llm_client : LLMClient
        The LLM client for detecting contradictions
    new_edge : EntityEdge
        The new edge to check for contradictions
    existing_edges : List[EntityEdge]
        Existing edges to check against
    group_id : str, optional
        The group ID for new edges, by default ""
        
    Returns
    -------
    Tuple[List[EntityEdge], List[EntityEdge]]
        A tuple containing the newly created CONTRADICTS edges and invalidated edges
    """
    # Use graphiti_core's built-in contradiction detection
    invalidation_candidates = await get_edge_contradictions(llm_client, new_edge, existing_edges)
    
    # Resolve contradictions according to graphiti_core's temporal logic
    invalidated_edges = resolve_edge_contradictions(new_edge, invalidation_candidates)
    
    # Create explicit CONTRADICTS edges between contradicting nodes
    contradiction_edges = []
    for invalidated_edge in invalidated_edges:
        # Skip if the contradiction is temporal only (same source and target nodes)
        if (new_edge.source_node_uuid == invalidated_edge.source_node_uuid and 
            new_edge.target_node_uuid == invalidated_edge.target_node_uuid):
            logger.debug(f"Skipping temporal-only contradiction for {invalidated_edge.uuid}")
            continue
            
        # Create a CONTRADICTS edge from the new edge's source to the invalidated edge's source
        # (if they are different)
        if new_edge.source_node_uuid != invalidated_edge.source_node_uuid:
            # Fetch the source nodes
            source_node_result, _, _ = await driver.execute_query(
                "MATCH (n:Entity {uuid: $uuid}) RETURN n",
                uuid=new_edge.source_node_uuid,
                database_="neo4j"
            )
            invalidated_source_result, _, _ = await driver.execute_query(
                "MATCH (n:Entity {uuid: $uuid}) RETURN n",
                uuid=invalidated_edge.source_node_uuid,
                database_="neo4j"
            )
            
            if source_node_result and invalidated_source_result:
                # Create source nodes from the results
                source_node = EntityNode(
                    uuid=new_edge.source_node_uuid,
                    name=source_node_result[0]["n"]["name"],
                    group_id=new_edge.group_id,
                    attributes=source_node_result[0]["n"].get("attributes", {})
                )
                invalidated_source = EntityNode(
                    uuid=invalidated_edge.source_node_uuid,
                    name=invalidated_source_result[0]["n"]["name"],
                    group_id=invalidated_edge.group_id,
                    attributes=invalidated_source_result[0]["n"].get("attributes", {})
                )
                
                # Build the contradiction fact
                fact = f"'{source_node.name}' contradicts '{invalidated_source.name}'"
                
                # Create the CONTRADICTS edge
                contradiction_edge = await add_custom_triplet(
                    driver=driver,
                    source_node=source_node,
                    edge_type=CONTRADICTS,
                    target_node=invalidated_source,
                    fact=fact,
                    group_id=group_id or new_edge.group_id,
                    valid_at=utc_now()
                )
                
                contradiction_edges.append(contradiction_edge)
                logger.info(f"Created CONTRADICTS edge: {source_node.name} → {invalidated_source.name}")
        
        # Create a CONTRADICTS edge from the new edge's target to the invalidated edge's target
        # (if they are different)
        if new_edge.target_node_uuid != invalidated_edge.target_node_uuid:
            # Fetch the target nodes
            target_node_result, _, _ = await driver.execute_query(
                "MATCH (n:Entity {uuid: $uuid}) RETURN n",
                uuid=new_edge.target_node_uuid,
                database_="neo4j"
            )
            invalidated_target_result, _, _ = await driver.execute_query(
                "MATCH (n:Entity {uuid: $uuid}) RETURN n",
                uuid=invalidated_edge.target_node_uuid,
                database_="neo4j"
            )
            
            if target_node_result and invalidated_target_result:
                # Create target nodes from the results
                target_node = EntityNode(
                    uuid=new_edge.target_node_uuid,
                    name=target_node_result[0]["n"]["name"],
                    group_id=new_edge.group_id,
                    attributes=target_node_result[0]["n"].get("attributes", {})
                )
                invalidated_target = EntityNode(
                    uuid=invalidated_edge.target_node_uuid,
                    name=invalidated_target_result[0]["n"]["name"],
                    group_id=invalidated_edge.group_id,
                    attributes=invalidated_target_result[0]["n"].get("attributes", {})
                )
                
                # Build the contradiction fact
                fact = f"'{target_node.name}' contradicts '{invalidated_target.name}'"
                
                # Create the CONTRADICTS edge
                contradiction_edge = await add_custom_triplet(
                    driver=driver,
                    source_node=target_node,
                    edge_type=CONTRADICTS,
                    target_node=invalidated_target,
                    fact=fact,
                    group_id=group_id or new_edge.group_id,
                    valid_at=utc_now()
                )
                
                contradiction_edges.append(contradiction_edge)
                logger.info(f"Created CONTRADICTS edge: {target_node.name} → {invalidated_target.name}")
    
    return contradiction_edges, invalidated_edges 