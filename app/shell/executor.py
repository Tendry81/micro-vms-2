"""
Shell command execution module with non-interactive and interactive (WebSocket) support.
Cross-platform implementation for Windows and Unix systems.

ENHANCEMENTS:
- Terminal IDs managed as rooms, allowing multiple WebSocket connections
- Connection manager for broadcasting to all clients in a terminal room
- Proper WebSocket binary/text handling
- Better error handling for receive operations
"""

import asyncio
import logging
import subprocess
import threading
import time
import uuid
import os
import queue
import signal
import platform
from pathlib import Path
from typing import Optional, Dict, Any, Set, List

from fastapi import HTTPException, WebSocket, WebSocketDisconnect

# Platform-specific imports
IS_WINDOWS = platform.system() == 'Windows'

if not IS_WINDOWS:
    import select
    import fcntl
    import pty
    import termios
    import struct
else:
    # Windows-specific imports
    try:
        import msvcrt
    except ImportError:
        pass

logger = logging.getLogger(__name__)


class ShellExecutor:
    """Non-interactive shell command execution (cross-platform)."""
    
    def __init__(self, project_root: Path):
        """Initialize executor with project root."""
        self.project_root = project_root
    
    async def execute(
        self,
        command: str,
        username: str,
        project_name: str,
        timeout: int = 30,
        cwd: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a shell command in project context.
        
        Args:
            command: Shell command to execute
            username: User executing the command
            project_name: Project name
            timeout: Execution timeout in seconds
            cwd: Working directory relative to project root
            
        Returns:
            Execution result dict
            
        Raises:
            HTTPException: If command fails or times out
        """
        # Validate cwd
        if cwd:
            if cwd.startswith("/") or (IS_WINDOWS and cwd[1:3] == ":\\"):
                raise HTTPException(status_code=400, detail="Absolute paths not allowed")
            working_dir = self.project_root / cwd
            try:
                working_dir.relative_to(self.project_root)
            except ValueError:
                raise HTTPException(status_code=403, detail="Path traversal detected")
        else:
            working_dir = self.project_root
        
        logger.info(f"Executing command: {command}")
        
        start_time = time.time()
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    self._run_command,
                    command,
                    working_dir
                ),
                timeout=timeout
            )
            duration = time.time() - start_time
            
            success = result["exit_code"] == 0
            
            # Log audit (you'll need to implement AuditLogger or remove this)
            try:
                from app.core.audit import AuditLogger
                AuditLogger.log_shell_execution(
                    username=username,
                    project_name=project_name,
                    command=command,
                    exit_code=result["exit_code"],
                    success=success
                )
            except ImportError:
                logger.info(f"Audit: user={username}, project={project_name}, success={success}")
            
            return {
                "command": command,
                "exit_code": result["exit_code"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "duration_seconds": duration
            }
        except asyncio.TimeoutError:
            logger.error(f"Command timeout: {command}")
            raise HTTPException(status_code=408, detail="Command execution timed out")
        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")
    
    @staticmethod
    def _run_command(command: str, cwd: Path) -> Dict[str, Any]:
        """
        Run command in subprocess.
        
        Args:
            command: Shell command
            cwd: Working directory
            
        Returns:
            Result dict
        """
        try:
            # Choose shell based on platform
            if IS_WINDOWS:
                shell_executable = True
                # Auto-confirm with 'y' for expo prompts on Windows
                if 'expo' in command:
                    result = subprocess.run(
                        command,
                        shell=True,
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        timeout=300,
                        input='y\n'
                    )
                else:
                    result = subprocess.run(
                        command,
                        shell=True,
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
            else:
                # Unix
                if 'expo' in command:
                    result = subprocess.run(
                        command,
                        shell=True,
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        timeout=300,
                        input='y\n'
                    )
                else:
                    result = subprocess.run(
                        command,
                        shell=True,
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
            
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": "Command timed out"
            }


# ============================================================================
# Connection Manager for Terminal Rooms
# ============================================================================

class TerminalConnectionManager:
    """
    Manages WebSocket connections for terminal rooms.
    Each terminal_id represents a room that can have multiple connected clients.
    """
    
    def __init__(self):
        """Initialize connection manager."""
        self._rooms: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, terminal_id: str, websocket: WebSocket) -> None:
        """
        Add a WebSocket connection to a terminal room.
        
        Args:
            terminal_id: Terminal session ID (room name)
            websocket: WebSocket connection to add
        """
        async with self._lock:
            if terminal_id not in self._rooms:
                self._rooms[terminal_id] = set()
            self._rooms[terminal_id].add(websocket)
            logger.info(f"Client connected to terminal room '{terminal_id}'. Total clients: {len(self._rooms[terminal_id])}")
    
    async def disconnect(self, terminal_id: str, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection from a terminal room.
        
        Args:
            terminal_id: Terminal session ID (room name)
            websocket: WebSocket connection to remove
        """
        async with self._lock:
            if terminal_id in self._rooms:
                self._rooms[terminal_id].discard(websocket)
                remaining = len(self._rooms[terminal_id])
                logger.info(f"Client disconnected from terminal room '{terminal_id}'. Remaining clients: {remaining}")
                
                # Clean up empty rooms
                if not self._rooms[terminal_id]:
                    del self._rooms[terminal_id]
                    logger.info(f"Terminal room '{terminal_id}' is now empty and removed")
    
    async def broadcast(self, terminal_id: str, message: str) -> None:
        """
        Broadcast a message to all clients in a terminal room.
        
        Args:
            terminal_id: Terminal session ID (room name)
            message: Message to broadcast
        """
        async with self._lock:
            if terminal_id not in self._rooms:
                return
            
            # Get a copy of connections to avoid modification during iteration
            connections = list(self._rooms[terminal_id])
        
        # Broadcast outside the lock to avoid blocking
        dead_connections = []
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.debug(f"Failed to send to client in room '{terminal_id}': {str(e)}")
                dead_connections.append(websocket)
        
        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                if terminal_id in self._rooms:
                    for ws in dead_connections:
                        self._rooms[terminal_id].discard(ws)
    
    def get_room_size(self, terminal_id: str) -> int:
        """
        Get the number of connections in a terminal room.
        
        Args:
            terminal_id: Terminal session ID (room name)
            
        Returns:
            Number of active connections
        """
        return len(self._rooms.get(terminal_id, set()))
    
    def list_rooms(self) -> List[Dict[str, Any]]:
        """
        List all active terminal rooms with connection counts.
        
        Returns:
            List of room information
        """
        return [
            {
                "terminal_id": terminal_id,
                "connection_count": len(connections)
            }
            for terminal_id, connections in self._rooms.items()
        ]
    
    def has_connections(self, terminal_id: str) -> bool:
        """
        Check if a terminal room has any active connections.
        
        Args:
            terminal_id: Terminal session ID (room name)
            
        Returns:
            True if room has connections, False otherwise
        """
        return terminal_id in self._rooms and len(self._rooms[terminal_id]) > 0


# Global connection manager instance
connection_manager = TerminalConnectionManager()


# ============================================================================
# Unix Terminal Implementation
# ============================================================================

if not IS_WINDOWS:
    class UnixTerminalProcessManager:
        """Manages terminal processes in separate threads (Unix only)."""
        
        _instances: Dict[str, 'UnixTerminalProcessManager'] = {}
        _lock = threading.Lock()
        
        def __init__(self, terminal_id: str, project_root: Path):
            """Initialize terminal process manager."""
            self.terminal_id = terminal_id
            self.project_root = project_root
            self.master_fd: Optional[int] = None
            self.slave_fd: Optional[int] = None
            self.process: Optional[subprocess.Popen] = None
            self.output_queue: queue.Queue = queue.Queue()
            self.input_queue: queue.Queue = queue.Queue()
            self.running = False
            self.error: Optional[str] = None
            self.reader_thread: Optional[threading.Thread] = None
            self.writer_thread: Optional[threading.Thread] = None
        
        def start(self) -> None:
            """Start terminal process."""
            try:
                # Create PTY
                self.master_fd, self.slave_fd = pty.openpty()
                
                # Configure terminal attributes for interactive shell
                attrs = termios.tcgetattr(self.slave_fd)
                
                # Enable ECHO so typed characters are visible
                attrs[3] = attrs[3] | termios.ECHO
                
                # Set other terminal flags for proper interactive behavior
                # ICANON: Enable canonical mode (line buffering)
                # ECHOE: Echo erase character as backspace
                # ECHOK: Echo newline after kill character
                # ECHONL: Echo newline
                attrs[3] = attrs[3] | termios.ICANON | termios.ECHOE | termios.ECHOK
                
                termios.tcsetattr(self.slave_fd, termios.TCSANOW, attrs)
                
                # Set non-blocking on master side
                flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
                fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                
                # Get default shell
                shell = os.environ.get('SHELL', '/bin/bash')
                
                # Start shell process
                self.process = subprocess.Popen(
                    [shell],
                    stdin=self.slave_fd,
                    stdout=self.slave_fd,
                    stderr=self.slave_fd,
                    cwd=str(self.project_root),
                    start_new_session=True
                )
                
                self.running = True
                
                # Register instance
                with UnixTerminalProcessManager._lock:
                    UnixTerminalProcessManager._instances[self.terminal_id] = self
                
                # Start reader and writer threads
                self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
                self.writer_thread = threading.Thread(target=self._write_loop, daemon=True)
                self.reader_thread.start()
                self.writer_thread.start()
                
                logger.info(f"Unix terminal process started: {self.terminal_id}")
                
            except Exception as e:
                self.error = str(e)
                self.running = False
                logger.error(f"Failed to start Unix terminal: {str(e)}")
                raise
        
        def _read_loop(self) -> None:
            """Read from terminal in separate thread."""
            try:
                while self.running:
                    try:
                        # Use select for non-blocking read
                        ready, _, _ = select.select([self.master_fd], [], [], 0.1)
                        
                        if ready:
                            data = os.read(self.master_fd, 4096)
                            if data:
                                output = data.decode('utf-8', errors='replace')
                                self.output_queue.put(output)
                    except OSError:
                        # PTY closed
                        break
                    except Exception as e:
                        logger.debug(f"Read error: {str(e)}")
                        time.sleep(0.1)
            finally:
                self.running = False
        
        def _write_loop(self) -> None:
            """Write to terminal in separate thread."""
            try:
                while self.running:
                    try:
                        data = self.input_queue.get(timeout=0.1)
                        if data and self.master_fd:
                            os.write(self.master_fd, data.encode('utf-8'))
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.debug(f"Write error: {str(e)}")
            finally:
                pass
        
        def read(self, timeout: float = 1.0) -> Optional[str]:
            """Read output from terminal."""
            try:
                return self.output_queue.get(timeout=timeout)
            except queue.Empty:
                return None
        
        def write(self, data: str) -> None:
            """Write input to terminal."""
            if self.running:
                self.input_queue.put(data)
        
        def resize(self, rows: int, cols: int) -> None:
            """Resize terminal window."""
            if self.master_fd:
                try:
                    size = struct.pack('HHHH', rows, cols, 0, 0)
                    fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)
                except Exception as e:
                    logger.debug(f"Resize error: {str(e)}")
        
        def stop(self) -> None:
            """Stop terminal process."""
            if not self.running:
                return
            
            self.running = False
            
            # Terminate process
            if self.process:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                    self.process.wait(timeout=2)
                except Exception:
                    try:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    except Exception as e:
                        logger.error(f"Error killing process: {str(e)}")
            
            # Close file descriptors
            if self.master_fd:
                try:
                    os.close(self.master_fd)
                except Exception:
                    pass
            
            if self.slave_fd:
                try:
                    os.close(self.slave_fd)
                except Exception:
                    pass
            
            # Wait for threads
            if self.reader_thread:
                self.reader_thread.join(timeout=1)
            if self.writer_thread:
                self.writer_thread.join(timeout=1)
            
            # Unregister instance
            with UnixTerminalProcessManager._lock:
                if self.terminal_id in UnixTerminalProcessManager._instances:
                    del UnixTerminalProcessManager._instances[self.terminal_id]
            
            logger.info(f"Unix terminal process stopped: {self.terminal_id}")
        
        @classmethod
        def get_instance(cls, terminal_id: str) -> Optional['UnixTerminalProcessManager']:
            """Get terminal instance by terminal ID."""
            with cls._lock:
                return cls._instances.get(terminal_id)
        
        @classmethod
        def list_instances(cls) -> List[str]:
            """List all active terminal instances."""
            with cls._lock:
                return list(cls._instances.keys())


