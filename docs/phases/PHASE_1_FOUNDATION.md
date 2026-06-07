# Phase 1: Foundation Plan

This document details the step-by-step tasks, files, code structures, and verification criteria required to implement Phase 1.

---

## 1. Goal Overview
Set up the base Docker-compose services (databases, queue brokers, caches, API shells), compile Flask application factories, define access rules and DB collections scoping, build JWT tokens rotation patterns, and construct the Flutter app shell.

---

## 2. Detailed Task Breakdown

### Task 1.1: Docker Infrastructure Setup
* **Objective**: Configure all services required for execution.
* **Files to create/modify**:
  - `docker/docker-compose.yml`
  - `docker/nginx/nginx.conf`
  - `docker/backend/Dockerfile`
  - `docker/frontend/Dockerfile`
* **Implementation Details**:
  - Set up service definition blocks: `nginx` (port 80/443), `backend` (port 5000), `celery_worker`, `mongo` (port 27017), `redis` (port 6379), `elasticsearch` (port 9200).
  - Configure Nginx upstream bindings and map certificates paths.
* **Acceptance Criteria**: Running `docker compose up -d` successfully boots all services and sets health status checks to `healthy`.

### Task 1.2: Flask Application Factory & Blueprints
* **Objective**: Scaffold route registries.
* **Files to create/modify**:
  - `backend/app/__init__.py`
  - `backend/app/config.py`
  - `backend/app/extensions.py`
  - `backend/wsgi.py`
* **Implementation Details**:
  - Write standard factory `create_app()` loading class settings from `config.py`.
  - Bind CORS permissions, PyMongo connectors, Redis managers, and registration paths.
* **Acceptance Criteria**: Sending a GET request to `/api/health` returns status code 200 and version information.

### Task 1.3: MongoDB Connection & Index Init
* **Objective**: Pre-configure database collection structures.
* **Files to create/modify**:
  - `backend/app/extensions.py`
  - `scripts/seed.py`
* **Implementation Details**:
  - PyMongo setup checks MongoDB links on app boot.
  - Implement index definitions (e.g. unique constraints on user email, TTL limits on session expires, indexing tags).
* **Acceptance Criteria**: Seeding the database generates the required indexes without collision errors.

### Task 1.4: Auth Flow - Register, Admin Approval & Login
* **Objective**: Build security registration and sign-in.
* **Files to create/modify**:
  - `backend/app/routes/auth.py`
  - `backend/app/services/auth_service.py`
  - `backend/app/utils/security.py`
* **Implementation Details**:
  - Registration sets user state to `pending_approval`.
  - Provide route `/api/internal/v1/users/<id>/approve` (super_admin scope) changing state to `active`.
  - Login checks bcrypt hashes and generates JWT access/refresh token structures.
* **Acceptance Criteria**: Submitting login request with valid credentials returns access and refresh token keys. Access is blocked if the user status is set to suspended.
