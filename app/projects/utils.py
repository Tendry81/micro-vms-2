"""
Utility functions for project management.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from app.core.models import ProjectMetadata

logger = logging.getLogger(__name__)


def validate_project_name(name: str) -> bool:
    """
    Validate project name is filesystem-safe.
    
    Args:
        name: Project name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not name or len(name.strip()) == 0:
        return False
    
    # Disallow dangerous characters
    dangerous_chars = {'/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0'}
    if any(c in name for c in dangerous_chars):
        return False
    
    # Disallow reserved names (Windows)
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    if name.upper() in reserved_names:
        return False
    
    # Basic length check
    if len(name) > 255:
        return False
    
    return True


def get_disk_usage(path: Path) -> int:
    """
    Calculate directory disk usage in bytes.
    
    Args:
        path: Directory path
        
    Returns:
        Total size in bytes
    """
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except (OSError, PermissionError):
                    # Skip files we can't access
                    continue
    except Exception as e:
        logger.error(f"Failed to calculate disk usage for {path}: {str(e)}")
    return total


def get_project_metadata(project_path: Path, project_name: str) -> ProjectMetadata:
    """
    Get metadata for a project.
    
    Args:
        project_path: Path to project directory
        project_name: Name of the project
        
    Returns:
        ProjectMetadata object
    """
    try:
        stat = project_path.stat()
        last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
    except Exception as e:
        logger.error(f"Failed to get stats for {project_path}: {str(e)}")
        last_modified = datetime.now().isoformat()
    
    try:
        disk_usage = get_disk_usage(project_path)
    except Exception as e:
        logger.error(f"Failed to calculate disk usage for {project_path}: {str(e)}")
        disk_usage = 0
    
    try:
        is_git_repo = (project_path / ".git").exists()
    except Exception:
        is_git_repo = False
    
    return ProjectMetadata(
        name=project_name,
        path=str(project_path),
        disk_usage_bytes=disk_usage,
        last_modified=last_modified,
        is_git_repo=is_git_repo
    )


def sanitize_project_name(name: str) -> str:
    """
    Sanitize project name by removing/replacing unsafe characters.
    
    Args:
        name: Raw project name
        
    Returns:
        Sanitized project name
    """
    import re
    
    # Replace dangerous characters with underscores
    dangerous_chars = r'[\/:*?"<>|\0]'
    sanitized = re.sub(dangerous_chars, '_', name)
    
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')
    
    # Replace multiple underscores with single one
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Ensure not empty
    if not sanitized:
        sanitized = "unnamed_project"
    
    # Truncate if too long
    if len(sanitized) > 255:
        sanitized = sanitized[:252] + "..."
    
    return sanitized


def check_disk_space(path: Path, required_bytes: int = 0) -> bool:
    """
    Check if there's enough disk space.
    
    Args:
        path: Path to check disk space for
        required_bytes: Bytes required (0 for just checking)
        
    Returns:
        True if enough space available
    """
    try:
        import shutil
        total, used, free = shutil.disk_usage(path)
        return free >= required_bytes
    except Exception as e:
        logger.error(f"Failed to check disk space: {str(e)}")
        return True  # Assume enough space if check fails


def validate_repo_url(url: str) -> bool:
    """
    Validate repository URL.
    
    Args:
        url: Repository URL
        
    Returns:
        True if URL is valid
    """
    if not url:
        return False
    
    # Check if it's a GitHub HTTPS URL
    if url.startswith("https://github.com/"):
        # Basic pattern for GitHub URLs
        import re
        pattern = r'^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(/.*)?$'
        return bool(re.match(pattern, url))
    
    # Allow other HTTPS URLs for flexibility
    elif url.startswith("https://"):
        return True
    
    return False