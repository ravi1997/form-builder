# Phase 2: Form Builder Plan

This document details the step-by-step tasks, files, code structures, and verification criteria required to implement Phase 2.

---

## 1. Goal Overview
Implement the visual Form Builder canvas (drag-drop properties), Git-like schema version control (commits, branches, branches conflict resolution), dynamic JSON UI rendering in Flutter, logic formulas evaluation, and offline Drift SQLite queues.

---

## 2. Detailed Task Breakdown

### Task 2.1: Versioning System - Commits & Branches
* **Objective**: Manage form schema changes via commits.
* **Files to create/modify**:
  - `backend/app/engines/form_engine.py`
  - `backend/app/routes/forms.py`
* **Implementation Details**:
  - Store revisions in the `form_commits` collection mapping properties.
  - Implement branch reference pointers (e.g. `main` HEAD pointing to commit).
  - Implement a diffing method comparing questions between commits.
* **Acceptance Criteria**: Creating a new branch from a commit and submitting modifications increments version indexes without altering parent commit objects.

### Task 2.2: 3-Way Schema Merge conflict Resolver
* **Objective**: Reconcile parallel changes made by developers.
* **Files to create/modify**:
  - `backend/app/engines/form_engine.py`
  - `backend/app/routes/forms.py`
* **Implementation Details**:
  - Compare base commit ancestor hash with branch commits (3-way merge).
  - Detect conflict properties (e.g. key renamed differently on both sides).
  - Return conflict JSON objects showing base, source, and target value maps.
* **Acceptance Criteria**: Attempting to merge branches with overlapping question modifications returns HTTP status code 409 and lists the conflict fields.

### Task 2.3: Flutter JSON UI Engine & Primitive Widgets
* **Objective**: Render compiled layout elements dynamically.
* **Files to create/modify**:
  - `frontend/lib/shared/json_ui_engine/json_ui_renderer.dart`
  - `frontend/lib/shared/json_ui_engine/widgets/text_input.dart`
  - `frontend/lib/shared/json_ui_engine/widgets/select_input.dart`
* **Implementation Details**:
  - Implement the UI rendering module mapping JSON component inputs directly to compiled Dart widgets.
  - Support text lines, paragraphs, integer metrics, multiple-choice options, drop-downs, date selectors, and check-boxes.
* **Acceptance Criteria**: Providing a JSON schema list correctly populates user interactive layout fields, capturing values inside Riverpod state scopes.