# ============================================================================
# Windows Terminal Implementation
# ============================================================================

if IS_WINDOWS:
    class WindowsTerminalProcessManager:
        """Manages terminal processes using cmd.exe (Windows only)."""
        
        _instances: Dict[str, 'WindowsTerminalProcessManager'] = {}
        _lock = threading.Lock()
        
        def __init__(self, terminal_id: str, project_root: Path):
            """Initialize Windows terminal process manager."""
            self.terminal_id = terminal_id
            self.project_root = project_root
            self.process: Optional[subprocess.Popen] = None
            self.output_queue: queue.Queue = queue.Queue()
            self.input_queue: queue.Queue = queue.Queue()
            self.running = False
            self.error: Optional[str] = None
            self.reader_thread: Optional[threading.Thread] = None
            self.writer_thread: Optional[threading.Thread] = None
        
        def start(self) -> None:
            """Start Windows terminal process."""
            try:
                # Start cmd.exe process
                self.process = subprocess.Popen(
                    ['cmd.exe'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=str(self.project_root),
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
                
                self.running = True
                
                # Register instance
                with WindowsTerminalProcessManager._lock:
                    WindowsTerminalProcessManager._instances[self.terminal_id] = self
                
                # Start reader and writer threads
                self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
                self.writer_thread = threading.Thread(target=self._write_loop, daemon=True)
                self.reader_thread.start()
                self.writer_thread.start()
                
                logger.info(f"Windows terminal process started: {self.terminal_id}")
                
            except Exception as e:
                self.error = str(e)
                self.running = False
                logger.error(f"Failed to start Windows terminal: {str(e)}")
                raise
        
        def _read_loop(self) -> None:
            """Read from process stdout."""
            try:
                while self.running and self.process:
                    try:
                        # Read with timeout simulation
                        line = self.process.stdout.readline()
                        if line:
                            output = line.decode('utf-8', errors='replace')
                            self.output_queue.put(output)
                        elif self.process.poll() is not None:
                            # Process ended
                            break
                    except Exception as e:
                        logger.debug(f"Read error: {str(e)}")
                        time.sleep(0.1)
            finally:
                self.running = False
        
        def _write_loop(self) -> None:
            """Write to process stdin."""
            try:
                while self.running and self.process:
                    try:
                        data = self.input_queue.get(timeout=0.1)
                        if data:
                            self.process.stdin.write(data.encode('utf-8'))
                            self.process.stdin.flush()
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.debug(f"Write error: {str(e)}")
            finally:
                pass
        
        def read(self, timeout: float = 1.0) -> Optional[str]:
            """Read output from terminal."""
            try:
                return self.output_queue.get(timeout=timeout)
            except queue.Empty:
                return None
        
        def write(self, data: str) -> None:
            """Write input to terminal."""
            if self.running:
                self.input_queue.put(data)
        
        def resize(self, rows: int, cols: int) -> None:
            """Resize terminal (no-op on Windows, not supported via subprocess)."""
            pass
        
        def stop(self) -> None:
            """Stop terminal process."""
            if not self.running:
                return
            
            self.running = False
            
            # Terminate process
            if self.process:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=2)
                except Exception:
                    try:
                        self.process.kill()
                    except Exception as e:
                        logger.error(f"Error terminating process: {str(e)}")
            
            # Wait for threads
            if self.reader_thread:
                self.reader_thread.join(timeout=1)
            if self.writer_thread:
                self.writer_thread.join(timeout=1)
            
            # Unregister instance
            with WindowsTerminalProcessManager._lock:
                if self.terminal_id in WindowsTerminalProcessManager._instances:
                    del WindowsTerminalProcessManager._instances[self.terminal_id]
            
            logger.info(f"Windows terminal process stopped: {self.terminal_id}")
        
        @classmethod
        def get_instance(cls, terminal_id: str) -> Optional['WindowsTerminalProcessManager']:
            """Get terminal instance by terminal ID."""
            with cls._lock:
                return cls._instances.get(terminal_id)
        
        @classmethod
        def list_instances(cls) -> List[str]:
            """List all active terminal instances."""
            with cls._lock:
                return list(cls._instances.keys())


# ============================================================================
# Platform-agnostic wrapper
# ============================================================================

# Use the appropriate implementation based on platform
if IS_WINDOWS:
    TerminalProcessManager = WindowsTerminalProcessManager
else:
    TerminalProcessManager = UnixTerminalProcessManager


class InteractiveTerminal:
    """
    WebSocket-based interactive terminal session (cross-platform).
    Now uses terminal_id as a room name, allowing multiple WebSocket connections.
    """
    
    def __init__(self, terminal_id: str, project_root: Path):
        """Initialize interactive terminal."""
        self.terminal_id = terminal_id
        self.project_root = project_root
        self.process_manager: Optional[TerminalProcessManager] = None
        self.reader_task: Optional[asyncio.Task] = None
    
    async def connect_client(self, websocket: WebSocket) -> None:
        """
        Connect a new client to this terminal room.
        
        Args:
            websocket: WebSocket connection from the client
        """
        # Accept the WebSocket connection
        await websocket.accept()
        
        # Add to connection manager
        await connection_manager.connect(self.terminal_id, websocket)
        
        # Check if process manager exists, if not create it
        if not self.process_manager:
            self.process_manager = TerminalProcessManager.get_instance(self.terminal_id)
            
            if not self.process_manager:
                # First client - create new terminal process
                try:
                    self.process_manager = TerminalProcessManager(self.terminal_id, self.project_root)
                    await asyncio.to_thread(self.process_manager.start)
                    
                    # Wait for process to start
                    await asyncio.sleep(0.3)
                    
                    if not self.process_manager.running:
                        error_msg = self.process_manager.error or "Failed to start terminal process"
                        logger.error(error_msg)
                        await connection_manager.broadcast(
                            self.terminal_id,
                            f"\r\n\x1b[31mError: {error_msg}\x1b[0m\r\n"
                        )
                        raise Exception(error_msg)
                    
                    logger.info(f"Terminal process created for room: {self.terminal_id}")
                    
                    # Start reader task for this terminal
                    self.reader_task = asyncio.create_task(self._read_from_terminal())
                    
                except Exception as e:
                    logger.error(f"Failed to create terminal process: {str(e)}")
                    await connection_manager.disconnect(self.terminal_id, websocket)
                    raise
        
        # Send welcome message to new client
        welcome_msg = f"\r\n\x1b[32m[Connected to terminal: {self.terminal_id}]\x1b[0m\r\n"
        try:
            await websocket.send_text(welcome_msg)
        except Exception as e:
            logger.error(f"Failed to send welcome message: {str(e)}")
        
        # Start writer task for this specific client
        writer_task = asyncio.create_task(self._write_to_terminal(websocket))
        
        try:
            # Wait for writer task (handles client input)
            await writer_task
        except Exception as e:
            logger.error(f"Client writer task failed: {str(e)}")
        finally:
            # Remove client from connection manager
            await connection_manager.disconnect(self.terminal_id, websocket)
            
            # If no more clients, cleanup process
            if not connection_manager.has_connections(self.terminal_id):
                await self.cleanup()
    
    async def _read_from_terminal(self) -> None:
        """
        Read from terminal and broadcast to all connected clients.
        This runs once per terminal, not once per client.
        """
        try:
            while self.process_manager and self.process_manager.running:
                try:
                    # Get output from terminal
                    output = await asyncio.to_thread(
                        self.process_manager.read,
                        timeout=1.0
                    )
                    
                    if output:
                        # Broadcast to all clients in this room
                        await connection_manager.broadcast(self.terminal_id, output)
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.debug(f"Read error: {str(e)}")
                    await asyncio.sleep(0.1)
                    
                # Check if any clients are still connected
                if not connection_manager.has_connections(self.terminal_id):
                    logger.info(f"No clients connected to terminal {self.terminal_id}, stopping reader")
                    break
                    
        except Exception as e:
            logger.error(f"Terminal read failed: {str(e)}")
    
    async def _write_to_terminal(self, websocket: WebSocket) -> None:
        """
        Receive from a specific WebSocket client and write to terminal.
        This runs once per connected client.
        
        Args:
            websocket: WebSocket connection for this client
        """
        logger.info(f"[Terminal {self.terminal_id}] Starting write loop for client")
        try:
            while self.process_manager and self.process_manager.running:
                try:
                    # Try to receive message
                    message = None
                    try:
                        message = await websocket.receive_text()
                        logger.info(f"[Terminal {self.terminal_id}] Received text message: {repr(message[:50]) if len(message) > 50 else repr(message)}")
                    except Exception as text_error:
                        logger.debug(f"[Terminal {self.terminal_id}] receive_text failed: {text_error}, trying bytes...")
                        try:
                            message_bytes = await websocket.receive_bytes()
                            message = message_bytes.decode('utf-8', errors='replace')
                            logger.info(f"[Terminal {self.terminal_id}] Received bytes message (decoded): {repr(message[:50]) if len(message) > 50 else repr(message)}")
                        except Exception as bytes_error:
                            logger.error(f"[Terminal {self.terminal_id}] Failed to receive message - text error: {text_error}, bytes error: {bytes_error}")
                            continue
                    
                    if message and self.process_manager:
                        logger.info(f"[Terminal {self.terminal_id}] Writing {len(message)} chars to terminal process")
                        # Write to terminal (shared by all clients)
                        await asyncio.to_thread(self.process_manager.write, message)
                    elif not message:
                        logger.warning(f"[Terminal {self.terminal_id}] Received empty message")
                        
                except WebSocketDisconnect:
                    logger.info(f"Client disconnected from terminal room: {self.terminal_id}")
                    break
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"[Terminal {self.terminal_id}] Write error: {str(e)}", exc_info=True)
                    break
        except Exception as e:
            logger.error(f"Terminal write failed: {str(e)}", exc_info=True)
    
    async def cleanup(self) -> None:
        """Clean up terminal session when all clients disconnect."""
        logger.info(f"Cleaning up terminal session: {self.terminal_id}")
        
        # Cancel reader task
        if self.reader_task and not self.reader_task.done():
            self.reader_task.cancel()
            try:
                await self.reader_task
            except asyncio.CancelledError:
                pass
        
        # Stop process manager
        if self.process_manager:
            await asyncio.to_thread(self.process_manager.stop)
            self.process_manager = None
        
        logger.info(f"Terminal session closed: {self.terminal_id}")
    
    @classmethod
    def list_terminals(cls) -> List[Dict[str, Any]]:
        """
        List all active terminal sessions with connection info.
        
        Returns:
            List of terminal information including connection counts
        """
        process_terminals = set(TerminalProcessManager.list_instances())
        rooms = connection_manager.list_rooms()
        
        result = []
        for room in rooms:
            terminal_id = room['terminal_id']
            result.append({
                'terminal_id': terminal_id,
                'connection_count': room['connection_count'],
                'has_process': terminal_id in process_terminals
            })
        
        return result
    
    @classmethod
    async def get_or_create(cls, terminal_id: str, project_root: Path) -> 'InteractiveTerminal':
        """
        Get existing terminal or create new one.
        
        Args:
            terminal_id: Terminal session ID
            project_root: Project root directory
            
        Returns:
            InteractiveTerminal instance
        """
        # Check if terminal process already exists
        process_manager = TerminalProcessManager.get_instance(terminal_id)
        
        # Create terminal instance (will reuse existing process if available)
        terminal = cls(terminal_id, project_root)
        if process_manager:
            terminal.process_manager = process_manager
            
        return terminal


# ============================================================================
# Utility functions
# ============================================================================

def get_platform_info() -> Dict[str, Any]:
    """Get platform information."""
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "is_windows": IS_WINDOWS,
        "has_pty_support": not IS_WINDOWS
    }


def get_connection_stats() -> Dict[str, Any]:
    """Get statistics about terminal connections."""
    rooms = connection_manager.list_rooms()
    total_connections = sum(room['connection_count'] for room in rooms)
    
    return {
        "total_rooms": len(rooms),
        "total_connections": total_connections,
        "rooms": rooms
    }