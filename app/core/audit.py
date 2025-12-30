"""
Logging and auditing module for security and compliance.
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Configure logging with file and console output
def setup_logging(log_dir: str = "./logs") -> None:
    """
    Set up comprehensive logging with file and console handlers.
    
    Args:
        log_dir: Directory for log files
    """
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = logging.FileHandler(log_path / "service.log")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Audit handler for security events
    audit_handler = logging.FileHandler(log_path / "audit.log")
    audit_handler.setLevel(logging.INFO)
    audit_formatter = logging.Formatter(
        '%(asctime)s - AUDIT - %(message)s'
    )
    audit_handler.setFormatter(audit_formatter)
    
    # Create audit logger
    audit_logger = logging.getLogger("audit")
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)


class AuditLogger:
    """Audit logger for security events."""
    
    _logger = logging.getLogger("audit")
    
    @classmethod
    def log_authentication_attempt(
        cls,
        username: Optional[str],
        success: bool,
        reason: Optional[str] = None
    ) -> None:
        """
        Log authentication attempt.
        
        Args:
            username: GitHub username or None
            success: Whether authentication succeeded
            reason: Failure reason if applicable
        """
        event = {
            "event": "authentication_attempt",
            "username": username,
            "success": success,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        cls._logger.info(json.dumps(event))
    
    @classmethod
    def log_project_creation(
        cls,
        username: str,
        project_name: str,
        repo_url: str,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """
        Log project creation event.
        
        Args:
            username: User who created project
            project_name: Project name
            repo_url: Repository URL
            success: Whether creation succeeded
            error: Error message if failed
        """
        event = {
            "event": "project_creation",
            "username": username,
            "project_name": project_name,
            "repo_url": repo_url,
            "success": success,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        cls._logger.info(json.dumps(event))
    
    @classmethod
    def log_project_deletion(
        cls,
        username: str,
        project_name: str,
        success: bool
    ) -> None:
        """
        Log project deletion event.
        
        Args:
            username: User who deleted project
            project_name: Project name
            success: Whether deletion succeeded
        """
        event = {
            "event": "project_deletion",
            "username": username,
            "project_name": project_name,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        cls._logger.info(json.dumps(event))
    
    @classmethod
    def log_shell_execution(
        cls,
        username: str,
        project_name: str,
        command: str,
        exit_code: int,
        success: bool
    ) -> None:
        """
        Log shell command execution.
        
        Args:
            username: User who executed command
            project_name: Project name
            command: Command executed (truncated)
            exit_code: Command exit code
            success: Whether execution succeeded
        """
        # Truncate command for logging
        cmd_display = command[:100] if len(command) > 100 else command
        
        event = {
            "event": "shell_execution",
            "username": username,
            "project_name": project_name,
            "command": cmd_display,
            "exit_code": exit_code,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        cls._logger.info(json.dumps(event))
    
    @classmethod
    def log_git_operation(
        cls,
        username: str,
        project_name: str,
        operation: str,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """
        Log git operation.
        
        Args:
            username: User who performed operation
            project_name: Project name
            operation: Git operation (push, pull, commit, etc)
            success: Whether operation succeeded
            error: Error message if failed
        """
        event = {
            "event": "git_operation",
            "username": username,
            "project_name": project_name,
            "operation": operation,
            "success": success,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        cls._logger.info(json.dumps(event))
    
    @classmethod
    def log_security_event(
        cls,
        username: str,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "warning"
    ) -> None:
        """
        Log security event.
        
        Args:
            username: User involved
            event_type: Type of security event
            details: Additional details
            severity: Event severity (info, warning, critical)
        """
        event = {
            "event": "security_event",
            "event_type": event_type,
            "username": username,
            "details": details,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }
        cls._logger.info(json.dumps(event))


# Create default logger
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)