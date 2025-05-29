"""
Copyright 2025, FCS Software, Inc

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
from datetime import datetime
from time import time
from typing import Any

from pydantic import BaseModel

from graphiti_core.cross_encoder.client import CrossEncoderClient
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from graphiti_core.edges import EntityEdge
from graphiti_core.embedder import EmbedderClient, OpenAIEmbedder
from graphiti_core.graphiti import AddEpisodeResults, Graphiti
from graphiti_core.helpers import semaphore_gather
from graphiti_core.llm_client import LLMClient, OpenAIClient
from graphiti_core.nodes import EntityNode, EpisodeType, EpisodicNode
from graphiti_core.search.search_config import SearchConfig, SearchResults
from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_CROSS_ENCODER
from graphiti_core.search.search_filters import SearchFilters
from graphiti_core.search.search_utils import get_relevant_nodes
from graphiti_core.utils.bulk_utils import add_nodes_and_edges_bulk
from graphiti_core.utils.datetime_utils import utc_now
from graphiti_core.utils.maintenance.edge_operations import (
    build_episodic_edges,
    extract_edges,
    resolve_extracted_edges,
)
from graphiti_core.utils.maintenance.graph_data_operations import (
    EPISODE_WINDOW_LEN,
    retrieve_episodes,
)
from graphiti_core.utils.maintenance.node_operations import (
    extract_attributes_from_nodes,
    extract_nodes,
    resolve_extracted_nodes,
)
from graphiti_core.utils.ontology_utils.entity_types_utils import validate_entity_types

from .node_operations import detect_and_create_node_contradictions
from .search import contradiction_aware_search, enhanced_contradiction_search

logger = logging.getLogger(__name__)


class ContradictionDetectionResult(BaseModel):
    """Result of contradiction detection during episode processing."""
    
    contradictions_found: bool
    contradiction_edges: list[EntityEdge]
    contradicted_nodes: list[EntityNode]
    contradicting_nodes: list[EntityNode]
    contradiction_message: str | None = None


class ExtendedAddEpisodeResults(AddEpisodeResults):
    """Extended results that include contradiction detection information."""
    
    contradiction_result: ContradictionDetectionResult


class ExtendedGraphiti(Graphiti):
    """
    Extended Graphiti class with contradiction detection capabilities.
    
    This class extends the base Graphiti functionality to include:
    1. Automatic contradiction detection between new and existing nodes
    2. Creation of CONTRADICTS edges when contradictions are found
    3. Enhanced search functionality that considers contradictions
    4. Integration with FCS system for contradiction notifications
    """

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        llm_client: LLMClient | None = None,
        embedder: EmbedderClient | None = None,
        cross_encoder: CrossEncoderClient | None = None,
        store_raw_episode_content: bool = True,
        enable_contradiction_detection: bool = True,
        contradiction_threshold: float = 0.7,
    ):
        """
        Initialize an ExtendedGraphiti instance.

        Parameters
        ----------
        uri : str
            The URI of the Neo4j database.
        user : str
            The username for authenticating with the Neo4j database.
        password : str
            The password for authenticating with the Neo4j database.
        llm_client : LLMClient | None, optional
            An instance of LLMClient for natural language processing tasks.
        embedder : EmbedderClient | None, optional
            An instance of EmbedderClient for generating embeddings.
        cross_encoder : CrossEncoderClient | None, optional
            An instance of CrossEncoderClient for reranking.
        store_raw_episode_content : bool, optional
            Whether to store raw episode content. Defaults to True.
        enable_contradiction_detection : bool, optional
            Whether to enable automatic contradiction detection. Defaults to True.
        contradiction_threshold : float, optional
            Similarity threshold for finding potential contradictions. Defaults to 0.7.
        """
        super().__init__(
            uri=uri,
            user=user,
            password=password,
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=cross_encoder,
            store_raw_episode_content=store_raw_episode_content,
        )
        
        self.enable_contradiction_detection = enable_contradiction_detection
        self.contradiction_threshold = contradiction_threshold

    async def add_episode_with_contradictions(
        self,
        name: str,
        episode_body: str,
        source_description: str,
        reference_time: datetime,
        source: EpisodeType = EpisodeType.message,
        group_id: str = '',
        uuid: str | None = None,
        update_communities: bool = False,
        entity_types: dict[str, BaseModel] | None = None,
        previous_episode_uuids: list[str] | None = None,
        edge_types: dict[str, BaseModel] | None = None,
        edge_type_map: dict[tuple[str, str], list[str]] | None = None,
    ) -> ExtendedAddEpisodeResults:
        """
        Process an episode with contradiction detection and update the graph.

        This method extends the base add_episode functionality by adding
        automatic contradiction detection between new and existing nodes.

        Parameters
        ----------
        name : str
            The name of the episode.
        episode_body : str
            The content of the episode.
        source_description : str
            A description of the episode's source.
        reference_time : datetime
            The reference time for the episode.
        source : EpisodeType, optional
            The type of the episode. Defaults to EpisodeType.message.
        group_id : str
            An id for the graph partition the episode is a part of.
        uuid : str | None
            Optional uuid of the episode.
        update_communities : bool
            Whether to update communities with new node information.
        entity_types : dict[str, BaseModel] | None
            Optional entity type definitions.
        previous_episode_uuids : list[str] | None
            Optional list of episode uuids to use as previous episodes.
        edge_types : dict[str, BaseModel] | None
            Optional edge type definitions.
        edge_type_map : dict[tuple[str, str], list[str]] | None
            Optional edge type mapping.

        Returns
        -------
        ExtendedAddEpisodeResults
            Results including episode, nodes, edges, and contradiction information.
        """
        try:
            start = time()
            now = utc_now()

            validate_entity_types(entity_types)

            previous_episodes = (
                await self.retrieve_episodes(
                    reference_time,
                    last_n=EPISODE_WINDOW_LEN,
                    group_ids=[group_id],
                    source=source,
                )
                if previous_episode_uuids is None
                else await EpisodicNode.get_by_uuids(self.driver, previous_episode_uuids)
            )

            episode = (
                await EpisodicNode.get_by_uuid(self.driver, uuid)
                if uuid is not None
                else EpisodicNode(
                    name=name,
                    group_id=group_id,
                    labels=[],
                    source=source,
                    content=episode_body,
                    source_description=source_description,
                    created_at=now,
                    valid_at=reference_time,
                )
            )

            # Create default edge type map
            edge_type_map_default = (
                {('Entity', 'Entity'): list(edge_types.keys())}
                if edge_types is not None
                else {('Entity', 'Entity'): []}
            )

            # Extract entities as nodes
            extracted_nodes = await extract_nodes(
                self.clients, episode, previous_episodes, entity_types
            )

            # Extract edges and resolve nodes
            (nodes, uuid_map), extracted_edges = await semaphore_gather(
                resolve_extracted_nodes(
                    self.clients,
                    extracted_nodes,
                    episode,
                    previous_episodes,
                    entity_types,
                ),
                extract_edges(
                    self.clients, episode, extracted_nodes, previous_episodes, group_id, edge_types
                ),
            )

            # Resolve edge pointers
            from graphiti_core.utils.bulk_utils import resolve_edge_pointers
            edges = resolve_edge_pointers(extracted_edges, uuid_map)

            # Resolve edges and get hydrated nodes
            (resolved_edges, invalidated_edges), hydrated_nodes = await semaphore_gather(
                resolve_extracted_edges(
                    self.clients,
                    edges,
                    episode,
                    nodes,
                    edge_types or {},
                    edge_type_map or edge_type_map_default,
                ),
                extract_attributes_from_nodes(
                    self.clients, nodes, episode, previous_episodes, entity_types
                ),
            )

            entity_edges = resolved_edges + invalidated_edges

            # Detect contradictions if enabled
            contradiction_result = ContradictionDetectionResult(
                contradictions_found=False,
                contradiction_edges=[],
                contradicted_nodes=[],
                contradicting_nodes=[],
            )

            if self.enable_contradiction_detection and hydrated_nodes:
                contradiction_edges_list = await self._detect_contradictions_for_nodes(
                    hydrated_nodes, episode, previous_episodes
                )
                
                if contradiction_edges_list:
                    # Flatten the list of contradiction edges
                    all_contradiction_edges = [
                        edge for edges in contradiction_edges_list for edge in edges
                    ]
                    
                    # Get unique contradicted and contradicting nodes
                    contradicted_node_uuids = set()
                    contradicting_node_uuids = set()
                    
                    for edge in all_contradiction_edges:
                        contradicting_node_uuids.add(edge.source_node_uuid)
                        contradicted_node_uuids.add(edge.target_node_uuid)
                    
                    # Find the actual node objects
                    node_uuid_map = {node.uuid: node for node in hydrated_nodes}
                    contradicted_nodes = [
                        node_uuid_map[uuid] for uuid in contradicted_node_uuids 
                        if uuid in node_uuid_map
                    ]
                    contradicting_nodes = [
                        node_uuid_map[uuid] for uuid in contradicting_node_uuids 
                        if uuid in node_uuid_map
                    ]
                    
                    contradiction_result = ContradictionDetectionResult(
                        contradictions_found=True,
                        contradiction_edges=all_contradiction_edges,
                        contradicted_nodes=contradicted_nodes,
                        contradicting_nodes=contradicting_nodes,
                        contradiction_message=self._generate_contradiction_message(
                            contradicting_nodes, contradicted_nodes
                        ),
                    )
                    
                    # Add contradiction edges to entity edges
                    entity_edges.extend(all_contradiction_edges)

            # Build episodic edges
            episodic_edges = build_episodic_edges(hydrated_nodes, episode, now)

            episode.entity_edges = [edge.uuid for edge in entity_edges]

            if not self.store_raw_episode_content:
                episode.content = ''

            # Save everything to the database
            await add_nodes_and_edges_bulk(
                self.driver, [episode], episodic_edges, hydrated_nodes, entity_edges, self.embedder
            )

            # Update communities if requested
            if update_communities:
                await semaphore_gather(
                    *[
                        self._update_community_if_exists(node)
                        for node in hydrated_nodes
                    ]
                )

            end = time()
            logger.info(f'Completed add_episode_with_contradictions in {(end - start) * 1000} ms')

            return ExtendedAddEpisodeResults(
                episode=episode,
                nodes=hydrated_nodes,
                edges=entity_edges,
                contradiction_result=contradiction_result,
            )

        except Exception as e:
            logger.error(f'Error in add_episode_with_contradictions: {str(e)}')
            raise e

    async def _detect_contradictions_for_nodes(
        self,
        nodes: list[EntityNode],
        episode: EpisodicNode,
        previous_episodes: list[EpisodicNode],
    ) -> list[list[EntityEdge]]:
        """
        Detect contradictions for a list of nodes.
        
        Parameters
        ----------
        nodes : list[EntityNode]
            List of nodes to check for contradictions.
        episode : EpisodicNode
            Current episode.
        previous_episodes : list[EpisodicNode]
            Previous episodes for context.
            
        Returns
        -------
        list[list[EntityEdge]]
            List of contradiction edge lists for each node.
        """
        # Get existing nodes for each new node
        existing_nodes_lists = await get_relevant_nodes(
            self.driver, nodes, SearchFilters(), min_score=self.contradiction_threshold
        )

        # Detect contradictions for each node
        contradiction_results = await semaphore_gather(
            *[
                detect_and_create_node_contradictions(
                    self.llm_client,
                    node,
                    existing_nodes,
                    episode,
                    previous_episodes,
                )
                for node, existing_nodes in zip(nodes, existing_nodes_lists, strict=True)
            ]
        )

        return contradiction_results

    def _generate_contradiction_message(
        self,
        contradicting_nodes: list[EntityNode],
        contradicted_nodes: list[EntityNode],
    ) -> str:
        """
        Generate a human-readable message about detected contradictions.
        
        Parameters
        ----------
        contradicting_nodes : list[EntityNode]
            Nodes that are contradicting others.
        contradicted_nodes : list[EntityNode]
            Nodes that are being contradicted.
            
        Returns
        -------
        str
            Human-readable contradiction message.
        """
        if not contradicting_nodes or not contradicted_nodes:
            return ""
        
        if len(contradicting_nodes) == 1 and len(contradicted_nodes) == 1:
            return (
                f"You said {contradicted_nodes[0].name} before. "
                f"This feels different with {contradicting_nodes[0].name}. "
                f"Want to look at it?"
            )
        elif len(contradicting_nodes) == 1:
            contradicted_names = ", ".join([node.name for node in contradicted_nodes])
            return (
                f"You said {contradicted_names} before. "
                f"This feels different with {contradicting_nodes[0].name}. "
                f"Want to look at it?"
            )
        else:
            contradicting_names = ", ".join([node.name for node in contradicting_nodes])
            contradicted_names = ", ".join([node.name for node in contradicted_nodes])
            return (
                f"You said {contradicted_names} before. "
                f"This feels different with {contradicting_names}. "
                f"Want to look at it?"
            )

    async def _update_community_if_exists(self, node: EntityNode):
        """
        Update community for a node if communities exist.
        
        This is a placeholder for community update functionality.
        In a full implementation, this would check if communities exist
        and update them accordingly.
        """
        # This is a simplified version - in practice you'd want to check
        # if communities are enabled and update them
        pass

    async def contradiction_aware_search(
        self,
        query: str,
        config: SearchConfig = COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
        group_ids: list[str] | None = None,
        center_node_uuid: str | None = None,
        bfs_origin_node_uuids: list[str] | None = None,
        search_filter: SearchFilters | None = None,
        include_contradictions: bool = True,
    ) -> SearchResults:
        """
        Perform a contradiction-aware search on the knowledge graph.
        
        This method extends the standard search functionality by including
        information about contradictions between nodes.
        
        Parameters
        ----------
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
        include_contradictions : bool, optional
            Whether to include contradiction information.
            
        Returns
        -------
        SearchResults
            Enhanced search results with contradiction information.
        """
        return await contradiction_aware_search(
            self.clients,
            query,
            config,
            group_ids,
            center_node_uuid,
            bfs_origin_node_uuids,
            search_filter,
            include_contradictions,
        )

    async def enhanced_contradiction_search(
        self,
        query: str,
        config: SearchConfig = COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
        group_ids: list[str] | None = None,
        center_node_uuid: str | None = None,
        bfs_origin_node_uuids: list[str] | None = None,
        search_filter: SearchFilters | None = None,
    ):
        """
        Perform an enhanced contradiction-aware search with detailed mappings.
        
        Parameters
        ----------
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
        return await enhanced_contradiction_search(
            self.clients,
            query,
            config,
            group_ids,
            center_node_uuid,
            bfs_origin_node_uuids,
            search_filter,
        )

    async def get_contradiction_summary(
        self, group_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Get a summary of all contradictions in the graph.
        
        Parameters
        ----------
        group_ids : list[str] | None, optional
            Filter by group IDs.
            
        Returns
        -------
        dict[str, Any]
            Summary of contradictions including counts and examples.
        """
        from .search import get_contradiction_edges
        
        contradiction_edges = await get_contradiction_edges(
            self.driver, group_ids, limit=1000
        )
        
        # Group contradictions by source node
        contradictions_by_source = {}
        for edge in contradiction_edges:
            source_uuid = edge.source_node_uuid
            if source_uuid not in contradictions_by_source:
                contradictions_by_source[source_uuid] = []
            contradictions_by_source[source_uuid].append(edge)
        
        return {
            'total_contradictions': len(contradiction_edges),
            'nodes_with_contradictions': len(contradictions_by_source),
            'contradictions_by_source': contradictions_by_source,
            'recent_contradictions': contradiction_edges[:10],  # Most recent 10
        } 