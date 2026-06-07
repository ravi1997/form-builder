# Phase 5: Advanced Platform Plan

This document details the step-by-step tasks, files, code structures, and verification criteria required to implement Phase 5.

---

## 1. Goal Overview
Implement SaaS platform controls: GDPR consent enforcements, HIPAA access audit trackers, Email/SMS providers dispatch integrations, webhook callbacks, API Keys validation pipelines, rate limiters, storage quota calculations, and the admin control interfaces.

---

## 2. Detailed Task Breakdown

### Task 5.1: Compliance Enforcement Middleware
* **Objective**: Inject compliance workflows automatically based on organization choices.
* **Files to create/modify**:
  - `backend/app/utils/security.py`
  - `backend/app/services/audit_service.py`
* **Implementation Details**:
  - Build middlewares checking user org compliance settings.
  - GDPR: Anonymize IP logs, force consent inputs on viewer pages, and automate data purge tasks.
  - HIPAA: Record every data-access event into append-only logs.
* **Acceptance Criteria**: Form viewers show consent checkboxes when GDPR is enabled. Read queries log audit trails when HIPAA is active.

### Task 5.2: Notification & Webhook Engine
* **Objective**: Dispatch transactional messages and third-party callouts.
* **Files to create/modify**:
  - `backend/app/services/notification_service.py`
  - `backend/app/workers/notification_tasks.py`
* **Implementation Details**:
  - Integrate email/SMS dispatches via the AIIMS endpoints using `urllib` or `requests`.
  - Implement rule-based condition evaluators verifying payload variables.
  - Sign webhook callbacks using SHA-256 HMAC keys.
* **Acceptance Criteria**: Submitting a response triggers emails. Webhook targets receive signed payloads matching the schema structure.

### Task 5.3: Storage Quota Enforcement
* **Objective**: Limit disk storage allocations per organization.
* **Files to create/modify**:
  - `backend/app/workers/maintenance_tasks.py`
  - `backend/app/services/storage_service.py`
* **Implementation Details**:
  - Calculate directory disk sizes under `uploads/{org_id}` and fetch MongoDB document sizes.
  - Block upload endpoints once limits are reached.
* **Acceptance Criteria**: Triggering uploads when org quota is exceeded returns HTTP status code 400.
