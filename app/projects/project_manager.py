"""
Project management module.
"""

import logging
import shutil
from pathlib import Path
from datetime import datetime

from fastapi import HTTPException, Request

from app.core.config import PROJECTS_ROOT
from app.core.models import ProjectCreateRequest, ProjectMetadata, ProjectListResponse
from app.core.audit import AuditLogger
from app.core.exceptions import (
    ValidationException,
    ProjectNotFoundException,
    AuthenticationException
)
from app.auth.auth import get_user_context, validate_scopes
from app.git.operations import GitOperations
from .utils import (
    validate_project_name,
    validate_repo_url,
    get_project_metadata,
    check_disk_space,
    sanitize_project_name
)

logger = logging.getLogger(__name__)

PROJECTS_DIR = Path(PROJECTS_ROOT)


async def create_project(request: ProjectCreateRequest, http_request: Request):
    """
    Create a new project by cloning a GitHub repository.
    
    Args:
        request: Project creation request
        http_request: FastAPI request for authentication
        
    Returns:
        Dict with status and project metadata
        
    Raises:
        HTTPException: If any validation or operation fails
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    # Validate inputs
    if not validate_project_name(request.project_name):
        raise ValidationException(
            message="Invalid project name. Use alphanumeric characters, hyphens, and underscores."
        )
    
    if not validate_repo_url(request.repo_url):
        raise ValidationException(
            message="Invalid repository URL. Only HTTPS URLs allowed."
        )
    
    
    # Check disk space before cloning
    if not check_disk_space(PROJECTS_DIR, 100 * 1024 * 1024):  # 100MB minimum
        raise HTTPException(
            status_code=507,
            detail="Insufficient disk space"
        )
    
    project_path = PROJECTS_DIR / request.project_name
    
    # Check if project already exists
    if project_path.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Project '{request.project_name}' already exists"
        )
    
    try:
        # Check if private repo (requires repo scope)
        if "github" in request.repo_url:
            validate_scopes(user_context, "clone_private")
        
        # Clone repository
        git_ops = GitOperations(PROJECTS_DIR, user_context.token_hash)
        git_ops.clone_repository(
            request.repo_url,
            project_path,
            request.branch
        )
        
        AuditLogger.log_project_creation(
            user_context.username,
            request.project_name,
            request.repo_url,
            True
        )
        logger.info(f"Project created: {request.project_name} by {user_context.username}")
        
        metadata = get_project_metadata(project_path, request.project_name)
        return {
            "status": "created",
            "project": metadata.dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        # Clean up on failure
        if project_path.exists():
            shutil.rmtree(project_path, ignore_errors=True)
        
        AuditLogger.log_project_creation(
            user_context.username,
            request.project_name,
            request.repo_url,
            False,
            str(e)
        )
        logger.error(f"Project creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


async def list_projects(http_request: Request):
    """
    List all projects.
    
    Args:
        http_request: FastAPI request for authentication
        
    Returns:
        ProjectListResponse with list of projects
        
    Raises:
        HTTPException: If listing fails
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    
    projects = []
    try:
        for project_dir in PROJECTS_DIR.iterdir():
            if project_dir.is_dir() and not project_dir.name.startswith("."):
                metadata = get_project_metadata(project_dir, project_dir.name)
                projects.append(metadata)
    except Exception as e:
        logger.error(f"Failed to list projects: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list projects")
    
    logger.info(f"Listed {len(projects)} projects for {user_context.username}")
    
    return ProjectListResponse(projects=projects, count=len(projects))


async def get_project_info(project_name: str, http_request: Request):
    """
    Get information about a specific project.
    
    Args:
        project_name: Name of the project
        http_request: FastAPI request for authentication
        
    Returns:
        Project metadata
        
    Raises:
        HTTPException: If project not found or access fails
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = PROJECTS_DIR / project_name
    
    if not project_path.exists() or not project_path.is_dir():
        raise ProjectNotFoundException(
            message=f"Project not found: {project_name}"
        )
    
    metadata = get_project_metadata(project_path, project_name)
    return metadata.dict()

async def download_project(project_name: str, http_request: Request):
    """
    Download a specific project.
    
    Args:
        project_name: Name of the project
        http_request: FastAPI request for authentication
        
    Returns:
        FileResponse for downloading the project as a zip file
        
    Raises:
        HTTPException: If project not found or access fails
    """
    from fastapi.responses import FileResponse
    import zipfile
    import os
    import tempfile

    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = PROJECTS_DIR / project_name
    
    if not project_path.exists() or not project_path.is_dir():
        raise ProjectNotFoundException(
            message=f"Project not found: {project_name}"
        )
    
    # Create a temporary zip file
    temp_dir = tempfile.gettempdir()
    zip_filename = os.path.join(temp_dir, f"{project_name}.zip")
    
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=project_path)
                    zipf.write(file_path, arcname)
        
        logger.info(f"Project {project_name} prepared for download by {user_context.username}")
        return FileResponse(zip_filename, media_type='application/zip', filename=f"{project_name}.zip")
    
    except Exception as e:
        logger.error(f"Failed to prepare project for download: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download project: {str(e)}")
    
async def delete_project(project_name: str, http_request: Request):
    """
    Delete a project.
    
    Args:
        project_name: Name of the project
        http_request: FastAPI request for authentication
        
    Returns:
        Dict with deletion status
        
    Raises:
        HTTPException: If deletion fails
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = PROJECTS_DIR / project_name
    
    if not project_path.exists():
        raise ProjectNotFoundException(
            message=f"Project not found: {project_name}"
        )
    
    try:
        shutil.rmtree(project_path)
        
        AuditLogger.log_project_deletion(
            user_context.username,
            project_name,
            True
        )
        logger.info(f"Project deleted: {project_name} by {user_context.username}")
        
        return {"status": "deleted", "project": project_name}
    except Exception as e:
        AuditLogger.log_project_deletion(
            user_context.username,
            project_name,
            False
        )
        logger.error(f"Failed to delete project: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")


async def get_project_stats(http_request: Request):
    """
    Get statistics about all projects.
    
    Args:
        http_request: FastAPI request for authentication
        
    Returns:
        Dict with project statistics
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
 
    
    total_projects = 0
    total_size = 0
    git_repos = 0
    
    try:
        for project_dir in PROJECTS_DIR.iterdir():
            if project_dir.is_dir() and not project_dir.name.startswith("."):
                total_projects += 1
                
                # Get disk usage
                try:
                    import os
                    for root, dirs, files in os.walk(project_dir):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                total_size += os.path.getsize(file_path)
                            except (OSError, PermissionError):
                                continue
                except Exception:
                    pass
                
                # Check if git repo
                if (project_dir / ".git").exists():
                    git_repos += 1
        
        return {
            "total_projects": total_projects,
            "total_size_bytes": total_size,
            "total_size_human": _format_size(total_size),
            "git_repositories": git_repos,
            "non_git_projects": total_projects - git_repos
        }
    except Exception as e:
        logger.error(f"Failed to get project stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get project statistics")


def _format_size(size_bytes: int) -> str:
    """
    Format size in bytes to human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"