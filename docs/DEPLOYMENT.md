# Form Builder Platform - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Form Builder Platform using Docker Compose. The platform consists of multiple services working together to provide a complete form building, analysis, and dashboard solution.

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ or Docker-compatible Linux distribution
- **RAM**: Minimum 8GB, Recommended 16GB
- **CPU**: Minimum 4 cores, Recommended 8 cores
- **Storage**: Minimum 50GB SSD, Recommended 100GB+ SSD
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+

### Network Requirements
- **Ports**: 80, 443 (web), 27017 (MongoDB), 6379 (Redis), 9200 (Elasticsearch), 3310 (ClamAV)
- **Firewall**: Ensure required ports are open
- **DNS**: Proper domain name resolution

## Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd form-builder
```

### 2. Environment Configuration
```bash
# Copy the environment template
cp .env.example .env

# Edit the environment file
nano .env
```

**Required Configuration:**
```bash
# Security (MUST CHANGE IN PRODUCTION)
SECRET_KEY=your-super-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Database (will be handled by Docker Compose)
MONGO_URI=mongodb://mongodb:27017/formbuilder
REDIS_URL=redis://redis:6379/0
ELASTICSEARCH_URL=http://elasticsearch:9200

# Email/SMS API (AIIMS)
EMAIL_API_URL=https://rpcapplication.aiims.edu/services/api/v1/mail/single
EMAIL_API_TOKEN=your-actual-api-token
SMS_API_URL=https://rpcapplication.aiims.edu/services/api/v1/sms/single
SMS_API_TOKEN=your-actual-api-token

# CORS Origins (comma-separated)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 3. SSL Certificates
```bash
# Create SSL directory
mkdir -p docker/nginx/certs

# Generate self-signed certificate (for development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/nginx/certs/key.pem \
  -out docker/nginx/certs/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# OR use Let's Encrypt (for production)
# certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
# Copy certificates to docker/nginx/certs/
```

### 4. Build and Start Services
```bash
# Development environment
docker-compose -f docker/docker-compose.yml up -d

# Production environment
docker-compose -f docker/docker-compose.prod.yml up -d
```

### 5. Verify Deployment
```bash
# Check service status
docker-compose -f docker/docker-compose.prod.yml ps

# Check logs
docker-compose -f docker/docker-compose.prod.yml logs -f backend

# Health check
curl https://localhost/health
```

## Service Details

### Core Services

#### 1. Nginx (Reverse Proxy)
- **Purpose**: SSL termination, load balancing, static file serving
- **Port**: 80, 443
- **Configuration**: `docker/nginx/nginx.conf`
- **Health**: Check at `https://localhost/health`

#### 2. Backend (Flask API)
- **Purpose**: Main application API
- **Port**: 5000 (internal)
- **Workers**: Multiple Gunicorn workers
- **Health**: `/api/health` endpoint

#### 3. MongoDB (Database)
- **Purpose**: Primary data storage
- **Port**: 27017
- **Data**: `mongodb_data` volume
- **Config**: `docker/mongodb/mongod.conf`

#### 4. Redis (Cache & Message Broker)
- **Purpose**: Caching, session storage, Celery broker
- **Port**: 6379
- **Data**: `redis_data` volume
- **Config**: `docker/redis/redis.conf`

#### 5. Elasticsearch (Search Engine)
- **Purpose**: Full-text search and analytics
- **Port**: 9200
- **Data**: `elasticsearch_data` volume
- **Config**: `docker/elasticsearch/elasticsearch.yml`

#### 6. ClamAV (Virus Scanner)
- **Purpose**: File upload virus scanning
- **Port**: 3310
- **Data**: `clamav_data` volume
- **Config**: `docker/clamav/clamd.conf`

### Supporting Services

#### 7. Celery Worker (Background Tasks)
- **Purpose**: Async task processing
- **Concurrency**: Configurable (default: 4)
- **Queues**: Analysis, export, notification, maintenance

#### 8. Celery Beat (Scheduled Tasks)
- **Purpose**: Cron-like scheduling
- **Schedule**: Persistent in `celerybeat-schedule`

