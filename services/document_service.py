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
from db.models import Document
from core.config import settings
from db.session import get_db 

from docling_core.types.doc import ImageRefMode
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import AcceleratorDevice

logger = logging.getLogger(__name__)

IMAGE_RESOLUTION_SCALE = 2.0


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
        """Queue a PDF document for processing in the background"""
        # Create a task for the async worker
        await async_worker.queue.put(partial(self._process_scanned_pdf, document_id))
        
        return {
            "status": "queued",
            "message": f"Document {document_id} queued for processing. Jobs in queue: {async_worker.queue.qsize()}",
            "queue_size": async_worker.queue.qsize()
        }
    
    async def _process_scanned_pdf(self, document_id: int) -> Dict[str, Any]:
        """Process a scanned PDF file to extract text using docling"""
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
            
            # Initialize options
            pipeline_options = PdfPipelineOptions()
            pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
            pipeline_options.generate_page_images = False  # Disable page images
            pipeline_options.generate_picture_images = True
            
            pipeline_options.accelerator_options.device = AcceleratorDevice.MPS
            pipeline_options.accelerator_options.num_threads = 8
            
            # Create converter with options
            doc_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
            
            start_time = time.time()
            
            # Convert the PDF
            conv_res = doc_converter.convert(pdf_path)
            
            # Create output directories
            doc_filename = conv_res.input.file.stem
            
            # Save markdown version
            md_ref_filename = self.upload_dir / f"{doc_filename}-with-refs.md"
            conv_res.document.save_as_markdown(
                md_ref_filename, image_mode=ImageRefMode.REFERENCED
            )
            
            end_time = time.time() - start_time
            
            logger.info(
                f"Document converted and figures exported in {end_time:.2f} seconds."
            )
            
            # Update document record
            document.markdown_path = str(md_ref_filename)
            document.status = "completed"
            document.processed_at = datetime.utcnow()
            db.commit()
            db.refresh(document)

            return {
                "status": "success",
                "message": f"Document processed successfully in {end_time:.2f} seconds",
                "document_id": document.id,
                "pdf": str(pdf_path),
                "markdown": str(md_ref_filename)
            }
        
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            
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
                
                # Check for artifacts directory
                artifacts_dir = markdown_path.parent / f"{markdown_path.stem}_artifacts"
                if artifacts_dir.exists() and artifacts_dir.is_dir():
                    for file in artifacts_dir.glob("*"):
                        file.unlink()
                        files_deleted.append(str(file))
                    artifacts_dir.rmdir()
                    files_deleted.append(str(artifacts_dir))
            
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