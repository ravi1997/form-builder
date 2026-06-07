# Phase 3: Analysis Plan

This document details the step-by-step tasks, files, code structures, and verification criteria required to implement Phase 3.

---

## 1. Goal Overview
Build the visual Directed Acyclic Graph coder, topological sort engines (NetworkX), async Celery executor pipelines, Pandas-based transform and join operations, Elasticsearch search configurations, and Flutter node canvas components.

---

## 2. Detailed Task Breakdown

### Task 3.1: DAG Parsing & Topological Sort
* **Objective**: Evaluate analysis graph schemas in order.
* **Files to create/modify**:
  - `backend/app/engines/analysis_engine.py`
* **Implementation Details**:
  - Build validation handlers reading visual node coordinates and connection edges.
  - Construct a dependency graph using NetworkX. Check for execution loops.
  - Return a resolved array list mapping node ids sequentially.
* **Acceptance Criteria**: Running the solver on a cyclic connection raises a `GraphCycleException`. Running on a validated connection structure returns the execution order.

### Task 3.2: Celery Pipeline Executor
* **Objective**: Process computations asynchronously.
* **Files to create/modify**:
  - `backend/app/workers/analysis_tasks.py`
  - `backend/app/services/analysis_service.py`
* **Implementation Details**:
  - Write Celery worker jobs executing the topological sequence.
  - Standardize node output interfaces (Pandas DataFrames, scalars, formatted JSONs).
  - Cache results to `analysis_results` collection and handle step execution failures.
* **Acceptance Criteria**: Triggering a run starts background Celery jobs. Checking run status endpoints tracks executing steps.

### Task 3.3: Elasticsearch Query Nodes
* **Objective**: Enable full-text search filters inside analysis flows.
* **Files to create/modify**:
  - `backend/app/services/search_service.py`
  - `backend/app/workers/sync_tasks.py`
* **Implementation Details**:
  - Create index templates mapping submitted response values.
  - Build Celery worker jobs syncing form responses to Elasticsearch.
  - Define an analysis node execution step that converts inputs into Elasticsearch queries, returning a matching DataFrame.
* **Acceptance Criteria**: Creating a response indexes the record in Elasticsearch within seconds.
