"""
Authentication and authorization module for GitHub token validation.
"""

import hashlib
import logging
from typing import Optional
from dataclasses import dataclass

import requests
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.audit import AuditLogger

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"


@dataclass
class UserContext:
    """Authenticated user context from GitHub."""
    username: str
    user_id: int
    scopes: list[str]
    token_hash: str


async def validate_github_token(token: str) -> UserContext:
    """
    Validate GitHub Personal Access Token with GitHub API.
    
    Args:
        token: GitHub PAT
        
    Returns:
        UserContext with user info and scopes
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        headers = {"Authorization": f"token {token}"}
        response = requests.get(f"{GITHUB_API_URL}/user", headers=headers, timeout=10)
        
        if response.status_code == 401:
            AuditLogger.log_authentication_attempt(None, False, "Invalid or expired token")
            raise HTTPException(status_code=401, detail="Invalid or expired GitHub token")
        
        if response.status_code != 200:
            logger.error(f"GitHub API error: {response.status_code}")
            raise HTTPException(status_code=401, detail="Failed to validate token")
        
        user_data = response.json()
        
        # Extract scopes from response headers
        scopes_header = response.headers.get("X-OAuth-Scopes", "")
        scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]
        
        # Create token hash for auditing (SHA256 of token)
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        
        user_context = UserContext(
            username=user_data.get("login", ""),
            user_id=user_data.get("id", 0),
            scopes=scopes,
            token_hash=token_hash
        )
        
        AuditLogger.log_authentication_attempt(user_context.username, True)
        logger.info(f"User authenticated: {user_context.username} (scopes: {scopes})")
        return user_context
        
    except requests.RequestException as e:
        logger.error(f"GitHub API request failed: {str(e)}")
        raise HTTPException(status_code=503, detail="GitHub API unavailable")


async def extract_token_from_header(request: Request) -> str:
    """
    Extract GitHub token from Authorization header.
    
    Args:
        request: FastAPI request
        
    Returns:
        Token string
        
    Raises:
        HTTPException: If no valid token provided
    """
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header format")
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Use: 'Authorization: token <github_pat>'"
        )
    
    token = auth_header[6:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token provided")
    
    return token


async def get_user_context(request: Request) -> UserContext:
    """
    Extract and validate user context from request.
    
    Args:
        request: FastAPI request
        
    Returns:
        Authenticated UserContext
        
    Raises:
        HTTPException: If authentication fails
    """
    token = await extract_token_from_header(request)
    return await validate_github_token(token)


def check_required_scopes(user_context: UserContext, required_scopes: list[str]) -> bool:
    """
    Check if user token has required scopes.
    
    Args:
        user_context: User context
        required_scopes: List of required scope strings
        
    Returns:
        True if all required scopes present
    """
    user_scopes = set(user_context.scopes)
    return all(scope in user_scopes for scope in required_scopes)


def validate_scopes(user_context: UserContext, operation: str) -> None:
    """
    Validate user has required scopes for operation.
    
    Args:
        user_context: User context
        operation: Operation type (clone_private, push, etc)
        
    Raises:
        HTTPException: If insufficient scopes
    """
    scope_requirements = {
        "clone_private": ["repo"],
        "push": ["repo"],
        "user_info": ["read:user"],
    }
    
    required = scope_requirements.get(operation, [])
    if required and not check_required_scopes(user_context, required):
        logger.warning(f"Insufficient scopes for {operation}: {user_context.scopes}")
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient scopes for this operation. Required: {required}"
        )