"""
Common models, error handling, and utilities for the project management service.
"""

from enum import Enum
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from dataclasses import dataclass


# ============================================================================
# Error Models & Codes
# ============================================================================

class ErrorCode(str, Enum):
    """Stable error identifiers."""
    AUTH_INVALID = "AUTH_INVALID"
    AUTH_SCOPE = "AUTH_SCOPE"
    PATH_TRAVERSAL = "PATH_TRAVERSAL"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    SHELL_DENIED = "SHELL_DENIED"
    GIT_ERROR = "GIT_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorResponse(BaseModel):
    """Standard error response model."""
    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None


class FileUploadResponse(BaseModel):
    """Response after uploading a file."""
    path: str
    uploaded: bool
    size_bytes: int


# ============================================================================
# Project Models
# ============================================================================

class ProjectCreateRequest(BaseModel):
    """Request to create a new project."""
    project_name: str = Field(..., min_length=1, max_length=255)
    repo_url: str = Field(..., description="HTTPS GitHub repository URL")
    branch: Optional[str] = Field(None, description="Optional branch or tag")


class ProjectMetadata(BaseModel):
    """Project metadata."""
    name: str
    path: str
    disk_usage_bytes: int
    last_modified: str  # ISO 8601
    is_git_repo: bool


class ProjectListResponse(BaseModel):
    """Response for listing projects."""
    projects: list[ProjectMetadata]
    count: int


# ============================================================================
# Filesystem Models
# ============================================================================

class FileEntry(BaseModel):
    """Represents a file or directory entry."""
    name: str
    path: str
    type: str  # "file" or "directory"
    size_bytes: Optional[int] = None
    modified: str  # ISO 8601
    is_ignored: bool = False


class DirectoryListResponse(BaseModel):
    """Response for directory listing."""
    entries: list[FileEntry]
    recursive: bool
    count: int


class FileReadRequest(BaseModel):
    """Request to read a file."""
    path: str
    preview: bool = False  # If True, only return first 10KB


class FileReadResponse(BaseModel):
    """Response containing file content."""
    path: str
    content: str
    size_bytes: int
    preview: bool
    truncated: bool


class FileCreateRequest(BaseModel):
    """Request to create a file."""
    path: str
    content: Optional[str] = None
    overwrite: bool = False


class FileCreateResponse(BaseModel):
    """Response after file creation."""
    path: str
    created: bool
    size_bytes: int


class DirectoryCreateRequest(BaseModel):
    """Request to create a directory."""
    path: str
    parents: bool = True  # Create parent directories


class FileDeletionRequest(BaseModel):
    """Request to delete a file or directory."""
    path: str
    recursive: bool = False


# ============================================================================
# Git Models
# ============================================================================

class GitStatusResponse(BaseModel):
    """Git repository status."""
    branch: str
    modified_files: list[str]
    untracked_files: list[str]
    commits_ahead: int = 0
    commits_behind: int = 0


class GitPullRequest(BaseModel):
    """Request to pull from remote."""
    remote: str = "origin"
    branch: Optional[str] = None


class GitPullResponse(BaseModel):
    """Response after git pull."""
    status: str  # "success" or error message
    files_changed: int
    insertions: int
    deletions: int


class GitCommitRequest(BaseModel):
    """Request to commit changes."""
    message: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None


class GitPushRequest(BaseModel):
    """Request to push to remote."""
    remote: str = "origin"
    branch: Optional[str] = None
    force: bool = False


class GitCheckoutRequest(BaseModel):
    """Request to checkout branch/tag."""
    ref: str  # branch or tag name


# ============================================================================
# Shell Models
# ============================================================================

class ShellExecuteRequest(BaseModel):
    """Request to execute a shell command."""
    project_name: str
    command: str
    timeout: int = 30  # seconds
    cwd: Optional[str] = None  # Relative to project root


class ShellExecuteResponse(BaseModel):
    """Response from shell command execution."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    
class TerminalResizeRequest(BaseModel):
    cols: int
    rows: int