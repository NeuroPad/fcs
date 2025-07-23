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
from typing import Any, Optional, Dict
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
from graphiti_core.search.search_utils import get_relevant_nodes, RELEVANT_SCHEMA_LIMIT
from graphiti_core.utils.bulk_utils import add_nodes_and_edges_bulk
from graphiti_core.utils.datetime_utils import utc_now
from graphiti_core.utils.maintenance.edge_operations import (
    build_duplicate_of_edges,
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
from graphiti_core.helpers import (
    get_default_group_id,
    validate_excluded_entity_types,
    validate_group_id,
)
from graphiti_core.driver.driver import GraphDriver

from .contradictions.handler import detect_node_contradictions_for_flow
from .search.handler import contradiction_aware_search as _contradiction_aware_search, enhanced_contradiction_search as _enhanced_contradiction_search
from .defaults.handler import apply_default_values_to_new_nodes, sanitize_node_attributes
from .salience.manager import SalienceManager
from .confidence.manager import ConfidenceManager
from .confidence.models import ConfidenceTrigger, OriginType

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
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        llm_client: LLMClient | None = None,
        embedder: EmbedderClient | None = None,
        cross_encoder: CrossEncoderClient | None = None,
        store_raw_episode_content: bool = True,
        graph_driver: GraphDriver | None = None,
        max_coroutines: int | None = None,
        enable_contradiction_detection: bool = True,
        contradiction_threshold: float = 0.7,
    ):
        """
        Initialize an ExtendedGraphiti instance.

        Parameters
        ----------
        uri : str | None, optional
            The URI of the Neo4j database. Required when graph_driver is None.
        user : str | None, optional
            The username for authenticating with the Neo4j database.
        password : str | None, optional
            The password for authenticating with the Neo4j database.
        llm_client : LLMClient | None, optional
            An instance of LLMClient for natural language processing tasks.
        embedder : EmbedderClient | None, optional
            An instance of EmbedderClient for generating embeddings.
        cross_encoder : CrossEncoderClient | None, optional
            An instance of CrossEncoderClient for reranking.
        store_raw_episode_content : bool, optional
            Whether to store raw episode content. Defaults to True.
        graph_driver : GraphDriver | None, optional
            An instance of GraphDriver for database operations.
            If not provided, a default Neo4jDriver will be initialized.
        max_coroutines : int | None, optional
            The maximum number of concurrent operations allowed. Overrides SEMAPHORE_LIMIT set in the environment.
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
            graph_driver=graph_driver,
            max_coroutines=max_coroutines,
        )
        
        self.enable_contradiction_detection = enable_contradiction_detection
        self.contradiction_threshold = contradiction_threshold
        
        # Initialize salience manager
        self.salience_manager = SalienceManager(self.driver)
        
        # Initialize confidence manager
        self.confidence_manager = ConfidenceManager(self.driver)
        
        # Track all created node UUIDs across episodes to prevent salience increases for new nodes
        self.created_node_uuids: set[str] = set()

    async def add_episode_with_contradictions(
        self,
        name: str,
        episode_body: str,
        source_description: str,
        reference_time: datetime,
        source: EpisodeType = EpisodeType.message,
        group_id: str | None = None,
        uuid: str | None = None,
        update_communities: bool = False,
        entity_types: dict[str, BaseModel] | None = None,
        excluded_entity_types: list[str] | None = None,
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
        excluded_entity_types : list[str] | None
            Optional list of entity type names to exclude from the graph.
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

            # if group_id is None, use the default group id by the provider
            group_id = group_id or get_default_group_id(self.driver.provider)
            validate_entity_types(entity_types)
            validate_excluded_entity_types(excluded_entity_types, entity_types)
            validate_group_id(group_id)

            previous_episodes = (
                await self.retrieve_episodes(
                    reference_time,
                    last_n=RELEVANT_SCHEMA_LIMIT,
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
                self.clients, episode, previous_episodes, entity_types, excluded_entity_types
            )

            # Extract edges and resolve nodes
            (nodes, uuid_map, node_duplicates), extracted_edges = await semaphore_gather(
                resolve_extracted_nodes(
                    self.clients,
                    extracted_nodes,
                    episode,
                    previous_episodes,
                    entity_types,
                ),
                extract_edges(
                    self.clients,
                    episode,
                    extracted_nodes,
                    previous_episodes,
                    edge_type_map or edge_type_map_default,
                    group_id,
                    edge_types,
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
            truly_new_node_uuids = set()  # Track truly new nodes (not seen before)
            episode_created_node_uuids = set()  # Track nodes created in this episode
            
            for extracted, resolved in zip(extracted_nodes, nodes):
                if extracted.uuid != resolved.uuid:  # Was a duplicate
                    duplicate_nodes.append(resolved)
                    duplicate_node_uuids.add(resolved.uuid)
                else:  # Was a new node
                    truly_new_node_uuids.add(resolved.uuid)
                    episode_created_node_uuids.add(resolved.uuid)
            
            # Add truly new nodes to the global tracking set
            self.created_node_uuids.update(truly_new_node_uuids)
            
            # Only apply duplicate_found salience to nodes that were created in previous episodes
            # (not nodes that were created earlier in this same episode)
            existing_duplicate_nodes = [
                node for node in duplicate_nodes 
                if node.uuid in self.created_node_uuids and node.uuid not in episode_created_node_uuids
            ]
            
            if existing_duplicate_nodes:
                await self.salience_manager.update_direct_salience(
                    existing_duplicate_nodes, 'duplicate_found', reference_time
                )

            # Assign initial confidence to all nodes
            confidence_updates = []
            for extracted, resolved in zip(extracted_nodes, nodes):
                is_duplicate = extracted.uuid != resolved.uuid
                origin_type = await self.confidence_manager.detect_origin_type(
                    resolved, episode_body, is_duplicate
                )
                await self.confidence_manager.assign_initial_confidence(
                    resolved, origin_type, is_duplicate
                )
                
                # Apply user reaffirmation boost for existing duplicates
                if is_duplicate and resolved.uuid in self.created_node_uuids:
                    confidence_updates.append((
                        resolved.uuid,
                        ConfidenceTrigger.USER_REAFFIRMATION,
                        "User reaffirmed existing entity",
                        {"episode_uuid": episode.uuid}
                    ))
            
            # Apply confidence updates in batch
            if confidence_updates:
                await self.confidence_manager.update_confidence_batch(confidence_updates)

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
            if existing_duplicate_nodes:
                await self.salience_manager.propagate_network_reinforcement(
                    existing_duplicate_nodes, [group_id] if group_id else None
                )
                
                # Apply confidence network reinforcement for existing duplicate nodes
                network_confidence_updates = []
                for node in existing_duplicate_nodes:
                    # Get connected nodes for network reinforcement calculation
                    connected_nodes = await self._get_connected_nodes(node.uuid)
                    if connected_nodes:
                        network_boost = await self.confidence_manager.calculate_network_reinforcement(
                            node.uuid, connected_nodes
                        )
                        if network_boost > 0:
                            network_confidence_updates.append((
                                node.uuid,
                                ConfidenceTrigger.NETWORK_SUPPORT,
                                f"Network reinforcement from {len(connected_nodes)} connected nodes",
                                {
                                    "network_boost": network_boost,
                                    "connected_node_count": len(connected_nodes)
                                }
                            ))
                
                # Apply network confidence updates in batch
                if network_confidence_updates:
                    await self.confidence_manager.update_confidence_batch(network_confidence_updates)
            
            # Apply structural boosts to existing nodes only (not new nodes)
            existing_nodes_for_structural_boosts = [
                node for node in hydrated_nodes 
                if node.uuid not in truly_new_node_uuids
            ]
            if existing_nodes_for_structural_boosts:
                hydrated_nodes = await self.salience_manager.apply_structural_boosts(existing_nodes_for_structural_boosts)

            duplicate_of_edges = build_duplicate_of_edges(episode, now, node_duplicates)

            entity_edges = resolved_edges + invalidated_edges + duplicate_of_edges

            # Create contradiction edges from edge invalidation if enabled
            invalidation_contradiction_edges = []
            # if self.enable_contradiction_detection and invalidated_edges:
            #     invalidation_contradiction_edges = await self._create_contradiction_edges_from_invalidation(
            #         resolved_edges, invalidated_edges, episode, hydrated_nodes
            #     )
            #     entity_edges.extend(invalidation_contradiction_edges)

            # Detect contradictions if enabled - INTEGRATED INTO MAIN FLOW
            contradiction_result = ContradictionDetectionResult(
                contradictions_found=False,
                contradiction_edges=[],
                contradicted_nodes=[],
                contradicting_nodes=[],
            )

            if self.enable_contradiction_detection and hydrated_nodes:
                # Apply salience for reasoning usage (only to existing nodes that are NOT new or duplicates)
                existing_nodes_for_reasoning = [
                    node for node in hydrated_nodes 
                    if node.uuid not in truly_new_node_uuids
                ]
                if existing_nodes_for_reasoning:
                    await self.salience_manager.update_direct_salience(
                        existing_nodes_for_reasoning, 'reasoning_usage', reference_time
                    )
                
                # Extract contradiction pairs as regular nodes during main extraction
                contradiction_nodes, contradiction_edges = await self._extract_contradiction_pairs_as_nodes(
                    hydrated_nodes, episode, previous_episodes
                )
                
                # Integrate contradiction nodes with the normal flow for proper deduplication
                if contradiction_nodes:
                    logger.info(f"Integrating {len(contradiction_nodes)} contradiction nodes into normal flow")
                    
                    # Process contradiction nodes through the normal resolution flow
                    resolved_contradiction_data = await resolve_extracted_nodes(
                        self.clients,
                        contradiction_nodes,  # Use as extracted nodes
                        episode,
                        previous_episodes,
                        entity_types,
                    )
                    
                    resolved_contradiction_nodes, contradiction_uuid_map, contradiction_duplicates = resolved_contradiction_data
                    
                    # Add resolved contradiction nodes to the main hydrated nodes list
                    hydrated_nodes.extend(resolved_contradiction_nodes)
                    
                    # Update contradiction edges with resolved UUIDs
                    for edge in contradiction_edges:
                        # Update source and target UUIDs if they were remapped during resolution
                        if edge.source_node_uuid in contradiction_uuid_map:
                            edge.source_node_uuid = contradiction_uuid_map[edge.source_node_uuid]
                        if edge.target_node_uuid in contradiction_uuid_map:
                            edge.target_node_uuid = contradiction_uuid_map[edge.target_node_uuid]
                    
                    logger.debug(f"Resolved {len(resolved_contradiction_nodes)} contradiction nodes through normal flow")
                
                # Add contradiction nodes and edges to the main entity_edges list
                entity_edges.extend(contradiction_edges)
                
                # Apply salience for contradiction involvement (only to existing nodes)
                contradicting_node_uuids = set()
                contradicted_node_uuids = set()
                
                for edge in contradiction_edges:
                    contradicting_node_uuids.add(edge.source_node_uuid)
                    contradicted_node_uuids.add(edge.target_node_uuid)
                
                # Find the actual node objects and apply salience updates
                # (only to existing nodes that haven't already received duplicate_found updates)
                node_uuid_map = {node.uuid: node for node in hydrated_nodes}
                contradiction_nodes_to_update = []
                
                for uuid in contradicting_node_uuids.union(contradicted_node_uuids):
                    if (uuid in node_uuid_map and 
                        uuid not in duplicate_node_uuids and 
                        uuid not in truly_new_node_uuids):  # Only existing nodes
                        contradiction_nodes_to_update.append(node_uuid_map[uuid])
                
                if contradiction_nodes_to_update:
                    await self.salience_manager.update_direct_salience(
                        contradiction_nodes_to_update, 'contradiction_involvement', reference_time
                    )
                
                    # Apply confidence penalties for contradicted nodes and boosts for contradicting nodes
                    contradiction_confidence_updates = []
                    for edge in contradiction_edges:
                        # Apply penalty to contradicted node
                        contradicted_confidence = await self.confidence_manager.get_confidence(edge.target_node_uuid)
                        contradicting_confidence = await self.confidence_manager.get_confidence(edge.source_node_uuid)
                        
                        if contradicted_confidence is not None and contradicting_confidence is not None:
                            # Calculate contradiction strength based on confidence difference
                            confidence_diff = contradicting_confidence - contradicted_confidence
                            contradiction_strength = max(0.5, min(1.0, 0.5 + abs(confidence_diff)))
                            
                            # Apply penalty to contradicted node
                            contradiction_confidence_updates.append((
                                edge.target_node_uuid,
                                ConfidenceTrigger.CONTRADICTION_DETECTED,
                                f"Contradicted by {edge.source_node_uuid}",
                                {
                                    "contradicting_node_uuid": edge.source_node_uuid,
                                    "contradiction_strength": contradiction_strength,
                                    "confidence_difference": confidence_diff
                                }
                            ))
                            
                            # Apply boost to contradicting node (if it has higher confidence)
                            if contradicting_confidence > contradicted_confidence:
                                contradiction_confidence_updates.append((
                                    edge.source_node_uuid,
                                    ConfidenceTrigger.NETWORK_SUPPORT,
                                    f"Successfully contradicted {edge.target_node_uuid}",
                                    {
                                        "contradicted_node_uuid": edge.target_node_uuid,
                                        "contradiction_strength": contradiction_strength
                                    }
                                ))
                    
                    # Apply contradiction confidence updates in batch
                    if contradiction_confidence_updates:
                        await self.confidence_manager.update_confidence_batch(contradiction_confidence_updates)
                else:
                    contradiction_edges = []
                
                # Combine all contradiction edges (from node detection and edge invalidation)
                # all_contradiction_edges.extend(invalidation_contradiction_edges) # This line is no longer needed
                
                if contradiction_edges:
                    # Get unique contradicted and contradicting nodes for final result
                    final_contradicted_node_uuids = set()
                    final_contradicting_node_uuids = set()
                    
                    for edge in contradiction_edges:
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
                        contradiction_edges=contradiction_edges,
                        contradicted_nodes=contradicted_nodes,
                        contradicting_nodes=contradicting_nodes,
                        contradiction_message=self._generate_contradiction_message(
                            contradicting_nodes, contradicted_nodes
                        ),
                    )

            # Build episodic edges
            episodic_edges = build_episodic_edges(nodes, episode.uuid, now)

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

            # Apply confidence decay for dormant nodes
            await self._apply_confidence_decay(group_id)

            end = time()
            logger.info(f'Completed add_episode_with_contradictions in {(end - start) * 1000} ms')

            return ExtendedAddEpisodeResults(
                episode=episode,
                nodes=nodes,
                edges=entity_edges,
                contradiction_result=contradiction_result,
            )

        except Exception as e:
            logger.error(f'Error in add_episode_with_contradictions: {str(e)}')
            raise e

    async def _extract_contradiction_pairs_as_nodes(
        self,
        nodes: list[EntityNode],
        episode: EpisodicNode,
        previous_episodes: list[EpisodicNode],
    ) -> tuple[list[EntityNode], list[EntityEdge]]:
        """
        Extract contradiction pairs as regular nodes during main extraction phase.
        This eliminates the need for separate processing and add_triplet function.
        
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
        tuple[list[EntityNode], list[EntityEdge]]
            Tuple of (contradiction_nodes, contradiction_edges) for normal flow integration
        """
        from graphiti_extend.prompts.contradiction import get_contradiction_pairs_prompt, ContradictionPairs
        from graphiti_core.nodes import EntityNode
        from graphiti_core.edges import EntityEdge
        # utc_now is already imported at the top of the file
        
        try:
            # Get all existing nodes in the group to check for contradictions
            search_query = """
            MATCH (n:Entity)
            WHERE n.group_id = $group_id
            RETURN n
            """
            
            records, _, _ = await self.driver.execute_query(
                search_query, 
                group_id=episode.group_id
            )
            
            existing_nodes = []
            for record in records:
                try:
                    neo4j_node = record["n"]
                    
                    # Convert Neo4j Node object to dictionary
                    node_data = dict(neo4j_node)
                    
                    # Add labels from the Neo4j node
                    node_data['labels'] = list(neo4j_node.labels)
                    
                    # Ensure created_at is a proper datetime object
                    if 'created_at' in node_data:
                        created_at = node_data['created_at']
                        if isinstance(created_at, str):
                            try:
                                node_data['created_at'] = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            except ValueError:
                                node_data['created_at'] = utc_now()
                        elif not isinstance(created_at, datetime):
                            node_data['created_at'] = utc_now()
                    else:
                        node_data['created_at'] = utc_now()
                    
                    # Ensure other required fields are present and valid
                    if 'labels' not in node_data or not node_data['labels']:
                        node_data['labels'] = ['Entity']
                    
                    if 'summary' not in node_data:
                        node_data['summary'] = ''
                    
                    if 'attributes' not in node_data:
                        node_data['attributes'] = {}
                    
                    existing_node = EntityNode(**node_data)
                    existing_nodes.append(existing_node)
                    
                except Exception as node_error:
                    logger.error(f"Error creating EntityNode from database record: {str(node_error)}")
                    continue
            
            # Filter out the new nodes themselves from existing node lists to prevent self-contradiction
            new_node_uuids = {node.uuid for node in nodes}
            filtered_existing_nodes = [
                node for node in existing_nodes 
                if node.uuid not in new_node_uuids
            ]
            
            if not filtered_existing_nodes:
                logger.debug("No existing nodes to check for contradictions")
                return [], []
            
            # Prepare context for contradiction pair extraction
            existing_nodes_context = [
                {
                    'name': node.name,
                    'summary': node.summary,
                    'uuid': node.uuid,
                    'attributes': node.attributes
                }
                for node in filtered_existing_nodes
            ]
            
            context = {
                'episode_content': episode.content,
                'existing_nodes': existing_nodes_context,
                'previous_episodes': [ep.content for ep in previous_episodes],
            }
            
            # Extract contradiction pairs using LLM
            llm_response = await self.llm_client.generate_response(
                get_contradiction_pairs_prompt(context),
                response_model=ContradictionPairs,
            )
            
            contradiction_pairs = llm_response.get('contradiction_pairs', [])
            
            if not contradiction_pairs:
                logger.debug("No contradiction pairs found")
                return [], []
            
            # Convert contradiction pairs to nodes and edges
            contradiction_nodes = []
            contradiction_edges = []
            now = utc_now()
            
            for pair in contradiction_pairs:
                # Handle both object and dict formats for node1 and node2
                if hasattr(pair, 'node1'):
                    node1_data = pair.node1
                    node2_data = pair.node2
                    contradiction_reason = pair.contradiction_reason
                else:
                    # Handle dict format
                    node1_data = pair.get('node1', {})
                    node2_data = pair.get('node2', {})
                    contradiction_reason = pair.get('contradiction_reason', 'Contradiction detected')
                
                # Extract node1 attributes
                if hasattr(node1_data, 'name'):
                    node1_name = node1_data.name
                    node1_summary = node1_data.summary
                    node1_entity_type = getattr(node1_data, 'entity_type', 'Entity')
                else:
                    node1_name = node1_data.get('name', 'Unknown')
                    node1_summary = node1_data.get('summary', '')
                    node1_entity_type = node1_data.get('entity_type', 'Entity')
                
                # Extract node2 attributes
                if hasattr(node2_data, 'name'):
                    node2_name = node2_data.name
                    node2_summary = node2_data.summary
                    node2_entity_type = getattr(node2_data, 'entity_type', 'Entity')
                else:
                    node2_name = node2_data.get('name', 'Unknown')
                    node2_summary = node2_data.get('summary', '')
                    node2_entity_type = node2_data.get('entity_type', 'Entity')
                
                # Create nodes for the contradiction pair
                node1 = EntityNode(
                    name=node1_name,
                    group_id=episode.group_id,
                    labels=['Entity', node1_entity_type],
                    summary=node1_summary,
                    created_at=now,
                )
                
                node2 = EntityNode(
                    name=node2_name,
                    group_id=episode.group_id,
                    labels=['Entity', node2_entity_type],
                    summary=node2_summary,
                    created_at=now,
                )
                
                contradiction_nodes.extend([node1, node2])
                
                # Create contradiction edge between the nodes
                contradiction_edge = EntityEdge(
                    source_node_uuid=node1.uuid,
                    target_node_uuid=node2.uuid,
                    name="CONTRADICTS",
                    fact=contradiction_reason,
                    episodes=[episode.uuid],
                    created_at=now,
                    valid_at=episode.valid_at,
                    group_id=episode.group_id,
                    attributes={
                        "contradiction_reason": contradiction_reason,
                        "detected_in_episode": episode.uuid
                    }
                )
                
                contradiction_edges.append(contradiction_edge)
            
            logger.info(f"Extracted {len(contradiction_nodes)} contradiction nodes and {len(contradiction_edges)} contradiction edges")
            return contradiction_nodes, contradiction_edges
            
        except Exception as e:
            logger.error(f"Error in _extract_contradiction_pairs_as_nodes: {str(e)}")
            return [], []

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
        return await _contradiction_aware_search(
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
        return await _enhanced_contradiction_search(
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
        from .search.handler import get_contradiction_edges
        
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

    async def _get_connected_nodes(self, node_uuid: str) -> list[EntityNode]:
        """
        Get nodes directly connected to the given node.
        
        Parameters
        ----------
        node_uuid : str
            UUID of the node to get connections for
            
        Returns
        -------
        list[EntityNode]
            List of connected nodes
        """
        query = """
        MATCH (n:Entity {uuid: $uuid})-[r]-(connected:Entity)
        RETURN connected
        """
        
        try:
            records, _, _ = await self.driver.execute_query(query, uuid=node_uuid)
            connected_nodes = []
            for record in records:
                node_data = record["connected"]
                connected_nodes.append(EntityNode(**node_data))
            return connected_nodes
        except Exception as e:
            logger.error(f"Error getting connected nodes for {node_uuid}: {e}")
            return []

    async def _apply_confidence_decay(self, group_id: str):
        """
        Apply confidence decay for dormant nodes.
        
        Parameters
        ----------
        group_id : str
            Group ID to filter nodes for decay
        """
        try:
            # Get nodes that haven't been referenced recently
            dormancy_query = """
            MATCH (n:Entity)
            WHERE n.confidence IS NOT NULL
            AND n.confidence_metadata IS NOT NULL
            AND n.group_id = $group_id
            RETURN n.uuid as uuid, n.confidence_metadata as metadata
            """
            
            records, _, _ = await self.driver.execute_query(dormancy_query, group_id=group_id)
            
            decay_updates = []
            now = utc_now()
            
            for record in records:
                node_uuid = record["uuid"]
                metadata_json = record["metadata"]
                
                if metadata_json:
                    try:
                        import json
                        metadata = json.loads(metadata_json)
                        last_reference = metadata.get("last_user_validation")
                        
                        if last_reference:
                            last_reference_dt = datetime.fromisoformat(last_reference)
                            days_since_reference = (now - last_reference_dt).days
                            
                            if days_since_reference > 90:
                                decay_updates.append((
                                    node_uuid,
                                    ConfidenceTrigger.EXTENDED_DORMANCY,
                                    f"Extended dormancy: {days_since_reference} days",
                                    {"days_since_reference": days_since_reference}
                                ))
                            elif days_since_reference > 30:
                                decay_updates.append((
                                    node_uuid,
                                    ConfidenceTrigger.DORMANCY_DECAY,
                                    f"Dormancy decay: {days_since_reference} days",
                                    {"days_since_reference": days_since_reference}
                                ))
                    except Exception as e:
                        logger.error(f"Error processing dormancy for node {node_uuid}: {e}")
            
            # Apply decay updates in batch
            if decay_updates:
                await self.confidence_manager.update_confidence_batch(decay_updates)
                logger.info(f"Applied confidence decay to {len(decay_updates)} dormant nodes")
                
        except Exception as e:
            logger.error(f"Error applying confidence decay: {e}")

    async def get_confidence(self, node_uuid: str) -> Optional[float]:
        """
        Get confidence for a specific node.
        
        Parameters
        ----------
        node_uuid : str
            UUID of the node
            
        Returns
        -------
        float, optional
            Confidence value (0.0-1.0) or None if not found
        """
        return await self.confidence_manager.get_confidence(node_uuid)
    
    async def get_confidence_metadata(self, node_uuid: str):
        """
        Get confidence metadata for a specific node.
        
        Parameters
        ----------
        node_uuid : str
            UUID of the node
            
        Returns
        -------
        ConfidenceMetadata, optional
            Confidence metadata or None if not found
        """
        return await self.confidence_manager.get_confidence_metadata(node_uuid)
    
    async def update_node_confidence(
        self,
        node_uuid: str,
        trigger: ConfidenceTrigger,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update confidence for a specific node.
        
        Parameters
        ----------
        node_uuid : str
            UUID of the node to update
        trigger : ConfidenceTrigger
            The trigger causing the update
        reason : str
            Human-readable reason for the update
        metadata : Dict[str, Any], optional
            Additional metadata for the update
        """
        return await self.confidence_manager.update_confidence(
            node_uuid, trigger, reason, metadata
        )
    
    async def get_low_confidence_nodes(
        self, 
        threshold: float = 0.4,
        group_ids: Optional[list[str]] = None,
        limit: int = 100
    ) -> list[tuple[str, float]]:
        """
        Get nodes with confidence below a threshold.
        
        Parameters
        ----------
        threshold : float, optional
            Confidence threshold (default: 0.4 for unstable nodes)
        group_ids : list[str], optional
            Filter by group IDs
        limit : int, optional
            Maximum number of results
            
        Returns
        -------
        list[tuple[str, float]]
            List of (node_uuid, confidence) tuples
        """
        query = """
        MATCH (n:Entity)
        WHERE n.confidence IS NOT NULL
        AND n.confidence < $threshold
        """
        
        params = {"threshold": threshold, "limit": limit}
        
        if group_ids:
            query += " AND n.group_id IN $group_ids"
            params["group_ids"] = group_ids
        
        query += """
        RETURN n.uuid as uuid, n.confidence as confidence
        ORDER BY n.confidence ASC
        LIMIT $limit
        """
        
        try:
            records, _, _ = await self.driver.execute_query(query, **params)
            return [(record["uuid"], record["confidence"]) for record in records]
        except Exception as e:
            logger.error(f"Error getting low confidence nodes: {e}")
            return []
    
    async def get_confidence_summary(self, group_ids: Optional[list[str]] = None) -> dict[str, Any]:
        """
        Get a summary of confidence statistics.
        
        Parameters
        ----------
        group_ids : list[str], optional
            Filter by group IDs
            
        Returns
        -------
        dict[str, Any]
            Confidence summary statistics
        """
        query = """
        MATCH (n:Entity)
        WHERE n.confidence IS NOT NULL
        """
        
        params = {}
        if group_ids:
            query += " AND n.group_id IN $group_ids"
            params["group_ids"] = group_ids
        
        query += """
        RETURN 
            count(n) as total_nodes,
            avg(n.confidence) as avg_confidence,
            min(n.confidence) as min_confidence,
            max(n.confidence) as max_confidence,
            count(CASE WHEN n.confidence < 0.4 THEN 1 END) as unstable_nodes,
            count(CASE WHEN n.confidence < 0.2 THEN 1 END) as low_confidence_nodes
        """
        
        try:
            records, _, _ = await self.driver.execute_query(query, **params)
            if records:
                record = records[0]
                return {
                    "total_nodes": record["total_nodes"],
                    "average_confidence": round(record["avg_confidence"], 3) if record["avg_confidence"] else 0,
                    "min_confidence": record["min_confidence"],
                    "max_confidence": record["max_confidence"],
                    "unstable_nodes": record["unstable_nodes"],
                    "low_confidence_nodes": record["low_confidence_nodes"],
                    "unstable_percentage": round((record["unstable_nodes"] / record["total_nodes"]) * 100, 1) if record["total_nodes"] > 0 else 0
                }
        except Exception as e:
            logger.error(f"Error getting confidence summary: {e}")
        
        return {}