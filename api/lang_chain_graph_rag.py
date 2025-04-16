from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from pathlib import Path
from schemas import GraphRAGResponse, Question
import logging
from core.config import settings
from services.langchain_graph_rag import LangchainGraphRAGService

router = APIRouter()

# langchain_graph_rag_service = LangchainGraphRAGService(settings)
# logger = logging.getLogger(__name__)


# @router.post("/process-documents-langchain")
# async def process_documents_langchain():
#     """Process all Markdown documents into the knowledge graph using Langchain"""
#     try:
#         result = await langchain_graph_rag_service.process_documents("./processed_files")
#         return JSONResponse(content={"status": "success", **result})
#     except Exception as e:
#         logger.error(f"Processing error: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/query-langchain")
# async def query_knowledge_graph(question: Question):
#     """Query the knowledge graph using Langchain"""
#     try:
#         response = await langchain_graph_rag_service.query_knowledge_graph(
#             question.text
#         )
#         return JSONResponse(content={"status": "success", "response": response})
#     except Exception as e:
#         logger.error(f"Query error: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/similar-documents-langchain")
# async def get_similar_documents(query: str, k: int = 5):
#     """Get similar documents using Langchain vector store"""
#     try:
#         documents = await langchain_graph_rag_service.get_similar_documents(query, k)
#         return JSONResponse(content={"status": "success", "documents": documents})
#     except Exception as e:
#         logger.error(f"Search error: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))
