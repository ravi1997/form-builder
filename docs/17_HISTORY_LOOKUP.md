# 17 — History / Keyed Response Lookup

> **Authoritative scope**: This document defines the feature currently called "History" in the UI.
> **Reframe**: This is not an audit timeline. It is a keyed lookup tool for prior submitted responses.
> **Primary use case**: A respondent enters a stable key such as a patient ID, clicks an action button, and sees prior submissions that match that key.

---

## Table of Contents

1. [Overview](#overview)
2. [Placement and Ownership](#placement-and-ownership)
3. [Configuration Model](#configuration-model)
4. [Lookup Semantics](#lookup-semantics)
5. [Result Presentation](#result-presentation)
6. [Validation and Edge Cases](#validation-and-edge-cases)
7. [Security and Privacy](#security-and-privacy)
8. [API Contract](#api-contract)
9. [Patient ID Example](#patient-id-example)
10. [MVP Scope vs Deferred Scope](#mvp-scope-vs-deferred-scope)
11. [Decision Log](#decision-log)

---

## Overview

History is a response retrieval feature:

- The user types a value into a designated question.
- The user clicks an associated action button.
- The system searches prior submitted responses from the same form using that value as the lookup key.
- Matching submissions are shown inline or in a drawer/table without leaving the form.

This feature exists to support workflows such as:

- patient id lookup
- member / enrollee id lookup
- registration number lookup
- any other stable identifier where a respondent needs to retrieve or verify historical submissions

This feature does **not** mean:

- an audit timeline of edits, approvals, or system events
- analytics dashboards or aggregated reports
- cross-form search
- response export
- the existing fetch/prefill action button
- generic section/question actions unrelated to response retrieval

Those features belong to other systems.

---

## Placement and Ownership

The feature should be exposed in **both** places:

1. **Form-level settings**
   - Enables the feature globally.
   - Sets governance defaults, privacy rules, and result limits.
   - Lives with the form-level settings / privacy controls because it exposes historical response data.

2. **Question-level settings**
   - Marks an individual question as searchable.
   - Configures the action button label and result presentation.
   - Lives with the question properties because the trigger is attached to a specific question.

### Ownership rule

- The **form** owns feature availability and policy defaults.
- The **question** owns the specific search trigger.
- Question-level configuration inherits from the form unless explicitly overridden.

This gives one consistent mental model:

- form-level = "may this form expose response lookup at all?"
- question-level = "is this question searchable, and how is the result shown?"

---

## Configuration Model

### Form-level settings

Proposed form-level object:

```json
{
  "history_lookup": {
    "enabled": true,
    "default_match_mode": "normalized",
    "default_result_view": "drawer",
    "default_button_label": "Search history",
    "max_results": 10,
    "redact_private_fields": true,
    "allowed_roles": ["org_viewer", "org_editor", "org_admin"],
    "allow_anonymous_lookup": false,
    "include_archived_responses": false
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `boolean` | `false` | Master switch for the feature. If `false`, all question-level history controls are hidden or disabled. |
| `default_match_mode` | `string` | `"normalized"` | Default lookup comparison mode inherited by searchable questions. Enum: `"exact"`, `"normalized"`. |
| `default_result_view` | `string` | `"drawer"` | Default result presentation inherited by searchable questions. Enum: `"inline"`, `"drawer"`, `"table"`. |
| `default_button_label` | `string` | `"Search history"` | Default label for the question action button when a question does not override it. |
| `max_results` | `number` | `10` | Maximum number of records returned per lookup request. Hard upper bound is enforced server-side. |
| `redact_private_fields` | `boolean` | `true` | If `true`, result cards and drawers omit or mask fields marked private/sensitive. |
| `allowed_roles` | `array[string]` | Inherit existing form view access | Optional extra role restriction. If omitted, the feature inherits the form's existing access checks. |
| `allow_anonymous_lookup` | `boolean` | `false` | If `true`, anonymous users may execute lookups when the form itself allows anonymous viewing. Default is off. |
| `include_archived_responses` | `boolean` | `false` | If `true`, archived/deleted responses may be included for admin-grade workflows. Default off. |

### Question-level settings

Proposed question-level object:

```json
{
  "history_lookup": {
    "searchable": true,
    "button_label": "Find prior visits",
    "match_mode": "normalized",
    "result_view": "drawer",
    "result_question_ids": ["q_visit_date", "q_department", "q_status"],
    "allow_open_response": true
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `searchable` | `boolean` | `false` | Marks this question as a lookup trigger. If `false`, the action button is not shown. |
| `button_label` | `string` | Inherit from form default | Text shown on the action button. Keep it short and verb-led. |
| `match_mode` | `string` | Inherit from form default | Matching strategy for this question. Enum: `"exact"`, `"normalized"`. |
| `result_view` | `string` | Inherit from form default | How results are displayed. Enum: `"inline"`, `"drawer"`, `"table"`. |
| `result_question_ids` | `array[string]` | `[]` | Question IDs to show as summary columns/cards in the result list. If empty, the platform uses a minimal summary (`submitted_at`, `submission_number`, status). |
| `allow_open_response` | `boolean` | `true` | Whether a result row can be opened to inspect the full past submission. |

### Inheritance rules

- Question-level settings inherit from the form-level defaults when omitted.
- Question-level values override form-level values only for that question.
- If the form-level feature is disabled, question-level settings are ignored.

---

## Lookup Semantics

### Lookup key

- The lookup key is the value entered into the searchable question.
- The lookup is scoped to the **current question ID** by default.
- Question IDs are stable across commits, so historical responses remain searchable even as the form evolves.

### Match modes

#### `exact`

- Compare the stored value exactly after type coercion to a canonical string representation.
- No case folding, no whitespace normalization beyond storage canonicalization.
- Use this when the key is case-sensitive or must match a code exactly.

#### `normalized`

Recommended default.

- Trim leading/trailing whitespace.
- Collapse repeated internal whitespace to a single space.
- Apply Unicode normalization (`NFKC`).
- Lowercase before comparison.
- Convert numbers and dates to a canonical string representation before compare.

### Scope

MVP scope is **same form only**:

- Search only within submissions for the same form.
- Do not search across multiple forms.
- Do not search across arbitrary fields unless explicitly configured later.

### Sorting

- Default sort order is newest-first.
- Tie-break by submission number descending, then response ID descending if needed.

### Duplicate matches

- If multiple submissions match the same key, return all matches up to the configured limit.
- Do not collapse duplicates in the backend.
- The UI may group or visually summarise duplicates, but it must not hide records.

### Empty or invalid source value

- If the source question is empty after normalization, disable the button or show a validation message.
- If the source value cannot be normalized for the configured type, block the lookup and show a user-facing error.
- If the configured searchable question is known to be low-cardinality or non-unique across historical data, show a warning that the lookup may return many matches.

---

## Result Presentation

### What gets shown

The result list should show enough context to identify the matching submission without exposing unnecessary private data.

Recommended row fields:

- `submission_number`
- `submitted_at`
- `status`
- configured summary fields from `result_question_ids`
- optional responder label if the user is authorized to see it

### Result views

#### `inline`

- Results appear directly below the searchable question.
- Best for small, self-contained forms.

#### `drawer`

- Results open in a side drawer or bottom sheet.
- Best for complex forms where the main canvas should stay visible.

#### `table`

- Results appear in a compact table.
- Best for admin or internal workflows with many columns.

### Loading, empty, and error states

- **Loading**: button shows a spinner and disables repeat clicks.
- **Empty**: show a clear no-match state, e.g. `No previous submissions found for this value.`
- **Error**: show a compact banner with retry, but keep the source value in the input.
- **Permission denied**: show a minimal access-denied state and do not reveal whether the value exists.

### Opening a record

- If `allow_open_response` is `true` and the user has sufficient permission, clicking a row opens the full response in a read-only detail view.
- The detail view must respect existing redaction / privacy rules.

---

## Validation and Edge Cases

### Supported question types

MVP should allow only question types that serialize to a single stable scalar value:

- single-line text
- patient / member / registration id fields
- email
- phone
- number
- date
- barcode / code-like inputs
- dropdown / radio selections if they resolve to a single scalar value

### Unsupported question types

Do not allow lookup on:

- file upload
- image capture
- repeatable groups / matrix answers
- rich text / long multi-line text if the value is not stable enough
- computed-only fields that are not user-entered
- multi-select arrays unless an explicit adapter exists later

### Validation rules

- The form-level feature must be enabled before any searchable question can be saved.
- A searchable question must have a non-empty button label or inherit one from the form.
- The result view must be one of the supported enums.
- The limit must be a positive integer.
- If a result field ID no longer exists in the current schema, the builder must warn and disable the action until remapped.

### Edge cases

- **No matches**: return an empty result set and a helpful empty state.
- **Multiple submissions for the same key**: show all matches, newest first.
- **Same key with different casing/formatting**: normalized mode should still match.
- **Deleted or archived submissions**: excluded by default; included only when explicitly allowed.
- **Schema changes after old submissions exist**: question IDs remain stable across commits, so the lookup remains valid. If a searchable question is removed entirely, the UI must flag the configuration as stale.
- **Lookup against a field missing from old responses**: the lookup returns no match for those records; it must not crash.
- **Empty source question**: lookup is blocked until a valid key exists.

---

## Security and Privacy

### Access control

- The lookup endpoint must enforce the same organization and form access controls as the form itself.
- The feature may apply additional role restrictions if configured.
- Anonymous lookup is disabled by default.

### Privacy

- Private / sensitive result fields should be redacted unless explicitly allowed.
- Lookup results must not reveal hidden metadata beyond what the user is authorized to see.
- When access is denied, the UI should not leak whether the key exists.

### Audit and rate limiting

- Each lookup invocation should be logged as an access event.
- The lookup endpoint should be rate-limited to reduce enumeration risk.
- The audit record must capture who searched, which form was searched, and when the lookup occurred, but the UI is still a lookup tool, not an audit timeline.

---

## API Contract

### `GET /api/internal/v1/forms/<form_id>/history`

**Description**: Search prior submitted responses for a keyed value entered in a searchable question.

**Auth Requirement**: JWT access token plus normal form-view permissions.

**Query Parameters**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `question_id` | Yes | The searchable question ID whose value is used as the lookup key. |
| `primary_value` | Yes | The value entered by the user. |
| `match_mode` | No | Optional override. Enum: `"exact"`, `"normalized"`. If omitted, inherit the form/question default. |
| `limit` | No | Maximum number of records to return. Defaults to the form-level maximum. |
| `cursor` | No | Pagination cursor for the next page. |
| `include_archived` | No | Admin-only override to include archived/deleted responses. Defaults to `false`. |

**Success response**

```json
{
  "status": "success",
  "data": {
    "lookup": {
      "form_id": "603d4a259c6b8c2c5c994550",
      "question_id": "q_patient_id",
      "primary_value": "PAT-10293",
      "match_mode": "normalized"
    },
    "count": 3,
    "next_cursor": null,
    "results": [
      {
        "response_id": "603d4a259c6b8c2c5c99450a",
        "submission_number": 435,
        "submitted_at": "2026-06-07T10:15:00Z",
        "status": "submitted",
        "summary": {
          "q_patient_name": "Jane Doe",
          "q_visit_date": "2026-06-07",
          "q_department": "Cardiology"
        },
        "can_open": true
      }
    ]
  }
}
```

**Common error responses**

- `400 Bad Request`: missing question/value, invalid match mode, unsupported question type, stale configuration.
- `403 Forbidden`: user cannot view lookup results.
- `404 Not Found`: form not found or not visible to the caller.
- `429 Too Many Requests`: lookup rate limit exceeded.

---

## Patient ID Example

### Form setup

- Form-level history lookup is enabled.
- Default match mode is `normalized`.
- Default result view is `drawer`.
- Private fields are redacted.

### Question setup

- Question label: `Patient ID`
- Searchable: `true`
- Button label: `Find prior visits`
- Result fields:
  - `Visit date`
  - `Department`
  - `Visit status`

### Runtime flow

1. The user types `PAT-10293` in the Patient ID field.
2. The user clicks `Find prior visits`.
3. The system normalizes the key and searches prior submissions from the same form.
4. Three previous submissions are found.
5. The result drawer shows the three rows, newest first.
6. The user opens one row to inspect the full previous submission.

### Why this works

- The key is stable and human-readable.
- Normalized matching tolerates accidental casing and whitespace differences.
- The user stays inside the form and can make decisions quickly.

---

## MVP Scope vs Deferred Scope

### MVP

- form-level enable / disable
- one searchable question at a time
- exact or normalized matching
- same-form lookup only
- simple list or drawer result view
- newest-first sorting
- open full past submission when allowed
- redaction of private fields

### Deferred

- cross-form search
- partial or fuzzy matching
- search across multiple fields at once
- rich comparison / diff views
- advanced filtering
- role-matrix UI for fine-grained permissions
- auto-search while typing
- lookups across archived data by default
- duplicate grouping / merge of repeated keys

---

## Decision Log

- The feature is **question-triggered**, not an audit timeline.
- The feature is **scoped to the current form** for MVP.
- The form owns **policy defaults**; the question owns the **search trigger**.
- Matching defaults to **normalized** because it is safer for human-entered identifiers.
- Results default to a **drawer** because it keeps the user in the form.
- Private fields are **redacted by default**.
- Anonymous lookup is **off by default**.
