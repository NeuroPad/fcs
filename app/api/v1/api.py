from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    chat,
    documents,
    files,
    memory,
    rag,
    roles,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
 