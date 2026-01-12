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
    Upload file(s) to a folder in the project.
    
    Args:
        project_name: Project name
        path: Folder path relative to project (where files will be created)
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    fs_ops = FilesystemOperations(project_path)
    
    try:
        form_data = await http_request.form()
        
        # Get files from formdata - support both single and multiple files
        # Clients can send either:
        # - Single file: "files" (UploadFile)
        # - Multiple files: "files[]" (List[UploadFile])
        files = []
        
        # Check for multiple files format (files[])
        if "files[]" in form_data:
            files_list = form_data.getlist("files[]")
            files = files_list
        # Check for single file format (files)
        elif "files" in form_data:
            single_file = form_data.get("files")
            files = [single_file]
        else:
            raise HTTPException(
                status_code=400, 
                detail="No files provided. Use 'files' or 'files[]' form field."
            )
        
        if not files:
            raise HTTPException(status_code=400, detail="No valid files provided")
        
        responses = []
        
        for uploaded_file in files:
            try:
                # Create full path for each file: folder/filename
                # Sanitize filename
                import os
                filename = uploaded_file.filename
                filename = os.path.basename(filename)  # Remove path components
                
                # Handle empty or malformed filename
                if not filename:
                    filename = f"file_{len(responses)}"
                
                # Build full path
                if path.endswith('/'):
                    full_path = f"{path}{filename}"
                else:
                    full_path = f"{path}/{filename}"
                
                # Upload the file
                response = fs_ops.upload_file(path=full_path, file=uploaded_file)
                
                # Add response with filename
                response_data = response.dict()
                response_data["filename"] = filename
                responses.append(response_data)
                
                logger.info(f"Uploaded file: {project_name}/{full_path}")
                
            except HTTPException as e:
                # Continue with other files if one fails
                filename = getattr(uploaded_file, 'filename', 'unknown')
                logger.warning(f"Failed to upload {filename}: {e.detail}")
                responses.append({
                    "filename": filename,
                    "uploaded": False,
                    "error": e.detail,
                    "size_bytes": 0
                })
            except Exception as e:
                filename = getattr(uploaded_file, 'filename', 'unknown')
                logger.error(f"Unexpected error uploading {filename}: {str(e)}")
                responses.append({
                    "filename": filename,
                    "uploaded": False,
                    "error": "Internal server error",
                    "size_bytes": 0
                })
        
        # Return appropriate response format
        if len(responses) == 1:
            # For single file, return the response directly (backward compatible)
            return responses[0]
        else:
            return {
                "total_files": len(files),
                "successful": len([r for r in responses if r.get("uploaded", False)]),
                "failed": len([r for r in responses if not r.get("uploaded", False)]),
                "files": responses
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))