# API Reference

Complete REST API reference for the Software Project Management Service.

## Authentication

All endpoints (except `/` and `/health`) require a GitHub Personal Access Token in the `Authorization` header:

```
Authorization: token ghp_xxxxxxxxxxxx
```

### Getting a Token

1. Visit https://github.com/settings/tokens
2. Click "Generate new token" → "Fine-grained tokens"
3. Give it a name and expiration
4. Select required permissions:
   - **Public Repositories**: `read:user` (public repo access)
   - **Contents**: Read and write (for private repos and push)
5. Copy the token (you can only see it once!)

---

## Endpoints

### Root

#### GET /

Returns service information.

**Response:**
```json
{
  "service": "Software Project Management Service",
  "version": "1.0.0",
  "endpoints": {
    "projects": "/projects",
    "filesystem": "/projects/{project_name}/files",
    "git": "/projects/{project_name}/git",
    "shell": "/projects/{project_name}/shell",
    "docs": "/api/docs"
  }
}
```

---

### Health

#### GET /health

Service health check.

**Response:**
```json
{
  "status": "healthy",
  "service": "project-manager"
}
```

---

## Projects

### POST /projects/create

Create a new project by cloning a repository.

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
Content-Type: application/json
```

**Request Body:**
```json
{
  "project_name": "my-project",
  "repo_url": "https://github.com/user/repo.git",
  "branch": "main"  // optional
}
```

**Response (201):**
```json
{
  "status": "created",
  "project": {
    "name": "my-project",
    "path": "./projects/my-project",
    "disk_usage_bytes": 2097152,
    "last_modified": "2025-01-15T10:30:00",
    "is_git_repo": true
  }
}
```

**Errors:**
- `400`: Invalid project name or repo URL
- `409`: Project already exists
- `401`: Authentication failed
- `403`: Insufficient scopes

---

### GET /projects/list

List all projects.

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "projects": [
    {
      "name": "my-project",
      "path": "./projects/my-project",
      "disk_usage_bytes": 2097152,
      "last_modified": "2025-01-15T10:30:00",
      "is_git_repo": true
    }
  ],
  "count": 1
}
```

**Errors:**
- `401`: Authentication failed

---

### GET /projects/{project_name}

Get information about a specific project.

**Parameters:**
- `project_name` (path): Project name

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "name": "my-project",
  "path": "./projects/my-project",
  "disk_usage_bytes": 2097152,
  "last_modified": "2025-01-15T10:30:00",
  "is_git_repo": true
}
```

**Errors:**
- `401`: Authentication failed
- `404`: Project not found

---

### DELETE /projects/{project_name}

Delete a project permanently.

**Parameters:**
- `project_name` (path): Project name

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "status": "deleted",
  "project": "my-project"
}
```

**Errors:**
- `401`: Authentication failed
- `404`: Project not found

---

## Filesystem

### GET /projects/{project_name}/files/list

List directory contents.

**Parameters:**
- `project_name` (path): Project name
- `path` (query): Path within project (default: ".")
- `recursive` (query): List recursively (default: false)

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "entries": [
    {
      "name": "README.md",
      "path": "README.md",
      "type": "file",
      "size_bytes": 1024,
      "modified": "2025-01-15T10:30:00",
      "is_ignored": false
    }
  ],
  "recursive": false,
  "count": 1
}
```

**Errors:**
- `401`: Authentication failed
- `404`: Project or path not found

---

### GET /projects/{project_name}/files/read

Read file contents.

**Parameters:**
- `project_name` (path): Project name
- `path` (query): File path (required)
- `preview` (query): Return only first 10KB (default: false)

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "path": "README.md",
  "content": "# My Project\n...",
  "size_bytes": 1024,
  "preview": false,
  "truncated": false
}
```

**Errors:**
- `401`: Authentication failed
- `404`: File not found
- `413`: File too large
- `400`: Not a file

---

### POST /projects/{project_name}/files/create-file

Create a file.

**Parameters:**
- `project_name` (path): Project name
- `path` (query): File path (required)
- `content` (query): File content
- `overwrite` (query): Allow overwriting (default: false)

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "path": "src/main.py",
  "created": true,
  "size_bytes": 100
}
```

**Errors:**
- `401`: Authentication failed
- `404`: Project not found
- `409`: File exists (and overwrite=false)

---

### POST /projects/{project_name}/files/create-directory

Create a directory.

**Parameters:**
- `project_name` (path): Project name
- `path` (query): Directory path (required)
- `parents` (query): Create parents (default: true)

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "path": "src/utils",
  "created": true,
  "message": "Directory created"
}
```

**Errors:**
- `401`: Authentication failed
- `404`: Project not found
- `409`: Path exists

---

### DELETE /projects/{project_name}/files/delete

Delete a file or directory.

**Parameters:**
- `project_name` (path): Project name
- `path` (query): Path to delete (required)
- `recursive` (query): Allow recursive (default: false)

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "path": "src/main.py",
  "deleted": true,
  "type": "file"
}
```

**Errors:**
- `401`: Authentication failed
- `404`: Path not found
- `400`: Not empty and recursive=false

---

## Git

### GET /projects/{project_name}/git/status

Get repository status.

**Parameters:**
- `project_name` (path): Project name

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "branch": "main",
  "modified_files": ["src/main.py"],
  "untracked_files": ["test.py"],
  "commits_ahead": 2,
  "commits_behind": 0
}
```

**Errors:**
- `401`: Authentication failed
- `404`: Project not found
- `400`: Not a git repository

---

### POST /projects/{project_name}/git/pull

Pull from remote.

