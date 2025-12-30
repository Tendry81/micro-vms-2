# Module Index & Architecture

## Complete Module Breakdown

### 1. Main Application (`main.py`)

**Purpose**: FastAPI application entry point and router registration

**Functions**:
- Initialize FastAPI app with metadata
- Configure CORS middleware
- Register all API routers
- Health check endpoint
- Root info endpoint
- Request validation error handler

**Dependencies**: FastAPI, all routers

---

### 2. Authentication Module (`auth.py`)

**Purpose**: GitHub token validation and user context management

**Classes**:
- `UserContext`: Data class containing user identity and scopes
- `AuditLogger`: Methods for logging auth attempts

**Functions**:
- `validate_github_token()`: Validates token with GitHub API
- `extract_token_from_header()`: Extracts token from request
- `get_user_context()`: Main auth function for endpoints
- `check_required_scopes()`: Validates token scopes
- `validate_scopes()`: Enforces scope requirements

**Features**:
- GitHub API integration
- Scope extraction from response headers
- Token hash creation for audit logging
- Comprehensive error handling

**Dependencies**: requests, FastAPI

---

### 3. Data Models (`models.py`)

**Purpose**: Pydantic models for all request/response data

**Enums**:
- `ErrorCode`: Error code identifiers

**Models**:
- `ErrorResponse`: Standard error format
- `ProjectCreateRequest`: Project creation input
- `ProjectMetadata`: Project information
- `ProjectListResponse`: Project list response
- `FileEntry`: File/directory entry
- `DirectoryListResponse`: Directory listing response
- `FileReadRequest/Response`: File read operations
- `FileCreateRequest/Response`: File creation
- `FileDeletionRequest`: Deletion request
- `GitStatusResponse`: Git status
- `GitPullRequest/Response`: Pull operations
- `GitCommitRequest`: Commit operations
- `GitPushRequest`: Push operations
- `GitCheckoutRequest`: Checkout operations
- `ShellExecuteRequest/Response`: Shell execution

**Constants**:
- File size limits (10MB read, 10KB preview)
- Project root path
- Default timeouts

**Dependencies**: Pydantic

---

### 4. Configuration (`config.py`)

**Purpose**: Centralized configuration management

**Variables**:
- LOG_LEVEL, LOG_DIR
- SERVER_HOST, SERVER_PORT
- PROJECTS_ROOT
- File size limits
- Timeout values
- Concurrency limits
- Feature flags

**Functions**:
- `validate_config()`: Validates configuration
- `get_logger()`: Logger factory

**Features**:
- Environment variable override support
- Type-safe configuration
- Default values

---

### 5. Filesystem Operations (`filesystem.py`)

**Purpose**: Safe filesystem operations with path validation

**Classes**:
- `SafePathResolver`: Path resolution and validation
- `FilesystemOperations`: File and directory operations

**SafePathResolver Methods**:
- `resolve()`: Safely resolve relative paths

**FilesystemOperations Methods**:
- `list_directory()`: List files with .gitignore support
- `read_file()`: Read with size limits
- `create_file()`: Create with parent auto-creation
- `create_directory()`: Create directories
- `delete_path()`: Safe deletion
- `_is_ignored()`: Check .gitignore patterns

**Features**:
- Path traversal prevention
- Symlink escape detection
- .gitignore integration
- File size limits
- Preview mode support

**Dependencies**: pathlib, os, shutil

---

### 6. Gitignore Handling (`gitignore.py`)

**Purpose**: .gitignore pattern parsing and caching

**Classes**:
- `GitignoreHandler`: Pattern management

**Methods**:
- `is_ignored()`: Check if path matches patterns
- `_load_patterns()`: Load from .gitignore file
- `get_ignored_patterns()`: Get pattern list
- `clear_cache()`: Manual cache invalidation

**Features**:
- Pattern caching with invalidation
- pathspec integration
- Comment filtering

**Dependencies**: pathspec, logging

---

### 7. Git Operations (`git_ops.py`)

