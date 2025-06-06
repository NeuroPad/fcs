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
import json

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
from .default_values_handler import apply_default_values_to_new_nodes, sanitize_node_attributes
from .salience_manager import SalienceManager

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
        
        # Initialize salience manager
        self.salience_manager = SalienceManager(self.driver)

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

            # Create contradiction edges from edge invalidation if enabled
            invalidation_contradiction_edges = []
            # if self.enable_contradiction_detection and invalidated_edges:
            #     invalidation_contradiction_edges = await self._create_contradiction_edges_from_invalidation(
            #         resolved_edges, invalidated_edges, episode, hydrated_nodes
            #     )
            #     entity_edges.extend(invalidation_contradiction_edges)

            # Detect contradictions if enabled
            contradiction_result = ContradictionDetectionResult(
                contradictions_found=False,
                contradiction_edges=[],
                contradicted_nodes=[],
                contradicting_nodes=[],
            )

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
                
                contradiction_edges_list = await self._detect_contradictions_for_nodes(
                    hydrated_nodes, episode, previous_episodes
                )
                
                if contradiction_edges_list:
                    # Flatten the list of contradiction edges
                    all_contradiction_edges = [
                        edge for edges in contradiction_edges_list for edge in edges
                    ]
                    
                    # Add contradiction edges to entity edges
                    entity_edges.extend(all_contradiction_edges)
                    
                    # Apply salience for contradiction involvement
                    contradicting_node_uuids = set()
                    contradicted_node_uuids = set()
                    
                    for edge in all_contradiction_edges:
                        contradicting_node_uuids.add(edge.source_node_uuid)
                        contradicted_node_uuids.add(edge.target_node_uuid)
                    
                    # Find the actual node objects and apply salience updates
                    # (only to nodes that haven't already received duplicate_found updates)
                    node_uuid_map = {node.uuid: node for node in hydrated_nodes}
                    contradiction_nodes = []
                    
                    for uuid in contradicting_node_uuids.union(contradicted_node_uuids):
                        if uuid in node_uuid_map and uuid not in duplicate_node_uuids:
                            contradiction_nodes.append(node_uuid_map[uuid])
                    
                    if contradiction_nodes:
                        await self.salience_manager.update_direct_salience(
                            contradiction_nodes, 'contradiction_involvement', reference_time
                        )
                else:
                    all_contradiction_edges = []
                
                # Combine all contradiction edges (from node detection and edge invalidation)
                all_contradiction_edges.extend(invalidation_contradiction_edges)
                
                if all_contradiction_edges:
                    # Get unique contradicted and contradicting nodes for final result
                    final_contradicted_node_uuids = set()
                    final_contradicting_node_uuids = set()
                    
                    for edge in all_contradiction_edges:
                        final_contradicting_node_uuids.add(edge.source_node_uuid)
                        final_contradicted_node_uuids.add(edge.target_node_uuid)
                    
                    # Find the actual node objects
                    node_uuid_map = {node.uuid: node for node in hydrated_nodes}
                    contradicted_nodes = [
                        node_uuid_map[uuid] for uuid in final_contradicted_node_uuids 
                        if uuid in node_uuid_map
                    ]
                    contradicting_nodes = [
                        node_uuid_map[uuid] for uuid in final_contradicting_node_uuids 
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

        # Filter out the new nodes themselves from existing node lists to prevent self-contradiction
        new_node_uuids = {node.uuid for node in nodes}
        filtered_existing_nodes_lists = []
        
        for existing_nodes in existing_nodes_lists:
            # Remove any nodes that are in the current batch of new nodes
            filtered_existing = [
                node for node in existing_nodes 
                if node.uuid not in new_node_uuids
            ]
            filtered_existing_nodes_lists.append(filtered_existing)

        # Only detect contradictions for nodes that have existing nodes to compare against
        contradiction_results = []
        for node, existing_nodes in zip(nodes, filtered_existing_nodes_lists, strict=True):
            if existing_nodes:  # Only check for contradictions if there are existing nodes
                result = await detect_and_create_node_contradictions(
                    self.llm_client,
                    node,
                    existing_nodes,
                    episode,
                    previous_episodes,
                )
                contradiction_results.append(result)
            else:
                # No existing nodes to contradict, return empty list
                contradiction_results.append([])

        return contradiction_results

    async def _create_contradiction_edges_from_invalidation(
        self,
        resolved_edges: list[EntityEdge],
        invalidated_edges: list[EntityEdge],
        episode: EpisodicNode,
        entities: list[EntityNode],
    ) -> list[EntityEdge]:
        """
        Create CONTRADICTS edges between nodes when edge invalidation occurs.
        
        When a new edge invalidates an old edge, this function creates a CONTRADICTS
        relationship between the nodes involved in the new edge and the nodes involved
        in the invalidated edge.
        
        Parameters
        ----------
        resolved_edges : list[EntityEdge]
            The new edges that caused invalidation
        invalidated_edges : list[EntityEdge]
            The edges that were invalidated
        episode : EpisodicNode
            The current episode
        entities : list[EntityNode]
            All entities in the current processing batch
            
        Returns
        -------
        list[EntityEdge]
            List of CONTRADICTS edges created
        """
        if not invalidated_edges:
            return []
        
        contradiction_edges = []
        now = utc_now()
        
        # Create a mapping from node UUID to node for quick lookup
        entity_map = {entity.uuid: entity for entity in entities}
        
        for invalidated_edge in invalidated_edges:
            # Find which resolved edge caused this invalidation
            # This is determined by the invalid_at timestamp matching the valid_at of the new edge
            causing_edge = None
            for resolved_edge in resolved_edges:
                if (invalidated_edge.invalid_at and resolved_edge.valid_at and 
                    invalidated_edge.invalid_at == resolved_edge.valid_at):
                    causing_edge = resolved_edge
                    break
            
            if not causing_edge:
                continue
                
            # Get the nodes involved in both edges
            new_source_node = entity_map.get(causing_edge.source_node_uuid)
            new_target_node = entity_map.get(causing_edge.target_node_uuid)
            old_source_node = entity_map.get(invalidated_edge.source_node_uuid)
            old_target_node = entity_map.get(invalidated_edge.target_node_uuid)
            
            if not all([new_source_node, new_target_node, old_source_node, old_target_node]):
                continue
                
            # Create contradiction edges between the nodes
            # We create edges from new nodes to old nodes to indicate what contradicts what
            
            # Create CONTRADICTS edge from new source to old source (if different)
            if new_source_node.uuid != old_source_node.uuid:
                contradiction_edge = EntityEdge(
                    source_node_uuid=new_source_node.uuid,
                    target_node_uuid=old_source_node.uuid,
                    name="CONTRADICTS",
                    fact=f"The new information about {new_source_node.name} contradicts previous information about {old_source_node.name}",
                    episodes=[episode.uuid],
                    created_at=now,
                    valid_at=episode.valid_at,
                    group_id=episode.group_id,
                    attributes={
                        "new_fact": causing_edge.fact,
                        "contradicted_fact": invalidated_edge.fact,
                        "invalidation_reason": "edge_invalidation"
                    }
                )
                contradiction_edges.append(contradiction_edge)
                
            # Create CONTRADICTS edge from new target to old target (if different)
            if new_target_node.uuid != old_target_node.uuid:
                contradiction_edge = EntityEdge(
                    source_node_uuid=new_target_node.uuid,
                    target_node_uuid=old_target_node.uuid,
                    name="CONTRADICTS",
                    fact=f"The new information about {new_target_node.name} contradicts previous information about {old_target_node.name}",
                    episodes=[episode.uuid],
                    created_at=now,
                    valid_at=episode.valid_at,
                    group_id=episode.group_id,
                    attributes={
                        "new_fact": causing_edge.fact,
                        "contradicted_fact": invalidated_edge.fact,
                        "invalidation_reason": "edge_invalidation"
                    }
                )
                contradiction_edges.append(contradiction_edge)
                
            # Also create cross-contradictions if the edges involve different entity pairs
            # New source contradicts old target
            if (new_source_node.uuid != old_target_node.uuid and 
                new_source_node.uuid != old_source_node.uuid):
                contradiction_edge = EntityEdge(
                    source_node_uuid=new_source_node.uuid,
                    target_node_uuid=old_target_node.uuid,
                    name="CONTRADICTS",
                    fact=f"The new information about {new_source_node.name} contradicts previous information about {old_target_node.name}",
                    episodes=[episode.uuid],
                    created_at=now,
                    valid_at=episode.valid_at,
                    group_id=episode.group_id,
                    attributes={
                        "new_fact": causing_edge.fact,
                        "contradicted_fact": invalidated_edge.fact,
                        "invalidation_reason": "edge_invalidation"
                    }
                )
                contradiction_edges.append(contradiction_edge)
                
            # New target contradicts old source
            if (new_target_node.uuid != old_source_node.uuid and 
                new_target_node.uuid != old_target_node.uuid):
                contradiction_edge = EntityEdge(
                    source_node_uuid=new_target_node.uuid,
                    target_node_uuid=old_source_node.uuid,
                    name="CONTRADICTS",
                    fact=f"The new information about {new_target_node.name} contradicts previous information about {old_source_node.name}",
                    episodes=[episode.uuid],
                    created_at=now,
                    valid_at=episode.valid_at,
                    group_id=episode.group_id,
                    attributes={
                        "new_fact": causing_edge.fact,
                        "contradicted_fact": invalidated_edge.fact,
                        "invalidation_reason": "edge_invalidation"
                    }
                )
                contradiction_edges.append(contradiction_edge)
        
        if contradiction_edges:
            logger.info(f"Created {len(contradiction_edges)} CONTRADICTS edges from edge invalidation")
        
        return contradiction_edges

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
        
        # Helper function to get meaningful description from node
        def get_node_description(node: EntityNode) -> str:
            # Use summary if available and meaningful
            if node.summary and len(node.summary.strip()) > 10:
                return node.summary.strip()
            # Otherwise use name
            return node.name
        
        # Helper function to detect preference/opinion contradictions
        def is_preference_contradiction(contradicting_desc: str, contradicted_desc: str) -> bool:
            preference_indicators = [
                'love', 'like', 'prefer', 'favorite', 'hate', 'dislike', 
                'enjoy', 'can\'t stand', 'adore', 'despise'
            ]
            return any(indicator in contradicting_desc.lower() or indicator in contradicted_desc.lower() 
                      for indicator in preference_indicators)
        
        if len(contradicting_nodes) == 1 and len(contradicted_nodes) == 1:
            contradicting_desc = get_node_description(contradicting_nodes[0])
            contradicted_desc = get_node_description(contradicted_nodes[0])
            
            # Check if this is a preference contradiction
            if is_preference_contradiction(contradicting_desc, contradicted_desc):
                return (
                    f"I notice you mentioned different preferences. "
                    f"Earlier you said: '{contradicted_desc}' "
                    f"But now: '{contradicting_desc}' "
                    f"Would you like to explore this change?"
                )
            else:
                return (
                    f"I found conflicting information. "
                    f"Previously: '{contradicted_desc}' "
                    f"Currently: '{contradicting_desc}' "
                    f"Want to look at this?"
                )
        elif len(contradicting_nodes) == 1:
            contradicting_desc = get_node_description(contradicting_nodes[0])
            contradicted_descriptions = [get_node_description(node) for node in contradicted_nodes]
            contradicted_text = "', '".join(contradicted_descriptions)
            
            return (
                f"I found some conflicting information. "
                f"You previously mentioned: '{contradicted_text}' "
                f"But now: '{contradicting_desc}' "
                f"Would you like to discuss this?"
            )
        else:
            contradicting_descriptions = [get_node_description(node) for node in contradicting_nodes]
            contradicted_descriptions = [get_node_description(node) for node in contradicted_nodes]
            contradicting_text = "', '".join(contradicting_descriptions)
            contradicted_text = "', '".join(contradicted_descriptions)
            
            return (
                f"I found multiple conflicting pieces of information. "
                f"Previously: '{contradicted_text}' "
                f"Currently: '{contradicting_text}' "
                f"Would you like to review these differences?"
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