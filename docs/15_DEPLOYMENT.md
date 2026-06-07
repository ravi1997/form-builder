# 15 — Deployment Specification

This document details the target environment requirements, deployment automation (Docker Compose), Nginx reverse proxy routing, and backup scripts.

---

## 1. Multi-Container Docker Compose

```yaml
# docker-compose.yml (Production configuration blueprint)
version: '3.8'

services:
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
      - upload_volume:/var/www/uploads:ro
      - web_static_volume:/var/www/html:ro
    depends_on:
      - backend

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    environment:
      - MONGO_URI=mongodb://mongo:27017/form_builder
      - REDIS_URI=redis://redis:6379/0
      - ELASTICSEARCH_URI=http://elasticsearch:9200
    volumes:
      - upload_volume:/app/uploads
    depends_on:
      - mongo
      - redis
      - elasticsearch

  celery_worker:
    build:
      context: ../backend
      dockerfile: Dockerfile
    command: celery -A app.wsgi.celery worker --loglevel=info
    environment:
      - MONGO_URI=mongodb://mongo:27017/form_builder
      - REDIS_URI=redis://redis:6379/0
      - ELASTICSEARCH_URI=http://elasticsearch:9200
    volumes:
      - upload_volume:/app/uploads
    depends_on:
      - redis
      - mongo

  mongo:
    image: mongo:7.0
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7.0-alpine

  elasticsearch:
    image: elasticsearch:8.11.1
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - es_data:/usr/share/elasticsearch/data

volumes:
  mongo_data:
  es_data:
  upload_volume:
  web_static_volume:
```

---

## 2. Nginx Configuration Blueprint

```nginx
# nginx.conf routing directive
upstream flask_backend {
    server backend:5000;
}

server {
    listen 80;
    server_name rpcapplication.aiims.edu;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name rpcapplication.aiims.edu;

    ssl_certificate /etc/nginx/certs/live.crt;
    ssl_certificate_key /etc/nginx/certs/live.key;

    # Static UI rendering
    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }

    # API request delegation
    location /api/ {
        proxy_pass http://flask_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Socket.IO websocket routing
    location /socket.io/ {
        proxy_pass http://flask_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## 3. Database Seeding (`scripts/seed.py`)

A script seeds system constants on initial startup:
- Registers the three default builder concept engines: `form_builder`, `analysis_coder`, `dashboard_builder`.
- Seeds the basic input question components into `component_schemas`.
- Provisions the root `super_admin` credential.
- Provisions default compliance definitions (e.g. `GDPR`, `HIPAA`).
