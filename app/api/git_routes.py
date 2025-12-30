"""
Git operations API endpoints.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.core.config import PROJECTS_ROOT
from app.auth.auth import get_user_context, validate_scopes
from app.git.operations import GitOperations
from app.core.audit import AuditLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_name}/git", tags=["git"])

PROJECTS_ROOT_DIR = Path(PROJECTS_ROOT)


def _get_project_path(project_name: str) -> Path:
    """Get project path and validate it exists."""
    project_path = PROJECTS_ROOT_DIR / project_name
    if not project_path.exists() or not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_name}")
    return project_path


@router.get("/status")
async def git_status(
    project_name: str,
    http_request: Request = None
):
    """
    Get git repository status.
    
    Args:
        project_name: Project name
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    git_ops = GitOperations(project_path)
    
    try:
        status = git_ops.get_status()
        logger.info(f"Git status retrieved for {project_name}")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Git status failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pull")
async def git_pull(
    project_name: str,
    remote: str = "origin",
    branch: str = None,
    http_request: Request = None
):
    """
    Pull from remote.
    
    Args:
        project_name: Project name
        remote: Remote name
        branch: Optional branch
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    git_ops = GitOperations(project_path)
    
    try:
        result = git_ops.pull(remote=remote, branch=branch)
        AuditLogger.log_git_operation(
            username=user_context.username,
            project_name=project_name,
            operation="pull",
            success=True
        )
        logger.info(f"Pulled from {remote} in {project_name}")
        return result
    except HTTPException as e:
        AuditLogger.log_git_operation(
            username=user_context.username,
            project_name=project_name,
            operation="pull",
            success=False,
            error=str(e.detail)
        )
        raise
    except Exception as e:
        AuditLogger.log_git_operation(
            username=user_context.username,
            project_name=project_name,
            operation="pull",
            success=False,
            error=str(e)
        )
        logger.error(f"Pull failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add")
async def git_add(
    project_name: str,
    pattern: str = ".",
    http_request: Request = None
):
    """
    Stage files for commit.
    
    Args:
        project_name: Project name
        pattern: File pattern
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    git_ops = GitOperations(project_path)
    
    try:
        result = git_ops.add_files(pattern=pattern)
        logger.info(f"Added files in {project_name}: {pattern}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/commit")
async def git_commit(
    project_name: str,
    message: str,
    author_name: str = None,
    author_email: str = None,
    http_request: Request = None
):
    """
    Commit staged changes.
    
    Args:
        project_name: Project name
        message: Commit message
        author_name: Optional author name
        author_email: Optional author email
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    git_ops = GitOperations(project_path)
    
    try:
        result = git_ops.commit(
            message=message,
            author_name=author_name,
            author_email=author_email
        )
        AuditLogger.log_git_operation(
            username=user_context.username,
            project_name=project_name,
            operation="commit",
            success=True
        )
        logger.info(f"Committed in {project_name}: {message[:50]}")
        return result
    except HTTPException as e:
        AuditLogger.log_git_operation(
            username=user_context.username,
            project_name=project_name,
            operation="commit",
            success=False,
            error=str(e.detail)
        )
        raise
    except Exception as e:
        AuditLogger.log_git_operation(
            username=user_context.username,
            project_name=project_name,
            operation="commit",
            success=False,
            error=str(e)
        )
        logger.error(f"Commit failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/push")
async def git_push(
    project_name: str,
    remote: str = "origin",
    branch: str = None,
    force: bool = False,
    http_request: Request = None
):
    """
    Push to remote.
    
    Args:
        project_name: Project name
        remote: Remote name
        branch: Optional branch
        force: Force push (use with caution)
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    # Check push scope
    validate_scopes(user_context, "push")
    
    project_path = _get_project_path(project_name)
    git_ops = GitOperations(project_path, user_context.token_hash)
    
    try:
        result = git_ops.push(remote=remote, branch=branch, force=force)
        AuditLogger.log_git_operation(
            username=user_context.username,
            project_name=project_name,
            operation="push",
            success=True
        )
        logger.info(f"Pushed to {remote} in {project_name}")
        return result
    except HTTPException as e:
        AuditLogger.log_git_operation(
            username=user_context.username,
            project_name=project_name,
            operation="push",
            success=False,
            error=str(e.detail)
        )
        raise
    except Exception as e:
        AuditLogger.log_git_operation(
            username=user_context.username,
            project_name=project_name,
            operation="push",
            success=False,
            error=str(e)
        )
        logger.error(f"Push failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/checkout")
async def git_checkout(
    project_name: str,
    ref: str,
    http_request: Request = None
):
    """
    Checkout a branch or tag.
    
    Args:
        project_name: Project name
        ref: Branch or tag name
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    git_ops = GitOperations(project_path)
    
    try:
        result = git_ops.checkout(ref=ref)
        AuditLogger.log_git_operation(
            username=user_context.username,
            project_name=project_name,
            operation="checkout",
            success=True
        )
        logger.info(f"Checked out {ref} in {project_name}")
        return result
    except HTTPException as e:
        AuditLogger.log_git_operation(
            username=user_context.username,
            project_name=project_name,
            operation="checkout",
            success=False,
            error=str(e.detail)
        )
        raise
    except Exception as e:
        AuditLogger.log_git_operation(
            username=user_context.username,
            project_name=project_name,
            operation="checkout",
            success=False,
            error=str(e)
        )
        logger.error(f"Checkout failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/modified-files")
async def git_modified_files(
    project_name: str,
    include_staged: bool = True,
    include_unstaged: bool = True,
    http_request: Request = None
):
    """
    Get list of modified files in repository.
    
    Args:
        project_name: Project name
        include_staged: Include staged files
        include_unstaged: Include unstaged files
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    git_ops = GitOperations(project_path)
    
    try:
        result = git_ops.get_modified_files(
            include_staged=include_staged,
            include_unstaged=include_unstaged
        )
        logger.info(f"Retrieved {result['count']} modified files for {project_name}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get modified files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))