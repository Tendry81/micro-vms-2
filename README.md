---
title: Micro Vms
emoji: 👁
colorFrom: blue
colorTo: red
sdk: docker
pinned: false
---

# Software Project Management Service

A **local Codespaces-like backend service** that manages isolated software projects stored under `./projects`. Provides authenticated access to Git operations, filesystem management, and shell execution with strong security and isolation guarantees.

## Features

✅ **Project Management**
- Clone GitHub repositories (public and private)
- List and inspect projects
- Delete projects

✅ **Filesystem Operations**
- Safe path resolution (prevents traversal attacks)
- List directories with .gitignore support
- Read files (with size limits and preview mode)
- Create files and directories
- Delete files and directories

✅ **Git Integration**
- Repository status
- Pull from remote
- Commit staged changes
- Push to remote
- Checkout branches/tags

✅ **Shell Execution**
- Non-interactive command execution
- Interactive WebSocket terminal (PTY)
- Project-scoped execution
- Timeout enforcement

✅ **Security**
- GitHub token authentication
- Scope-based authorization
- Path traversal prevention
- Symlink escape prevention
- Comprehensive audit logging

## Requirements

- Python 3.10+
- Git installed
- Linux with PTY support (for interactive terminals)
- GitHub Personal Access Token

## Installation

### 1. Clone and Install Dependencies

```bash
cd micro-vms
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file (optional):

```bash
# Logging
LOG_LEVEL=INFO
LOG_DIR=./logs

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Projects
PROJECTS_ROOT=./projects
```

### 3. Run Server

```bash
# Development (with auto-reload)
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

The service will be available at `http://localhost:8000`

## Authentication

All endpoints require a GitHub Personal Access Token in the `Authorization` header:

```bash
Authorization: token ghp_xxxxxxxxx
```

### Obtain a Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Create a "Fine-grained token" with:
   - **Public Repositories (read-only)** - for public repo access
   - **Contents** - for private repo access and git push

## API Endpoints

### Root

```http
GET /
```

Returns service information and endpoints.

### Health Check

```http
GET /health
```

### Projects

#### Create Project

```http
POST /projects/create
Authorization: token ghp_xxxxxxxxx

{
  "project_name": "my-project",
  "repo_url": "https://github.com/user/repo.git",
  "branch": "main"  // optional
}
```

#### List Projects

```http
GET /projects/list
Authorization: token ghp_xxxxxxxxx
```

Response:
```json
{
  "projects": [
    {
      "name": "my-project",
      "path": "./projects/my-project",
      "disk_usage_bytes": 1048576,
      "last_modified": "2025-01-15T10:30:00",
      "is_git_repo": true
    }
  ],
  "count": 1
}
```

#### Get Project Info

```http
GET /projects/{project_name}
Authorization: token ghp_xxxxxxxxx
```

#### Delete Project

```http
DELETE /projects/{project_name}
Authorization: token ghp_xxxxxxxxx
```

### Filesystem Operations

#### List Files

```http
GET /projects/{project_name}/files/list?path=.&recursive=false
Authorization: token ghp_xxxxxxxxx
```

#### Read File

```http
GET /projects/{project_name}/files/read?path=README.md&preview=false
Authorization: token ghp_xxxxxxxxx
```

#### Create File

```http
POST /projects/{project_name}/files/create-file
Authorization: token ghp_xxxxxxxxx

{
  "path": "src/main.py",
  "content": "print('hello')",
  "overwrite": false
}
```

#### Create Directory

```http
POST /projects/{project_name}/files/create-directory
Authorization: token ghp_xxxxxxxxx

{
  "path": "src/utils",
  "parents": true
}
```

#### Delete File/Directory

```http
DELETE /projects/{project_name}/files/delete?path=src/main.py&recursive=false
Authorization: token ghp_xxxxxxxxx
```

### Git Operations

#### Status

```http
GET /projects/{project_name}/git/status
Authorization: token ghp_xxxxxxxxx
```

#### Pull

```http
POST /projects/{project_name}/git/pull
Authorization: token ghp_xxxxxxxxx

{
  "remote": "origin",
  "branch": "main"  // optional
}
```

#### Add Files

```http
POST /projects/{project_name}/git/add
Authorization: token ghp_xxxxxxxxx

{
  "pattern": "."  // default: all files
}
```

#### Commit

```http
POST /projects/{project_name}/git/commit
Authorization: token ghp_xxxxxxxxx

{
  "message": "Fix bug in parser",
  "author_name": "John Doe",
  "author_email": "john@example.com"
}
```

#### Push

```http
POST /projects/{project_name}/git/push
Authorization: token ghp_xxxxxxxxx

{
  "remote": "origin",
  "branch": "main",
  "force": false
}
```

#### Checkout

```http
POST /projects/{project_name}/git/checkout
Authorization: token ghp_xxxxxxxxx

{
  "ref": "develop"
}
```

### Shell Execution

