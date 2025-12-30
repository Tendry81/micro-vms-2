"""
Custom exceptions for the project management service.
"""

from typing import Optional, Dict, Any
from .models import ErrorCode


class ServiceException(Exception):
    """Base exception for service errors."""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class AuthenticationException(ServiceException):
    """Authentication related errors."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            code=ErrorCode.AUTH_INVALID,
            message=message,
            details=details
        )


class AuthorizationException(ServiceException):
    """Authorization related errors."""
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            code=ErrorCode.AUTH_SCOPE,
            message=message,
            details=details
        )


class PathTraversalException(ServiceException):
    """Path traversal attempt detected."""
    
    def __init__(
        self,
        message: str = "Path traversal detected",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            code=ErrorCode.PATH_TRAVERSAL,
            message=message,
            details=details
        )


class FileTooLargeException(ServiceException):
    """File size exceeds limit."""
    
    def __init__(
        self,
        message: str = "File too large",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            code=ErrorCode.FILE_TOO_LARGE,
            message=message,
            details=details
        )


class ProjectNotFoundException(ServiceException):
    """Project not found."""
    
    def __init__(
        self,
        message: str = "Project not found",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            code=ErrorCode.PROJECT_NOT_FOUND,
            message=message,
            details=details
        )


class GitException(ServiceException):
    """Git operation errors."""
    
    def __init__(
        self,
        message: str = "Git operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            code=ErrorCode.GIT_ERROR,
            message=message,
            details=details
        )


class ShellExecutionException(ServiceException):
    """Shell execution errors."""
    
    def __init__(
        self,
        message: str = "Shell execution failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            code=ErrorCode.SHELL_DENIED,
            message=message,
            details=details
        )


class ValidationException(ServiceException):
    """Request validation errors."""
    
    def __init__(
        self,
        message: str = "Invalid request",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            code=ErrorCode.INVALID_REQUEST,
            message=message,
            details=details
        )