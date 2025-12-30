"""
Shell execution API endpoints for non-interactive and interactive terminal access.
FIXED: WebSocket endpoint now supports terminal_id as room name for multi-client connections.
"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from app.core.config import PROJECTS_ROOT
from app.auth.auth import get_user_context
from app.core.models import ShellExecuteRequest, TerminalResizeRequest
from app.shell.executor import ShellExecutor, InteractiveTerminal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_name}/shell", tags=["shell"])

PROJECTS_ROOT_DIR = Path(PROJECTS_ROOT)


def _get_project_path(project_name: str) -> Path:
    """Get project path and validate it exists."""
    project_path = PROJECTS_ROOT_DIR / project_name
    if not project_path.exists() or not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_name}")
    return project_path


@router.post("/execute")
async def execute_command(
    body: ShellExecuteRequest,
    http_request: Request = None
):
    """
    Execute a shell command.
    
    Args:
        project_name: Project name
        command: Shell command to execute
        timeout: Command timeout in seconds
        cwd: Working directory relative to project root
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    if not body.command or len(body.command.strip()) == 0:
        raise HTTPException(status_code=400, detail="Command cannot be empty")
    
    if body.timeout < 1 or body.timeout > 3600:
        raise HTTPException(status_code=400, detail="Timeout must be between 1 and 3600 seconds")
    
    project_path = _get_project_path(body.project_name)
    executor = ShellExecutor(project_path)
    
    try:
        logger.info(f"Executing command in {body.project_name}: {body.command[:100]}")
        result = await executor.execute(
            command=body.command,
            username=user_context.username,
            project_name=body.project_name,
            timeout=body.timeout,
            cwd=''
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Command execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# FIXED: Added terminal_id parameter to support room-based connections
@router.websocket("/terminal/{terminal_id}")
async def websocket_terminal(
    project_name: str,
    terminal_id: str,  # NEW: Terminal ID from URL path
    websocket: WebSocket,
    http_request: Request = None
):
    """
    WebSocket endpoint for interactive terminal access.
    
    ENHANCED: Supports room-based terminal connections where multiple clients
    can connect to the same terminal_id and share the same terminal session.
    
    Args:
        project_name: Project name
        terminal_id: Terminal session ID (room name) - from URL path
        websocket: WebSocket connection
        http_request: FastAPI request for authentication
    
    URL Pattern: /projects/{project_name}/shell/terminal/{terminal_id}
    Example: /projects/bible/shell/terminal/term-1766922382929-1eih7kapf
    """
    
    logger.info(f"=" * 70)
    logger.info(f"WebSocket Terminal Connection Request")
    logger.info(f"  Project: {project_name}")
    logger.info(f"  Terminal ID: {terminal_id}")
    logger.info(f"  Client: {websocket.client.host}:{websocket.client.port}")
    logger.info(f"=" * 70)
    
    # Validate project exists
    project_path = PROJECTS_ROOT_DIR / project_name
    if not project_path.exists():
        logger.error(f"Project not found: {project_name}")
        await websocket.close(code=1008, reason="Project not found")
        return
    
    # Note: Authentication for WebSocket happens after accept
    # This is a limitation of FastAPI WebSocket handling
    # You can add token-based auth via query params if needed
    
    try:
        # Get or create terminal for this room
        # This uses the refactored room-based architecture
        terminal = await InteractiveTerminal.get_or_create(
            terminal_id=terminal_id,
            project_root=project_path
        )
        
        logger.info(f"Terminal instance ready for room: {terminal_id}")
        
        # Connect this client to the terminal room
        # This will:
        # 1. Accept the WebSocket connection
        # 2. Add client to the room
        # 3. Share terminal process with other clients in the same room
        # 4. Block until this client disconnects
        await terminal.connect_client(websocket)
        
        logger.info(f"Client disconnected normally from room: {terminal_id}")
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {terminal_id}")
    except Exception as e:
        logger.error(f"WebSocket error in {terminal_id}: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass


# LEGACY ENDPOINT: Keep for backward compatibility if needed
# You can remove this if you're not using it
@router.websocket("/terminal")
async def websocket_terminal_legacy(
    project_name: str,
    websocket: WebSocket,
    http_request: Request = None,
    id: str = None  # Optional query parameter: ?id=terminal-123
):
    """
    LEGACY WebSocket endpoint (backward compatibility).
    
    This endpoint generates a random session ID if not provided via query param.
    NEW CLIENTS SHOULD USE: /terminal/{terminal_id} instead
    
    Args:
        project_name: Project name
        websocket: WebSocket connection
        http_request: FastAPI request for authentication
        id: Optional terminal ID from query parameter
    
    URL Pattern: /projects/{project_name}/shell/terminal?id={terminal_id}
    """
    
    # Use provided ID or generate new one
    terminal_id = id if id else str(uuid.uuid4())
    
    logger.info(f"Legacy WebSocket connection: {project_name} / {terminal_id}")
    
    project_path = PROJECTS_ROOT_DIR / project_name
    if not project_path.exists():
        await websocket.close(code=1008, reason="Project not found")
        return
    
    try:
        # Use the new room-based architecture
        terminal = await InteractiveTerminal.get_or_create(
            terminal_id=terminal_id,
            project_root=project_path
        )
        
        await terminal.connect_client(websocket)
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {terminal_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass


@router.get("/terminals")
async def list_terminals(
    project_name: str,
    http_request: Request = None
):
    """
    List active terminal sessions.
    
    Returns information about all active terminals including:
    - terminal_id: The unique ID (room name)
    - connection_count: Number of clients connected to this terminal
    - has_process: Whether the terminal process is running
    
    Args:
        project_name: Project name
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    
    # Get terminals with enhanced info (connection counts, etc.)
    terminals = InteractiveTerminal.list_terminals()
    
    return {
        "project": project_name,
        "terminals": terminals,
        "count": len(terminals)
    }
    
@router.post("/resize/{terminal_id}")
async def resize_terminal(
    project_name: str,
    terminal_id: str,
    resize_data: TerminalResizeRequest,  # Changed: accept body data
    http_request: Request = None
):
    """
    Resize an interactive terminal session.
    
    Args:
        project_name: Project name
        terminal_id: Terminal session ID
        resize_data: Resize dimensions (cols and rows)
        http_request: FastAPI request for authentication
    """
    # Authenticate user
    user_context = await get_user_context(http_request)
    
    project_path = _get_project_path(project_name)
    
    try:
        terminal = InteractiveTerminal.get_or_create(terminal_id, project_path)
        if not terminal:
            raise HTTPException(status_code=404, detail="Terminal not found")
        
        terminal.resize(resize_data.cols, resize_data.rows)  # Changed: access from model
        logger.info(f"Resized terminal {terminal_id} to {resize_data.cols}x{resize_data.rows}")
        return {
            "status": "success", 
            "terminal_id": terminal_id, 
            "cols": resize_data.cols, 
            "rows": resize_data.rows
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resize failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))