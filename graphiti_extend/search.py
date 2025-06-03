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
from typing import Any

from neo4j import AsyncDriver
from typing_extensions import LiteralString

from graphiti_core.edges import EntityEdge, get_entity_edge_from_record
from graphiti_core.graphiti_types import GraphitiClients
from graphiti_core.helpers import DEFAULT_DATABASE, RUNTIME_QUERY
from graphiti_core.nodes import EntityNode, get_entity_node_from_record
from graphiti_core.search.search import search
from graphiti_core.search.search_config import SearchConfig, SearchResults
from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_CROSS_ENCODER
from graphiti_core.search.search_filters import SearchFilters

logger = logging.getLogger(__name__)


async def get_contradiction_edges(
    driver: AsyncDriver,
    group_ids: list[str] | None = None,
    limit: int = 100,
) -> list[EntityEdge]:
    """
    Retrieve all CONTRADICTS edges from the graph.
    
    Parameters
    ----------
    driver : AsyncDriver
        The Neo4j driver instance.
    group_ids : list[str] | None, optional
        Filter by group IDs.
    limit : int, optional
        Maximum number of edges to return.
        
    Returns
    -------
    list[EntityEdge]
        List of CONTRADICTS edges.
    """
    query_params: dict[str, Any] = {}
    
    group_filter_query: LiteralString = ''
    if group_ids is not None:
        group_filter_query = 'WHERE e.group_id IN $group_ids'
        query_params['group_ids'] = group_ids

    query = (
        RUNTIME_QUERY
        + """
        MATCH (n:Entity)-[e:RELATES_TO {name: 'CONTRADICTS'}]->(m:Entity)
        """
        + group_filter_query
        + """
        RETURN e.uuid as uuid,
               startNode(e).uuid as source_node_uuid,
               endNode(e).uuid as target_node_uuid,
               e.created_at as created_at,
               e.name as name,
               e.group_id as group_id,
               e.fact as fact,
               e.fact_embedding as fact_embedding,
               e.episodes as episodes,
               e.expired_at as expired_at,
               e.valid_at as valid_at,
               e.invalid_at as invalid_at,
               properties(e) as attributes
        LIMIT $limit
        """
    )

    records, _, _ = await driver.execute_query(
        query,
        query_params,
        limit=limit,
        database_=DEFAULT_DATABASE,
        routing_='r',
    )
    
    edges = [get_entity_edge_from_record(record) for record in records]
    return edges


async def get_contradicted_nodes(
    driver: AsyncDriver,
    node_uuids: list[str],
    group_ids: list[str] | None = None,
) -> dict[str, list[EntityNode]]:
    """
    Get nodes that are contradicted by the given nodes.
    
    Parameters
    ----------
    driver : AsyncDriver
        The Neo4j driver instance.
    node_uuids : list[str]
        UUIDs of nodes to check for contradictions.
    group_ids : list[str] | None, optional
        Filter by group IDs.
        
    Returns
    -------
    dict[str, list[EntityNode]]
        Mapping of node UUID to list of nodes it contradicts.
    """
    if not node_uuids:
        return {}
    
    query_params: dict[str, Any] = {'node_uuids': node_uuids}
    
    group_filter_query: LiteralString = ''
    if group_ids is not None:
        group_filter_query = 'WHERE e.group_id IN $group_ids'
        query_params['group_ids'] = group_ids

    query = (
        RUNTIME_QUERY
        + """
        UNWIND $node_uuids AS node_uuid
        MATCH (n:Entity {uuid: node_uuid})-[e:RELATES_TO {name: 'CONTRADICTS'}]->(m:Entity)
        """
        + group_filter_query
        + """
        RETURN node_uuid,
               collect({
                   uuid: m.uuid,
                   name: m.name,
                   name_embedding: m.name_embedding,
                   group_id: m.group_id,
                   summary: m.summary,
                   created_at: m.created_at,
                   labels: labels(m),
                   attributes: properties(m)
               }) as contradicted_nodes
        """
    )

    records, _, _ = await driver.execute_query(
        query,
        query_params,
        database_=DEFAULT_DATABASE,
        routing_='r',
    )
    
    result = {}
    for record in records:
        node_uuid = record['node_uuid']
        contradicted_nodes = [
            get_entity_node_from_record(node_data) 
            for node_data in record['contradicted_nodes']
        ]
        result[node_uuid] = contradicted_nodes
    
    return result


