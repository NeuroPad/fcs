"""
Main Fluid Cognitive Scaffolding (FCS) module that integrates all components.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from graphiti_core.llm_client import LLMClient
from graphiti_core.embedder import EmbedderClient
from graphiti_core.cross_encoder.client import CrossEncoderClient
from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EntityNode

from graphiti_extend.enhanced_graphiti import EnhancedGraphiti, CustomEntityAttributes
from graphiti_extend.custom_edges import REINFORCES, CONTRADICTS, EXTENDS, SUPPORTS, ELABORATES

from fcs_core.cognitive_objects import (
    CognitiveObject, 
    COType, 
    COSource, 
    COFlags, 
    FCSSessionState
)
from fcs_core.contradiction_detector import ContradictionDetector

logger = logging.getLogger(__name__)

class ContradictionResult:
    """
    Represents the result of a contradiction detection.
    """
    def __init__(
        self, 
        original_co: CognitiveObject, 
        contradicted_co: CognitiveObject, 
        contradiction_edge: EntityEdge,
        confidence: float
    ):
        self.original_co = original_co
        self.contradicted_co = contradicted_co
        self.contradiction_edge = contradiction_edge
        self.confidence = confidence

class FCS:
    """
    Fluid Cognitive Scaffolding (FCS) system.
    """
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        llm_client: Optional[LLMClient] = None,
        embedder: Optional[EmbedderClient] = None,
        cross_encoder: Optional[CrossEncoderClient] = None,
    ):
        """
        Initialize the FCS system.
        
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
        """
        # Initialize with default FCS entity attributes
        default_attributes = CustomEntityAttributes(
            salience=0.5,
            confidence=0.8,
            flags=[]
        )
        
        # Initialize the enhanced Graphiti client
        self.graphiti = EnhancedGraphiti(
            uri=uri,
            user=user,
            password=password,
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=cross_encoder,
            default_entity_attributes=default_attributes
        )
        
        # Initialize the LLM client (reuse the one from Graphiti)
        self.llm_client = self.graphiti.llm_client
        
        # Initialize the contradiction detector
        self.contradiction_detector = ContradictionDetector(self.llm_client)
        
        # Initialize the session state
        self.session_state = FCSSessionState()
    
    async def add_user_input(
        self,
        content: str,
        reference_time: Optional[datetime] = None,
        group_id: str = "fcs_session"
    ) -> Tuple[List[CognitiveObject], List[ContradictionResult]]:
        """
        Add user input to the FCS system.
        
        Parameters
        ----------
        content : str
            The user input content.
        reference_time : Optional[datetime], optional
            The reference time for the input, by default None
        group_id : str, optional
            The group ID for the session, by default "fcs_session"
            
        Returns
        -------
        Tuple[List[CognitiveObject], List[ContradictionResult]]
            A tuple containing the list of extracted cognitive objects and
            the list of detected contradictions.
        """
        if reference_time is None:
            reference_time = datetime.now()
        
        # Add the episode with contradiction detection
        result, contradiction_results = await self.graphiti.add_episode_with_contradiction_detection(
            name=f"User input at {reference_time.isoformat()}",
            episode_body=content,
            source_description="User input",
            reference_time=reference_time,
            group_id=group_id,
            custom_attributes={
                "flags": [COFlags.TRACKED.value]  # Track user inputs by default
            }
        )
        
        # Convert the extracted entities to cognitive objects
        cos = []
        node_to_co_map = {}  # Map node UUIDs to their corresponding cognitive objects
        
        for node in result.nodes:
            co = CognitiveObject(
                id=node.uuid,
                content=node.name,
                type=COType.IDEA,
                confidence=node.attributes.get("confidence", 0.8),
                salience=node.attributes.get("salience", 0.5),
                timestamp=reference_time,
                source=COSource.USER,
                flags=node.attributes.get("flags", [])
            )
            
            # Add the cognitive object to the session state
            self.session_state.add_cognitive_object(co)
            cos.append(co)
            
            # Map the node UUID to its cognitive object
            node_to_co_map[node.uuid] = co
        
        # Process contradiction results to create ContradictionResult objects
        contradiction_objects = []
        for edge, contradiction_edges, invalidated_edges in contradiction_results:
            # For each contradiction edge, create a ContradictionResult
            for contradiction_edge in contradiction_edges:
                # Get the source and target cognitive objects
                source_co = node_to_co_map.get(contradiction_edge.source_node_uuid)
                target_co = node_to_co_map.get(contradiction_edge.target_node_uuid)
                
                # If either the source or target node is not found in our map,
                # we need to fetch it from the session state or create a new CO
                if not source_co:
                    source_node_result, _, _ = await self.graphiti.driver.execute_query(
                        "MATCH (n:Entity {uuid: $uuid}) RETURN n",
                        uuid=contradiction_edge.source_node_uuid,
                        database_="neo4j"
                    )
                    
                    if source_node_result:
                        # Create a new CO for this node
                        source_co = CognitiveObject(
                            id=contradiction_edge.source_node_uuid,
                            content=source_node_result[0]["n"]["name"],
                            type=COType.IDEA,
                            confidence=0.8,
                            salience=0.5,
                            timestamp=reference_time,
                            source=COSource.USER,
                            flags=[]
                        )
                        self.session_state.add_cognitive_object(source_co)
                
                if not target_co:
                    target_node_result, _, _ = await self.graphiti.driver.execute_query(
                        "MATCH (n:Entity {uuid: $uuid}) RETURN n",
                        uuid=contradiction_edge.target_node_uuid,
                        database_="neo4j"
                    )
                    
                    if target_node_result:
                        # Create a new CO for this node
                        target_co = CognitiveObject(
                            id=contradiction_edge.target_node_uuid,
                            content=target_node_result[0]["n"]["name"],
                            type=COType.IDEA,
                            confidence=0.8,
                            salience=0.5,
                            timestamp=reference_time,
                            source=COSource.USER,
                            flags=[]
                        )
                        self.session_state.add_cognitive_object(target_co)
                
                # If we have both source and target COs, create a ContradictionResult
                if source_co and target_co:
                    # Flag both COs as involved in a contradiction
                    if not source_co.has_flag(COFlags.CONTRADICTION):
                        source_co.add_flag(COFlags.CONTRADICTION)
                    
                    if not target_co.has_flag(COFlags.CONTRADICTION):
                        target_co.add_flag(COFlags.CONTRADICTION)
                    
                    # Create a contradiction result
                    contradiction_result = ContradictionResult(
                        original_co=source_co,
                        contradicted_co=target_co,
                        contradiction_edge=contradiction_edge,
                        confidence=0.9  # High confidence since this is based on graphiti_core's detection
                    )
                    
                    # Add the contradiction result to our list
                    contradiction_objects.append(contradiction_result)
                    
                    # Create a contradiction CO in the session state
                    contradiction_co = CognitiveObject(
                        content=f"Contradiction detected between:\n1. \"{source_co.content}\"\n2. \"{target_co.content}\"",
                        type=COType.CONTRADICTION,
                        confidence=0.9,
                        salience=max(source_co.salience, target_co.salience),
                        source=COSource.SYSTEM,
                        flags=[COFlags.CONTRADICTION.value],
                        parent_ids=[source_co.id, target_co.id],
                    )
                    
                    # Add the contradiction to the session state
                    self.session_state.add_cognitive_object(contradiction_co)
                    
                    # Update the parent-child relationships
                    source_co.add_child(contradiction_co.id)
                    target_co.add_child(contradiction_co.id)
        
        return cos, contradiction_objects
    
    async def add_external_reference(
        self,
        content: str,
        source_url: str,
        title: str,
        authors: List[str],
        abstract: str,
        reference_time: Optional[datetime] = None,
        group_id: str = "fcs_session"
    ) -> Tuple[List[CognitiveObject], List[ContradictionResult]]:
        """
        Add an external reference to the FCS system.
        
        Parameters
        ----------
        content : str
            The content of the external reference.
        source_url : str
            The URL of the source.
        title : str
            The title of the reference.
        authors : List[str]
            The list of authors.
        abstract : str
            The abstract of the reference.
        reference_time : Optional[datetime], optional
            The reference time, by default None
        group_id : str, optional
            The group ID for the session, by default "fcs_session"
            
        Returns
        -------
        Tuple[List[CognitiveObject], List[ContradictionResult]]
            A tuple containing the list of extracted cognitive objects and
            the list of detected contradictions.
        """
        if reference_time is None:
            reference_time = datetime.now()
        
        # Add the episode with contradiction detection
        result, contradiction_results = await self.graphiti.add_episode_with_contradiction_detection(
            name=title,
            episode_body=content,
            source_description="External reference",
            reference_time=reference_time,
            group_id=group_id,
            custom_attributes={
                "flags": [COFlags.EXTERNAL.value, COFlags.UNVERIFIED.value],
                "confidence": 0.3  # Lower confidence for external references
            }
        )
        
        # Convert the extracted entities to cognitive objects
        cos = []
        node_to_co_map = {}  # Map node UUIDs to their corresponding cognitive objects
        
        for node in result.nodes:
            co = CognitiveObject(
                id=node.uuid,
                content=node.name,
                type=COType.REFERENCE,
                confidence=node.attributes.get("confidence", 0.3),
                salience=node.attributes.get("salience", 0.4),
                timestamp=reference_time,
                source=COSource.EXTERNAL,
                flags=node.attributes.get("flags", [COFlags.EXTERNAL.value, COFlags.UNVERIFIED.value]),
                external_metadata={
                    "source_url": source_url,
                    "title": title,
                    "authors": authors,
                    "abstract": abstract
                }
            )
            
            # Add the cognitive object to the session state
            self.session_state.add_cognitive_object(co)
            cos.append(co)
            
            # Map the node UUID to its cognitive object
            node_to_co_map[node.uuid] = co
        
        # Process contradiction results to create ContradictionResult objects
        contradiction_objects = []
        for edge, contradiction_edges, invalidated_edges in contradiction_results:
            # For each contradiction edge, create a ContradictionResult
            for contradiction_edge in contradiction_edges:
                # Get the source and target cognitive objects
                source_co = node_to_co_map.get(contradiction_edge.source_node_uuid)
                target_co = node_to_co_map.get(contradiction_edge.target_node_uuid)
                
                # If either the source or target node is not found in our map,
                # we need to fetch it from the session state or create a new CO
                if not source_co:
                    source_node_result, _, _ = await self.graphiti.driver.execute_query(
                        "MATCH (n:Entity {uuid: $uuid}) RETURN n",
                        uuid=contradiction_edge.source_node_uuid,
                        database_="neo4j"
                    )
                    
                    if source_node_result:
                        # Create a new CO for this node
                        source_co = CognitiveObject(
                            id=contradiction_edge.source_node_uuid,
                            content=source_node_result[0]["n"]["name"],
                            type=COType.REFERENCE,
                            confidence=0.3,
                            salience=0.4,
                            timestamp=reference_time,
                            source=COSource.EXTERNAL,
                            flags=[COFlags.EXTERNAL.value, COFlags.UNVERIFIED.value],
                            external_metadata={
                                "source_url": source_url,
                                "title": title,
                                "authors": authors,
                                "abstract": abstract
                            }
                        )
                        self.session_state.add_cognitive_object(source_co)
                
                if not target_co:
                    target_node_result, _, _ = await self.graphiti.driver.execute_query(
                        "MATCH (n:Entity {uuid: $uuid}) RETURN n",
                        uuid=contradiction_edge.target_node_uuid,
                        database_="neo4j"
                    )
                    
                    if target_node_result:
                        # Create a new CO for this node
                        target_co = CognitiveObject(
                            id=contradiction_edge.target_node_uuid,
                            content=target_node_result[0]["n"]["name"],
                            type=COType.REFERENCE,
                            confidence=0.3,
                            salience=0.4,
                            timestamp=reference_time,
                            source=COSource.EXTERNAL,
                            flags=[COFlags.EXTERNAL.value, COFlags.UNVERIFIED.value],
                            external_metadata={
                                "source_url": source_url,
                                "title": title,
                                "authors": authors,
                                "abstract": abstract
                            }
                        )
                        self.session_state.add_cognitive_object(target_co)
                
                # If we have both source and target COs, create a ContradictionResult
                if source_co and target_co:
                    # Flag both COs as involved in a contradiction
                    if not source_co.has_flag(COFlags.CONTRADICTION):
                        source_co.add_flag(COFlags.CONTRADICTION)
                    
                    if not target_co.has_flag(COFlags.CONTRADICTION):
                        target_co.add_flag(COFlags.CONTRADICTION)
                    
                    # Create a contradiction result
                    contradiction_result = ContradictionResult(
                        original_co=source_co,
                        contradicted_co=target_co,
                        contradiction_edge=contradiction_edge,
                        confidence=0.7  # Slightly lower confidence for external references
                    )
                    
                    # Add the contradiction result to our list
                    contradiction_objects.append(contradiction_result)
                    
                    # Create a contradiction CO in the session state
                    contradiction_co = CognitiveObject(
                        content=f"Contradiction detected between:\n1. \"{source_co.content}\"\n2. \"{target_co.content}\"",
                        type=COType.CONTRADICTION,
                        confidence=0.7,
                        salience=max(source_co.salience, target_co.salience),
                        source=COSource.SYSTEM,
                        flags=[COFlags.CONTRADICTION.value, COFlags.EXTERNAL.value],
                        parent_ids=[source_co.id, target_co.id],
                    )
                    
                    # Add the contradiction to the session state
                    self.session_state.add_cognitive_object(contradiction_co)
                    
                    # Update the parent-child relationships
                    source_co.add_child(contradiction_co.id)
                    target_co.add_child(contradiction_co.id)
        
        return cos, contradiction_objects
    
    def reset(self) -> None:
        """
        Reset the FCS session state.
        """
        self.session_state.reset()
    
    async def close(self) -> None:
        """
        Close the FCS system and release resources.
        """
        await self.graphiti.close() 