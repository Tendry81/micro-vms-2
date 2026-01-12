"""
Filesystem API endpoints for file and directory operations.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.core.config import PROJECTS_ROOT
from app.auth.auth import get_user_context
from app.filesystem.operations import FilesystemOperations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_name}/files", tags=["filesystem"])

PROJECTS_ROOT_DIR = Path(PROJECTS_ROOT)


def _get_project_path(project_name: str) -> Path:
    """Get project path and validate it exists."""
    project_path = PROJECTS_ROOT_DIR / project_name
    if not project_path.exists() or not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_name}")
    return project_path


@router.get("/list")
async def list_files(
    project_name: str,
    path: str = ".",
    recursive: bool = False,
    include_ignored: bool = False,
    http_request: Request = None
):
    """
    List directory contents.
    
    Args:
        project_name: Project name
        path: Path within project
        recursive: List recursively
        include_ignored: Include ignored files
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    fs_ops = FilesystemOperations(project_path)
    
    try:
        response = fs_ops.list_directory(
            path=path,
            recursive=recursive,
            include_ignored=include_ignored
        )
        logger.info(f"Listed {response.count} entries in {project_name}/{path}")
        return response.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/read")
async def read_file(
    project_name: str,
    path: str,
    preview: bool = False,
    http_request: Request = None
):
    """
    Read file contents.
    
    Args:
        project_name: Project name
        path: File path relative to project
        preview: Return only first 10KB
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    fs_ops = FilesystemOperations(project_path)
    
    try:
        response = fs_ops.read_file(path=path, preview=preview)
        logger.info(f"Read file: {project_name}/{path}")
        return response.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Read failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-file")
async def create_file(
    project_name: str,
    path: str,
    content: str = None,
    overwrite: bool = False,
    http_request: Request = None
):
    """
    Create a file.
    
    Args:
        project_name: Project name
        path: File path relative to project
        content: Optional file content
        overwrite: Allow overwriting
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    fs_ops = FilesystemOperations(project_path)
    
    try:
        response = fs_ops.create_file(
            path=path,
            content=content,
            overwrite=overwrite
        )
        logger.info(f"Created file: {project_name}/{path}")
        return response.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-directory")
async def create_directory(
    project_name: str,
    path: str,
    parents: bool = True,
    http_request: Request = None
):
    """
    Create a directory.
    
    Args:
        project_name: Project name
        path: Directory path relative to project
        parents: Create parent directories
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    fs_ops = FilesystemOperations(project_path)
    
    try:
        response = fs_ops.create_directory(path=path, parents=parents)
        logger.info(f"Created directory: {project_name}/{path}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Directory creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete")
async def delete_path(
    project_name: str,
    path: str,
    recursive: bool = False,
    http_request: Request = None
):
    """
    Delete a file or directory.
    
    Args:
        project_name: Project name
        path: Path relative to project
        recursive: Allow recursive deletion
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    fs_ops = FilesystemOperations(project_path)
    
    try:
        response = fs_ops.delete_path(path=path, recursive=recursive)
        logger.info(f"Deleted: {project_name}/{path}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deletion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/upload")
async def upload_file(
    project_name: str,
    path: str,
    http_request: Request = None):
    """
    Upload a file to the project.
    Args:
        project_name: Project name
        path: File path relative to project
        http_request: FastAPI request for authentication
    # Authenticate user
    user_context = await get_user_context(http_request)
    """
    project_path = _get_project_path(project_name)
    fs_ops = FilesystemOperations(project_path)
    try:
        files = await http_request.form()
        upload_file = files.get("files")
        response = fs_ops.upload_file(path=path, file=upload_file)
        logger.info(f"Uploaded file: {project_name}/{path}")
        return response.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 