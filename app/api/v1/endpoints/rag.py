from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
import asyncio

from app.core.config import settings
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.services.rag_service import RAGService
from app.services.llama_index_graph_rag import GraphRAGService
from app.services.auth.auth_service import get_current_active_user
from app.schemas.graph_rag import ExtendedGraphRAGResponse
from app.schemas import GraphRAGResponse, Question

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
rag_service = RAGService()
graph_rag_service = GraphRAGService()


# ============= STANDARD RAG ENDPOINTS =============

@router.post("/index-document/{document_id}")
async def index_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Index a specific document in the RAG system (manual re-indexing)"""
    try:
        # Get document from database
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        
        # Add document processing to background tasks
        background_tasks.add_task(rag_service.process_document, document.id, db)
        
        return JSONResponse(content={
            "status": "processing",
            "message": f"Document {document_id} is being processed in the background",
            "document_id": document_id
        })
    except Exception as e:
        logger.error(f"Error indexing document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-pending")
async def process_pending_documents(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Process and index all pending documents in the database (unified workflow)"""
    try:
        # Import the unified processing function
        from app.api.v1.endpoints.documents import process_and_index_document
        
        # Get all documents that need processing or indexing
        from app.models.document import Document
        pending_documents = db.query(Document).filter(
            Document.user_id == current_user.id,
            (Document.is_indexed == False) | (Document.status.in_(["pending", "uploaded"]))
        ).all()
        
        if not pending_documents:
            return JSONResponse(content={
                "status": "success",
                "message": "No pending documents to process"
            })
        
        # Queue each document for unified processing
        for document in pending_documents:
            background_tasks.add_task(
                process_and_index_document,
                document.id,
                current_user.id
            )
            # Update status
            document.status = "processing"
        
        db.commit()
        
        return JSONResponse(content={
            "status": "processing",
            "message": f"Processing and indexing {len(pending_documents)} pending documents in the background",
            "queued_count": len(pending_documents)
        })
    except Exception as e:
        logger.error(f"Error processing pending documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def query_documents(
    query: str,
    top_k: Optional[int] = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Query the RAG system"""
    try:
        result = await rag_service.query(query, current_user.id, top_k)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/document/{document_id}")
async def delete_document_from_index(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a document from the RAG index"""
    try:
        result = await rag_service.delete_document(document_id, current_user.id, db)
        if result["status"] == "error":
            raise HTTPException(status_code=404, detail=result["message"])
        return JSONResponse(content=result)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= GRAPH RAG ENDPOINTS =============

@router.post("/graph/process-documents")
async def process_all_documents_graph(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """Process all documents into the knowledge graph for the current user"""
    try:
        # Add the processing task to background tasks
        background_tasks.add_task(graph_rag_service.process_documents)
        return JSONResponse(content={
            "status": "processing",
            "message": "Document processing started in the background"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/similar/")
async def get_similar_nodes(
    question: Question,
    current_user: User = Depends(get_current_active_user)
):
    """Get similar nodes from the knowledge graph for the current user."""
    try:
        nodes = await graph_rag_service.get_similar_nodes(question.text)
        return {"similar_nodes": nodes}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/graph/ask/", response_model=ExtendedGraphRAGResponse)
async def ask_graph_question(
    question: Question,
    current_user: User = Depends(get_current_active_user)
):
    """Ask a question and get a response using GraphRAG for the current user."""
    try:
        response = await graph_rag_service.get_answer(question.text)
        return response
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/graph/stats")
async def get_graph_stats(
    current_user: User = Depends(get_current_active_user)
):
    """Get statistics about the knowledge graph for the current user"""
    try:
        stats = await graph_rag_service.get_graph_stats(user_id=current_user.id)
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/relationships")
async def get_graph_relationships(
    current_user: User = Depends(get_current_active_user)
):
    """Get all relationships from the knowledge graph for the current user"""
    try:
        relationships = await graph_rag_service.get_relationships(user_id=current_user.id)
        return JSONResponse(content=relationships)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graph/process-documents/status")
async def get_processing_status():
    """Get the current status of document processing"""
    try:
        status = await graph_rag_service.get_processing_status()
        return JSONResponse(content=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/graph/ws/process-documents")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time processing status updates"""
    await websocket.accept()
    
    try:
        while True:
            # Get current status
            status = await graph_rag_service.get_processing_status()
            
            # Create a serializable status object
            status_update = {
                "status": status.get("status", "unknown"),
                "message": status.get("message", ""),
                "progress": status.get("progress", 0),
                "processed_documents": status.get("processed_documents", 0),
                "total_documents": status.get("total_documents", 0)
            }
            
            # Send the status update
            await websocket.send_json(status_update)
            
            # If processing is complete or has errored, break the loop
            if status["status"] in ["completed", "error"]:
                break
                
            # Wait before next update
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        try:
            await websocket.close()
        except:
            pass


# ============= COMBINED RAG ENDPOINTS =============

@router.post("/combined/query")
async def combined_query(
    query: str,
    use_graph: bool = True,
    use_standard: bool = True,
    top_k: Optional[int] = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Query both standard RAG and Graph RAG systems and combine results"""
    try:
        results = {}
        
        if use_standard:
            standard_result = await rag_service.query(query, current_user.id, top_k)
            results["standard_rag"] = standard_result
        
        if use_graph:
            graph_result = await graph_rag_service.get_answer(query)
            results["graph_rag"] = {
                "answer": graph_result.answer,
                "reasoning_nodes": graph_result.reasoning_nodes,
                "sources": graph_result.sources
            }
        
        # Combine results if both are enabled
        if use_standard and use_graph:
            combined_answer = f"Standard RAG: {standard_result.get('answer', '')}\n\nGraph RAG: {graph_result.answer}"
            combined_sources = list(set((standard_result.get('sources', []) or []) + (graph_result.sources or [])))
            
            results["combined"] = {
                "answer": combined_answer,
                "sources": combined_sources,
                "reasoning_nodes": graph_result.reasoning_nodes
            }
        
        return JSONResponse(content=results)
    except Exception as e:
        logger.error(f"Combined query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
def get_rag_info():
    """Placeholder endpoint - to be implemented."""
    return {"message": "RAG endpoints will be moved here"}