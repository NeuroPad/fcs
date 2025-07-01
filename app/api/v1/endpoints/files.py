from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
import json
from typing import List
import logging
from pathlib import Path

from app.core.config import settings
from app.schemas.upload import FileUpload
from app.schemas import PageRange
from app.utils.file_utils import process_file_upload
from app.services.file_service import FileService
from app.services.llama_index_graph_rag import GraphRAGService

router = APIRouter()

# Create directories if they don't exist
for dir_path in [settings.UPLOAD_DIR, settings.PROCESSED_FILES_DIR]:
    Path(dir_path).mkdir(exist_ok=True)

# Initialize service
pdf_service = FileService(
    settings.UPLOAD_DIR, settings.PROCESSED_FILES_DIR
)

logger = logging.getLogger(__name__)


@router.post("/upload-files")
async def upload_files(files: List[UploadFile] = File(...)):
    try:
        uploaded_files = []
        for file in files:
            file_path = await pdf_service.save_upload_file(file)
            uploaded_files.append(str(file_path))

        return JSONResponse(
            content={
                "status": "success",
                "message": f"Uploaded {len(uploaded_files)} files",
                "files": uploaded_files,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-pdfs-to-markdown")
async def process_pdfs():
    """Process uploaded PDFs and convert to markdown using docling"""
    try:
        result = await pdf_service.process_uploads()
        return JSONResponse(content={"status": "success", **result})
    except Exception as e:
        # logger.error(f"Processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files")
async def list_files():
    """Get list of all uploaded files with their metadata"""
    try:
        files = await pdf_service.get_uploaded_files()
        return JSONResponse(content={"status": "success", "files": files})
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/file/{filename}")
async def delete_pdf(filename: str):
    """Delete a PDF file and its associated processed files"""
    try:
        # Delete from PDF service
        result = await pdf_service.delete_file_and_associated_files(filename)

        # Also clean up from image RAG if it exists
        try:
            # Only attempt to delete from image RAG if we successfully deleted the PDF
            from app.services.image_rag_service import ImageRAGService
            image_rag_service = ImageRAGService()
            image_rag_service.delete_document_images(filename)
            result["message"] += " and cleaned up image indexes"
        except Exception as e:
            logger.warning(f"Could not clean up image indexes: {str(e)}")

        return JSONResponse(content=result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{filename}")
async def get_file(filename: str):
    """Serve any file type with appropriate media type"""
    try:
        file_path = await pdf_service.get_any_file(filename)
        
        # Map file extensions to media types
        media_types = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.json': 'application/json',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        
        # Get file extension and corresponding media type
        extension = Path(filename).suffix.lower()
        media_type = media_types.get(extension, 'application/octet-stream')
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error serving file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 