**Purpose**: Git repository operations

**Classes**:
- `GitOperations`: Git command execution

**Methods**:
- `clone_repository()`: Clone repos
- `get_status()`: Repository status
- `pull()`: Pull from remote
- `commit()`: Commit changes
- `push()`: Push to remote
- `checkout()`: Checkout refs
- `add_files()`: Stage files
- `_run_git_command()`: Execute git commands
- `_parse_pull_stats()`: Parse output

**Features**:
- Subprocess-based execution
- Token injection for auth
- Output parsing
- Error handling
- Timeout enforcement

**Dependencies**: subprocess, pathlib, logging

---

### 8. Shell Execution (`shell_exec.py`)

**Purpose**: Non-interactive and interactive shell execution

**Classes**:
- `ShellExecutor`: Non-interactive execution
- `InteractiveTerminal`: WebSocket terminal sessions

**ShellExecutor Methods**:
- `execute()`: Async command execution
- `_run_command()`: Subprocess wrapper

**InteractiveTerminal Methods**:
- `start()`: Start terminal session
- `_handle_io()`: Bidirectional I/O
- `_read_output()`: Read shell output
- `cleanup()`: Session cleanup
- `get_terminal()`: Retrieve session
- `list_terminals()`: List active sessions

**Features**:
- Async execution with timeout
- PTY support for interactive terminals
- WebSocket bidirectional communication
- Session tracking
- Output streaming

**Dependencies**: asyncio, subprocess, pathlib, logging

---

### 9. Audit Logging (`audit.py`)

**Purpose**: Security event logging

**Classes**:
- `AuditLogger`: Central audit logger

**Methods**:
- `log_authentication_attempt()`: Auth events
- `log_project_creation()`: Project creation
- `log_project_deletion()`: Project deletion
- `log_shell_execution()`: Shell commands
- `log_git_operation()`: Git operations
- `log_security_event()`: General security events

**Functions**:
- `setup_logging()`: Initialize logging
- `get_logger()`: Get logger instance

**Features**:
- Structured JSON logging
- Separate audit log file
- Console and file handlers
- Event timestamps

**Dependencies**: logging, json, pathlib

---

### 10. Project Manager Routes (`project_manager.py`)

**Purpose**: Project management API endpoints

**Functions**:
- `create_project()`: POST /projects/create
- `list_projects()`: GET /projects/list
- `get_project_info()`: GET /projects/{name}
- `delete_project()`: DELETE /projects/{name}

**Helper Functions**:
- `_validate_project_name()`: Name validation
- `_get_disk_usage()`: Calculate size
- `_get_project_metadata()`: Gather metadata

**Features**:
- GitHub token validation
- Project name validation
- Disk usage calculation
- Metadata gathering

**Dependencies**: FastAPI, auth, models

---

### 11. Filesystem Routes (`filesystem_routes.py`)

**Purpose**: Filesystem API endpoints

**Functions**:
- `list_files()`: GET /projects/{name}/files/list
- `read_file()`: GET /projects/{name}/files/read
- `create_file()`: POST /projects/{name}/files/create-file
- `create_directory()`: POST /projects/{name}/files/create-directory
- `delete_path()`: DELETE /projects/{name}/files/delete

**Features**:
- Path parameter extraction
- Error handling
- .gitignore integration
- Authentication on all endpoints

**Dependencies**: FastAPI, auth, filesystem, gitignore

---

### 12. Git Routes (`git_routes.py`)

**Purpose**: Git operations API endpoints

**Functions**:
- `git_status()`: GET /projects/{name}/git/status
- `git_pull()`: POST /projects/{name}/git/pull
- `git_add()`: POST /projects/{name}/git/add
- `git_commit()`: POST /projects/{name}/git/commit
- `git_push()`: POST /projects/{name}/git/push
- `git_checkout()`: POST /projects/{name}/git/checkout

**Features**:
- Scope validation for sensitive operations
- Token injection for push operations
- Error handling and logging

