import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from functools import partial
from neo4j import GraphDatabase
from pydantic import BaseModel, Field
from schemas.memory import SearchQuery
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType, EpisodicNode, EntityNode
from graphiti_core.edges import EntityEdge
from graphiti_core.errors import EdgeNotFoundError, GroupsEdgesNotFoundError, NodeNotFoundError
from graphiti_core.utils.maintenance.graph_data_operations import clear_data

from langchain.text_splitter import RecursiveCharacterTextSplitter

from core.config import settings
import json
from graphiti_core.utils.bulk_utils import RawEpisode

logger = logging.getLogger(__name__)


class CognitiveObject(BaseModel):
    """Structured representation of user-expressed or system-derived ideas."""
    id: str = Field(..., description="Unique identifier (UUID)")
    content: str = Field(..., description="Natural language text expressed or inferred")
    type: str = Field(..., description="Enum: idea, contradiction, reference, system_note")
    confidence: float = Field(..., description="Float [0.0 – 1.0] — how sure the system is this idea is currently valid")
    salience: float = Field(..., description="Float — how central or reinforced this idea is within the session")
    source: str = Field(..., description="One of user, external, or system")
    flags: List[str] = Field(default_factory=list, description="Optional list, e.g. tracked, contradiction, external, unverified, dismissed")
    parent_ids: List[str] = Field(default_factory=list, description="List of UUIDs — COs this idea directly builds on")
    child_ids: List[str] = Field(default_factory=list, description="List of UUIDs — COs derived from this idea")
    match_history: List[str] = Field(default_factory=list, description="Optional list of CO IDs that have semantically reinforced this CO")
    arbitration_score: Optional[float] = Field(None, description="Optional — last known score from arbitration pass")
    linked_refs: List[str] = Field(default_factory=list, description="Optional list of CO.id or source string, e.g., reference DOI or URL")
    generated_from: List[str] = Field(default_factory=list, description="Optional list of CO IDs used to construct this one (for LLM output tracking)")


class Message(BaseModel):
    """Message model for chat interactions"""
    content: str = Field(..., description="The content of the message")
    uuid: str | None = Field(default=None, description='The uuid of the message (optional)')
    name: str = Field(default="", description="The name of the episodic node for the message (optional)")
    role_type: str = Field(..., description="The role type of the message (user, assistant or system)")
    role: Optional[str] = Field(None, description="The custom role of the message")
    timestamp: datetime = Field(default_factory=datetime.now, description="The timestamp of the message")
    source_description: str = Field(default="", description="The description of the source of the message")


class AsyncWorker:
    """Worker for processing background tasks asynchronously"""
    def __init__(self):
        self.queue = asyncio.Queue()
        self.task = None
        self.max_retries = 3  # Maximum number of retries for a job

    async def worker(self):
        while True:
            try:
                print(f'Got a job: (size of remaining queue: {self.queue.qsize()})')
                job = await self.queue.get()
                
                # Wrap the job in retry logic
                retry_count = 0
                while retry_count <= self.max_retries:
                    try:
                        await job()
                        # If job succeeds, break out of retry loop
                        break
                    except Exception as e:
                        # Check if error is from graphiti_core
                        error_module = e.__class__.__module__
                        is_graphiti_error = error_module.startswith('graphiti_core')
                        
                        # Increment retry count
                        retry_count += 1
                        
                        if is_graphiti_error and retry_count <= self.max_retries:
                            # Log the error but retry the job
                            logger.warning(f"Graphiti core error: {e.__class__.__name__}: {str(e)}. Retrying job ({retry_count}/{self.max_retries})...")
                            # Wait a bit before retrying with exponential backoff
                            await asyncio.sleep(5 * retry_count)
                        else:
                            # For non-graphiti errors or after max retries, log and break
                            if is_graphiti_error:
                                logger.error(f"Max retries reached for graphiti_core error: {e.__class__.__name__}: {str(e)}")
                            else:
                                logger.error(f"Non-graphiti error in job: {e.__class__.__name__}: {str(e)}")
                            break
                
                # Mark job as done regardless of outcome
                self.queue.task_done()
                await asyncio.sleep(25)  # Add a small delay to prevent rate limiting
            except asyncio.CancelledError:
                # Handle worker cancellation
                break
            except Exception as e:
                # Catch-all for worker-level exceptions to keep the worker alive
                logger.error(f"Critical error in worker: {e.__class__.__name__}: {str(e)}")
                await asyncio.sleep(10)  # Brief pause before continuing

    async def start(self):
        self.task = asyncio.create_task(self.worker())

    async def stop(self):
        """Gracefully stop the worker and clear any pending jobs"""
        try:
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    # Expected cancellation
                    pass
                except Exception as e:
                    # Log any other errors during task cancellation
                    logger.error(f"Error during AsyncWorker task cancellation: {str(e)}")
            
            # Clear the queue safely
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                except Exception:
                    # Queue may have changed during iteration
                    pass
            
            logger.info("AsyncWorker stopped and queue cleared")
        except Exception as e:
            logger.error(f"Error during AsyncWorker shutdown: {str(e)}")
            # Even if there's an error, we want to ensure task is properly cancelled
            if self.task and not self.task.cancelled():
                self.task.cancel()