#### Execute Command (Non-Interactive)

```http
POST /projects/{project_name}/shell/execute
Authorization: token ghp_xxxxxxxxx

{
  "command": "ls -la",
  "timeout": 30,
  "cwd": "."  // optional, relative to project root
}
```

Response:
```json
{
  "command": "ls -la",
  "exit_code": 0,
  "stdout": "...",
  "stderr": "",
  "duration_seconds": 0.123
}
```

#### Interactive Terminal (WebSocket)

```javascript
const ws = new WebSocket(
  "ws://localhost:8000/projects/{project_name}/shell/terminal?token=ghp_xxx"
);

ws.onmessage = (event) => {
  console.log("Terminal output:", event.data);
};

// Send command
ws.send("ls -la\n");
```

#### List Terminals

```http
GET /projects/{project_name}/shell/terminals
Authorization: token ghp_xxxxxxxxx
```

## Error Responses

All errors follow this format:

```json
{
  "code": "ERROR_CODE",
  "message": "Human readable message",
  "details": {}
}
```

### Error Codes

| Code | Meaning |
|------|---------|
| `AUTH_INVALID` | Invalid or expired token |
| `AUTH_SCOPE` | Missing required scope |
| `PATH_TRAVERSAL` | Unsafe path (traversal detected) |
| `FILE_TOO_LARGE` | File exceeds size limit |
| `PROJECT_NOT_FOUND` | Project doesn't exist |
| `SHELL_DENIED` | Command execution blocked |
| `GIT_ERROR` | Git operation failed |
| `INVALID_REQUEST` | Invalid request parameters |
| `INTERNAL_ERROR` | Server error |

## Limits

| Limit | Value |
|-------|-------|
| Max file read | 10 MB |
| Max file preview | 10 KB |
| Default shell timeout | 30 seconds |
| Max shell timeout | 3600 seconds |
| Default concurrent shells | Configurable |

## Security Considerations

### Path Isolation

All filesystem operations are confined to the project directory:
- Absolute paths rejected
- `..` traversal prevented
- Symlink escapes blocked

### Git Security

- No arbitrary Git config changes
- No credential persistence
- No submodule auto-init
- No hooks execution
- Token not logged (only hash logged)

### Shell Isolation

- Non-privileged execution
- Project root scope enforced
- Timeout-based DOS prevention
- Output size limits

### Audit Logging

All security events are logged to `./logs/audit.log`:
- Authentication attempts
- Project operations
- Git operations
- Shell commands

## Development

### Project Structure

```
app/
├── __init__.py
├── main.py              # FastAPI application
├── auth.py              # GitHub authentication
├── models.py            # Pydantic models
├── filesystem.py        # Filesystem operations
├── git_ops.py           # Git operations
├── shell_exec.py        # Shell execution
├── gitignore.py         # .gitignore handling
├── project_manager.py   # Project management endpoints
├── filesystem_routes.py # Filesystem API routes
├── git_routes.py        # Git API routes
├── shell_routes.py      # Shell API routes
└── audit.py             # Logging and auditing
```

### Testing

```bash
# Create a test project
curl -X POST http://localhost:8000/projects/create \
  -H "Authorization: token ghp_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "test-project",
    "repo_url": "https://github.com/octocat/Hello-World.git"
  }'

# List projects
curl http://localhost:8000/projects/list \
  -H "Authorization: token ghp_xxx"

# Execute a command
curl -X POST http://localhost:8000/projects/test-project/shell/execute \
  -H "Authorization: token ghp_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "pwd",
    "timeout": 10
  }'
```

## Troubleshooting

### "Invalid or expired GitHub token"
- Verify token format: `ghp_xxx...`
- Check token hasn't expired
- Verify scopes in GitHub settings

### "Project not found"
- Verify project name matches exactly (case-sensitive)
- Check projects directory: `./projects`

### "Git operation failed"
- Verify repository URL is valid
- Check network connectivity
- Verify token has required scopes (`repo` for private repos)

### "Path traversal detected"
- Use relative paths only
- Avoid `..` in paths
- Check for symlinks escaping project

## Production Deployment

### Docker

See `Dockerfile` for containerized deployment.

```bash
docker build -t project-manager .
docker run -p 8000:8000 -v ./projects:/app/projects project-manager
```

### Environment Variables

```bash
export LOG_LEVEL=WARNING
export LOG_DIR=/var/log/project-manager
export PROJECTS_ROOT=/data/projects
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Authorization $http_authorization;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Performance

- **Concurrent Projects**: Unlimited (filesystem bound)
- **Concurrent Shell Sessions**: Configurable per project
- **File Operations**: Optimized with streaming for large files
- **Git Operations**: 60-second timeout per command

## Non-Goals

- Multi-tenant cloud hosting
- Browser-based IDE UI
- Long-running background jobs
- Container orchestration (optional future enhancement)


# URL
https://rtendry81-micro-vms.hf.space/