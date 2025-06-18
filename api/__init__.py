from fastapi import APIRouter
from .chat import router as chat_router
from .graph_rag import router as graph_rag_router
from .files import router as files_router
from .lang_chain_graph_rag import router as langchain_router
#from .multimodal_rag import router as multimodal_rag_router
from .memory import router as memory_router
from .auth_routes import router as auth_router
from .documents import router as documents_router
from .rag import router as rag_router
# from api import files, chat, graph_rag, multimodal_rag
#from api import relik_graph_rag

# Create a main router for the API
router = APIRouter()

# Include all sub-routers
router.include_router(files_router, prefix="/files", tags=["files"])
# router.include_router(graph_rag_router, prefix="/graph-rag", tags=["graph-rag"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(langchain_router, prefix="/langchain", tags=["langchain"])
router.include_router(memory_router, prefix="/memory", tags=["memory"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(documents_router, prefix="/documents", tags=["documents"])
router.include_router(rag_router, prefix="/rag", tags=["rag"])
# Export the main router
__all__ = ["router"]