async_worker = AsyncWorker()


class GraphitiMemoryService:
    """Service for managing memory using Graphiti"""
    
    def __init__(self):
        """Initialize the GraphitiMemoryService"""
        self.graphiti = Graphiti(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD
        )
        
        # Add direct Neo4j driver
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
        
        # Ensure required directories exist
        Path(settings.PROCESSED_FILES_DIR).mkdir(exist_ok=True, parents=True)
    
    @classmethod
    async def initialize_worker(cls):
        """Initialize the async worker for background processing"""
        await async_worker.start()
        logger.info("Started AsyncWorker for GraphitiMemoryService")
    
    @classmethod
    async def shutdown_worker(cls):
        """Shutdown the async worker gracefully, handling any errors"""
        try:
            logger.info("Attempting to shut down AsyncWorker gracefully...")
            await async_worker.stop()
            logger.info("Stopped AsyncWorker for GraphitiMemoryService")
        except Exception as e:
            logger.error(f"Error during AsyncWorker shutdown: {e.__class__.__name__}: {str(e)}")
            # Force cancel task if still running
            if async_worker.task and not async_worker.task.cancelled():
                try:
                    async_worker.task.cancel()
                    logger.info("Forcefully cancelled AsyncWorker task")
                except Exception:
                    logger.error("Failed to forcefully cancel AsyncWorker task")
            logger.info("AsyncWorker shutdown completed with errors")
    
    async def initialize(self):
        """Initialize the service and create necessary indices and constraints"""
        await self.graphiti.build_indices_and_constraints()
        logger.info("Initialized GraphitiMemoryService with indices and constraints")
    
    async def add_message(self, user_id: str, message: Message) -> Dict[str, Any]:
        """Add a chat message to the memory graph in the background
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            message: The message to add
            
        Returns:
            Dict with status information
        """
        async def add_message_task(m: Message):
            # Format the episode body
            episode_body = f"{m.role or ''}({m.role_type}): {m.content}"
            
            # Add the episode - let Graphiti handle UUID if not provided
            await self.graphiti.add_episode(
                #uuid=m.uuid,
                group_id=user_id,
                name=m.name or f"Message-{m.uuid[:8] if m.uuid else 'new'}",
                episode_body=episode_body,
                reference_time=m.timestamp,
                source=EpisodeType.message,
                source_description=m.source_description or "Chat message",
                entity_types=self.entity_types
            )
            
            logger.info(f"Added message {m.uuid or 'with auto-generated UUID'} to memory for user {user_id}")
        
        # Queue the task for background processing
        await async_worker.queue.put(partial(add_message_task, message))
        
        return {
            "status": "queued",
            "message": f"Message queued for processing. Jobs in queue: {async_worker.queue.qsize()}",
            "queue_size": async_worker.queue.qsize()
        }
    
    async def add_messages(self, user_id: str, messages: List[Message]) -> Dict[str, Any]:
        """Add multiple chat messages to the memory graph in the background
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            messages: List of messages to add
            
        Returns:
            Dict with status information
        """
        async def add_message_task(m: Message):
            # Format the episode body
            episode_body = f"{m.role or ''}({m.role_type}): {m.content}"
            
            # Add the episode - let Graphiti handle UUID if not provided
            await self.graphiti.add_episode(
                #uuid=m.uuid,
                group_id=user_id,
                name=m.name or f"Message-{m.uuid[:8] if m.uuid else 'new'}",
                episode_body=episode_body,
                reference_time=m.timestamp,
                source=EpisodeType.message,
                source_description=m.source_description or "Chat message",
                entity_types=self.entity_types
            )
            
            logger.info(f"Added message {m.uuid or 'with auto-generated UUID'} to memory for user {user_id}")
        
        # Queue the tasks for background processing
        for message in messages:
            await async_worker.queue.put(partial(add_message_task, message))
        
        return {
            "status": "queued",
            "message": f"Queued {len(messages)} messages for processing. Jobs in queue: {async_worker.queue.qsize()}",
            "count": len(messages),
            "queue_size": async_worker.queue.qsize()
        }
    
    async def add_text(self, user_id: str, content: str, source_name: str, 
                      source_description: str = "") -> Dict[str, Any]:
        """Add a text document to the memory graph with chunking in the background
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            content: The text content to add
            source_name: Name of the source document
            source_description: Description of the source
            
        Returns:
            Dict with status information
        """
        async def add_text_chunk_task(chunk: str, chunk_name: str, chunk_desc: str, chunk_uuid: str = None):
            await self.graphiti.add_episode(
                #uuid=chunk_uuid,  # Let Graphiti handle UUID generation internally
                group_id=user_id,
                name=chunk_name,
                episode_body=chunk,
                reference_time=datetime.now(),
                source=EpisodeType.text,
                source_description=chunk_desc,
                entity_types=self.entity_types
            )
            
            logger.info(f"Added text chunk to memory for user {user_id}")
        
        try:
            # Split text into chunks
            chunks = self.text_splitter.split_text(content)
            
            # Process each chunk as a separate episode
            for i, chunk in enumerate(chunks):
                chunk_name = f"{source_name}-chunk-{i+1}"
                chunk_desc = source_description or f"Document: {source_name}"
                
                # Queue the task for background processing
                await async_worker.queue.put(
                    partial(add_text_chunk_task, chunk, chunk_name, chunk_desc)
                )
            
            return {
                "status": "queued",
                "message": f"Queued document with {len(chunks)} chunks for processing",
                "chunks": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Error preparing text chunks: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to prepare text chunks: {str(e)}"
            }
    
    async def add_document(self, user_id: str, file_path: str, 
                         source_name: Optional[str] = None,
                         source_description: str = "") -> Dict[str, Any]:
        """Add a document from a file to the memory graph in the background
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            file_path: Path to the document file
            source_name: Name of the source document (defaults to filename)
            source_description: Description of the source
            
        Returns:
            Dict with status information
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {
                    "status": "error",
                    "message": f"File not found: {file_path}"
                }
                
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
            return {
                "status": "error",
                "message": f"Failed to add document: {str(e)}"
            }
    
    # The following methods don't need background processing as they're read operations
    # or don't involve episode creation
    
    async def search_memory(self, user_id: str, query: SearchQuery) -> Dict[str, Any]:
        """Search the memory graph for relevant information
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            query: The search query
            top_k: Maximum number of results to return
            
        Returns:
            Dict with search results
        """
        try:
            # Perform search with group_id filter
            results = await self.graphiti.search(
                group_ids=[user_id],
                query=query.query,
                num_results=query.max_facts,
            )
            
            # Format the results
            formatted_results = []
            for edge in results:
                formatted_results.append({
                    "uuid": edge.uuid,
                    "name": edge.name,
                    "fact": edge.fact,
                    "valid_at": edge.valid_at,
                    "invalid_at": edge.invalid_at,
                    "created_at": edge.created_at,
                    "expired_at": edge.expired_at,
                })
            
            return {
                "status": "success",
                "results": formatted_results,
                "count": len(formatted_results)
            }
            
        except Exception as e:
            logger.error(f"Error searching memory: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to search memory: {str(e)}",
                "results": []
            }
    
    
    
    async def add_cognitive_object(self, user_id: str, cognitive_object: CognitiveObject) -> Dict[str, Any]:
        """Add a cognitive object to the memory graph
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            cognitive_object: The cognitive object to add
            
        Returns:
            Dict with status information
        """
        try:
            # Create entity node
            node = await self.graphiti.save_entity_node(
                name=cognitive_object.content[:50],  # Use truncated content as name
                uuid=cognitive_object.id,
                group_id=user_id,
                summary=cognitive_object.content,
            )
            
            # Add attributes to the node
            node.attributes = {
                "type": cognitive_object.type,
                "confidence": cognitive_object.confidence,
                "salience": cognitive_object.salience,
                "source": cognitive_object.source,
                "flags": ",".join(cognitive_object.flags),
                "timestamp": cognitive_object.timestamp.isoformat(),
                "last_updated": cognitive_object.last_updated.isoformat(),
            }
            
            # Save the updated node
            await node.save(self.graphiti.driver)
            
            # Create relationships for parent/child connections
            for parent_id in cognitive_object.parent_ids:
                try:
                    # Try to get the parent node
                    parent_node = await EntityNode.get_by_uuid(self.graphiti.driver, parent_id)
                    
                    # Create edge from parent to this node
                    edge = EntityEdge(
                        name=f"parent_of_{cognitive_object.id[:8]}",
                        fact=f"{parent_node.name} is a parent of {node.name}",
                        source_id=parent_id,
                        target_id=cognitive_object.id,
                        group_id=user_id,
                    )
                    
                    await edge.save(self.graphiti.driver)
                except NodeNotFoundError:
                    logger.warning(f"Parent node {parent_id} not found")
            
            return {
                "status": "success",
                "message": "Cognitive object added to memory",
                "uuid": cognitive_object.id
            }
            
        except Exception as e:
            logger.error(f"Error adding cognitive object: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to add cognitive object: {str(e)}"
            }
    
    async def get_cognitive_object(self, user_id: str, object_id: str) -> Optional[Dict[str, Any]]:
        """Get a cognitive object from the memory graph
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            object_id: The ID of the cognitive object to retrieve
            
        Returns:
            Dict with the cognitive object data or None if not found
        """
        try:
            # Get the entity node
            node = await EntityNode.get_by_uuid(self.graphiti.driver, object_id)
            
            # Check if the node belongs to the user
            if node.group_id != user_id:
                logger.warning(f"Node {object_id} does not belong to user {user_id}")
                return None
            
            # Get parent relationships
            parent_ids = []
            child_ids = []
            
            # Query for parent relationships
            with self.graphiti.driver.session() as session:
                # Find parents (nodes that point to this node)
                parent_result = session.run(
                    "MATCH (parent)-[r]->(child) WHERE child.uuid = $uuid RETURN parent.uuid",
                    uuid=object_id
                )
                for record in parent_result:
                    parent_ids.append(record["parent.uuid"])
                    
                # Find children (nodes that this node points to)
                child_result = session.run(
                    "MATCH (parent)-[r]->(child) WHERE parent.uuid = $uuid RETURN child.uuid",
                    uuid=object_id
                )
                for record in child_result:
                    child_ids.append(record["child.uuid"])
            
            # Extract attributes
            attributes = node.attributes or {}
            flags = attributes.get("flags", "").split(",") if attributes.get("flags") else []
            
            # Construct the cognitive object
            cognitive_object = {
                "id": node.uuid,
                "content": node.summary,
                "type": attributes.get("type", "idea"),
                "confidence": float(attributes.get("confidence", 1.0)),
                "salience": float(attributes.get("salience", 1.0)),
                "timestamp": attributes.get("timestamp"),
                "last_updated": attributes.get("last_updated"),
                "source": attributes.get("source", "system"),
                "flags": flags,
                "parent_ids": parent_ids,
                "child_ids": child_ids,
            }
            
            return cognitive_object
            
        except NodeNotFoundError:
            logger.warning(f"Cognitive object {object_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting cognitive object: {str(e)}")
            return None
    
    async def delete_user_memory(self, user_id: str) -> Dict[str, Any]:
        """Delete all memory for a specific user
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            
        Returns:
            Dict with status information
        """
        try:
            await self.graphiti.delete_group(user_id)
            
            return {
                "status": "success",
                "message": f"Deleted all memory for user {user_id}"
            }
            
        except Exception as e:
            logger.error(f"Error deleting user memory: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to delete user memory: {str(e)}"
            }
    
    async def process_documents(self) -> Dict[str, Any]:
        """Process all documents in the PROCESSED_FILES_DIR directory
        
        This function reads all files from the PROCESSED_FILES_DIR using SimpleDirectoryReader,
        processes them and adds them to the Graphiti memory graph.
        
        Returns:
            Dict with status information
        """
        try:
            # Import here to avoid circular imports
            from llama_index.core import SimpleDirectoryReader
            from llama_index.core.node_parser import SentenceSplitter
            
            processing_status = {
                "status": "processing",
                "message": "Initializing document processing",
                "progress": 0,
                "processed_documents": 0,
                "total_documents": 0
            }
            
            # First, clear existing graph data
            await clear_data(self.graphiti.driver)
            await self.graphiti.build_indices_and_constraints()
            logger.info("Cleared existing graph data")
            processing_status.update({
                "message": "Cleared existing graph data",
                "progress": 10
            })
            
            # Initialize SimpleDirectoryReader to handle various file types
            reader = SimpleDirectoryReader(
                input_dir=str(settings.PROCESSED_FILES_DIR), 
                required_exts=[".md", ".json", ".txt", ".docx", ".doc", ".pdf"]
            )
            
            # Load all documents
            documents = reader.load_data()
            total_documents = len(documents)
            
            if total_documents == 0:
                return {
                    "status": "completed",
                    "message": "No documents found to process",
                    "processed_documents": 0,
                    "total_documents": 0
                }
            
            processing_status.update({
                "message": f"Found {total_documents} documents to process",
                "total_documents": total_documents,
                "progress": 20
            })
            
            # Set up the sentence splitter
            splitter = SentenceSplitter(chunk_size=100, chunk_overlap=10)
            
            # Process each document
            processed_count = 0
            
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
                            # Parse JSON content
                            json_content = json.loads(raw_text)
                            
                            # Queue the task for background processing
                            async def process_json_task(json_content, file_name):
                                await self.graphiti.add_episode(
                                    name=f"JSON-{Path(file_name).stem}",
                                    episode_body=json.dumps(json_content),
                                    reference_time=datetime.now(),
                                    source=EpisodeType.json,
                                    source_description=f"JSON file: {file_name}",
                                    entity_types=self.entity_types
                                )
                                logger.info(f"Added JSON document {file_name} to memory")
                            
                            await async_worker.queue.put(
                                partial(process_json_task, json_content, file_name)
                            )
                        except json.JSONDecodeError:
                            logger.error(f"Error parsing JSON file {file_name}")
                            continue
                    else:
                        # For text, markdown, doc, docx - chunk the content using SentenceSplitter
                        chunks = splitter.split_text(raw_text)
                        
                        # Process each chunk as a separate episode
                        for i, chunk in enumerate(chunks):
                            chunk_name = f"{Path(file_name).stem}-chunk-{i+1}"
                            
                            # Determine the appropriate EpisodeType based on file extension
                            
                            source_type = EpisodeType.text
                            
                            # Queue the task for background processing
                            async def process_chunk_task(chunk_content, chunk_name, source_type, file_name, i, chunks_len):
                                await self.graphiti.add_episode(
                                    name=chunk_name,
                                    episode_body=chunk_content,
                                    reference_time=datetime.now(),
                                    source=source_type,
                                    source_description=f"File: {file_name}, Chunk {i+1}/{chunks_len}",
                                    entity_types=self.entity_types
                                )
                                logger.info(f"Added chunk {chunk_name} to memory")
                            
                            await async_worker.queue.put(
                                partial(process_chunk_task, chunk, chunk_name, source_type, file_name, i, len(chunks))
                            )
                    
                    processed_count += 1
                    processing_status.update({
                        "message": f"Processing document {idx} of {total_documents}",
                        "processed_documents": processed_count,
                        "progress": 20 + (70 * idx // total_documents)
                    })
                    await asyncio.sleep(0.1)  # Prevent blocking
                    
                except Exception as e:
                    logger.error(f"Error processing document {idx}: {str(e)}")
                    continue
            
            processing_status.update({
                "status": "completed",
                "message": "Processing completed successfully",
                "progress": 100,
                "processed_documents": processed_count
            })
            
            return {
                "status": "success",
                "message": "Documents processed successfully",
                "processed_documents": processed_count,
                "total_documents": total_documents
            }
            
        except Exception as e:
            error_msg = f"Error processing documents: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
    
    async def clear_neo4j_data(self) -> Dict[str, Any]:
        """Clear all data in the Neo4j database"""
        try:
            with self.neo4j_driver.session() as session:  # Correct usage of Neo4j driver session
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("Cleared existing graph data")
            return {
                "status": "success",
                "message": "Cleared existing graph data"
            }
        except Exception as e:
            logger.error(f"Error clearing graph data: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to clear graph data: {str(e)}"
            }
    
    async def close(self):
        """Close the connection to the graph database"""
        await self.graphiti.close()
        logger.info("Closed GraphitiMemoryService connection")

    async def get_top_connections(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get the most connected nodes and facts for a specific user
        
        Args:
            user_id: The user ID (will be used as group_id internally)
            limit: Maximum number of top nodes to return
            
        Returns:
            Dict with top nodes and facts
        """
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
                
                # Find the most relevant facts (edges with the highest count of occurrences)
                edge_result = session.run(
                    """
                    MATCH (src:Entity)-[r:RELATES_TO]->(tgt:Entity)
                    WHERE r.group_id = $group_id
                    WITH r.fact as fact, count(r) as occurrences
                    ORDER BY occurrences DESC
                    LIMIT $limit
                    RETURN fact, occurrences
                    """,
                    group_id=user_id,
                    limit=limit
                )
                
                top_facts = []
                for record in edge_result:
                    top_facts.append({
                        "fact": record["fact"],
                        "occurrences": record["occurrences"]
                    })
                
            return {
                "status": "success",
                "top_nodes": top_nodes,
                "top_facts": top_facts
            }
            
        except Exception as e:
            logger.error(f"Error getting top connections: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to get top connections: {str(e)}"
            }