#### 9. Flower (Celery Monitor)
- **Purpose**: Web-based Celery monitoring
- **Port**: 5555 (internal)
- **Access**: `http://localhost:5555`

#### 10. Redis Commander (Optional)
- **Purpose**: Web-based Redis management
- **Port**: 8081
- **Access**: `http://localhost:8081`

#### 11. Mongo Express (Optional)
- **Purpose**: Web-based MongoDB management
- **Port**: 8082
- **Access**: `http://localhost:8082`

## Configuration

### Environment Variables

#### Security Configuration
```bash
# Secrets (MUST CHANGE)
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Authentication
BCRYPT_ROUNDS=12
JWT_ACCESS_TOKEN_EXPIRES_SECONDS=900
JWT_REFRESH_TOKEN_EXPIRES_SECONDS=2592000
```

#### Database Configuration
```bash
# MongoDB
MONGO_URI=mongodb://mongodb:27017/formbuilder
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=your-mongo-password

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_CACHE_DB=0
REDIS_SESSION_DB=1
REDIS_RATE_LIMIT_DB=2
REDIS_PRESENCE_DB=3

# Elasticsearch
ELASTICSEARCH_URL=http://elasticsearch:9200
ELASTICSEARCH_INDEX_PREFIX=formbuilder
```

#### Performance Configuration
```bash
# Celery
CELERY_CONCURRENCY=4
CELERY_TASK_ROUTES={"analysis.tasks.*": {"queue": "analysis"}}

# Analysis
ANALYSIS_MAX_RUNTIME_SECONDS=300
ANALYSIS_MAX_NODES=100
ANALYSIS_CACHE_TTL_SECONDS=3600

# Dashboard
DASHBOARD_MAX_WIDGETS=50
DASHBOARD_DEFAULT_REFRESH_INTERVAL_SECONDS=300
```

#### File Upload Configuration
```bash
# Sizes (in bytes)
MAX_UPLOAD_SIZE_PDF=52428800      # 50MB
MAX_UPLOAD_SIZE_VIDEO=314572800   # 300MB
MAX_UPLOAD_SIZE_IMAGE=52428800    # 50MB
MAX_UPLOAD_SIZE_OTHER=104857600   # 100MB

# Tus (Resumable uploads)
TUS_CHUNK_SIZE=5242880           # 5MB
TUS_MAX_FILE_SIZE=1073741824      # 1GB
```

#### Monitoring Configuration
```bash
# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring
SENTRY_DSN=your-sentry-dsn
METRICS_ENABLED=true
HEALTH_CHECK_ENABLED=true
```

### Docker Compose Overrides

Create a `docker-compose.override.yml` for local development:

```yaml
version: '3.8'
services:
  backend:
    environment:
      - FLASK_ENV=development
      - DEBUG=true
    volumes:
      - ../backend:/app
    command: python -m flask run --host=0.0.0.0 --port=5000 --reload

  mongodb:
    ports:
      - "27017:27017"

  redis:
    ports:
      - "6379:6379"

  elasticsearch:
    ports:
      - "9200:9200"
```

## Scaling

### Horizontal Scaling

#### Backend Workers
```yaml
# In docker-compose.prod.yml
backend:
  deploy:
    replicas: 4
    resources:
      limits:
        memory: 1G
      reservations:
        memory: 512M
```

#### Celery Workers
```yaml
# In docker-compose.prod.yml
celery_worker:
  deploy:
    replicas: 2
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 1G
```

### Vertical Scaling

#### Resource Allocation
```yaml
# In docker-compose.prod.yml
services:
  elasticsearch:
    environment:
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
  
  mongodb:
    environment:
      - MONGO_MEMORY_SIZE=4G
```

## Monitoring and Logging

### Application Logs
```bash
# View all logs
docker-compose -f docker/docker-compose.prod.yml logs -f

# View specific service logs
docker-compose -f docker/docker-compose.prod.yml logs -f backend

# View logs since specific time
docker-compose -f docker/docker-compose.prod.yml logs --since 1h
```

