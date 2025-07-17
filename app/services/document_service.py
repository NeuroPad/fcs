# services/document_service.py
import logging
import time
from pathlib import Path
import shutil
from typing import List, Dict, Any, Optional
from fastapi import UploadFile, BackgroundTasks
from datetime import datetime
import asyncio
import os
from functools import partial

from sqlalchemy.orm import Session
from app.models.document import Document
from app.core.config import settings
from app.db.session import get_db 
from app.services.mineru_service import MinerUService

logger = logging.getLogger(__name__)


class AsyncWorker:
    """Worker for processing background tasks asynchronously"""
    def __init__(self):
        self.queue = asyncio.Queue()
        self.task = None

    async def worker(self):
        while True:
            try:
                logger.info(f'Processing document job: (size of remaining queue: {self.queue.qsize()})')
                job = await self.queue.get()
                await job()
                self.queue.task_done()
                await asyncio.sleep(1)  # Add a small delay to prevent CPU overload
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in document worker: {str(e)}")

    async def start(self):
        self.task = asyncio.create_task(self.worker())
        logger.info("Started AsyncWorker for DocumentService")

    async def stop(self):
        if self.task:
            self.task.cancel()
            await self.task
        while not self.queue.empty():
            self.queue.get_nowait()
        logger.info("Stopped AsyncWorker for DocumentService")


# Create a global instance of the worker
async_worker = AsyncWorker()


