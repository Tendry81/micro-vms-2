# Deployment Guide

Complete guide for deploying the Software Project Management Service.

---

## Local Development

### Prerequisites
- Python 3.10+
- Git
- GitHub Personal Access Token

### Setup

```bash
# 1. Clone the repository
cd micro-vms

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create environment file
cp .env.example .env
# Edit .env with your settings

# 5. Create projects directory
mkdir -p projects logs

# 6. Start development server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Server runs at: `http://localhost:8000`
API docs: `http://localhost:8000/api/docs`

---

## Docker Deployment

### Build Image

```bash
docker build -t project-manager:1.0.0 .
```

### Run Container

```bash
docker run \
  --name project-manager \
  -p 8000:8000 \
  -v ./projects:/app/projects \
  -v ./logs:/app/logs \
  -e LOG_LEVEL=INFO \
  -e SERVER_PORT=8000 \
  project-manager:1.0.0
```

### Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## Production Deployment

### System Requirements

- **OS**: Linux (Ubuntu 20.04+, Debian 11+)
- **Python**: 3.10+
- **RAM**: 512MB minimum, 2GB recommended
- **Disk**: 1GB+ for projects
- **Git**: Latest version

### Installation

```bash
# 1. Create application user
sudo useradd -m -s /bin/bash projectmgr

# 2. Create application directory
sudo mkdir -p /opt/project-manager
sudo chown projectmgr:projectmgr /opt/project-manager

# 3. Copy application
sudo cp -r /path/to/micro-vms/* /opt/project-manager/

# 4. Create virtual environment
cd /opt/project-manager
sudo -u projectmgr python3 -m venv venv
sudo -u projectmgr venv/bin/pip install -r requirements.txt

# 5. Create required directories
sudo -u projectmgr mkdir -p projects logs
```

### Configuration

```bash
# Edit environment file
sudo nano /opt/project-manager/.env
```

Content:
```
LOG_LEVEL=WARNING
LOG_DIR=/var/log/project-manager
PROJECTS_ROOT=/var/lib/project-manager/projects
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
MAX_PROJECTS=100
MAX_CONCURRENT_SHELLS=50
```

### Systemd Service

Create `/etc/systemd/system/project-manager.service`:

```ini
[Unit]
Description=Software Project Management Service
After=network.target

[Service]
Type=notify
User=projectmgr
WorkingDirectory=/opt/project-manager
Environment="PATH=/opt/project-manager/venv/bin"
ExecStart=/opt/project-manager/venv/bin/uvicorn \
  app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --timeout-keep-alive 65

Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable project-manager
sudo systemctl start project-manager
sudo systemctl status project-manager
```

View logs:
```bash
journalctl -u project-manager -f
```

---

## Reverse Proxy Setup (Nginx)

### Configuration

Create `/etc/nginx/sites-available/project-manager`:

```nginx
upstream project_manager {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    # SSL Certificates
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Proxy settings
    client_max_body_size 100M;

    location / {
        proxy_pass http://project_manager;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Authorization $http_authorization;

        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/project-manager \
  /etc/nginx/sites-enabled/

sudo nginx -t
sudo systemctl reload nginx
```

---

## SSL/TLS Certificate

### Let's Encrypt with Certbot

```bash
sudo apt install certbot python3-certbot-nginx

sudo certbot certonly --standalone \
  -d api.example.com \
  -d *.api.example.com

# Auto-renewal (should be enabled by default)
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## Database Setup (if needed)

For persistence beyond local files:

```bash
# PostgreSQL example
sudo apt install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb project_manager
sudo -u postgres createuser projectmgr

# Grant permissions
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE project_manager TO projectmgr;"
```

Update connection in `.env`:
```
DATABASE_URL=postgresql://projectmgr:password@localhost/project_manager
```

---

## Backup Strategy

### Daily Backups

Create `/usr/local/bin/backup-projects.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/project-manager"
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup projects
tar -czf "$BACKUP_DIR/projects-$DATE.tar.gz" \
  /var/lib/project-manager/projects/

# Backup logs
tar -czf "$BACKUP_DIR/logs-$DATE.tar.gz" \
  /var/log/project-manager/

# Keep last 30 days
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
```

Make executable:
```bash
chmod +x /usr/local/bin/backup-projects.sh
```

Add to crontab:
```bash
0 2 * * * /usr/local/bin/backup-projects.sh
```

---

## Monitoring

### Health Check

```bash
# Manual check
curl https://api.example.com/health