### Service Monitoring

#### Flower (Celery)
- **URL**: `http://localhost:5555`
- **Features**: Task monitoring, worker status, statistics

#### Redis Commander
- **URL**: `http://localhost:8081`
- **Features**: Redis data browser, command execution

#### Mongo Express
- **URL**: `http://localhost:8082`
- **Features**: MongoDB browser, query execution

### Health Checks

#### Application Health
```bash
curl https://localhost/health
curl https://localhost/api/health
```

#### Service Health
```bash
# Check container status
docker-compose -f docker/docker-compose.prod.yml ps

# Check container health
docker inspect --format='{{.State.Health.Status}}' form-builder_backend_1
```

### Performance Monitoring

#### Resource Usage
```bash
# Monitor resource usage
docker stats

# Monitor specific service
docker stats form-builder_backend_1
```

#### Application Metrics
- **Metrics**: Enabled via `METRICS_ENABLED=true`
- **Endpoint**: `/api/metrics` (if implemented)
- **Format**: Prometheus-compatible (if implemented)

## Backup and Recovery

### Database Backup

#### MongoDB
```bash
# Create backup
docker exec -i form-builder_mongodb_1 mongodump --archive --gzip > backup_$(date +%Y%m%d_%H%M%S).gz

# Restore backup
docker exec -i form-builder_mongodb_1 mongorestore --archive --gzip < backup_20240101_120000.gz
```

#### Redis
```bash
# Create backup
docker exec form-builder_redis_1 redis-cli SAVE
docker cp form-builder_redis_1:/data/dump.rdb redis_backup_$(date +%Y%m%d_%H%M%S).rdb

# Restore backup
docker cp redis_backup_20240101_120000.rdb form-builder_redis_1:/data/dump.rdb
docker restart form-builder_redis_1
```

#### Elasticsearch
```bash
# Create snapshot
curl -X PUT "localhost:9200/_snapshot/backup/snapshot_1?wait_for_completion=true"

# Restore snapshot
curl -X POST "localhost:9200/_snapshot/backup/snapshot_1/_restore"
```

### File Backup
```bash
# Backup uploads
docker cp form-builder_backend_1:/app/uploads uploads_backup_$(date +%Y%m%d_%H%M%S)

# Restore uploads
docker cp uploads_backup_20240101_120000 form-builder_backend_1:/app/uploads
```

### Automated Backup Script
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# MongoDB backup
docker exec -i form-builder_mongodb_1 mongodump --archive --gzip > $BACKUP_DIR/mongo_$DATE.gz

# Redis backup
docker exec form-builder_redis_1 redis-cli SAVE
docker cp form-builder_redis_1:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Uploads backup
docker cp form-builder_backend_1:/app/uploads $BACKUP_DIR/uploads_$DATE

# Keep last 7 days of backups
find $BACKUP_DIR -name "*.gz" -o -name "*.rdb" -mtime +7 -delete
```

## Security

### Network Security

#### Firewall Configuration
```bash
# UFW configuration
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp  # SSH
ufw enable
```

#### SSL/TLS
- Use valid SSL certificates from Let's Encrypt or your CA
- Configure proper SSL protocols and ciphers
- Enable HTTP Strict Transport Security (HSTS)

### Application Security

#### Environment Variables
- Never commit secrets to version control
- Use Docker secrets or environment files
- Rotate secrets regularly

#### Database Security
- Enable authentication for all databases
- Use strong passwords
- Restrict network access to databases

#### File Security
- Set proper file permissions
- Use virus scanning for uploads
- Implement file size limits

### Monitoring Security

#### Log Monitoring
- Monitor logs for suspicious activity
- Set up log aggregation (ELK stack, Graylog)
- Configure alerts for security events

#### Intrusion Detection
- Monitor file integrity
- Detect unauthorized access attempts
- Set up fail2ban for brute force protection

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
docker-compose -f docker/docker-compose.prod.yml logs <service_name>

# Check resource usage
docker stats

# Check port conflicts
netstat -tulpn | grep :<port>
```

