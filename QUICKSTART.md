# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get a GitHub Token

1. Visit [github.com/settings/tokens](https://github.com/settings/tokens)
2. Create a "Fine-grained token" with:
   - Public Repositories (read-only)
   - Contents (for push)
3. Copy the token

### 3. Start the Service

```bash
uvicorn app:app --reload
```

Server runs at `http://localhost:8000`

## Testing the API

### 1. Create a Project

```bash
curl -X POST http://localhost:8000/projects/create \
  -H "Authorization: token ghp_YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "test-repo",
    "repo_url": "https://github.com/octocat/Hello-World.git"
  }'
```

### 2. List Projects

```bash
curl http://localhost:8000/projects/list \
  -H "Authorization: token ghp_YOUR_TOKEN_HERE"
```

### 3. Read a File

```bash
curl "http://localhost:8000/projects/test-repo/files/read?path=README" \
  -H "Authorization: token ghp_YOUR_TOKEN_HERE"
```

### 4. Execute a Command

```bash
curl -X POST http://localhost:8000/projects/test-repo/shell/execute \
  -H "Authorization: token ghp_YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "ls -la",
    "timeout": 10
  }'
```

### 5. Check Git Status

```bash
curl http://localhost:8000/projects/test-repo/git/status \
  -H "Authorization: token ghp_YOUR_TOKEN_HERE"
```

## API Documentation

Open `http://localhost:8000/api/docs` in your browser for interactive API documentation.

## Environment Setup

Copy and customize the environment:

```bash
cp .env.example .env
# Edit .env with your settings
```

## Common Tasks

### Clone a Private Repository

Your token needs `repo` scope:

```bash
curl -X POST http://localhost:8000/projects/create \
  -H "Authorization: token ghp_YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "private-repo",
    "repo_url": "https://github.com/your-user/private-repo.git"
  }'
```

### Push Changes

1. Make changes to files:

```bash
curl -X POST http://localhost:8000/projects/test-repo/files/create-file \
  -H "Authorization: token ghp_YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "new-file.txt",
    "content": "Hello World"
  }'
```

2. Stage changes:

```bash
curl -X POST http://localhost:8000/projects/test-repo/git/add \
  -H "Authorization: token ghp_YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pattern": "."}'
```

3. Commit:

```bash
curl -X POST http://localhost:8000/projects/test-repo/git/commit \
  -H "Authorization: token ghp_YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Add new file"}'
```

4. Push:

```bash
curl -X POST http://localhost:8000/projects/test-repo/git/push \
  -H "Authorization: token ghp_YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"remote": "origin", "branch": "main"}'
```

### Access Interactive Terminal

```javascript
// In browser console or Node.js
const ws = new WebSocket('ws://localhost:8000/projects/test-repo/shell/terminal');

ws.onopen = () => {
  ws.send('ls -la\n');
};

ws.onmessage = (event) => {
  console.log(event.data);
};
```

## Troubleshooting

### "Invalid token"
- Verify token format starts with `ghp_`
- Check token hasn't expired in GitHub settings
- Ensure correct capitalization

### "Project not found"
- Check project name is spelled correctly (case-sensitive)
- Verify directory exists: `./projects/{project_name}`

### "Git operation failed"
- Ensure Git is installed: `git --version`
- Check network connectivity
- Verify token has required scopes

### Port Already in Use

```bash
# Use a different port
uvicorn app:app --port 8001
```

## Next Steps

- Read [README.md](README.md) for complete documentation
- Check [API docs](http://localhost:8000/api/docs)
- Explore [app structure](app/) for implementation details
