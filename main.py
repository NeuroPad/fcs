from fastapi import Request, FastAPI, File, UploadFile, Form, HTTPException
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from db.session import init_db, Base, engine
from core.config import settings

import logging
from pathlib import Path
import os


from fcs_core import FCSMemoryService
from fcs_core.async_worker import async_worker
from services.document_service import DocumentService
from api import router as api_router



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
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

@app.on_event("startup")
async def startup_event():
    # Initialize database
    init_db()
    
    # Initialize FCSMemoryService worker
    await FCSMemoryService.initialize_worker()
    
    # Initialize DocumentService worker
    await DocumentService.initialize_worker()
    
    # Initialize a FCSMemoryService instance to build indices and constraints
    memory_service = FCSMemoryService()
    await memory_service.initialize()
    logger.info("Initialized FCSMemoryService on startup")
    logger.info("Initialized DocumentService worker on startup")

    # Debug print for NEO4J-related environment variables
    # print("DOCKER ENV DEBUG:", {k: v for k, v in os.environ.items() if "NEO4J" in k})

@app.on_event("shutdown")
async def shutdown_event():
    # Shutdown FCSMemoryService worker
    await FCSMemoryService.shutdown_worker()
    
    # Shutdown DocumentService worker
    await DocumentService.shutdown_worker()
    
    logger.info("Shutdown FCSMemoryService and DocumentService workers")

# Include the API router
app.include_router(api_router, prefix="/api")



@app.get("/")
async def read_root():
    """Root endpoint that redirects to the API documentation."""
    return RedirectResponse(url="/docs")

@app.get('/healthcheck')
async def healthcheck():
    return JSONResponse(content={'status': 'healthy'}, status_code=200)