async def get_contradicting_nodes(
    driver: AsyncDriver,
    node_uuids: list[str],
    group_ids: list[str] | None = None,
) -> dict[str, list[EntityNode]]:
    """
    Get nodes that contradict the given nodes.
    
    Parameters
    ----------
    driver : AsyncDriver
        The Neo4j driver instance.
    node_uuids : list[str]
        UUIDs of nodes to check for contradictions.
    group_ids : list[str] | None, optional
        Filter by group IDs.
        
    Returns
    -------
    dict[str, list[EntityNode]]
        Mapping of node UUID to list of nodes that contradict it.
    """
    if not node_uuids:
        return {}
    
    query_params: dict[str, Any] = {'node_uuids': node_uuids}
    
    group_filter_query: LiteralString = ''
    if group_ids is not None:
        group_filter_query = 'WHERE e.group_id IN $group_ids'
        query_params['group_ids'] = group_ids

    query = (
        RUNTIME_QUERY
        + """
        UNWIND $node_uuids AS node_uuid
        MATCH (n:Entity)-[e:RELATES_TO {name: 'CONTRADICTS'}]->(m:Entity {uuid: node_uuid})
        """
        + group_filter_query
        + """
        RETURN node_uuid,
               collect({
                   uuid: n.uuid,
                   name: n.name,
                   name_embedding: n.name_embedding,
                   group_id: n.group_id,
                   summary: n.summary,
                   created_at: n.created_at,
                   labels: labels(n),
                   attributes: properties(n)
               }) as contradicting_nodes
        """
    )

    records, _, _ = await driver.execute_query(
        query,
        query_params,
        database_=DEFAULT_DATABASE,
        routing_='r',
    )
    
    result = {}
    for record in records:
        node_uuid = record['node_uuid']
        contradicting_nodes = [
            get_entity_node_from_record(node_data) 
            for node_data in record['contradicting_nodes']
        ]
        result[node_uuid] = contradicting_nodes
    
    return result


async def contradiction_aware_search(
    clients: GraphitiClients,
    query: str,
    config: SearchConfig = COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
    group_ids: list[str] | None = None,
    center_node_uuid: str | None = None,
    bfs_origin_node_uuids: list[str] | None = None,
    search_filter: SearchFilters | None = None,
    include_contradictions: bool = True,
    contradiction_weight: float = 0.1,
) -> SearchResults:
    """
    Perform a contradiction-aware search on the knowledge graph.
    
    This search extends the standard search functionality by including information
    about contradictions between nodes. It can optionally include contradicted
    nodes in the results with lower weights.
    
    Parameters
    ----------
    clients : GraphitiClients
        The Graphiti clients containing driver, LLM, embedder, etc.
    query : str
        The search query string.
    config : SearchConfig, optional
        Search configuration. Defaults to COMBINED_HYBRID_SEARCH_CROSS_ENCODER.
    group_ids : list[str] | None, optional
        Filter by group IDs.
    center_node_uuid : str | None, optional
        Center node for distance-based reranking.
    bfs_origin_node_uuids : list[str] | None, optional
        Origin nodes for BFS search.
    search_filter : SearchFilters | None, optional
        Additional search filters.
    include_contradictions : bool, optional
        Whether to include contradiction information in results. Defaults to True.
    contradiction_weight : float, optional
        Weight to apply to contradicted nodes in scoring. Defaults to 0.1.
        
    Returns
    -------
    SearchResults
        Enhanced search results with contradiction information.
    """
    # Perform standard search
    search_results = await search(
        clients,
        query,
        group_ids,
        config,
        search_filter if search_filter is not None else SearchFilters(),
        center_node_uuid,
        bfs_origin_node_uuids,
    )
    
    if not include_contradictions:
        return search_results
    
    # Get contradiction information for nodes in results
    node_uuids = [node.uuid for node in search_results.nodes]
    edge_source_uuids = [edge.source_node_uuid for edge in search_results.edges]
    edge_target_uuids = [edge.target_node_uuid for edge in search_results.edges]
    all_node_uuids = list(set(node_uuids + edge_source_uuids + edge_target_uuids))
    
    if all_node_uuids:
        contradicted_map = await get_contradicted_nodes(
            clients.driver, all_node_uuids, group_ids
        )
        contradicting_map = await get_contradicting_nodes(
            clients.driver, all_node_uuids, group_ids
        )
        
        # Add contradiction metadata to nodes
        for node in search_results.nodes:
            node.attributes = node.attributes or {}
            node.attributes['contradicted_nodes'] = [
                n.uuid for n in contradicted_map.get(node.uuid, [])
            ]
            node.attributes['contradicting_nodes'] = [
                n.uuid for n in contradicting_map.get(node.uuid, [])
            ]
            node.attributes['has_contradictions'] = (
                len(contradicted_map.get(node.uuid, [])) > 0 or
                len(contradicting_map.get(node.uuid, [])) > 0
            )
    
    # Get all CONTRADICTS edges for additional context
    contradiction_edges = await get_contradiction_edges(
        clients.driver, group_ids, limit=1000
    )
    
    # Add contradiction edges to results
    search_results.edges.extend(contradiction_edges)
    
    logger.debug(
        f'Contradiction-aware search found {len(contradiction_edges)} contradiction edges'
    )
    
    return search_results


