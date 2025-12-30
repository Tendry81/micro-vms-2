"""
API endpoints module.
"""

from .main import app
from .projects_routes import router as projects_router
from .filesystem_routes import router as filesystem_router
from .git_routes import router as git_router
from .shell_routes import router as shell_router