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
from datetime import datetime
from time import time
from typing import Any

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

from .contradictions import ContradictionHandler, ContradictionDetectionResult
from .search import contradiction_aware_search, enhanced_contradiction_search
from .defaults import apply_default_values_to_new_nodes, sanitize_node_attributes
from .salience import SalienceManager

logger = logging.getLogger(__name__)


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
        
        # Initialize handlers
        self.salience_manager = SalienceManager(self.driver)
        self.contradiction_handler = ContradictionHandler(self.llm_client)

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
        entity_types: dict[str, Any] | None = None,
        previous_episode_uuids: list[str] | None = None,
        edge_types: dict[str, Any] | None = None,
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
        entity_types : dict[str, Any] | None
            Optional entity type definitions.
        previous_episode_uuids : list[str] | None
            Optional list of episode uuids to use as previous episodes.
        edge_types : dict[str, Any] | None
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

            # Apply default values to new nodes (only for new nodes, not existing duplicates)
            if entity_types:
                nodes = apply_default_values_to_new_nodes(
                    extracted_nodes, nodes, uuid_map, entity_types
                )

            # Apply salience updates for duplicate detection
            duplicate_nodes = []
            duplicate_node_uuids = set()
            for extracted, resolved in zip(extracted_nodes, nodes):
                if extracted.uuid != resolved.uuid:  # Was a duplicate
                    duplicate_nodes.append(resolved)
                    duplicate_node_uuids.add(resolved.uuid)
            
            if duplicate_nodes:
                await self.salience_manager.update_direct_salience(
                    duplicate_nodes, 'duplicate_found', reference_time
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

            # Apply network reinforcement for duplicate nodes only
            if duplicate_nodes:
                await self.salience_manager.propagate_network_reinforcement(
                    duplicate_nodes, [group_id] if group_id else None
                )
            
            # Apply structural boosts to all nodes
            hydrated_nodes = await self.salience_manager.apply_structural_boosts(hydrated_nodes)

            entity_edges = resolved_edges + invalidated_edges

            # Initialize contradiction result
            contradiction_result = ContradictionDetectionResult(
                contradictions_found=False,
                contradiction_edges=[],
                contradicted_nodes=[],
                contradicting_nodes=[],
            )

            # Detect contradictions if enabled
            if self.enable_contradiction_detection and hydrated_nodes:
                # Apply salience for reasoning usage (only to nodes that haven't already been updated)
                nodes_for_reasoning = [
                    node for node in hydrated_nodes 
                    if node.uuid not in duplicate_node_uuids
                ]
                if nodes_for_reasoning:
                    await self.salience_manager.update_direct_salience(
                        nodes_for_reasoning, 'reasoning_usage', reference_time
                    )
                
                # Get existing nodes for each new node
                existing_nodes_lists = await get_relevant_nodes(
                    self.driver, hydrated_nodes, SearchFilters(), min_score=self.contradiction_threshold
                )

                # Filter out the new nodes themselves from existing node lists to prevent self-contradiction
                new_node_uuids = {node.uuid for node in hydrated_nodes}
                filtered_existing_nodes_lists = []
                
                for existing_nodes in existing_nodes_lists:
                    # Remove any nodes that are in the current batch of new nodes
                    filtered_existing = [
                        node for node in existing_nodes 
                        if node.uuid not in new_node_uuids
                    ]
                    filtered_existing_nodes_lists.append(filtered_existing)

                # Detect contradictions for each node
                contradiction_results = []
                for node, existing_nodes in zip(hydrated_nodes, filtered_existing_nodes_lists, strict=True):
                    if existing_nodes:  # Only check for contradictions if there are existing nodes
                        result = await self.contradiction_handler.detect_contradictions(
                            node,
                            existing_nodes,
                            episode,
                            previous_episodes,
                        )
                        contradiction_results.append(result)

                # Combine all contradiction results
                all_contradiction_edges = []
                all_contradicted_nodes = []
                all_contradicting_nodes = []
                
                for result in contradiction_results:
                    if result.contradictions_found:
                        all_contradiction_edges.extend(result.contradiction_edges)
                        all_contradicted_nodes.extend(result.contradicted_nodes)
                        all_contradicting_nodes.extend(result.contradicting_nodes)
                
                if all_contradiction_edges:
                    # Add contradiction edges to entity edges
                    entity_edges.extend(all_contradiction_edges)
                    
                    # Apply salience for contradiction involvement
                    contradiction_nodes = [
                        node for node in all_contradicting_nodes + all_contradicted_nodes
                        if node.uuid not in duplicate_node_uuids
                    ]
                    
                    if contradiction_nodes:
                        await self.salience_manager.update_direct_salience(
                            contradiction_nodes, 'contradiction_involvement', reference_time
                        )
                    
                    contradiction_result = ContradictionDetectionResult(
                        contradictions_found=True,
                        contradiction_edges=all_contradiction_edges,
                        contradicted_nodes=all_contradicted_nodes,
                        contradicting_nodes=all_contradicting_nodes,
                        contradiction_message=self.contradiction_handler._generate_contradiction_message(
                            all_contradicting_nodes,
                            all_contradicted_nodes,
                            'preference_change' if any(
                                edge.attributes.get('contradiction_type') == 'preference_change'
                                for edge in all_contradiction_edges
                            ) else 'factual_contradiction'
                        ),
                    )

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