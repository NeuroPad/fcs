# api/documents.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
from pathlib import Path

from core.config import settings
from db.session import get_db
from db.models import Document, User
from services.document_service import DocumentService
from api.auth.jwt_handler import get_current_active_user
from schemas.upload import DocumentResponse, DocumentList

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize document service
document_service = DocumentService(upload_dir=settings.UPLOAD_DIR)

@router.post("/upload", response_model=List[DocumentResponse]) # Change response model to List
async def upload_file(
    files: List[UploadFile] = File(...), # Change parameter name and type to List[UploadFile]
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload multiple files and optionally process them in the background"""
    uploaded_documents = []
    try:
        for file in files: # Loop through the list of files
            # Save file and create document record
            document = await document_service.save_upload_file(file, current_user.id, db)
            uploaded_documents.append(document)

            # If it's a PDF, queue it for processing
            if document.content_type.endswith("/pdf"):
                # Queue the PDF for processing
                await document_service.queue_pdf_processing(document.id)
                # Update status immediately for response, actual processing happens later
                document.status = "processing"
                db.commit()
                db.refresh(document)
            else:
                # Non-PDF files don't need processing
                document.status = "completed"
                db.commit()
                db.refresh(document)

        return uploaded_documents # Return the list of saved documents
    except Exception as e:
        logger.error(f"Error uploading files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=DocumentList)
async def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all documents for the current user"""
    try:
        documents = await document_service.get_user_documents(current_user.id, db)
        return {"documents": documents}
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific document"""
    try:
        document = await document_service.get_document(document_id, current_user.id, db)
        return document
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{document_id}/process")
async def process_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Process a document (for scanned PDFs)"""
    try:
        # Get document
        document = await document_service.get_document(document_id, current_user.id, db)
        
        # Check if document is a PDF
        if not document.content_type.endswith("/pdf"):
            return JSONResponse(content={
                "status": "success",
                "message": "Non-PDF file doesn't need processing"
            })
        
        # Check if document is already processed
        if document.status == "completed" and document.markdown_path:
            return JSONResponse(content={
                "status": "success",
                "message": "Document already processed"
            })
        
        # Queue document for processing
        result = await document_service.queue_pdf_processing(document.id)
        
        # Update status
        document.status = "processing"
        db.commit()
        
        return JSONResponse(content={
            "status": "processing",
            "message": "Document is being processed in the background",
            "document_id": document.id
        })
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a document and its associated files"""
    try:
        result = await document_service.delete_document(document_id, current_user.id, db)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))