**Parameters:**
- `project_name` (path): Project name
- `remote` (query): Remote name (default: "origin")
- `branch` (query): Branch name

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "status": "success",
  "files_changed": 3,
  "insertions": 10,
  "deletions": 2,
  "output": "Already up to date."
}
```

**Errors:**
- `401`: Authentication failed
- `404`: Project not found
- `400`: Git operation failed

---

### POST /projects/{project_name}/git/add

Stage files for commit.

**Parameters:**
- `project_name` (path): Project name
- `pattern` (query): File pattern (default: ".")

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "status": "success"
}
```

**Errors:**
- `401`: Authentication failed
- `404`: Project not found

---

### POST /projects/{project_name}/git/commit

Commit staged changes.

**Parameters:**
- `project_name` (path): Project name
- `message` (query): Commit message (required)
- `author_name` (query): Author name
- `author_email` (query): Author email

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "status": "success",
  "output": "[main abc123] Commit message\n 1 file changed"
}
```

**Errors:**
- `401`: Authentication failed
- `404`: Project not found
- `400`: Git operation failed

---

### POST /projects/{project_name}/git/push

Push to remote.

**Parameters:**
- `project_name` (path): Project name
- `remote` (query): Remote name (default: "origin")
- `branch` (query): Branch name
- `force` (query): Force push (default: false)

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "status": "success",
  "output": "To github.com/user/repo.git\n   abc123..def456  main -> main"
}
```

**Errors:**
- `401`: Authentication failed or insufficient scopes
- `404`: Project not found
- `403`: Missing `repo` scope
- `400`: Git operation failed

---

### POST /projects/{project_name}/git/checkout

Checkout a branch or tag.

**Parameters:**
- `project_name` (path): Project name
- `ref` (query): Branch or tag name (required)

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "status": "success",
  "ref": "develop",
  "output": "Switched to branch 'develop'"
}
```

**Errors:**
- `401`: Authentication failed
- `404`: Project not found
- `400`: Git operation failed

---

## Shell

### POST /projects/{project_name}/shell/execute

Execute a shell command.

**Parameters:**
- `project_name` (path): Project name
- `command` (query): Command to execute (required)
- `timeout` (query): Timeout in seconds (default: 30, max: 3600)
- `cwd` (query): Working directory relative to project

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "command": "ls -la",
  "exit_code": 0,
  "stdout": "total 24\ndrwxr-xr-x  5 user  group  160 Jan 15 10:30 .\n...",
  "stderr": "",
  "duration_seconds": 0.123
}
```

**Errors:**
- `401`: Authentication failed
- `404`: Project not found
- `400`: Invalid parameters
- `408`: Command timeout

---

### WS /projects/{project_name}/shell/terminal

WebSocket endpoint for interactive terminal.

**Connection:**
```javascript
const ws = new WebSocket(
  'ws://localhost:8000/projects/{project_name}/shell/terminal'
);
```

**Messages:**
- Send: Text command (e.g., "ls\n")
- Receive: Terminal output

**Example:**
```javascript
ws.onopen = () => {
  ws.send('ls -la\n');
};

ws.onmessage = (event) => {
  console.log('Output:', event.data);
};

ws.onclose = () => {
  console.log('Terminal closed');
};
```

---

### GET /projects/{project_name}/shell/terminals

List active terminal sessions.

**Parameters:**
- `project_name` (path): Project name

**Headers:**
```
Authorization: token ghp_xxxxxxxxxxxx
```

**Response (200):**
```json
{
  "project": "my-project",
  "terminals": [
    "550e8400-e29b-41d4-a716-446655440000"
  ],
  "count": 1
}
```

**Errors:**
- `401`: Authentication failed
- `404`: Project not found

---

## Error Responses

All errors follow this format:

```json
{
  "code": "ERROR_CODE",
  "message": "Human readable error message",
  "details": {}
}
```

### Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `AUTH_INVALID` | 401 | Invalid or expired token |
| `AUTH_SCOPE` | 403 | Missing required scope |
| `PATH_TRAVERSAL` | 403 | Path traversal attempted |
| `FILE_TOO_LARGE` | 413 | File exceeds size limit |
| `PROJECT_NOT_FOUND` | 404 | Project doesn't exist |
| `SHELL_DENIED` | 403 | Command execution blocked |
| `GIT_ERROR` | 400 | Git operation failed |
| `INVALID_REQUEST` | 400 | Invalid request parameters |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Rate Limits

No explicit rate limiting implemented. Per-request timeouts are enforced:

| Operation | Timeout |
|-----------|---------|
| File operations | 30s |
| Shell execute | 30-3600s (configurable) |
| Git pull | 300s |
| Git push | 300s |
| Project clone | 600s |

---

## Pagination

Not implemented. All list endpoints return complete results.

---

## Webhooks

Not implemented.

---

## Versioning

Current API version: 1.0.0

No explicit API versioning in URLs. Breaking changes will increment the version number.

---

## Testing

Use the included test script:

```bash
python test_service.py <github_token>
```

Or test with curl:

```bash
# List projects
curl -H "Authorization: token ghp_xxx" \
  http://localhost:8000/projects/list

# Create project
curl -X POST \
  -H "Authorization: token ghp_xxx" \
  -H "Content-Type: application/json" \
  -d '{"project_name":"test","repo_url":"https://github.com/octocat/Hello-World.git"}' \
  http://localhost:8000/projects/create
```

---

## Support

For issues and questions:
1. Check the [README.md](README.md)
2. Review the [QUICKSTART.md](QUICKSTART.md)
3. Check API documentation at `/api/docs`