# Automated monitoring
*/5 * * * * curl -f https://api.example.com/health || systemctl restart project-manager
```

### Log Monitoring

```bash
# Real-time logs
journalctl -u project-manager -f

# Error tracking
journalctl -u project-manager -p err -f

# Audit log
tail -f /var/log/project-manager/audit.log
```

### Metrics (Optional)

Use Prometheus/Grafana for metrics:

```yaml
# Prometheus config
scrape_configs:
  - job_name: 'project-manager'
    static_configs:
      - targets: ['localhost:8000']
```

---

## Performance Tuning

### Uvicorn Workers

```bash
# Calculate optimal worker count
# Formula: (2 × CPU_count) + 1
# For 4 CPU cores: 9 workers

uvicorn app:app --workers 9
```

### System Limits

```bash
# Increase file descriptors
sudo nano /etc/security/limits.conf
# Add: projectmgr soft nofile 65536
# Add: projectmgr hard nofile 65536

# Apply changes
sudo sysctl -p
```

### Kernel Tuning

```bash
# For WebSocket support
sudo sysctl -w net.core.somaxconn=65535
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=65535
```

---

## Security Hardening

### Firewall Rules

```bash
# UFW (Debian/Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### User Permissions

```bash
# Restrict project directory
sudo chmod 700 /var/lib/project-manager/projects

# Restrict logs
sudo chmod 700 /var/log/project-manager
sudo chown projectmgr:projectmgr /var/log/project-manager
```

### Token Management

```bash
# Store sensitive tokens in environment only
# Never commit .env to git
echo ".env" >> .gitignore

# Use secrets management for production
# Example: AWS Secrets Manager, HashiCorp Vault
```

---

## Health Check Endpoint

The service provides health checks:

```bash
curl https://api.example.com/health
# Response: {"status": "healthy", "service": "project-manager"}
```

Configure your load balancer to use this endpoint.

---

## Scaling Considerations

### Horizontal Scaling

```bash
# Multiple instances behind load balancer
# Use shared storage for projects

# Example: NFS mount
sudo mount -t nfs server:/export /var/lib/project-manager/projects
```

### Load Balancer Configuration

```nginx
upstream project_manager_cluster {
    least_conn;
    server 10.0.1.10:8000;
    server 10.0.1.11:8000;
    server 10.0.1.12:8000;
}
```

### Database Scaling

For concurrent projects, consider:
- PostgreSQL with replication
- Redis for session management
- Memcached for caching

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>

# Or use different port
sudo systemctl set-environment PORT=8001
```

### Permission Denied Errors

```bash
# Check directory ownership
sudo ls -la /var/lib/project-manager/

# Fix ownership
sudo chown projectmgr:projectmgr /var/lib/project-manager/ -R
```

### WebSocket Connection Issues

```bash
# Ensure proxy supports WebSocket
# Check nginx config has:
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";
```

### Out of Memory

```bash
# Monitor memory usage
free -h

# Check swap
swapon --show

# Reduce worker count if needed
```

---

## Upgrade Procedure

```bash
# 1. Stop service
sudo systemctl stop project-manager

# 2. Backup current version
sudo cp -r /opt/project-manager /opt/project-manager.backup

# 3. Update code
cd /opt/project-manager
git pull origin main

# 4. Update dependencies
venv/bin/pip install -r requirements.txt

# 5. Run migrations (if any)
venv/bin/python -m alembic upgrade head

# 6. Restart service
sudo systemctl start project-manager

# 7. Verify
curl https://api.example.com/health
```

---

## Maintenance

### Weekly Tasks
- [ ] Review audit logs
- [ ] Monitor disk usage
- [ ] Check for updates

### Monthly Tasks
- [ ] Review security logs
- [ ] Test backup restoration
- [ ] Performance analysis
- [ ] Update dependencies

### Quarterly Tasks
- [ ] Security audit
- [ ] Capacity planning
- [ ] Disaster recovery drill

---

## Support Resources

- **Documentation**: README.md
- **API Reference**: API_REFERENCE.md
- **Quick Start**: QUICKSTART.md
- **Module Documentation**: MODULE_INDEX.md

---

**Last Updated**: December 26, 2025  
**Version**: 1.0.0