#### Database Connection Issues
```bash
# Check database service status
docker-compose -f docker/docker-compose.prod.yml ps mongodb

# Test database connection
docker exec -it form-builder_backend_1 python -c "
from pymongo import MongoClient
client = MongoClient('mongodb://mongodb:27017')
print(client.server_info())
"
```

#### High Memory Usage
```bash
# Check memory usage
docker stats --format "table {{.Container}}\t{{.MemUsage}}"

# Restart services
docker-compose -f docker/docker-compose.prod.yml restart
```

#### Performance Issues
```bash
# Check slow queries
docker exec form-builder_mongodb_1 mongotop

# Check Redis performance
docker exec form-builder_redis_1 redis-cli INFO memory

# Check Elasticsearch performance
curl -X GET "localhost:9200/_nodes/stats"
```

### Debug Mode

#### Enable Debug Logging
```bash
# In .env file
LOG_LEVEL=DEBUG
DEBUG=true

# Restart services
docker-compose -f docker/docker-compose.prod.yml restart backend
```

#### Shell Access
```bash
# Access container shell
docker exec -it form-builder_backend_1 bash

# Access specific service
docker exec -it form-builder_mongodb_1 mongo
```

## Maintenance

### System Updates

#### Docker Images
```bash
# Pull latest images
docker-compose -f docker/docker-compose.prod.yml pull

# Rebuild and restart
docker-compose -f docker/docker-compose.prod.yml up -d --force-recreate
```

#### Dependencies
```bash
# Update Python dependencies
cd backend
pip-compile requirements.in
pip install -r requirements.txt

# Update Docker images
docker-compose -f docker/docker-compose.prod.yml build
```

### Database Maintenance

#### MongoDB
```bash
# Repair database
docker exec form-builder_mongodb_1 mongod --repair

# Update statistics
docker exec form-builder_mongodb_1 mongo --eval "db.runCommand({collStats: 'forms'})"
```

#### Redis
```bash
# Optimize memory
docker exec form-builder_redis_1 redis-cli BGREWRITEAOF

# Clear expired keys
docker exec form-builder_redis_1 redis-cli FLUSHDB
```

#### Elasticsearch
```bash
# Optimize indices
curl -X POST "localhost:9200/_optimize"

# Clear cache
curl -X POST "localhost:9200/_cache/clear"
```

### Log Rotation

#### Configure Log Rotation
```bash
# Create logrotate configuration
cat > /etc/logrotate.d/form-builder << EOF
/var/lib/docker/containers/*/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker exec form-builder_backend_1 kill -USR1 $(cat /var/run/nginx.pid 2>/dev/null) 2>/dev/null || true
    endscript
}
EOF
```

#### Enable Log Rotation
```bash
# Test logrotate
logrotate -f /etc/logrotate.d/form-builder

# Enable automatic rotation
systemctl enable logrotate
systemctl start logrotate
```

## Support

### Getting Help

#### Documentation
- **API Documentation**: `/api/docs` (if Swagger enabled)
- **Service Documentation**: Individual service README files
- **Configuration Reference**: This deployment guide

#### Monitoring
- **Flower**: `http://localhost:5555` (Celery monitoring)
- **Redis Commander**: `http://localhost:8081` (Redis management)
- **Mongo Express**: `http://localhost:8082` (MongoDB management)

#### Logs
- **Application Logs**: `docker-compose logs -f backend`
- **Service Logs**: `docker-compose logs -f <service_name>`
- **System Logs**: `/var/log/syslog`

### Best Practices

#### Deployment
- Always test in development first
- Use version control for all configuration
- Implement automated testing and deployment
- Monitor system performance and health

#### Security
- Keep all components updated
- Use strong authentication and authorization
- Implement proper backup and recovery
- Monitor for security issues

#### Performance
- Monitor resource usage
- Implement proper caching strategies
- Optimize database queries
- Use appropriate scaling strategies

---

This deployment guide provides comprehensive instructions for setting up and maintaining the Form Builder Platform. For additional assistance, please refer to the project documentation or contact the development team.