from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
import uuid
from datetime import datetime

from fcs_core import FCSMemoryService, Message, CognitiveObject
from schemas.memory import (
    MessageCreate,
    MessageResponse,
    CognitiveObjectCreate,
    CognitiveObjectResponse,
    TextDocumentCreate,
    SearchQuery,
    SearchResults,
    OperationResponse,
    FactResult,
    TopConnectionsResponse
)

router = APIRouter(prefix="/memory", tags=["memory"])

# Dependency to get the FCSMemoryService
async def get_memory_service():
    service = FCSMemoryService()
    try:
        await service.initialize()
        yield service
    finally:
        await service.close()


@router.post("/messages/{user_id}", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
async def add_message(user_id: str, message: MessageCreate, service: FCSMemoryService = Depends(get_memory_service)):
    """Add a single message to the memory graph"""
    # Convert from API schema to service model
    msg = Message(
        content=message.content,
        name=message.name or "",
        role_type=message.role_type,
        role=message.role,
        timestamp=datetime.now(),
        source_description=message.source_description or ""
    )
    
    result = await service.add_message(user_id, msg)
    
    if result["status"] == "error":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
    
    return OperationResponse(
        status=result["status"],
        message=result["message"],
        #data={"uuid": result["uuid"]}
    )


@router.post("/messages/batch/{user_id}", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
async def add_messages(user_id: str, messages: List[MessageCreate], service: FCSMemoryService = Depends(get_memory_service)):
    """Add multiple messages to the memory graph"""
    # Convert from API schema to service model
    msgs = [
        Message(
            content=msg.content,
            uuid=msg.uuid,  # Just use the UUID from the message, don't generate one
            name=msg.name or "",
            role_type=msg.role_type,
            role=msg.role,
            timestamp=datetime.now(),
            source_description=msg.source_description or ""
        ) for msg in messages
    ]
    
    result = await service.add_messages(user_id, msgs)
    
    return OperationResponse(
        status=result["status"],
        message=result["message"],
        data={"count": result.get("count", 0), "queue_size": result.get("queue_size", 0)}
    )


@router.post("/text/{user_id}", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
async def add_text(user_id: str, document: TextDocumentCreate, service: FCSMemoryService = Depends(get_memory_service)):
    """Add a text document to the memory graph"""
    result = await service.add_text(
        user_id=user_id,
        content=document.content,
        source_name=document.source_name,
        source_description=document.source_description or ""
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
    
    return OperationResponse(
        status=result["status"],
        message=result["message"],
        data={"chunks": result.get("chunks", 0)}
    )


@router.post("/document/{user_id}", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
async def add_document(user_id: str, file_path: str, source_name: Optional[str] = None, source_description: Optional[str] = None, 
                     service: FCSMemoryService = Depends(get_memory_service)):
    """Add a document from a file to the memory graph"""
    result = await service.add_document(
        user_id=user_id,
        file_path=file_path,
        source_name=source_name,
        source_description=source_description or ""
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
    
    return OperationResponse(
        status=result["status"],
        message=result["message"],
        data={"chunks": result.get("chunks", 0)}
    )


@router.post("/search/{user_id}", response_model=SearchResults)
async def search_memory(user_id: str, query: SearchQuery, service: FCSMemoryService = Depends(get_memory_service)):
    """Search the memory graph for relevant information"""
    result = await service.search_memory(
        user_id=user_id,
        query=query
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
    
    # Convert to FactResult objects
    facts = [FactResult(**fact) for fact in result["results"]]
    
    return SearchResults(
        status=result["status"],
        results=facts,
        count=result["count"],
        contradiction_count=result.get("contradiction_count"),
        has_contradictions=result.get("has_contradictions"),
        summary=result.get("summary")
    )


@router.post("/cognitive-objects/{user_id}", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
async def add_cognitive_object(user_id: str, cognitive_object: CognitiveObjectCreate, 
                              service: FCSMemoryService = Depends(get_memory_service)):
    """Add a cognitive object to the memory graph"""
    # Convert from API schema to service model
    co = CognitiveObject(
        id=str(uuid.uuid4()),
        content=cognitive_object.content,
        type=cognitive_object.type,
        confidence=cognitive_object.confidence,
        salience=cognitive_object.salience,
        timestamp=datetime.now(),
        last_updated=datetime.now(),
        source=cognitive_object.source,
        flags=cognitive_object.flags,
        parent_ids=cognitive_object.parent_ids,
        linked_refs=cognitive_object.linked_refs,
        external_metadata=cognitive_object.external_metadata
    )
    
    result = await service.add_cognitive_object(user_id, co)
    
    if result["status"] == "error":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
    
    return OperationResponse(
        status=result["status"],
        message=result["message"],
        data={"uuid": result["uuid"]}
    )


@router.get("/cognitive-objects/{user_id}/{object_id}", response_model=CognitiveObjectResponse)
async def get_cognitive_object(user_id: str, object_id: str, service: FCSMemoryService = Depends(get_memory_service)):
    """Get a cognitive object from the memory graph"""
    result = await service.get_cognitive_object(user_id, object_id)
    
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cognitive object {object_id} not found")
    
    return CognitiveObjectResponse(**result)


@router.delete("/user/{user_id}", response_model=OperationResponse)
async def delete_user_memory(user_id: str, service: FCSMemoryService = Depends(get_memory_service)):
    """Delete all memory for a specific user"""
    result = await service.delete_user_memory(user_id)
    
    if result["status"] == "error":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
    
    return OperationResponse(
        status=result["status"],
        message=result["message"],
        data=None
    )


@router.post("/process-documents", response_model=OperationResponse)
async def process_documents(service: FCSMemoryService = Depends(get_memory_service)):
    """Process all documents in the PROCESSED_FILES_DIR directory
    
    This endpoint reads all files from the PROCESSED_FILES_DIR using SimpleDirectoryReader,
    processes them and adds them to the Graphiti memory graph.
    
    Returns:
        OperationResponse with status information
    """
    result = await service.process_documents()
    
    if result["status"] == "error":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
    
    return OperationResponse(
        status=result["status"],
        message=result.get("message", "Documents processed successfully"),
        data={
            "processed_documents": result.get("processed_documents", 0),
            "total_documents": result.get("total_documents", 0)
        }
    )


@router.post("/clear-neo4j", response_model=OperationResponse, status_code=status.HTTP_200_OK)
async def clear_neo4j_data(service: FCSMemoryService = Depends(get_memory_service)):
    """Clear all data in the Neo4j database"""
    result = await service.clear_neo4j_data()
    
    if result.status == "error":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.message)
    
    return OperationResponse(
        status=result.status,
        message=result.message
    )


@router.get("/top-connections/{user_id}", response_model=TopConnectionsResponse)
async def get_top_connections(
    user_id: str, 
    limit: int = 10, 
    service: FCSMemoryService = Depends(get_memory_service)
):
    """Get the most connected nodes and facts for a specific user
    
    This endpoint finds the nodes with the most connections and the facts 
    that appear most frequently in the user's knowledge graph.
    
    Args:
        user_id: The user ID to query
        limit: Maximum number of nodes and facts to return (default: 10)
        
    Returns:
        TopConnectionsResponse with top nodes and facts
    """
    result = await service.get_top_connections(user_id, limit)
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=result["message"]
        )
    
    return result