**Dependencies**: FastAPI, auth, git_ops

---

### 13. Shell Routes (`shell_routes.py`)

**Purpose**: Shell execution API endpoints

**Functions**:
- `execute_command()`: POST /projects/{name}/shell/execute
- `websocket_terminal()`: WS /projects/{name}/shell/terminal
- `list_terminals()`: GET /projects/{name}/shell/terminals

**Features**:
- Async command execution
- WebSocket support
- Timeout validation
- Session listing

**Dependencies**: FastAPI, auth, shell_exec

---

## Module Dependencies Graph

```
main.py
├── auth.py
│   └── requests
├── models.py
│   └── pydantic
├── project_manager.py
│   ├── auth.py
│   ├── models.py
│   └── git_ops.py
├── filesystem_routes.py
│   ├── auth.py
│   ├── filesystem.py
│   │   ├── pathlib
│   │   └── shutil
│   └── gitignore.py
│       └── pathspec
├── git_routes.py
│   ├── auth.py
│   └── git_ops.py
│       └── subprocess
├── shell_routes.py
│   ├── auth.py
│   └── shell_exec.py
│       ├── asyncio
│       └── subprocess
└── audit.py
    └── logging
```

---

## Data Flow

### Authentication Flow
```
Request with Token
  ↓
extract_token_from_header()
  ↓
validate_github_token() → GitHub API
  ↓
UserContext created with scopes
  ↓
Route handler receives UserContext
```

### File Read Flow
```
GET /projects/{name}/files/read?path=...
  ↓
Authenticate user
  ↓
Get project path
  ↓
FilesystemOperations.read_file()
  ↓
SafePathResolver.resolve() → validates path
  ↓
Read file with size limits
  ↓
Return FileReadResponse
```

### Git Push Flow
```
POST /projects/{name}/git/push
  ↓
Authenticate user
  ↓
validate_scopes(user, "push") → requires 'repo' scope
  ↓
GitOperations.push()
  ↓
Inject token for authentication
  ↓
Execute git push command
  ↓
Log operation in audit trail
  ↓
Return result
```

### Shell Execution Flow
```
POST /projects/{name}/shell/execute
  ↓
Authenticate user
  ↓
ShellExecutor.execute()
  ↓
asyncio.wait_for() with timeout
  ↓
subprocess.run() in project directory
  ↓
Capture stdout/stderr/exit_code
  ↓
Log to audit trail
  ↓
Return ShellExecuteResponse
```

---

## Error Handling Pattern

All modules follow this pattern:
1. Validate inputs
2. Check authentication/authorization
3. Perform operation
4. Catch exceptions
5. Log error (including in audit trail)
6. Return HTTPException with ErrorCode

---

## Testing Coverage

Each module has:
- Input validation testing
- Error condition testing
- Happy path testing
- Security boundary testing

See `test_service.py` for integration tests.

---

## Security Boundaries

### Authentication Boundary
- All route handlers require `get_user_context()`
- Token validated against GitHub API
- Scope verification per operation

### Path Boundary
- `SafePathResolver.resolve()` enforces project root confinement
- Prevents `..`, absolute paths, symlink escapes

### Execution Boundary
- Shell commands run in project directory
- Timeouts prevent resource exhaustion
- Output captured and size-limited

### Git Boundary
- HTTPS URLs only
- No arbitrary config changes
- Token used but not persisted

---

## Performance Notes

- **Async**: Shell execution uses asyncio
- **Caching**: .gitignore patterns cached
- **Streaming**: File operations use streaming (not full load)
- **Subprocess**: Git and shell via subprocess (reliable)

---

## Extension Points

To add new features:
1. Define models in `models.py`
2. Implement logic in core module
3. Create routes in `*_routes.py`
4. Register router in `main.py`
5. Add authentication checks
6. Add audit logging

---

**Module Count**: 13 core modules  
**Total Lines**: ~3,500+  
**Test Coverage**: 15+ test scenarios  
**Documentation**: 4 comprehensive guides  
