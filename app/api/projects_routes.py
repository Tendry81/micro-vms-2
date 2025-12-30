"""
Project management API endpoints.
"""

from fastapi import APIRouter, Request

from app.core.models import ProjectCreateRequest
from app.projects.project_manager import (
    create_project,
    list_projects,
    get_project_info,
    delete_project,
    download_project
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/create")
async def create_project_endpoint(request: ProjectCreateRequest, http_request: Request):
    """
    Create a new project by cloning a GitHub repository.
    
    Args:
        request: Project creation request
        http_request: FastAPI request for authentication
    """
    return await create_project(request, http_request)


@router.get("/list")
async def list_projects_endpoint(http_request: Request):
    """
    List all projects.
    
    Args:
        http_request: FastAPI request for authentication
    """
    return await list_projects(http_request)


@router.get("/{project_name}")
async def get_project_info_endpoint(project_name: str, http_request: Request):
    """
    Get information about a specific project.
    
    Args:
        project_name: Name of the project
        http_request: FastAPI request for authentication
    """
    return await get_project_info(project_name, http_request)

@router.get("/{project_name}/download")
async def download_project_endpoint(project_name: str, http_request: Request):
    """
    Download a specific project.
    
    Args:
        project_name: Name of the project
        http_request: FastAPI request for authentication
    """
    return await download_project(project_name, http_request)


@router.delete("/{project_name}")
async def delete_project_endpoint(project_name: str, http_request: Request):
    """
    Delete a project.
    
    Args:
        project_name: Name of the project
        http_request: FastAPI request for authentication
    """
    return await delete_project(project_name, http_request)