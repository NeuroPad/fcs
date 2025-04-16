from fastapi import APIRouter, Depends, HTTPException,Form, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
import json
from typing import List
import logging
from pathlib import Path
from core.config import settings

from schemas.upload import FileUpload
from schemas import PageRange
from utils.file_utils import process_file_upload
from services.file_service import FileService
from services.llama_index_graph_rag import GraphRAGService
from services.image_rag_service import ImageRAGService

router = APIRouter()

graph_rag_service = GraphRAGService()
image_rag_service = ImageRAGService(
    chroma_db_path=str(settings.CHROMA_DB_DIR),
    markdown_dir=settings.PROCESSED_FILES_DIR,
)

# Create directories if they don't exist
for dir_path in [settings.UPLOAD_DIR, settings.PROCESSED_FILES_DIR]:
    Path(dir_path).mkdir(exist_ok=True)

# Initialize service
pdf_service = FileService(
    settings.UPLOAD_DIR, settings.PROCESSED_FILES_DIR, image_rag_service=image_rag_service
)

logger = logging.getLogger(__name__)


@router.post("/upload/", deprecated=True)
async def upload_file(
        file: UploadFile = File(...), page_range: str = Form(default='{"all_pages": true}')
):
    """
     **Deprecated**: This endpoint is deprecated and will be removed in future versions.
    Please use the `/upload-files` endpoint instead.

    Upload a PDF or TXT file to create a knowledge graph.
    Specify page range for PDF files:
    - all_pages=true for all pages
    - start and end for specific range
    """
    try:
        page_range_dict = json.loads(page_range)
        file_upload = FileUpload(page_range=PageRange(**page_range_dict))
        content = await process_file_upload(file, file_upload.page_range)
        await graph_rag_service.process_document(content)
        return {
            "message": "File processed successfully",
            "pages_processed": file_upload.page_range,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


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