class ContradictionSearchResults(SearchResults):
    """Extended search results that include contradiction information."""
    
    contradiction_edges: list[EntityEdge]
    contradicted_nodes_map: dict[str, list[EntityNode]]
    contradicting_nodes_map: dict[str, list[EntityNode]]
    
    def __init__(
        self,
        edges: list[EntityEdge],
        nodes: list[EntityNode],
        episodes: list,
        communities: list,
        contradiction_edges: list[EntityEdge] | None = None,
        contradicted_nodes_map: dict[str, list[EntityNode]] | None = None,
        contradicting_nodes_map: dict[str, list[EntityNode]] | None = None,
    ):
        super().__init__(edges=edges, nodes=nodes, episodes=episodes, communities=communities)
        self.contradiction_edges = contradiction_edges or []
        self.contradicted_nodes_map = contradicted_nodes_map or {}
        self.contradicting_nodes_map = contradicting_nodes_map or {}


async def enhanced_contradiction_search(
    clients: GraphitiClients,
    query: str,
    config: SearchConfig = COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
    group_ids: list[str] | None = None,
    center_node_uuid: str | None = None,
    bfs_origin_node_uuids: list[str] | None = None,
    search_filter: SearchFilters | None = None,
) -> ContradictionSearchResults:
    """
    Perform an enhanced contradiction-aware search with detailed contradiction mappings.
    
    This function provides more detailed contradiction information compared to
    the basic contradiction_aware_search function.
    
    Parameters
    ----------
    clients : GraphitiClients
        The Graphiti clients containing driver, LLM, embedder, etc.
    query : str
        The search query string.
    config : SearchConfig, optional
        Search configuration.
    group_ids : list[str] | None, optional
        Filter by group IDs.
    center_node_uuid : str | None, optional
        Center node for distance-based reranking.
    bfs_origin_node_uuids : list[str] | None, optional
        Origin nodes for BFS search.
    search_filter : SearchFilters | None, optional
        Additional search filters.
        
    Returns
    -------
    ContradictionSearchResults
        Enhanced search results with detailed contradiction mappings.
    """
    # Perform standard search
    search_results = await search(
        clients,
        query,
        group_ids,
        config,
        search_filter if search_filter is not None else SearchFilters(),
        center_node_uuid,
        bfs_origin_node_uuids,
    )
    
    # Get all node UUIDs from results
    node_uuids = [node.uuid for node in search_results.nodes]
    edge_source_uuids = [edge.source_node_uuid for edge in search_results.edges]
    edge_target_uuids = [edge.target_node_uuid for edge in search_results.edges]
    all_node_uuids = list(set(node_uuids + edge_source_uuids + edge_target_uuids))
    
    # Get contradiction mappings
    contradicted_map = {}
    contradicting_map = {}
    contradiction_edges = []
    
    if all_node_uuids:
        contradicted_map = await get_contradicted_nodes(
            clients.driver, all_node_uuids, group_ids
        )
        contradicting_map = await get_contradicting_nodes(
            clients.driver, all_node_uuids, group_ids
        )
        contradiction_edges = await get_contradiction_edges(
            clients.driver, group_ids, limit=1000
        )
    
    return ContradictionSearchResults(
        edges=search_results.edges,
        nodes=search_results.nodes,
        episodes=search_results.episodes,
        communities=search_results.communities,
        contradiction_edges=contradiction_edges,
        contradicted_nodes_map=contradicted_map,
        contradicting_nodes_map=contradicting_map,
    ) 