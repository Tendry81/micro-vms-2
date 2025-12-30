"""
Software Project Management Service - FastAPI Application

A local Codespaces-like backend service for managing isolated software projects
with Git integration, filesystem operations, and shell execution.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Import routers
from .projects_routes import router as projects_router
from .filesystem_routes import router as filesystem_router
from .git_routes import router as git_router
from .shell_routes import router as shell_router

from app.core.audit import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Software Project Management Service",
    description="Local project management backend with Git, filesystem, and shell access",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects_router)
app.include_router(filesystem_router)
app.include_router(git_router)
app.include_router(shell_router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "project-manager"}


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Software Project Management Service",
        "version": "1.0.0",
        "endpoints": {
            "projects": "/projects",
            "filesystem": "/projects/{project_name}/files",
            "git": "/projects/{project_name}/git",
            "shell": "/projects/{project_name}/shell",
            "docs": "/api/docs"
        }
    }


# Error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "code": "INVALID_REQUEST",
            "message": "Request validation failed",
            "details": exc.errors()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7860,
        reload=True,
        log_level="info"
    )