"""
Configuration settings for the project management service.
"""

import os
from pathlib import Path

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = Path(os.getenv("LOG_DIR", "./logs"))

# Server
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# Projects
PROJECTS_ROOT = Path(os.getenv("PROJECTS_ROOT", "../micro-vms-projects"))

# Security
MAX_FILE_READ_SIZE = int(os.getenv("MAX_FILE_READ_SIZE", str(10 * 1024 * 1024)))  # 10 MB
MAX_FILE_PREVIEW_SIZE = int(os.getenv("MAX_FILE_PREVIEW_SIZE", str(10 * 1024)))  # 10 KB
MAX_SHELL_TIMEOUT = int(os.getenv("MAX_SHELL_TIMEOUT", "3600"))  # 1 hour
DEFAULT_SHELL_TIMEOUT = int(os.getenv("DEFAULT_SHELL_TIMEOUT", "30"))  # 30 seconds

# Git
GIT_TIMEOUT = int(os.getenv("GIT_TIMEOUT", "300"))  # 5 minutes
GIT_CLONE_TIMEOUT = int(os.getenv("GIT_CLONE_TIMEOUT", "600"))  # 10 minutes

# Concurrent limits
MAX_CONCURRENT_SHELLS = int(os.getenv("MAX_CONCURRENT_SHELLS", "100"))
MAX_PROJECTS = int(os.getenv("MAX_PROJECTS", "1000"))

# GitHub API
GITHUB_API_URL = "https://api.github.com"
GITHUB_API_TIMEOUT = 10

# Validation
MIN_PROJECT_NAME_LENGTH = 1
MAX_PROJECT_NAME_LENGTH = 255

# Features
ENABLE_GITIGNORE_SUPPORT = os.getenv("ENABLE_GITIGNORE_SUPPORT", "true").lower() == "true"
ENABLE_AUDIT_LOGGING = os.getenv("ENABLE_AUDIT_LOGGING", "true").lower() == "true"

def validate_config() -> bool:
    """Validate configuration."""
    try:
        # Check if projects root can be created
        PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
        
        # Check if log directory can be created
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        return True
    except Exception as e:
        print(f"Configuration validation failed: {str(e)}")
        return False