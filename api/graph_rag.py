from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
from fastapi.responses import JSONResponse

from pathlib import Path
from schemas import GraphRAGResponse, Question
from schemas.graph_rag import ExtendedGraphRAGResponse
from services.llama_index_graph_rag import GraphRAGService
from core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

graph_rag_service = GraphRAGService()



@router.post("/process-documents")
async def process_all_documents(background_tasks: BackgroundTasks):
    """Process all documents into the knowledge graph"""
    try:
        # Add the processing task to background tasks
        background_tasks.add_task(graph_rag_service.process_documents)
        return JSONResponse(content={
            "status": "processing",
            "message": "Document processing started in the background"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/similar/")
async def get_similar(question: Question):
    """
    Get similar nodes from the knowledge graph.
    """
    try:
        nodes = await graph_rag_service.get_similar_nodes(question.text)
        return {"similar_nodes": nodes}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/ask/", response_model=ExtendedGraphRAGResponse)
async def ask_question(question: Question):
    """
    Ask a question and get a response using GraphRAG.
    """
    try:
        response = await graph_rag_service.get_answer(question.text)
        return response
    except ValueError as e:
        raise HTTPException(400, str(e))




@router.get("/stats")
async def get_graph_stats():
    """Get statistics about the knowledge graph"""
    try:
        stats = await graph_rag_service.get_graph_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationships")
async def get_graph_relationships():
    """Get all relationships from the knowledge graph"""
    try:
        relationships = await graph_rag_service.get_relationships()
        return JSONResponse(content=relationships)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/process-documents/status")
async def get_processing_status():
    """Get the current status of document processing"""
    try:
        status = await graph_rag_service.get_processing_status()
        return JSONResponse(content=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/process-documents")
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
