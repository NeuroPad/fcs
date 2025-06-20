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

import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from functools import partial
from neo4j import GraphDatabase
from graphiti_core.utils.datetime_utils import utc_now

from langchain.text_splitter import RecursiveCharacterTextSplitter

from graphiti_extend import ExtendedGraphiti
from graphiti_core.nodes import EpisodeType, EpisodicNode, EntityNode
from graphiti_core.edges import EntityEdge
from graphiti_core.errors import EdgeNotFoundError, GroupsEdgesNotFoundError, NodeNotFoundError
from graphiti_core.utils.maintenance.graph_data_operations import clear_data
from graphiti_core.utils.bulk_utils import RawEpisode

from schemas.memory import SearchQuery
from core.config import settings

from .models import CognitiveObject, Message, ContradictionAlert, FCSResponse
from .async_worker import async_worker

logger = logging.getLogger(__name__)


class FCSMemoryService:
    """
    FCS Memory Service with contradiction detection capabilities.
    
    This service extends the standard Graphiti functionality with:
    - Automatic contradiction detection between new and existing nodes
    - FCS system integration for contradiction alerts
    - Enhanced search with contradiction awareness
    """

    def __init__(
        self,
        enable_contradiction_detection: bool = True,
        contradiction_threshold: float = 0.7,
        contradiction_callback: Optional[callable] = None
    ):
        """
        Initialize the FCSMemoryService.

        Parameters
        ----------
        enable_contradiction_detection : bool
            Whether to enable automatic contradiction detection.
        contradiction_threshold : float
            Similarity threshold for finding potential contradictions.
        contradiction_callback : callable, optional
            Callback function to handle contradiction alerts.
        """
        # Initialize ExtendedGraphiti with contradiction detection
        self.graphiti = ExtendedGraphiti(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD,
            enable_contradiction_detection=enable_contradiction_detection,
            contradiction_threshold=contradiction_threshold
        )
        
        # Add direct Neo4j driver for custom queries
        self.neo4j_driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
        )
        
        # Initialize text splitter for document chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=50,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
        # Define entity types
        self.entity_types = {"CognitiveObject": CognitiveObject}
        
        # Contradiction handling
        self.contradiction_callback = contradiction_callback
        self.contradiction_alerts: List[ContradictionAlert] = []
        
        # Ensure required directories exist
        Path(settings.PROCESSED_FILES_DIR).mkdir(exist_ok=True, parents=True)

    @classmethod
    async def initialize_worker(cls):
        """Initialize the async worker for background processing."""
        await async_worker.start()
        logger.info("Started AsyncWorker for FCSMemoryService")

    @classmethod
    async def shutdown_worker(cls):
        """Shutdown the async worker gracefully."""
        try:
            logger.info("Attempting to shut down AsyncWorker gracefully...")
            await async_worker.stop()
            logger.info("Stopped AsyncWorker for FCSMemoryService")
        except Exception as e:
            logger.error(f"Error during AsyncWorker shutdown: {e.__class__.__name__}: {str(e)}")
            logger.info("AsyncWorker shutdown completed with errors")

    async def initialize(self):
        """Initialize the service and create necessary indices and constraints."""
        await self.graphiti.build_indices_and_constraints()
        logger.info("Initialized FCSMemoryService with indices and constraints")

    async def _handle_contradiction_result(
        self, 
        user_id: str, 
        contradiction_result, 
        episode_uuid: str
    ) -> Optional[ContradictionAlert]:
        """
        Handle contradiction detection results and create alerts.
        
        Parameters
        ----------
        user_id : str
            The user ID associated with the contradiction.
        contradiction_result
            The contradiction detection result from ExtendedGraphiti.
        episode_uuid : str
            UUID of the episode that triggered the contradiction.
            
        Returns
        -------
        ContradictionAlert or None
            Contradiction alert if contradictions were found.
        """
        if not contradiction_result.contradictions_found:
            return None

        # Create contradiction alert
        alert = ContradictionAlert(
            user_id=user_id,
            message=contradiction_result.contradiction_message or "Contradiction detected",
            contradicting_nodes=[node.uuid for node in contradiction_result.contradicting_nodes],
            contradicted_nodes=[node.uuid for node in contradiction_result.contradicted_nodes],
            contradiction_edges=[edge.uuid for edge in contradiction_result.contradiction_edges],
            timestamp=utc_now(),
            severity=self._determine_contradiction_severity(contradiction_result),
            status="pending"
        )

        # Store the alert
        self.contradiction_alerts.append(alert)

        # Call the contradiction callback if provided
        if self.contradiction_callback:
            try:
                await self.contradiction_callback(alert)
            except Exception as e:
                logger.error(f"Error in contradiction callback: {str(e)}")

        logger.info(f"Contradiction detected for user {user_id}: {alert.message}")
        return alert

    def _determine_contradiction_severity(self, contradiction_result) -> str:
        """Determine the severity of a contradiction based on the result."""
        num_contradictions = len(contradiction_result.contradiction_edges)
        
        if num_contradictions >= 3:
            return "high"
        elif num_contradictions >= 2:
            return "medium"
        else:
            return "low"

    async def add_message(self, user_id: str, message: Message) -> FCSResponse:
        """
        Add a chat message to the memory graph with contradiction detection.
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            message: The message to add
            
        Returns:
            FCSResponse with status and potential contradiction alert
        """
        async def add_message_task(m: Message) -> Optional[ContradictionAlert]:
            # Format the episode body
            episode_body = f"{m.role or ''}({m.role_type}): {m.content}"
            
            # Add the episode with contradiction detection
            result = await self.graphiti.add_episode_with_contradictions(
                group_id=user_id,
                name=m.name or f"Message-{m.uuid[:8] if m.uuid else 'new'}",
                episode_body=episode_body,
                reference_time=m.timestamp,
                source=EpisodeType.message,
                source_description=m.source_description or "Chat message",
                entity_types=self.entity_types
            )
            
            # Handle contradiction results
            alert = await self._handle_contradiction_result(
                user_id, result.contradiction_result, result.episode.uuid
            )
            
            logger.info(f"Added message {m.uuid or 'with auto-generated UUID'} to memory for user {user_id}")
            return alert

        # Queue the task for background processing
        queue_size = await async_worker.add_job(partial(add_message_task, message))
        
        return FCSResponse(
            status="queued",
            message=f"Message queued for processing. Jobs in queue: {queue_size}",
            queue_size=queue_size
        )

    async def add_messages(self, user_id: str, messages: List[Message]) -> FCSResponse:
        """
        Add multiple chat messages to the memory graph with contradiction detection.
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            messages: List of messages to add
            
        Returns:
            FCSResponse with status information
        """
        async def add_message_task(m: Message) -> Optional[ContradictionAlert]:
            # Format the episode body
            episode_body = f"{m.role or ''}({m.role_type}): {m.content}"
            
            # Add the episode with contradiction detection
            result = await self.graphiti.add_episode_with_contradictions(
                group_id=user_id,
                name=m.name or f"Message-{m.uuid[:8] if m.uuid else 'new'}",
                episode_body=episode_body,
                reference_time=m.timestamp,
                source=EpisodeType.message,
                source_description=m.source_description or "Chat message",
                entity_types=self.entity_types
            )
            
            # Handle contradiction results
            alert = await self._handle_contradiction_result(
                user_id, result.contradiction_result, result.episode.uuid
            )
            
            logger.info(f"Added message {m.uuid or 'with auto-generated UUID'} to memory for user {user_id}")
            return alert

        # Queue the tasks for background processing
        total_queue_size = 0
        for message in messages:
            total_queue_size = await async_worker.add_job(partial(add_message_task, message))

        return FCSResponse(
            status="queued",
            message=f"Queued {len(messages)} messages for processing. Jobs in queue: {total_queue_size}",
            queue_size=total_queue_size,
            additional_data={"count": len(messages)}
        )

    async def add_text(
        self, 
        user_id: str, 
        content: str, 
        source_name: str,
        source_description: str = ""
    ) -> FCSResponse:
        """
        Add a text document to the memory graph with chunking and contradiction detection.
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            content: The text content to add
            source_name: Name of the source document
            source_description: Description of the source
            
        Returns:
            FCSResponse with status information
        """
        async def add_text_chunk_task(
            chunk: str, 
            chunk_name: str, 
            chunk_desc: str
        ) -> Optional[ContradictionAlert]:
            result = await self.graphiti.add_episode_with_contradictions(
                group_id=user_id,
                name=chunk_name,
                episode_body=chunk,
                reference_time=utc_now(),
                source=EpisodeType.text,
                source_description=chunk_desc,
                entity_types=self.entity_types
            )
            
            # Handle contradiction results
            alert = await self._handle_contradiction_result(
                user_id, result.contradiction_result, result.episode.uuid
            )
            
            logger.info(f"Added text chunk to memory for user {user_id}")
            return alert

        try:
            # Split text into chunks
            chunks = self.text_splitter.split_text(content)
            
            # Process each chunk as a separate episode
            total_queue_size = 0
            for i, chunk in enumerate(chunks):
                chunk_name = f"{source_name}-chunk-{i+1}"
                chunk_desc = source_description or f"Document: {source_name}"
                
                # Queue the task for background processing
                total_queue_size = await async_worker.add_job(
                    partial(add_text_chunk_task, chunk, chunk_name, chunk_desc)
                )

            return FCSResponse(
                status="queued",
                message=f"Queued document with {len(chunks)} chunks for processing",
                queue_size=total_queue_size,
                additional_data={"chunks": len(chunks)}
            )

        except Exception as e:
            logger.error(f"Error preparing text chunks: {str(e)}")
            return FCSResponse(
                status="error",
                message=f"Failed to prepare text chunks: {str(e)}"
            )

    async def add_document(
        self, 
        user_id: str, 
        file_path: str,
        source_name: Optional[str] = None,
        source_description: str = ""
    ) -> FCSResponse:
        """
        Add a document from a file to the memory graph with contradiction detection.
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            file_path: Path to the document file
            source_name: Name of the source document (defaults to filename)
            source_description: Description of the source
            
        Returns:
            FCSResponse with status information
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return FCSResponse(
                    status="error",
                    message=f"File not found: {file_path}"
                )

            # Use filename as source_name if not provided
            if not source_name:
                source_name = path.name

            # Read file content
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Process the text content
            return await self.add_text(
                user_id=user_id,
                content=content,
                source_name=source_name,
                source_description=source_description or f"File: {path.name}"
            )

        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            return FCSResponse(
                status="error",
                message=f"Failed to add document: {str(e)}"
            )


    async def search_memory(self, user_id: str, query: SearchQuery) -> Dict[str, Any]:
        """
        Search the memory graph with contradiction awareness.
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            query: The search query
            
        Returns:
            Dict with search results including contradiction information
        """
        try:
            # Perform contradiction-aware search using the ExtendedGraphiti instance
            results = await self.graphiti.contradiction_aware_search(
                query=query.query,
                group_ids=[user_id],
                include_contradictions=True
            )

            # Format the results - include edges, nodes, and episodes
            formatted_results = []
            
            # Process edges (facts)
            for edge in results.edges:
                edge_data = {
                    "uuid": edge.uuid,
                    "name": edge.name,
                    "fact": edge.fact,
                    "valid_at": edge.valid_at,
                    "invalid_at": edge.invalid_at,
                    "created_at": edge.created_at,
                    "expired_at": edge.expired_at,
                    "type": "edge",
                    "source_node_uuid": edge.source_node_uuid,
                    "target_node_uuid": edge.target_node_uuid,
                }
                
                # Add contradiction flag
                if edge.name == "CONTRADICTS":
                    edge_data["is_contradiction"] = True
                
                formatted_results.append(edge_data)

            # Process nodes (entities)
            for node in results.nodes:
                node_data = {
                    "uuid": node.uuid,
                    "name": node.name,
                    "summary": node.summary,
                    "created_at": node.created_at,
                    "type": "node",
                    "labels": node.labels,
                    "attributes": node.attributes,
                }
                formatted_results.append(node_data)

            # Process episodes (conversations/messages)
            for episode in results.episodes:
                episode_data = {
                    "uuid": episode.uuid,
                    "name": episode.name,
                    "content": episode.content,
                    "source_description": episode.source_description,
                    "created_at": episode.created_at,
                    "valid_at": episode.valid_at,
                    "type": "episode",
                    "source": episode.source.value if episode.source else None,
                }
                formatted_results.append(episode_data)

            # Count contradiction edges
            contradiction_count = len([e for e in results.edges if e.name == "CONTRADICTS"])

            return {
                "status": "success",
                "results": formatted_results,
                "count": len(formatted_results),
                "contradiction_count": contradiction_count,
                "has_contradictions": contradiction_count > 0,
                "summary": {
                    "edges": len(results.edges),
                    "nodes": len(results.nodes),
                    "episodes": len(results.episodes),
                    "communities": len(results.communities)
                }
            }

        except Exception as e:
            logger.error(f"Error searching memory: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to search memory: {str(e)}",
                "results": []
            }


    async def get_contradiction_alerts(
        self, 
        user_id: str, 
        status: Optional[str] = None
    ) -> List[ContradictionAlert]:
        """
        Get contradiction alerts for a user.
        
        Args:
            user_id: The user ID
            status: Optional status filter (pending, acknowledged, resolved, ignored)
            
        Returns:
            List of contradiction alerts
        """
        alerts = [alert for alert in self.contradiction_alerts if alert.user_id == user_id]
        
        if status:
            alerts = [alert for alert in alerts if alert.status == status]
        
        return alerts

    async def update_contradiction_alert(
        self, 
        alert_id: str, 
        status: str, 
        user_response: Optional[str] = None,
        resolution_action: Optional[str] = None
    ) -> bool:
        """
        Update a contradiction alert status.
        
        Args:
            alert_id: The alert ID (timestamp-based)
            status: New status (acknowledged, resolved, ignored)
            user_response: Optional user response
            resolution_action: Optional resolution action taken
            
        Returns:
            True if alert was found and updated, False otherwise
        """
        for alert in self.contradiction_alerts:
            if str(alert.timestamp) == alert_id:
                alert.status = status
                if user_response:
                    alert.user_response = user_response
                if resolution_action:
                    alert.resolution_action = resolution_action
                return True
        return False

    async def get_contradiction_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get a summary of contradictions for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dict with contradiction summary
        """
        try:
            summary = await self.graphiti.get_contradiction_summary(group_ids=[user_id])
            
            # Add FCS-specific information
            user_alerts = await self.get_contradiction_alerts(user_id)
            pending_alerts = [a for a in user_alerts if a.status == "pending"]
            
            summary.update({
                "fcs_alerts_total": len(user_alerts),
                "fcs_alerts_pending": len(pending_alerts),
                "fcs_alerts_recent": user_alerts[-5:] if user_alerts else []
            })
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting contradiction summary: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to get contradiction summary: {str(e)}"
            }

    # Keep the remaining methods from the original service for compatibility
    async def delete_user_memory(self, user_id: str) -> FCSResponse:
        """Delete all memory for a specific user."""
        try:
            await self.graphiti.delete_group(user_id)
            
            # Also clear user's contradiction alerts
            self.contradiction_alerts = [
                alert for alert in self.contradiction_alerts 
                if alert.user_id != user_id
            ]
            
            return FCSResponse(
                status="success",
                message=f"Deleted all memory for user {user_id}"
            )
            
        except Exception as e:
            logger.error(f"Error deleting user memory: {str(e)}")
            return FCSResponse(
                status="error",
                message=f"Failed to delete user memory: {str(e)}"
            )

    async def process_documents(self) -> FCSResponse:
        """Process all documents in the PROCESSED_FILES_DIR directory with contradiction detection."""
        try:
            # Import here to avoid circular imports
            from llama_index.core import SimpleDirectoryReader
            from llama_index.core.node_parser import SentenceSplitter

            # First, clear existing graph data
            await clear_data(self.graphiti.driver)
            await self.graphiti.build_indices_and_constraints()
            logger.info("Cleared existing graph data")

            # Initialize SimpleDirectoryReader
            reader = SimpleDirectoryReader(
                input_dir=str(settings.PROCESSED_FILES_DIR),
                required_exts=[".md", ".json", ".txt", ".docx", ".doc", ".pdf"]
            )

            # Load all documents
            documents = reader.load_data()
            total_documents = len(documents)

            if total_documents == 0:
                return FCSResponse(
                    status="completed",
                    message="No documents found to process",
                    additional_data={"processed_documents": 0, "total_documents": 0}
                )

            # Set up the sentence splitter
            splitter = SentenceSplitter(chunk_size=100, chunk_overlap=10)

            # Process each document
            processed_count = 0
            total_queue_size = 0

            for idx, doc in enumerate(documents, 1):
                try:
                    # Get metadata from the document
                    file_path = doc.metadata.get("file_path", "")
                    file_name = Path(file_path).name if file_path else f"Document-{idx}"
                    file_ext = Path(file_path).suffix.lower() if file_path else ""

                    # Get raw text from the document
                    raw_text = doc.text

                    # Handle JSON files specially
                    if file_ext == '.json':
                        try:
                            json_content = json.loads(raw_text)

                            async def process_json_task(json_content, file_name):
                                result = await self.graphiti.add_episode_with_contradictions(
                                    name=f"JSON-{Path(file_name).stem}",
                                    episode_body=json.dumps(json_content),
                                    reference_time=utc_now(),
                                    source=EpisodeType.json,
                                    source_description=f"JSON file: {file_name}",
                                    entity_types=self.entity_types
                                )
                                logger.info(f"Added JSON document {file_name} to memory")
                                return result

                            total_queue_size = await async_worker.add_job(
                                partial(process_json_task, json_content, file_name)
                            )
                        except json.JSONDecodeError:
                            logger.error(f"Error parsing JSON file {file_name}")
                            continue
                    else:
                        # For text, markdown, doc, docx - chunk the content
                        chunks = splitter.split_text(raw_text)

                        # Process each chunk as a separate episode
                        for i, chunk in enumerate(chunks):
                            chunk_name = f"{Path(file_name).stem}-chunk-{i+1}"
                            source_type = EpisodeType.text

                            async def process_chunk_task(chunk_content, chunk_name, source_type, file_name, i, chunks_len):
                                result = await self.graphiti.add_episode_with_contradictions(
                                    name=chunk_name,
                                    episode_body=chunk_content,
                                    reference_time=utc_now(),
                                    source=source_type,
                                    source_description=f"File: {file_name}, Chunk {i+1}/{chunks_len}",
                                    entity_types=self.entity_types
                                )
                                logger.info(f"Added chunk {chunk_name} to memory")
                                return result

                            total_queue_size = await async_worker.add_job(
                                partial(process_chunk_task, chunk, chunk_name, source_type, file_name, i, len(chunks))
                            )

                    processed_count += 1
                    await asyncio.sleep(0.1)  # Prevent blocking

                except Exception as e:
                    logger.error(f"Error processing document {idx}: {str(e)}")
                    continue

            return FCSResponse(
                status="success",
                message="Documents processed successfully",
                queue_size=total_queue_size,
                additional_data={
                    "processed_documents": processed_count,
                    "total_documents": total_documents
                }
            )

        except Exception as e:
            error_msg = f"Error processing documents: {str(e)}"
            logger.error(error_msg)
            return FCSResponse(
                status="error",
                message=error_msg
            )

    async def clear_neo4j_data(self) -> FCSResponse:
        """Clear all data in the Neo4j database."""
        try:
            with self.neo4j_driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("Cleared existing graph data")
            
            # Also clear contradiction alerts
            self.contradiction_alerts.clear()
            
            return FCSResponse(
                status="success",
                message="Cleared existing graph data and contradiction alerts"
            )
        except Exception as e:
            logger.error(f"Error clearing graph data: {str(e)}")
            return FCSResponse(
                status="error",
                message=f"Failed to clear graph data: {str(e)}"
            )


    async def get_top_connections(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get the most connected nodes and facts for a specific user."""
        try:
            with self.neo4j_driver.session() as session:
                # Find the most connected nodes
                node_result = session.run(
                    """
                    MATCH (n:Entity)-[r]-(other)
                    WHERE n.group_id = $group_id
                    WITH n, count(r) as connections
                    ORDER BY connections DESC
                    LIMIT $limit
                    RETURN n.uuid as uuid, n.name as name, n.summary as summary, connections
                    """,
                    group_id=user_id,
                    limit=limit
                )

                top_nodes = []
                for record in node_result:
                    top_nodes.append({
                        "uuid": record["uuid"],
                        "name": record["name"],
                        "summary": record["summary"],
                        "connections": record["connections"]
                    })

                # Find the most relevant facts
                edge_result = session.run(
                    """
                    MATCH (src:Entity)-[r:RELATES_TO]->(tgt:Entity)
                    WHERE r.group_id = $group_id
                    WITH r.fact as fact, count(r) as occurrences, r.name as edge_type
                    ORDER BY occurrences DESC
                    LIMIT $limit
                    RETURN fact, occurrences, edge_type
                    """,
                    group_id=user_id,
                    limit=limit
                )

                top_facts = []
                contradiction_facts = []
                for record in edge_result:
                    fact_data = {
                        "fact": record["fact"],
                        "occurrences": record["occurrences"],
                        "edge_type": record["edge_type"]
                    }
                    
                    if record["edge_type"] == "CONTRADICTS":
                        contradiction_facts.append(fact_data)
                    else:
                        top_facts.append(fact_data)

            return {
                "status": "success",
                "top_nodes": top_nodes,
                "top_facts": top_facts,
                "contradiction_facts": contradiction_facts
            }

        except Exception as e:
            logger.error(f"Error getting top connections: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to get top connections: {str(e)}"
            }

    async def close(self):
        """Close the connection to the graph database."""
        await self.graphiti.close()
        if self.neo4j_driver:
            self.neo4j_driver.close()
        logger.info("Closed FCSMemoryService connection") 