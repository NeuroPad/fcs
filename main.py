from fastapi import Request, FastAPI, File, UploadFile, Form, HTTPException
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from db.session import init_db, Base, engine
from core.config import settings

import logging
from pathlib import Path


from services.image_rag_service import ImageRAGService
from services.graphiti_memory_service import GraphitiMemoryService, async_worker
from api import router as api_router
from api import relik_graph_rag

# Initialize the services
image_rag_service = ImageRAGService(
    chroma_db_path=str(settings.CHROMA_DB_DIR),
    markdown_dir=settings.PROCESSED_FILES_DIR,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/processed_files", StaticFiles(directory=str(settings.PROCESSED_FILES_DIR)), name="processed_files")

@app.on_event("startup")
async def startup_event():
    # Initialize database
    init_db()
    
    # Initialize GraphitiMemoryService worker
    await GraphitiMemoryService.initialize_worker()
    
    # Initialize a GraphitiMemoryService instance to build indices and constraints
    memory_service = GraphitiMemoryService()
    await memory_service.initialize()
    logger.info("Initialized GraphitiMemoryService on startup")

@app.on_event("shutdown")
async def shutdown_event():
    # Shutdown GraphitiMemoryService worker
    await GraphitiMemoryService.shutdown_worker()
    logger.info("Shutdown GraphitiMemoryService worker")

# Include the API router
app.include_router(api_router)


@app.get("/")
async def read_root():
    """Root endpoint that redirects to the API documentation."""
    return RedirectResponse(url="/docs")

@app.get('/healthcheck')
async def healthcheck():
    return JSONResponse(content={'status': 'healthy'}, status_code=200)