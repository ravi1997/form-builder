# Phase 6: LLM Integration Plan

This document details the step-by-step tasks, files, code structures, and verification criteria required to implement Phase 6.

---

## 1. Goal Overview
Integrate LLM capability options: a custom LLM transformation node inside the Analysis Coder DAG, a conversational Copilot for building form configurations, automatic question recommendation panels, and response data summaries.

---

## 2. Detailed Task Breakdown

### Task 6.1: Unified LLM Client Interface
* **Objective**: Abstract LLM API calls behind a single connector client.
* **Files to create/modify**:
  - `backend/app/services/llm_service.py`
  - `backend/app/config.py`
* **Implementation Details**:
  - Implement dynamic API client loaders supporting OpenAI, Anthropic, or local Ollama servers.
  - Implement token-usage logging and cost mapping saved per organization context.
  - Scrub PII (Names, Emails, IPs) from text prompts before transmission.
* **Acceptance Criteria**: Running prompt requests returns correct textual formats and logs cost usage in MongoDB.

### Task 6.2: LLM Analysis Graph Node
* **Objective**: Inject AI prompts directly into transformations flows.
* **Files to create/modify**:
  - `backend/app/engines/analysis_engine.py`
  - `backend/app/plugins/builtin/llm_node/handler.py`
* **Implementation Details**:
  - Define a node component schema accepting table dataframes and prompt templates.
  - Format table data structures into prompt contexts and return parsed output fields.
* **Acceptance Criteria**: Running the analysis DAG passes DataFrame tables to the LLM and outputs structured column outputs.

### Task 6.3: Conversational Form Assistant
* **Objective**: Generate complete form configurations using natural language requests.
* **Files to create/modify**:
  - `backend/app/routes/forms.py`
  - `frontend/lib/features/form_builder/presentation/widgets/llm_copilot_drawer.dart`
* **Implementation Details**:
  - Implement a prompt endpoint on Flask that accepts description text.
  - Structure prompt templates to return a JSON schema mapping sections, repeatable sub-sections, and fields.
* **Acceptance Criteria**: Entering a description in the Copilot panel renders form components on the builder canvas.
