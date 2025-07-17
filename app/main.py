from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.api import api_router
from app.db.session import engine
from app.db.base import Base

# Services imports (keeping your existing services)
from fcs_core import FCSMemoryService
from app.services.document_service import DocumentService

# Setup logging
logger = setup_logging()

# Create FastAPI app
app = FastAPI(
    title="MemDuo API",
    description="Memory-enhanced document understanding and chat API",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/processed_files", StaticFiles(directory=str(settings.PROCESSED_FILES_DIR)), name="processed_files")
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting MemDuo API...")
    
    # Initialize FCSMemoryService worker
    await FCSMemoryService.initialize_worker()
    
    # Initialize DocumentService worker
    await DocumentService.initialize_worker()
    
    # Initialize a FCSMemoryService instance to build indices and constraints
    memory_service = FCSMemoryService()
    await memory_service.initialize()
    
    logger.info("✅ All services initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down MemDuo API...")
    
    # Shutdown FCSMemoryService worker
    await FCSMemoryService.shutdown_worker()
    
    # Shutdown DocumentService worker
    await DocumentService.shutdown_worker()
    
    logger.info("✅ All services shut down successfully")


# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def read_root():
    """Root endpoint that redirects to the API documentation."""
    return RedirectResponse(url="/docs")


@app.get('/healthcheck')
async def healthcheck():
    """Health check endpoint."""
    return JSONResponse(content={'status': 'healthy'}, status_code=200)