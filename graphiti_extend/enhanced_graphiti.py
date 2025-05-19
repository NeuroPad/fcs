"""
Enhanced version of the Graphiti class with additional functionality.
"""

from datetime import datetime
from typing import Optional, Any, Dict, List, Tuple
from pydantic import BaseModel

from graphiti_core import Graphiti
from graphiti_core.nodes import EntityNode, EpisodeType, EpisodicNode
from graphiti_core.edges import EntityEdge
from graphiti_core.llm_client import LLMClient
from graphiti_core.embedder import EmbedderClient
from graphiti_core.cross_encoder.client import CrossEncoderClient
from graphiti_core.graphiti import AddEpisodeResults
from graphiti_core.utils.maintenance.edge_operations import get_edge_contradictions

from graphiti_extend.custom_triplet import add_custom_triplet
from graphiti_extend.contradiction_handler import detect_and_connect_contradictions

import logging

logger = logging.getLogger(__name__)

class CustomEntityAttributes(BaseModel):
    """
    Defines default attributes for custom entity types.
    """
    salience: float = 0.5  # Default salience value
    confidence: float = 0.8  # Default confidence value
    flags: List[str] = []  # Default flags (empty list)
    
class EnhancedGraphiti(Graphiti):
    """
    Enhanced version of Graphiti that adds additional functionality
    without modifying the original Graphiti class.
    """
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        llm_client: Optional[LLMClient] = None,
        embedder: Optional[EmbedderClient] = None,
        cross_encoder: Optional[CrossEncoderClient] = None,
        store_raw_episode_content: bool = True,
        default_entity_attributes: Optional[CustomEntityAttributes] = None,
    ):
        """
        Initialize an EnhancedGraphiti instance.
        
        Parameters
        ----------
        uri : str
            The URI of the Neo4j database.
        user : str
            The username for authenticating with the Neo4j database.
        password : str
            The password for authenticating with the Neo4j database.
        llm_client : Optional[LLMClient], optional
            An instance of LLMClient for natural language processing tasks.
        embedder : Optional[EmbedderClient], optional
            An instance of EmbedderClient for generating embeddings.
        cross_encoder : Optional[CrossEncoderClient], optional
            An instance of CrossEncoderClient for ranking search results.
        store_raw_episode_content : bool, optional
            Whether to store the raw content of episodes, by default True
        default_entity_attributes : Optional[CustomEntityAttributes], optional
            Default attributes to apply to all entity nodes, by default None
        """
        super().__init__(
            uri=uri,
            user=user,
            password=password,
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=cross_encoder,
            store_raw_episode_content=store_raw_episode_content
        )
        
        self.default_entity_attributes = default_entity_attributes or CustomEntityAttributes()
    
    async def add_episode_with_defaults(
        self,
        name: str,
        episode_body: str,
        source_description: str,
        reference_time: datetime,
        source: EpisodeType = EpisodeType.message,
        group_id: str = '',
        uuid: Optional[str] = None,
        update_communities: bool = False,
        entity_types: Optional[Dict[str, BaseModel]] = None,
        previous_episode_uuids: Optional[List[str]] = None,
        custom_attributes: Optional[Dict[str, Any]] = None,
    ) -> AddEpisodeResults:
        """
        Add an episode with default entity attributes.
        
        This method extends the original add_episode method by allowing
        custom default attributes to be applied to the extracted entities.
        
        Parameters
        ----------
        name : str
            The name of the episode.
        episode_body : str
            The content of the episode.
        source_description : str
            Description of the data source.
        reference_time : datetime
            The reference time for the episode.
        source : EpisodeType, optional
            The type of episode, by default EpisodeType.message
        group_id : str, optional
            The group ID, by default ''
        uuid : Optional[str], optional
            The UUID for the episode, by default None
        update_communities : bool, optional
            Whether to update communities, by default False
        entity_types : Optional[Dict[str, BaseModel]], optional
            Entity types definition, by default None
        previous_episode_uuids : Optional[List[str]], optional
            Previous episode UUIDs, by default None
        custom_attributes : Optional[Dict[str, Any]], optional
            Custom attributes to override defaults, by default None
            
        Returns
        -------
        AddEpisodeResults
            The results of adding the episode.
        """
        # Call the original add_episode method
        result = await super().add_episode(
            name=name,
            episode_body=episode_body,
            source_description=source_description,
            reference_time=reference_time,
            source=source,
            group_id=group_id,
            uuid=uuid,
            update_communities=update_communities,
            entity_types=entity_types,
            previous_episode_uuids=previous_episode_uuids,
        )
        
        # Apply default attributes to the extracted entity nodes
        merged_attributes = {
            "salience": self.default_entity_attributes.salience,
            "confidence": self.default_entity_attributes.confidence,
            "flags": self.default_entity_attributes.flags,
        }
        
        # Override with custom attributes if provided
        if custom_attributes:
            merged_attributes.update(custom_attributes)
        
        # Update each entity node with the default/custom attributes
        for node in result.nodes:
            # Update the node's attributes
            for key, value in merged_attributes.items():
                if key not in node.attributes:
                    node.attributes[key] = value
            
            # Save the updated node back to the database
            await node.save(self.driver)
        
        # Process contradictions for each new edge
        contradiction_results = []
        for edge in result.edges:
            # Get all existing edges that involve the same entities
            existing_edges_query = """
            MATCH (s:Entity)-[e:RELATES_TO]->(t:Entity)
            WHERE (s.uuid = $source_uuid OR t.uuid = $target_uuid)
            AND e.uuid <> $edge_uuid
            RETURN e
            """
            
            records, _, _ = await self.driver.execute_query(
                existing_edges_query,
                source_uuid=edge.source_node_uuid,
                target_uuid=edge.target_node_uuid,
                edge_uuid=edge.uuid,
                database_="neo4j"
            )
            
            # Convert records to EntityEdge objects
            existing_edges = []
            for record in records:
                e = record["e"]
                existing_edge = EntityEdge(
                    uuid=e["uuid"],
                    group_id=e["group_id"],
                    source_node_uuid=e["source_node_uuid"],
                    target_node_uuid=e["target_node_uuid"],
                    name=e["name"],
                    fact=e["fact"],
                    created_at=e["created_at"],
                    episodes=e.get("episodes", []),
                    valid_at=e.get("valid_at"),
                    invalid_at=e.get("invalid_at"),
                    expired_at=e.get("expired_at"),
                )
                existing_edges.append(existing_edge)
            
            # Detect contradictions and create CONTRADICTS relationships
            if existing_edges:
                contradiction_edges, invalidated_edges = await detect_and_connect_contradictions(
                    driver=self.driver,
                    llm_client=self.llm_client,
                    new_edge=edge,
                    existing_edges=existing_edges,
                    group_id=group_id
                )
                
                contradiction_results.append((edge, contradiction_edges, invalidated_edges))
                
                # Log the contradictions
                if contradiction_edges:
                    logger.info(f"Created {len(contradiction_edges)} contradiction relationships for edge {edge.uuid}")
                if invalidated_edges:
                    logger.info(f"Invalidated {len(invalidated_edges)} edges that contradict edge {edge.uuid}")
        
        # Return the original result (the contradiction info is logged but not returned)
        return result
    
    async def add_episode_with_contradiction_detection(
        self,
        name: str,
        episode_body: str,
        source_description: str,
        reference_time: datetime,
        source: EpisodeType = EpisodeType.message,
        group_id: str = '',
        uuid: Optional[str] = None,
        update_communities: bool = False,
        entity_types: Optional[Dict[str, BaseModel]] = None,
        previous_episode_uuids: Optional[List[str]] = None,
        custom_attributes: Optional[Dict[str, Any]] = None,
    ) -> Tuple[AddEpisodeResults, List[Tuple[EntityEdge, List[EntityEdge], List[EntityEdge]]]]:
        """
        Add an episode with contradiction detection and relationship creation.
        
        This method extends add_episode_with_defaults by also returning information
        about detected contradictions and created CONTRADICTS relationships.
        
        Parameters
        ----------
        name : str
            The name of the episode.
        episode_body : str
            The content of the episode.
        source_description : str
            Description of the data source.
        reference_time : datetime
            The reference time for the episode.
        source : EpisodeType, optional
            The type of episode, by default EpisodeType.message
        group_id : str, optional
            The group ID, by default ''
        uuid : Optional[str], optional
            The UUID for the episode, by default None
        update_communities : bool, optional
            Whether to update communities, by default False
        entity_types : Optional[Dict[str, BaseModel]], optional
            Entity types definition, by default None
        previous_episode_uuids : Optional[List[str]], optional
            Previous episode UUIDs, by default None
        custom_attributes : Optional[Dict[str, Any]], optional
            Custom attributes to override defaults, by default None
            
        Returns
        -------
        Tuple[AddEpisodeResults, List[Tuple[EntityEdge, List[EntityEdge], List[EntityEdge]]]]
            A tuple containing the results of adding the episode and information about
            detected contradictions (edge, contradiction_edges, invalidated_edges)
        """
        # Call the original add_episode method
        result = await super().add_episode(
            name=name,
            episode_body=episode_body,
            source_description=source_description,
            reference_time=reference_time,
            source=source,
            group_id=group_id,
            uuid=uuid,
            update_communities=update_communities,
            entity_types=entity_types,
            previous_episode_uuids=previous_episode_uuids,
        )
        
        # Apply default attributes to the extracted entity nodes
        merged_attributes = {
            "salience": self.default_entity_attributes.salience,
            "confidence": self.default_entity_attributes.confidence,
            "flags": self.default_entity_attributes.flags,
        }
        
        # Override with custom attributes if provided
        if custom_attributes:
            merged_attributes.update(custom_attributes)
        
        # Update each entity node with the default/custom attributes
        for node in result.nodes:
            # Update the node's attributes
            for key, value in merged_attributes.items():
                if key not in node.attributes:
                    node.attributes[key] = value
            
            # Save the updated node back to the database
            await node.save(self.driver)
        
        # Process contradictions for each new edge
        contradiction_results = []
        for edge in result.edges:
            # Get all existing edges that involve the same entities
            existing_edges_query = """
            MATCH (s:Entity)-[e:RELATES_TO]->(t:Entity)
            WHERE (s.uuid = $source_uuid OR t.uuid = $target_uuid)
            AND e.uuid <> $edge_uuid
            RETURN e
            """
            
            records, _, _ = await self.driver.execute_query(
                existing_edges_query,
                source_uuid=edge.source_node_uuid,
                target_uuid=edge.target_node_uuid,
                edge_uuid=edge.uuid,
                database_="neo4j"
            )
            
            # Convert records to EntityEdge objects
            existing_edges = []
            for record in records:
                e = record["e"]
                existing_edge = EntityEdge(
                    uuid=e["uuid"],
                    group_id=e["group_id"],
                    source_node_uuid=e["source_node_uuid"],
                    target_node_uuid=e["target_node_uuid"],
                    name=e["name"],
                    fact=e["fact"],
                    created_at=e["created_at"],
                    episodes=e.get("episodes", []),
                    valid_at=e.get("valid_at"),
                    invalid_at=e.get("invalid_at"),
                    expired_at=e.get("expired_at"),
                )
                existing_edges.append(existing_edge)
            
            # Detect contradictions and create CONTRADICTS relationships
            if existing_edges:
                contradiction_edges, invalidated_edges = await detect_and_connect_contradictions(
                    driver=self.driver,
                    llm_client=self.llm_client,
                    new_edge=edge,
                    existing_edges=existing_edges,
                    group_id=group_id
                )
                
                contradiction_results.append((edge, contradiction_edges, invalidated_edges))
                
                # Log the contradictions
                if contradiction_edges:
                    logger.info(f"Created {len(contradiction_edges)} contradiction relationships for edge {edge.uuid}")
                if invalidated_edges:
                    logger.info(f"Invalidated {len(invalidated_edges)} edges that contradict edge {edge.uuid}")
        
        # Return both the episode results and contradiction information
        return result, contradiction_results
    
    async def add_custom_edge(
        self,
        source_node: EntityNode,
        edge_type: str,
        target_node: EntityNode,
        fact: str,
        group_id: str = "",
        episodes: Optional[List[str]] = None,
        valid_at: Optional[datetime] = None,
        invalid_at: Optional[datetime] = None,
    ) -> EntityEdge:
        """
        Add a custom edge between two entity nodes.
        
        Parameters
        ----------
        source_node : EntityNode
            The source node.
        edge_type : str
            The type of edge (e.g., REINFORCES, CONTRADICTS).
        target_node : EntityNode
            The target node.
        fact : str
            The fact representing the relationship.
        group_id : str, optional
            The group ID, by default ""
        episodes : Optional[List[str]], optional
            List of episode UUIDs, by default None
        valid_at : Optional[datetime], optional
            When the fact became valid, by default None
        invalid_at : Optional[datetime], optional
            When the fact became invalid, by default None
            
        Returns
        -------
        EntityEdge
            The created edge.
        """
        return await add_custom_triplet(
            driver=self.driver,
            source_node=source_node,
            edge_type=edge_type,
            target_node=target_node,
            fact=fact,
            group_id=group_id,
            episodes=episodes,
            valid_at=valid_at,
            invalid_at=invalid_at,
        )
    
    async def add_custom_triplet(
        self,
        source_node: EntityNode,
        edge_type: str,
        target_node: EntityNode,
        fact: str,
        group_id: str = "",
        episodes: Optional[List[str]] = None,
        valid_at: Optional[datetime] = None,
        invalid_at: Optional[datetime] = None,
    ) -> EntityEdge:
        """
        Alias for add_custom_edge. Adds a custom edge between two entity nodes.
        
        Parameters
        ----------
        source_node : EntityNode
            The source node.
        edge_type : str
            The type of edge (e.g., REINFORCES, CONTRADICTS).
        target_node : EntityNode
            The target node.
        fact : str
            The fact representing the relationship.
        group_id : str, optional
            The group ID, by default ""
        episodes : Optional[List[str]], optional
            List of episode UUIDs, by default None
        valid_at : Optional[datetime], optional
            When the fact became valid, by default None
        invalid_at : Optional[datetime], optional
            When the fact became invalid, by default None
            
        Returns
        -------
        EntityEdge
            The created edge.
        """
        return await self.add_custom_edge(
            source_node=source_node,
            edge_type=edge_type,
            target_node=target_node,
            fact=fact,
            group_id=group_id,
            episodes=episodes,
            valid_at=valid_at,
            invalid_at=invalid_at,
        ) 