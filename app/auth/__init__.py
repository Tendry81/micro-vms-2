"""
Authentication and authorization module for GitHub token validation.
"""

from .auth import (
    UserContext,
    validate_github_token,
    extract_token_from_header,
    get_user_context,
    check_required_scopes,
    validate_scopes
)