class DocumentService:
    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
        
        # Create upload directory if it doesn't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize MinerU service
        if settings.MINERU_API_TOKEN:
            self.mineru_service = MinerUService(settings.MINERU_API_TOKEN)
        else:
            logger.warning("MinerU API token not configured - PDF processing will be disabled")
            self.mineru_service = None
    
    @classmethod
    async def initialize_worker(cls):
        """Initialize the async worker for background processing"""
        await async_worker.start()
    
    @classmethod
    async def shutdown_worker(cls):
        """Shutdown the async worker"""
        await async_worker.stop()
    
    def clean_filename(self, filename: str) -> str:
        """Clean filename to remove spaces and special characters, ensuring only underscores between words while preserving extension"""
        # Split filename into name and extension
        name, extension = Path(filename).stem, Path(filename).suffix

        # Clean the name part
        clean_name = "".join("_" if not c.isalnum() else c for c in name)

        # Replace multiple underscores with single underscore
        while "__" in clean_name:
            clean_name = clean_name.replace("__", "_")

        # Remove leading/trailing underscores
        clean_name = clean_name.strip("_")

        # Combine with original extension
        return f"{clean_name}{extension}"
    
    async def save_upload_file(self, file: UploadFile, user_id: int, db: Session) -> Document:
        """Save an uploaded file and create a database record"""
        try:
            # Clean filename
            clean_name = self.clean_filename(file.filename)
            
            # Create file path
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            file_path = self.upload_dir / f"{user_id}_{timestamp}_{clean_name}"
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Determine content type based on extension
            file_extension = Path(file.filename).suffix.lower()
            content_type_map = {
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.md': 'text/markdown',
                '.txt': 'text/plain',
                '.html': 'text/html',
                '.htm': 'text/html',
                '.rtf': 'application/rtf',
                '.odt': 'application/vnd.oasis.opendocument.text',
                '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.epub': 'application/epub+zip'
            }
            content_type = content_type_map.get(file_extension, file.content_type)
            
            # Create document record
            document = Document(
                user_id=user_id,
                filename=file.filename,
                content_type=content_type,
                file_path=str(file_path),
                file_size=file_size,
                status="pending"
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            logger.info(f"Saved file: {file_path}")
            return document
        
        except Exception as e:
            logger.error(f"Error saving file {file.filename}: {str(e)}")
            raise
    
    async def queue_pdf_processing(self, document_id: int) -> Dict[str, Any]:
        """Queue a PDF document for processing in the background using MinerU"""
        if not self.mineru_service:
            logger.warning(f"MinerU service not available for document {document_id} - API token not configured")
            return {
                "status": "warning",
                "message": "MinerU service not available - PDF processing disabled",
                "queue_size": 0
            }
        
        # Test MinerU service availability by trying to get upload URL
        try:
            batch_id, upload_url = await self.mineru_service.get_upload_url("test.pdf")
            if not batch_id or not upload_url:
                logger.warning(f"MinerU service test failed for document {document_id} - service unavailable")
                return {
                    "status": "warning",
                    "message": "MinerU service unavailable - PDF processing disabled",
                    "queue_size": 0
                }
        except Exception as e:
            logger.warning(f"MinerU service test failed for document {document_id}: {str(e)}")
            return {
                "status": "warning",
                "message": "MinerU service unavailable - PDF processing disabled",
                "queue_size": 0
            }
        
        # Create a task for the async worker
        await async_worker.queue.put(partial(self._process_pdf_with_mineru, document_id))
        
        return {
            "status": "queued",
            "message": f"Document {document_id} queued for MinerU processing. Jobs in queue: {async_worker.queue.qsize()}",
            "queue_size": async_worker.queue.qsize()
        }
    
    async def _process_pdf_with_mineru(self, document_id: int) -> Dict[str, Any]:
        """Process a PDF file using MinerU API"""
        # Get a new database session for this background task
        db: Session = next(get_db())
        try:
            # Get document from database
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Update document status
            document.status = "processing"
            db.commit()
            db.refresh(document)
            
            # Check if MinerU service is available
            if not self.mineru_service:
                error_msg = "MinerU service not available - API token not configured"
                logger.error(error_msg)
                document.status = "failed"
                document.error_message = error_msg
                db.commit()
                return {
                    "status": "error",
                    "message": error_msg,
                    "document_id": document.id
                }
            
            # Check if file is a PDF
            if not document.content_type.endswith("/pdf"):
                document.status = "completed"  # Non-PDF files don't need processing
                db.commit()
                return {
                    "status": "success",
                    "message": "Non-PDF file doesn't need processing",
                    "document_id": document.id
                }
            
            # Get file path
            pdf_path = Path(document.file_path)
            
            # Check file size (MinerU has 200MB limit)
            file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 200:
                error_msg = f"File size ({file_size_mb:.1f} MB) exceeds MinerU limit of 200MB"
                logger.error(error_msg)
                document.status = "failed"
                document.error_message = error_msg
                db.commit()
                return {
                    "status": "error",
                    "message": error_msg,
                    "document_id": document.id
                }
            
            # Create output directory for this document
            doc_filename = pdf_path.stem
            output_dir = self.upload_dir / f"{doc_filename}_mineru_output"
            
            start_time = time.time()
            
            # Process with MinerU
            logger.info(f"Starting MinerU processing for document {document_id}")
            result = await self.mineru_service.process_document(
                file_path=pdf_path,
                output_dir=output_dir,
                data_id=f"doc_{document.id}_{int(time.time())}"
            )
            
            end_time = time.time() - start_time
            
            if result["status"] == "success":
                # Update document record with success
                markdown_path = result["markdown_path"]
                document.markdown_path = markdown_path
                document.status = "completed"
                document.processed_at = datetime.utcnow()
                db.commit()
                db.refresh(document)

                logger.info(f"MinerU processing completed in {end_time:.2f} seconds for document {document_id}")
                
                return {
                    "status": "success",
                    "message": f"Document processed successfully in {end_time:.2f} seconds",
                    "document_id": document.id,
                    "pdf": str(pdf_path),
                    "markdown": markdown_path,
                    "zip_url": result.get("zip_url")
                }
            else:
                # Processing failed
                error_msg = result.get("error", "Unknown MinerU processing error")
                logger.error(f"MinerU processing failed for document {document_id}: {error_msg}")
                
                document.status = "failed"
                document.error_message = error_msg
                db.commit()
                
                return {
                    "status": "error",
                    "message": error_msg,
                    "document_id": document.id
                }
        
        except Exception as e:
            logger.error(f"Error processing document {document_id} with MinerU: {str(e)}")
            
            # Update document status
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = "failed"
                document.error_message = str(e)
                db.commit()
            
            raise
        finally:
            # Close the session
            db.close()
    
    async def get_document(self, document_id: int, user_id: int, db: Session) -> Document:
        """Get a document by ID and user ID"""
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
        
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        return document
    
    async def get_user_documents(self, user_id: int, db: Session) -> List[Document]:
        """Get all documents for a user"""
        documents = db.query(Document).filter(Document.user_id == user_id).all()
        return documents
    
    async def delete_document(self, document_id: int, user_id: int, db: Session) -> Dict[str, Any]:
        """Delete a document and its associated files"""
        try:
            # Get document
            document = await self.get_document(document_id, user_id, db)
            
            # Get file paths
            file_path = Path(document.file_path)
            markdown_path = Path(document.markdown_path) if document.markdown_path else None
            
            files_deleted = []
            
            # Delete original file
            if file_path.exists():
                file_path.unlink()
                files_deleted.append(str(file_path))
            
            # Delete markdown file if exists
            if markdown_path and markdown_path.exists():
                markdown_path.unlink()
                files_deleted.append(str(markdown_path))
                
                # Check for MinerU output directory
                output_dir = markdown_path.parent
                if output_dir.exists() and output_dir.is_dir() and "mineru_output" in output_dir.name:
                    for file in output_dir.glob("*"):
                        if file.is_file():
                            file.unlink()
                            files_deleted.append(str(file))
                    output_dir.rmdir()
                    files_deleted.append(str(output_dir))
            
            # Delete document from database
            db.delete(document)
            db.commit()
            
            return {
                "status": "success",
                "message": f"Deleted document and {len(files_deleted)} associated files",
                "deleted_files": files_deleted
            }
        
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            raise