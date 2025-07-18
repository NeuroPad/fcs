from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
import asyncio
import json
from pathlib import Path

from app.core.config import settings
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.services.document_service import DocumentService
from app.services.auth.auth_service import get_current_active_user
from app.services.rag_service import RAGService
from app.schemas.document import DocumentResponse, DocumentList

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
document_service = DocumentService(upload_dir=settings.UPLOAD_DIR)
rag_service = RAGService()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: dict = {}  # user_id -> [websockets]
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections.append(websocket)
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        self.active_connections.remove(websocket)
        if user_id in self.user_connections:
            self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
    
    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_text(message)
                except:
                    # Remove broken connections
                    self.user_connections[user_id].remove(connection)
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)

manager = ConnectionManager()


async def process_and_index_document(document_id: int, user_id: int):
    """Unified background task to process and index a document"""
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    try:
        # Get document from database
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
        
        if not document:
            logger.error(f"Document {document_id} not found for user {user_id}")
            return
        
        # Helper function to broadcast status updates
        async def broadcast_status(status: str, message: str = ""):
            status_update = {
                "type": "document_status_update",
                "document_id": document_id,
                "filename": document.filename,
                "status": status,
                "message": message,
                "is_indexed": document.is_indexed
            }
            await manager.send_personal_message(json.dumps(status_update), user_id)
        
        # If it's a PDF, process it first
        if document.content_type.endswith("/pdf"):
            logger.info(f"Processing PDF document {document_id}: {document.filename}")
            await broadcast_status("processing", "Processing PDF document...")
            
            result = await document_service.queue_pdf_processing(document.id)
            
            if result["status"] == "queued":
                # Wait for PDF processing to complete
                # Note: In a production environment, you might want to use a proper queue system
                # For now, we'll check the status periodically
                max_wait_time = 300  # 5 minutes
                wait_interval = 10   # 10 seconds
                elapsed_time = 0
                
                while elapsed_time < max_wait_time:
                    await asyncio.sleep(wait_interval)
                    elapsed_time += wait_interval
                    
                    # Refresh document from database
                    db.refresh(document)
                    
                    if document.status == "completed":
                        logger.info(f"PDF processing completed for document {document_id}")
                        await broadcast_status("processing", "PDF processing completed, starting indexing...")
                        break
                    elif document.status == "failed":
                        logger.error(f"PDF processing failed for document {document_id}: {document.error_message}")
                        await broadcast_status("failed", f"PDF processing failed: {document.error_message}")
                        return
                
                if document.status != "completed":
                    logger.warning(f"PDF processing timed out for document {document_id}")
                    await broadcast_status("processing", "PDF processing timed out, continuing with indexing...")
                    # Continue with indexing anyway, using the original file
            elif result["status"] == "warning":
                logger.warning(f"MinerU not available for document {document_id}: {result['message']}")
                await broadcast_status("processing", "PDF processor unavailable, using fallback...")
                # Continue with indexing the original file
            else:
                logger.error(f"PDF processing failed for document {document_id}: {result['message']}")
                await broadcast_status("processing", "PDF processing failed, continuing with indexing...")
                # Continue with indexing anyway
        
        # Index the document in RAG system
        logger.info(f"Indexing document {document_id} in RAG system")
        await broadcast_status("processing", "Indexing document in knowledge base...")
        
        rag_result = await rag_service.process_document(document_id, db)
        
        if rag_result["status"] == "success":
            logger.info(f"Successfully indexed document {document_id}: {document.filename}")
            await broadcast_status("completed", "Document successfully processed and indexed")
        else:
            logger.error(f"Failed to index document {document_id}: {rag_result['message']}")
            await broadcast_status("failed", f"Indexing failed: {rag_result['message']}")
            
    except Exception as e:
        logger.error(f"Error in unified document processing for document {document_id}: {str(e)}")
        # Try to broadcast error status
        try:
            error_update = {
                "type": "document_status_update",
                "document_id": document_id,
                "status": "error",
                "message": f"Processing error: {str(e)}",
                "is_indexed": False
            }
            await manager.send_personal_message(json.dumps(error_update), user_id)
        except:
            pass  # Don't fail if WebSocket broadcast fails
    finally:
        db.close()


@router.post("/upload", response_model=List[DocumentResponse])
async def upload_file(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload multiple files and process them in the background (including indexing)"""
    uploaded_documents = []
    try:
        for file in files:
            # Save file and create document record
            document = await document_service.save_upload_file(file, current_user.id, db)
            uploaded_documents.append(document)

            # Queue the unified processing and indexing task
            background_tasks.add_task(
                process_and_index_document,
                document.id,
                current_user.id
            )
            
            # Set initial status based on file type
            if document.content_type.endswith("/pdf"):
                document.status = "processing"  # Will be processed and indexed
            else:
                document.status = "processing"  # Will be indexed directly
            
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
    """Process and index a document (manual re-processing)"""
    try:
        # Get document
        document = await document_service.get_document(document_id, current_user.id, db)
        
        # Check if document is already processed and indexed
        if document.status == "completed" and document.is_indexed:
            return JSONResponse(content={
                "status": "success",
                "message": "Document already processed and indexed"
            })
        
        # Queue the unified processing and indexing task
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
            "message": "Document is being processed and indexed in the background",
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
    """Process and index all pending documents for the current user"""
    try:
        # Get all user documents
        documents = await document_service.get_user_documents(current_user.id, db)
        
        # Filter pending documents (not processed or not indexed)
        pending_documents = [doc for doc in documents if doc.status in ["pending", "uploaded"] or not doc.is_indexed]
        
        if not pending_documents:
            return JSONResponse(content={
                "status": "success",
                "message": "No pending documents to process"
            })
        
        processed_count = 0
        for document in pending_documents:
            try:
                # Queue the unified processing and indexing task
                background_tasks.add_task(
                    process_and_index_document,
                    document.id,
                    current_user.id
                )
                
                # Update status
                document.status = "processing"
                db.commit()
                db.refresh(document)
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error queuing document {document.id}: {str(e)}")
                continue
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Started processing and indexing {processed_count} pending documents",
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


@router.websocket("/ws/status")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = None
):
    """WebSocket endpoint for real-time document status updates"""
    try:
        # Authenticate user using token from query parameter
        from app.services.auth.auth_service import get_current_user_from_token
        from app.db.session import get_db
        
        if not token:
            await websocket.close(code=1008, reason="Authentication token required")
            return
            
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            current_user = get_current_user_from_token(db, token)
            if not current_user:
                await websocket.close(code=1008, reason="Invalid authentication token")
                return
        except Exception as e:
            await websocket.close(code=1008, reason="Authentication failed")
            return
        finally:
            db.close()
        
        await manager.connect(websocket, current_user.id)
        
        try:
            while True:
                # Keep the connection alive
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket, current_user.id)
        except Exception as e:
            logger.error(f"WebSocket error for user {current_user.id}: {str(e)}")
            manager.disconnect(websocket, current_user.id)
            
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass