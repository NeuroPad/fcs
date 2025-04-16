# from fastapi import APIRouter, HTTPException, BackgroundTasks
# from fastapi.responses import JSONResponse
# from pydantic import BaseModel
# from typing import Dict, Optional

# from services.relik_graph_rag import RelikGraphRAGService

# router = APIRouter()
# service = RelikGraphRAGService()

# class DocumentRequest(BaseModel):
#     content: str

# class QueryRequest(BaseModel):
#     question: str

# @router.post("/process")
# async def process_document(request: DocumentRequest) -> Dict:
#     """Process a single document using Relik extractor"""
#     result = await service.process_document(request.content)
#     if result["status"] == "error":
#         raise HTTPException(status_code=500, detail=result["message"])
#     return result

# @router.post("/process-documents")
# async def process_all_documents():
#     """Process all documents into the knowledge graph using Relik"""
#     try:
#         # Process documents synchronously
#         result = await service.process_documents()
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/status")
# async def get_processing_status() -> Dict:
#     """Get the current status of document processing"""
#     return await service.get_processing_status()