from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from core.config import settings
from services.multimodal_rag_service import MultiModalRAGService
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

multimodal_service = MultiModalRAGService(
    chroma_db_path=str(settings.CHROMA_DB_DIR)
)

@router.post("/index-documents")
async def index_documents():
    """Index all markdown documents and their associated images"""
    try:
        result = await multimodal_service.process_documents(
            markdown_dir=settings.PROCESSED_FILES_DIR
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Indexing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def query_documents(query: str, top_k: Optional[int] = 3):
    """Query the multimodal index"""
    try:
        result = await multimodal_service.query_index(query, top_k=top_k)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/enhanced-query")
async def enhanced_query_documents(query: str, top_k: Optional[int] = 3):
    """Query using both multimodal and graph-based context"""
    try:
        result = await multimodal_service.enhanced_query(query, top_k=top_k)
        # Convert ExtendedGraphRAGResponse to dict before JSONResponse
        return JSONResponse(content={
            "status": "success",
            "answer": result.answer,
            "images": result.images,
            "sources": result.sources
        })
    except Exception as e:
        logger.error(f"Enhanced query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))