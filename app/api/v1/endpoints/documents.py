from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
from pathlib import Path

from app.core.config import settings
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.services.document_service import DocumentService
from app.services.auth.auth_service import get_current_active_user
from app.schemas.document import DocumentResponse, DocumentList

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize document service
document_service = DocumentService(upload_dir=settings.UPLOAD_DIR)

@router.post("/upload", response_model=List[DocumentResponse])
async def upload_file(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload multiple files and optionally process them in the background"""
    uploaded_documents = []
    try:
        for file in files:
            # Save file and create document record
            document = await document_service.save_upload_file(file, current_user.id, db)
            uploaded_documents.append(document)

            # If it's a PDF, queue it for processing
            if document.content_type.endswith("/pdf"):
                # Queue the PDF for processing
                result = await document_service.queue_pdf_processing(document.id)
                if result["status"] == "queued":
                    # Update status immediately for response, actual processing happens later
                    document.status = "processing"
                elif result["status"] == "warning":
                    # MinerU not available, mark as uploaded but not processed
                    document.status = "uploaded"
                    document.error_message = result["message"]
                else:
                    # Error occurred
                    document.status = "failed"
                    document.error_message = result["message"]
                db.commit()
                db.refresh(document)
            else:
                # Non-PDF files don't need processing
                document.status = "completed"
                db.commit()
                db.refresh(document)

        return uploaded_documents
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
        total_size = sum(doc.file_size for doc in documents)
        
        # Convert datetime objects to strings
        doc_list = []
        for doc in documents:
            doc_dict = {
                "id": doc.id,
                "user_id": doc.user_id,
                "filename": doc.filename,
                "content_type": doc.content_type,
                "file_path": doc.file_path,
                "markdown_path": doc.markdown_path,
                "file_size": doc.file_size,
                "status": doc.status,
                "is_indexed": doc.is_indexed,
                "error_message": doc.error_message,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
                "indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else None
            }
            doc_list.append(doc_dict)
            
        return {
            "documents": doc_list,
            "count": len(documents),
            "total_size": total_size
        }
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/count")
async def get_documents_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get document count for the current user"""
    try:
        documents = await document_service.get_user_documents(current_user.id, db)
        total_count = len(documents)
        processed_count = len([doc for doc in documents if doc.status == "completed"])
        pending_count = len([doc for doc in documents if doc.status == "pending"])
        indexed_count = len([doc for doc in documents if doc.is_indexed])
        
        return {
            "total": total_count,
            "processed": processed_count,
            "pending": pending_count,
            "indexed": indexed_count
        }
    except Exception as e:
        logger.error(f"Error getting document count: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific document"""
    try:
        doc = await document_service.get_document(document_id, current_user.id, db)
        # Convert datetime objects to strings
        return {
            "id": doc.id,
            "user_id": doc.user_id,
            "filename": doc.filename,
            "content_type": doc.content_type,
            "file_path": doc.file_path,
            "markdown_path": doc.markdown_path,
            "file_size": doc.file_size,
            "status": doc.status,
            "is_indexed": doc.is_indexed,
            "error_message": doc.error_message,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
            "indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else None
        }
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

@router.post("/process-pending")
async def process_pending_documents(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Process all pending documents for the current user"""
    try:
        # Get all user documents
        documents = await document_service.get_user_documents(current_user.id, db)
        
        # Filter pending documents
        pending_documents = [doc for doc in documents if doc.status == "pending" or (doc.status == "processing" and not doc.is_indexed)]
        
        if not pending_documents:
            return JSONResponse(content={
                "status": "success",
                "message": "No pending documents to process"
            })
        
        processed_count = 0
        for document in pending_documents:
            try:
                # Queue the document for processing if it's a PDF
                if document.content_type.endswith("/pdf"):
                    await document_service.queue_pdf_processing(document.id)
                    document.status = "processing"
                else:
                    # For non-PDF files, mark as completed
                    document.status = "completed"
                    document.is_indexed = True
                
                db.commit()
                db.refresh(document)
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing document {document.id}: {str(e)}")
                continue
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Started processing {processed_count} pending documents",
            "processed_count": processed_count,
            "total_pending": len(pending_documents)
        })
        
    except Exception as e:
        logger.error(f"Error processing pending documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a document"""
    try:
        result = await document_service.delete_document(document_id, current_user.id, db)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))