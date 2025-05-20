# api/rag.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from core.config import settings
from db.session import get_db
from db.models import Document, User
from services.rag_service import RAGService
from api.auth.jwt_handler import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize RAG service with ChromaDB as the default
rag_service = RAGService()

@router.post("/index-document/{document_id}")
async def index_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Index a specific document in the RAG system"""
    try:
        # Get document from database
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        
        # Add document processing to background tasks
        background_tasks.add_task(rag_service.process_document, document, db)
        
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
    """Process all pending documents in the database"""
    try:
        # Check if user is admin
        # if current_user.role != "admin":
        #     raise HTTPException(status_code=403, detail="Only admins can process all pending documents")
        
        # Add processing to background tasks
        background_tasks.add_task(rag_service.process_pending_documents, db)
        
        return JSONResponse(content={
            "status": "processing",
            "message": "Processing pending documents in the background"
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