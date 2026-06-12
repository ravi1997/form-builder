# 06 — Form System

> **Authoritative reference**: Always read `/docs/CONTEXT.md` before modifying this document.  
> **Scope**: This document covers the complete Form System — schema specification, versioning, branching, response lifecycle, visibility rules, offline behavior, and backward compatibility.

---

## Table of Contents

1. [Overview](#overview)
2. [Form JSON Schema Specification](#form-json-schema-specification)
   - [Form Document](#form-document)
   - [form_commits.schema Object](#form_commitsschema-object)
   - [Section](#section)
   - [SubSection](#subsection)
   - [Question](#question)
   - [VisibilityRules](#visibilityrules)
   - [Condition Types](#condition-types)
   - [ValidationRule](#validationrule)
   - [CalculationDef](#calculationdef)
   - [FetchActionDef](#fetchactiondef)
   - [SkipLogicDef](#skiplogicdef)
3. [Form Versioning System (Git-Like Model)](#form-versioning-system-git-like-model)
4. [Branch Operations](#branch-operations)
5. [Production Branch Concept](#production-branch-concept)
6. [Merge and Conflict Flow](#merge-and-conflict-flow)
7. [Form Lifecycle](#form-lifecycle)
8. [Form Settings](#form-settings)
9. [Form Access Control](#form-access-control)
10. [Question Types (Primitive Components)](#question-types-primitive-components)
11. [Visibility Rules — Evaluation Algorithm](#visibility-rules--evaluation-algorithm)
12. [Skip Logic](#skip-logic)
13. [Calculation Definitions and Formula Engine](#calculation-definitions-and-formula-engine)
14. [Fetch Action Button](#fetch-action-button)
15. [Repeatable Sections and Sub-Sections](#repeatable-sections-and-sub-sections)
16. [Response Lifecycle](#response-lifecycle)
17. [Anonymous Response Handling](#anonymous-response-handling)
18. [File Upload in Forms](#file-upload-in-forms)
19. [Form Templates](#form-templates)
20. [Cover Page and Thank You Page](#cover-page-and-thank-you-page)
21. [Multi-Page Layout](#multi-page-layout)
22. [Offline Response Collection](#offline-response-collection)
23. [Legacy Response Display](#legacy-response-display)
24. [Backward Compatibility Algorithm](#backward-compatibility-algorithm)

---

## Overview

The Form System is the primary data collection mechanism of the platform. Forms are defined as structured JSON documents with a git-like versioning system. The structure of a form follows a strict hierarchy:

```
Form
 └─ Branch (e.g., "main", "v2-redesign")
     └─ Commit (snapshot of the full schema)
         └─ schema
             ├─ ui (theme, layout, cover page, thank you page)
             ├─ access (who can fill this form)
             ├─ settings (expiry, caps, edit policy)
             ├─ webhook_configs
             └─ sections[]
                 └─ Section
                     ├─ sub_sections[]
                     │    └─ SubSection
                     │        └─ questions[]
                     │             └─ Question
                     │                 ├─ visibility_rules
                     │                 ├─ validation_rules
                     │                 ├─ calculations
                     │                 ├─ fetch_action
                     │                 └─ skip_logic
                     └─ visibility_rules
```

Responses are always tied to a specific `commit_id`. This ensures that even after a form is updated, historical responses accurately reflect the version of the form that was filled.

---

## Form JSON Schema Specification

### Form Document

Stored in the `forms` MongoDB collection. This is the lightweight "pointer" document — it does not store the form content itself, only the branch/tag pointers.

```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "project_id": "ObjectId",
  "name": "Patient Intake Form",
  "description": "Used for new patient registration.",
  "branches": {
    "main": "commit_abc123",
    "v2-redesign": "commit_def456"
  },
  "production_branch": "main",
  "tags": {
    "v1.0": "commit_abc000",
    "stable-backup": "commit_abc123"
  },
  "template_id": null,
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "created_by": "ObjectId",
  "is_deleted": false,
  "deleted_at": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | `ObjectId` | Auto | Primary key. |
| `org_id` | `ObjectId` | **Yes** | Organisation that owns this form. |
| `project_id` | `ObjectId` | **Yes** | Project this form belongs to. |
| `name` | `string` | **Yes** | Form display name. Max 256 chars. |
| `description` | `string` | No | Optional description shown in the form listing. Max 1024 chars. |
| `branches` | `object` | **Yes** | Map of `branch_name → commit_id`. `"main"` branch always exists. Branch names must match `^[a-z0-9-_]+$`. |
| `production_branch` | `string` | **Yes** | The branch name that is currently "live" and accepting responses. Defaults to `"main"`. Must be a key in `branches`. |
| `tags` | `object` | No | Map of `tag_name → commit_id`. Used for named snapshots (like git tags). Tag names must match `^[a-z0-9._-]+$`. Immutable — once a tag is created, it should not be moved. |
| `template_id` | `ObjectId` or `null` | No | If this form was created from a template, the template's `_id`. Null otherwise. |

---

### form_commits.schema Object

The `form_commits` collection stores each commit as a full snapshot of the form schema at that point in time. The `schema` sub-document is the complete form definition.

```json
{
  "_id": "ObjectId",
  "form_id": "ObjectId",
  "commit_id": "a3f8c2d1e0b7",
  "parent_ids": ["prev_commit_id"],
  "author_id": "ObjectId",
  "message": "Added section 2 with medical history questions",
  "branch": "main",
  "tag": null,
  "timestamp": "ISODate",
  "schema": {
    "ui": { ... },
    "access": { ... },
    "settings": { ... },
    "webhook_configs": [...],
    "sections": [...]
  }
}
```

#### Commit Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | `ObjectId` | Auto | Primary key. |
| `form_id` | `ObjectId` | **Yes** | Parent form document. |
| `commit_id` | `string` | **Yes** | Unique identifier for this commit, per form. Generated as a 12-character hex string (SHA-like, not globally unique — unique within the form). Example: `"a3f8c2d1e0b7"`. |
| `parent_ids` | `array[string]` | **Yes** | Array of parent `commit_id` strings. Empty `[]` for the first commit (root). Exactly one element for regular commits. Two elements for merge commits (first = branch being merged into, second = the merged branch's tip). |
| `author_id` | `ObjectId` | **Yes** | User who created this commit (made the save). |
| `message` | `string` | **Yes** | Commit message. Max 512 chars. In the builder UI, this is prompted when the user saves or publishes. |
| `branch` | `string` | **Yes** | Branch name this commit belongs to at the time of creation. |
| `tag` | `string` or `null` | No | If a tag was created at this commit, the tag name. Null otherwise. |
| `timestamp` | `ISODate` | **Yes** | When this commit was created. |
| `schema` | `object` | **Yes** | Full form schema snapshot. See below for sub-fields. |

#### schema.ui Object

```json
"ui": {
  "theme": {
    "primary_color": "#2196F3",
    "background_color": "#FFFFFF",
    "font_family": "Roboto",
    "font_size_base": 14,
    "border_radius": 8,
    "input_style": "outlined"
  },
  "layout": "multi_page",
  "logo_url": "https://cdn.example.com/logo.png",
  "cover_page": {
    "enabled": true,
    "title": "Patient Intake Form",
    "description": "Please fill in your details carefully.",
    "image_url": null,
    "button_label": "Start"
  },
  "thank_you_page": {
    "enabled": true,
    "title": "Thank You!",
    "message": "Your response has been recorded.",
    "show_response_id": true,
    "redirect_url": null,
    "redirect_delay_seconds": null
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `theme` | `object` | **Yes** | Visual theming options. |
| `theme.primary_color` | `string` | **Yes** | Hex color for primary UI elements (buttons, active inputs). |
| `theme.background_color` | `string` | **Yes** | Hex color for the form background. Default: `"#FFFFFF"`. |
| `theme.font_family` | `string` | **Yes** | Font family name. Platform loads fonts from Google Fonts. Default: `"Roboto"`. |
| `theme.font_size_base` | `number` | **Yes** | Base font size in logical pixels. Default: `14`. Range: `10–24`. |
| `theme.border_radius` | `number` | No | Corner radius in pixels for inputs/cards. Default: `8`. |
| `theme.input_style` | `string` | No | Input border style. Enum: `"outlined"`, `"filled"`, `"underlined"`. Default: `"outlined"`. |
| `layout` | `string` | **Yes** | Form layout mode. Enum: `"single_page"`, `"multi_page"`, `"wizard"`. |
| `logo_url` | `string` or `null` | No | URL to display a logo at the top of the form. Null means no logo. |
| `cover_page` | `object` | **Yes** | Cover/welcome screen configuration. See [Cover Page and Thank You Page](#cover-page-and-thank-you-page). |
| `thank_you_page` | `object` | **Yes** | Post-submission screen configuration. See [Cover Page and Thank You Page](#cover-page-and-thank-you-page). |

#### schema.access Object

```json
"access": {
  "type": "org",
  "allowed_org_ids": ["ObjectId"],
  "allowed_group_ids": [],
  "allowed_user_ids": [],
  "allow_anonymous": false
}
```

See [Form Access Control](#form-access-control) for full details.

#### schema.settings Object

See [Form Settings](#form-settings) for full details.

#### schema.webhook_configs Array

```json
"webhook_configs": [
  {
    "url": "https://api.example.com/webhook",
    "events": ["response.submitted", "response.edited"],
    "secret": "hmac-signing-secret"
  }
]
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | `string` | **Yes** | HTTPS endpoint to deliver events to. |
| `events` | `array[string]` | **Yes** | List of events that trigger delivery. See CONTEXT.md §11 for all event types. For forms, relevant events: `"response.submitted"`, `"response.edited"`, `"form.published"`. |
| `secret` | `string` | **Yes** | HMAC SHA-256 signing secret. The platform signs each webhook payload with this key and includes the signature in the `X-Signature-SHA256` header. |

---

### Section

A top-level grouping within the form. In `multi_page` layout, each section typically maps to one page.

```json
{
  "id": "sec_550e8400",
  "title": "Personal Information",
  "description": "Please provide your personal details.",
  "repeatable": false,
  "max_repeats": 1,
  "min_repeats": 1,
  "visibility_rules": {
    "operator": "AND",
    "conditions": []
  },
  "sub_sections": [...]
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `string` | **Yes** | — | UUID (v4) generated at creation. Stable — never changes after creation. Used as the reference target for skip logic. |
| `title` | `string` | **Yes** | — | Section heading. Max 256 chars. Shown as a page title in `multi_page` layout. |
| `description` | `string` | No | `""` | Optional section-level description text shown below the title. |
| `repeatable` | `boolean` | No | `false` | Whether this entire section can repeat. If `true`, the respondent sees an "Add Another" button. |
| `max_repeats` | `number` | No | `10` | Maximum number of times this section can repeat. Only relevant if `repeatable: true`. Range: `1–100`. |
| `min_repeats` | `number` | No | `1` | Minimum number of times this section must have data (for validation). Only relevant if `repeatable: true`. |
| `visibility_rules` | `VisibilityRules` | **Yes** | `{operator:"AND", conditions:[]}` | Conditions that determine whether this section is shown. Empty conditions array = always visible. |
| `sub_sections` | `array[SubSection]` | **Yes** | — | Must contain at least one SubSection. |

---

### SubSection

A logical sub-grouping within a Section. Can be independently repeatable.

```json
{
  "id": "ssec_7c9d4f12",
  "title": "Contact Details",
  "repeatable": false,
  "max_repeats": 5,
  "visibility_rules": {
    "operator": "OR",
    "conditions": [...]
  },
  "questions": [...]
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `string` | **Yes** | — | UUID (v4). Stable identifier. Used as skip logic target. |
| `title` | `string` | No | `""` | Optional sub-section heading. If empty, no heading is rendered. |
| `repeatable` | `boolean` | No | `false` | Whether this sub-section can repeat independently of its parent section. |
| `max_repeats` | `number` | No | `10` | Max repeats when `repeatable: true`. Range: `1–100`. |
| `visibility_rules` | `VisibilityRules` | **Yes** | `{operator:"AND", conditions:[]}` | Conditional visibility. |
| `questions` | `array[Question]` | **Yes** | — | Must contain at least one Question. |

---

### Question

A single data collection field in the form.

```json
{
  "id": "q_3a1f7b2c",
  "type": "text_input",
  "label": "Full Name",
  "description": "Enter your full legal name as per your ID.",
  "required": true,
  "properties": {
    "placeholder": "e.g., Jane Doe",
    "max_length": 100
  },
  "visibility_rules": {
    "operator": "AND",
    "conditions": []
  },
  "validation_rules": [
    {
      "type": "min_length",
      "value": 2,
      "message": "Name must be at least 2 characters."
    }
  ],
  "calculations": [],
  "fetch_action": null,
  "skip_logic": null,
  "ui": {
    "plugin_version": "1.0.0",
    "full_width": true,
    "order": 1
  }
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `string` | **Yes** | — | UUID (v4). Stable across commits. This is the key used in `form_responses.answers`. Must be unique within the form. |
| `type` | `string` | **Yes** | — | Component type identifier. Must match a registered `component_schema.component_type`. Built-in types: see CONTEXT.md §9. |
| `label` | `string` | **Yes** | — | Question label text. Shown above the input. Max 512 chars. |
| `description` | `string` | No | `""` | Hint/description below the label. Supports a limited markdown subset (bold, italic, links). Max 1024 chars. |
| `required` | `boolean` | No | `false` | Whether this question must be answered before the form can be submitted. |
| `properties` | `object` | **Yes** | `{}` | Key-value pairs of component-specific properties. Must conform to the `PropertyDef` schema for this `type`. Validated against `component_schemas.properties` at save time. |
| `visibility_rules` | `VisibilityRules` | **Yes** | `{operator:"AND", conditions:[]}` | Determines whether this question is visible. |
| `validation_rules` | `array[ValidationRule]` | No | `[]` | Additional validation rules applied on top of `required`. |
| `calculations` | `array[CalculationDef]` | No | `[]` | Formula-driven auto-fill definitions. See [Calculation Definitions](#calculation-definitions-and-formula-engine). |
| `fetch_action` | `FetchActionDef` or `null` | No | `null` | Data pre-fill action triggered by a fetch button or automatically. See [Fetch Action Button](#fetch-action-button). |
| `skip_logic` | `SkipLogicDef` or `null` | No | `null` | Skip logic definition. See [Skip Logic](#skip-logic). |
| `ui` | `object` | No | `{}` | UI rendering overrides and metadata. |
| `ui.plugin_version` | `string` | No | Active plugin version at creation time | The plugin version used when this question was added. Used for version-pinned schema lookup. |
| `ui.full_width` | `boolean` | No | `true` | Whether the question occupies the full column width or half-width in the form. |
| `ui.order` | `number` | No | Sequential | Explicit ordering override (usually managed by the builder drag-and-drop). |

---

### VisibilityRules

```json
{
  "operator": "AND",
  "conditions": [
    { "type": "answer", "field_id": "q_abc", "operator": "equals", "value": "yes" },
    { "type": "role", "roles": ["org_admin", "org_editor"] }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `operator` | `string` | **Yes** | Logical combination operator for conditions. Enum: `"AND"`, `"OR"`. `"AND"` means ALL conditions must be true. `"OR"` means ANY condition must be true. |
| `conditions` | `array[Condition]` | **Yes** | List of conditions to evaluate. Empty array with any operator = always visible (equivalent to `always_visible` condition). |

---

### Condition Types

Conditions are a union type — each condition has a `type` field that determines its shape.

#### `type: "always_visible"`

```json
{ "type": "always_visible" }
```
Always evaluates to `true`. Used to explicitly mark something as unconditionally visible. Overrides any other conditions in the same rule if `operator: "OR"`.

#### `type: "always_hidden"`

```json
{ "type": "always_hidden" }
```
Always evaluates to `false`. Used by the builder to temporarily hide elements during development without deleting them. If `operator: "AND"`, makes the entire element hidden.

#### `type: "role"`

```json
{ "type": "role", "roles": ["org_admin", "org_editor"] }
```
Visible only to users whose org role (in the form's org) is in the `roles` array.

| Field | Type | Description |
|-------|------|-------------|
| `roles` | `array[string]` | List of role names. Valid values: `"org_admin"`, `"org_editor"`, `"org_analyst"`, `"org_viewer"`, `"project_owner"`, `"project_editor"`, `"project_analyst"`, `"project_viewer"`. |

For anonymous users: this condition evaluates to `false` (anonymous users have no role).

#### `type: "group"`

```json
{ "type": "group", "group_ids": ["ObjectId1", "ObjectId2"] }
```
Visible only to users who are members of at least one of the specified groups.

| Field | Type | Description |
|-------|------|-------------|
| `group_ids` | `array[string]` | Array of group ObjectId strings. |

For anonymous users: evaluates to `false`.

#### `type: "answer"`

```json
{
  "type": "answer",
  "field_id": "q_3a1f7b2c",
  "operator": "equals",
  "value": "yes"
}
```
Visible based on the value of another question's answer.

| Field | Type | Description |
|-------|------|-------------|
| `field_id` | `string` | The UUID of the question whose answer is evaluated. Must be a question defined earlier in the form (no forward references in AND chains — OR chains may have forward references but behavior is undefined until the referenced question is reached). |
| `operator` | `string` | Comparison operator. See table below. |
| `value` | `any` | The value to compare against. Type must match the referenced question's answer type. |

**Answer Condition Operators:**

| Operator | Description | Value Type |
|----------|-------------|------------|
| `equals` | Answer strictly equals `value`. | any |
| `not_equals` | Answer does not equal `value`. | any |
| `contains` | Answer (string or array) contains `value` as a substring or array element. | string or array element |
| `not_contains` | Inverse of `contains`. | string or array element |
| `greater_than` | Answer (number) > `value`. | number |
| `less_than` | Answer (number) < `value`. | number |
| `greater_than_or_equal` | Answer (number) >= `value`. | number |
| `less_than_or_equal` | Answer (number) <= `value`. | number |
| `in` | Answer is one of the values in `value` (array). | array |
| `not_in` | Answer is not any of the values in `value` (array). | array |
| `is_empty` | Answer is null, empty string, or empty array. `value` is ignored. | — |
| `is_not_empty` | Answer is not empty. `value` is ignored. | — |
| `matches_pattern` | Answer (string) matches the regex in `value`. | string (regex) |

---

### ValidationRule

```json
{
  "type": "min_length",
  "value": 5,
  "message": "Must be at least 5 characters."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `string` | **Yes** | Validation type. Enum: `"min"`, `"max"`, `"min_length"`, `"max_length"`, `"pattern"`, `"custom"`. |
| `value` | `any` | Conditional | The constraint value. For `"min"` / `"max"`: a number. For `"min_length"` / `"max_length"`: an integer. For `"pattern"`: a regex string. For `"custom"`: not used (logic is in plugin handler). |
| `message` | `string` | **Yes** | User-facing error message shown when validation fails. Max 256 chars. |

| Type | Applies To | Description |
|------|------------|-------------|
| `min` | `number_input`, `slider`, `rating` | Minimum numeric value. |
| `max` | `number_input`, `slider`, `rating` | Maximum numeric value. |
| `min_length` | `text_input`, `text_area` | Minimum character count. |
| `max_length` | `text_input`, `text_area` | Maximum character count (overrides `properties.max_length` if both set — ValidationRule takes precedence). |
| `pattern` | `text_input`, `email_input`, `url_input` | Regex pattern. Value must fully match (anchored with `^...$`). |
| `custom` | Any | Plugin-provided server-side validation. The plugin's `handler.py` is invoked with `action: "validate"`. |

---

### CalculationDef

```json
{
  "trigger": "on_change",
  "formula_ast": {
    "type": "binary_op",
    "op": "multiply",
    "left": {
      "type": "field_ref",
      "field_id": "q_weight_kg"
    },
    "right": {
      "type": "literal",
      "value": 2.2046
    }
  },
  "target_question_id": "q_weight_lbs"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trigger` | `string` | **Yes** | When to evaluate the formula. Enum: `"on_change"` (any referenced field changes), `"on_load"` (evaluated once when the form loads). |
| `formula_ast` | `object` | **Yes** | Abstract Syntax Tree (AST) produced by the visual formula builder. See [Calculation Definitions and Formula Engine](#calculation-definitions-and-formula-engine) for AST node types. |
| `target_question_id` | `string` | **Yes** | UUID of the question whose value this calculation writes to. The target question must have its `readonly` property set to `true` in the builder to prevent manual editing. |

---

### FetchActionDef

```json
{
  "source": "other_form_last_response",
  "form_id": "ObjectId",
  "url": null,
  "method": "GET",
  "headers": {},
  "body_template": null,
  "field_mapping": [
    {
      "source_path": "answers.q_patient_name.value",
      "target_question_id": "q_full_name"
    },
    {
      "source_path": "answers.q_dob.value",
      "target_question_id": "q_date_of_birth"
    }
  ],
  "offline_behavior": "use_cache"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | `string` | **Yes** | Data source type. Enum: `"own_previous_response"`, `"other_form_last_response"`, `"external_url"`. |
| `form_id` | `ObjectId` or `null` | Conditional | Required when `source` is `"other_form_last_response"`. The ObjectId of the form to fetch the last response from (scoped to the same org as the respondent). |
| `url` | `string` or `null` | Conditional | Required when `source` is `"external_url"`. The HTTP/HTTPS endpoint to call. |
| `method` | `string` | No | HTTP method for external URL calls. Enum: `"GET"`, `"POST"`. Default: `"GET"`. Ignored for `own_previous_response` and `other_form_last_response`. |
| `headers` | `object` | No | HTTP headers for external URL calls. Key-value map. Values can reference form properties with `{{property_key}}` syntax. |
| `body_template` | `string` or `null` | No | JSON body template string for `POST` requests. Supports `{{question_id}}` placeholders for current form answers. |
| `field_mapping` | `array[object]` | **Yes** | Maps source data paths to target question IDs in this form. See below. |
| `offline_behavior` | `string` | **Yes** | What to do when the fetch action cannot be completed offline. Enum: `"leave_blank"`, `"block_submission"`, `"use_cache"`. |

#### field_mapping Item

| Field | Type | Description |
|-------|------|-------------|
| `source_path` | `string` | JSONPath-like dot-notation path to extract from the source response. For form responses: `"answers.{question_id}.value"`. For external URLs: `"data.field_name"` (based on JSON structure of the response). Supports array index access: `"results[0].name"`. |
| `target_question_id` | `string` | UUID of the question in the current form that receives the fetched value. |

---

### SkipLogicDef

```json
{
  "conditions": {
    "operator": "AND",
    "conditions": [
      {
        "type": "answer",
        "field_id": "q_has_allergies",
        "operator": "equals",
        "value": "no"
      }
    ]
  },
  "jump_to": "section",
  "target_id": "sec_medical_history"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `conditions` | `VisibilityRules` | **Yes** | The condition set that, when true, triggers the skip. Uses the same `VisibilityRules` structure as visibility. |
| `jump_to` | `string` | **Yes** | Type of target to jump to. Enum: `"section"`, `"sub_section"`, `"question"`, `"end"`. `"end"` jumps to the Thank You page immediately. |
| `target_id` | `string` | Conditional | Required unless `jump_to` is `"end"`. The `id` of the target section, sub-section, or question to jump to. |

---

## Form Versioning System (Git-Like Model)

### Commit Model

Every save of a form's content creates a new `form_commits` document. A commit is an immutable snapshot of the complete `schema` object at that moment.

**Commit creation rules:**
- A commit is created when: the user clicks "Save" in the form builder, when publishing, or when creating a merge commit.
- The `commit_id` is a 12-character hex string generated as `sha256(form_id + timestamp + author_id)[:12]`. Unique per form (not globally).
- `parent_ids` is an array to support merge commits (two parents).
- The first commit on a new form has `parent_ids: []`.

**What is stored in a commit:**
- The complete `schema` object — no deltas or diffs. Every commit is self-contained.
- This means a form with 50 questions and 10 commits stores the full 50-question schema 10 times. This is intentional: it makes rendering historical responses simple and avoids complex delta reconstruction.

### Branch Model

A branch is a named pointer to a `commit_id`. When a new commit is made on a branch, the branch pointer advances to the new commit.

```
main: [A] → [B] → [C]  ← branch pointer currently at C
                   ↑
             production_branch
```

**Branch operations:**
- Creating a branch: creates a new branch pointer at the current commit of the source branch.
- Committing on a branch: creates a new commit with `parent_ids: [previous_branch_tip]` and advances the branch pointer.
- A branch is just a pointer — moving a branch pointer does not move or copy any commit data.

### Parent IDs for Merge Commits

A merge commit has `parent_ids` with exactly two entries:

```
main:     [A] → [B] → [D_merge]
                 ↑          ↑
v2:       [A] → [C] ────────┘

D_merge.parent_ids = ["B", "C"]
```

The merge commit represents the point at which `v2` branch was merged into `main`. After the merge, the `main` branch pointer moves to `D_merge`. The `v2` branch pointer remains at `C` (or can be deleted).

### How Branching Works in Practice

1. **Create branch**: `POST /api/internal/v1/forms/{form_id}/branches` with `{ "name": "v2-redesign", "from_branch": "main" }`. Creates a new pointer at `main`'s current commit.
2. **Edit on branch**: All saves on the `v2-redesign` branch create new commits that advance the `v2-redesign` pointer. `main` is unaffected.
3. **Publish branch**: Promotes `v2-redesign` to production by setting `forms.production_branch = "v2-redesign"`.
4. **Merge branches**: Creates a merge commit on the target branch (e.g., `main`) that incorporates changes from both branches.

---

## Branch Operations

### Create Branch

**Endpoint**: `POST /api/internal/v1/forms/{form_id}/branches`

**Request Body**:
```json
{
  "name": "v2-redesign",
  "from_branch": "main",
  "from_commit_id": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `string` | **Yes** | Branch name. Must match `^[a-z0-9-_]+$`. Max 64 chars. Must not already exist on this form. |
| `from_branch` | `string` | Conditional | Branch to fork from. Either `from_branch` or `from_commit_id` must be provided. |
| `from_commit_id` | `string` | Conditional | Specific commit to fork from. Either `from_branch` or `from_commit_id` must be provided. If both provided, `from_commit_id` takes precedence. |

**Behavior**: Creates a new entry in `forms.branches` with the same commit_id as the source branch/commit. No new commit is created.

### Switch Branch (Builder)

The builder switches branches by loading the commit pointed to by the target branch. This is a client-side concept — no server endpoint for "switching" exists. The client simply calls `GET /api/internal/v1/forms/{form_id}/branches/{branch_name}/schema` to load that branch's current content.

### Delete Branch

**Endpoint**: `DELETE /api/internal/v1/forms/{form_id}/branches/{branch_name}`

**Constraints**:
- Cannot delete the `main` branch.
- Cannot delete the branch that is currently set as `production_branch`.
- Deleting a branch only removes the pointer from `forms.branches`; all commits remain in `form_commits`.

### Publish Branch (Promote to Production)

**Endpoint**: `POST /api/internal/v1/forms/{form_id}/publish`

**Request Body**:
```json
{
  "branch": "v2-redesign",
  "commit_message": "v2 redesign complete — publishing to production"
}
```

**Behavior**:
1. Sets `forms.production_branch = "v2-redesign"`.
2. Creates a commit on the branch if the current state has unsaved changes (ensures the published state is always a commit).
3. Fires a `form.published` event (notifications + webhooks).
4. Updates Elasticsearch index for the form's searchable content.

---

## Production Branch Concept

The **production branch** is the branch whose latest commit is used when respondents open the form. It is the "live" version of the form.

- `forms.production_branch` stores the branch name (not a commit ID).
- When a respondent opens the form, the system reads `forms.production_branch`, then resolves it to a `commit_id` via `forms.branches[production_branch]`.
- This commit_id is stored in `form_responses.commit_id` for every new response.
- The production branch can be changed at any time by publishing a different branch. After the change, **new** responses use the new branch's commit; **existing** responses retain their original `commit_id`.

### What Happens When a New Version Is Published

1. `forms.production_branch` points to the new branch/commit.
2. All new form opens use the new schema.
3. Existing responses are **not** affected — they remain tied to their original `commit_id`.
4. Responses submitted against the old commit are tagged `is_legacy: true` (see [Legacy Response Display](#legacy-response-display)).
5. The system sends a `form.version_changed` notification to form editors.

---

## Merge and Conflict Flow

### Conflict Detection Algorithm

When merging branch B into branch A (A = target, B = source):

1. **Find the common ancestor**: Walk the `parent_ids` graph of both branches backward until a common commit is found. This is the **base commit**.
2. **Diff A vs base**: Compute the set of changes made on branch A since the base commit.
3. **Diff B vs base**: Compute the set of changes made on branch B since the base commit.
4. **Identify conflicts**: A conflict exists for a specific element (question, section, etc.) if that element was **modified by both A and B** since the base commit. Deletions count as modifications.

A "modification" is defined at the level of:
- A section (if `title`, `description`, `repeatable`, `min_repeats`, `max_repeats`, or `visibility_rules` changed).
- A sub-section (if `title`, `repeatable`, `max_repeats`, or `visibility_rules` changed).
- A question (if ANY field in the Question object changed).
- Form-level `ui`, `access`, `settings` objects as a whole (any change = one conflict unit).

**No conflict cases** (auto-merge):
- Element modified in A but not B → take A's version.
- Element modified in B but not A → take B's version.
- Element added in A, not in B → include in merge.
- Element added in B, not in A → include in merge.
- Element deleted in A, not modified in B → deleted in merge.
- Structural changes (re-ordering questions within a section) are auto-merged if no content conflicts exist.

### 3-Way Diff Data Structure

The conflict data is stored in the `pending_merges` collection:

```json
{
  "_id": "ObjectId",
  "form_id": "ObjectId",
  "branch_name": "main",
  "base_commit_id": "abc000",
  "their_commit_id": "def456",
  "our_changes": {
    "sections": { ... },
    "ui": { ... }
  },
  "conflict_fields": [
    "sections.sec_550e8400.title",
    "sections.sec_550e8400.sub_sections.ssec_7c9d4f12.questions.q_3a1f7b2c.label"
  ],
  "status": "pending",
  "resolver_id": null,
  "resolved_at": null,
  "created_at": "ISODate",
  "created_by": "ObjectId"
}
```

| Field | Description |
|-------|-------------|
| `branch_name` | The target branch being merged into. |
| `base_commit_id` | The common ancestor commit. |
| `their_commit_id` | The tip commit of the source branch (B). |
| `our_changes` | Delta of changes made on the target branch (A) since base. Stored as a JSON patch-like object. |
| `conflict_fields` | Dot-notation paths of all conflicting fields. |
| `status` | `"pending"` → `"resolved"` or `"abandoned"`. |

### Conflict Resolution UI Data Model

The Flutter builder presents a GitHub-style 3-way merge UI when a `pending_merge` is in `status: "pending"`. For each `conflict_field`, the UI shows:

```json
{
  "field_path": "sections.sec_550e8400.title",
  "base_value": "Personal Info",
  "our_value": "Personal Information",
  "their_value": "Patient Personal Details",
  "resolution": null
}
```

The user selects either `"ours"` or `"theirs"` (or edits a custom value) for each conflict. The UI enforces that all conflicts are resolved before the merge commit can be created.

### Merge Commit Creation

Once all conflicts are resolved:

1. The platform applies all non-conflicting auto-merged changes.
2. Applies the user-selected resolution for each conflict.
3. Creates a new `form_commits` document:
   - `parent_ids: [target_branch_tip, source_branch_tip]`
   - `message`: auto-generated or user-provided merge message.
   - `schema`: the fully resolved merged schema.
4. Updates `forms.branches[target_branch]` to the new merge commit.
5. Sets `pending_merges.status = "resolved"`.

---

## Form Lifecycle

### States

A form does not have an explicit `status` field in the `forms` document. Instead, lifecycle state is derived from the form's settings and timestamps:

| Derived State | Condition | Description |
|---------------|-----------|-------------|
| **Draft** | No branch is published to production and no responses exist | Form is being built; not accessible to respondents. |
| **Published / Active** | `production_branch` is set and `settings.expires_at` is null or in the future, and `settings.max_responses` is null or not yet reached | Form is live and accepting responses. |
| **Expired** | `settings.expires_at` is set and is in the past | Form is no longer accepting responses. Existing responses are still accessible. |
| **Closed (Response Cap Reached)** | `settings.max_responses` is set and the count of submitted responses >= that number | Form is no longer accepting responses due to cap. |
| **Deleted** | `forms.is_deleted = true` | Soft-deleted. Not accessible to any user. Retained in DB for audit. |

### State Transitions

```
            [Create Form]
                 │
                 ▼
             [Draft]
                 │
         [Publish Branch]
                 │
                 ▼
    [Published / Active] ──────────► [Expired]        (when expires_at passes)
            │                               │
            │                        (no new responses)
     [Max responses reached]               │
            │                              │
            ▼                              │
       [Closed]                    [Data still accessible]
            │
     [Admin soft-deletes]
            │
            ▼
        [Deleted]
```

**Transitions:**
- Draft → Published: Call publish endpoint. Sets `production_branch`.
- Published → Expired: Automatic (checked at request time against `expires_at`).
- Published → Closed: Automatic (checked against `max_responses` count at each new submission).
- Any → Deleted: Admin soft-deletes the form (`is_deleted: true`).
- Expired/Closed → Published: Update `settings.expires_at` to null/future, or increase `max_responses`.

---

## Form Settings

Stored in `form_commits.schema.settings`:

```json
"settings": {
  "expires_at": "2026-12-31T23:59:59Z",
  "max_responses": 1000,
  "allow_multiple_submissions": false,
  "allow_draft_save": true,
  "response_edit_policy": "time_window_edit",
  "edit_time_window_hours": 24,
  "edit_allowed_roles": ["org_admin"],
  "require_login": true
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `expires_at` | `ISODate` or `null` | No | `null` | UTC datetime after which the form stops accepting new responses. Null means no expiry. Checked server-side on every submission attempt. |
| `max_responses` | `number` or `null` | No | `null` | Maximum total submitted (non-draft) responses. Null means unlimited. When reached, new submissions return HTTP 409 with error code `FORM_RESPONSE_CAP_REACHED`. |
| `allow_multiple_submissions` | `boolean` | No | `false` | Whether an authenticated user can submit more than once. If `false`, a second submission attempt returns HTTP 409 `FORM_ALREADY_SUBMITTED`. For anonymous forms, this check is skipped (session-based dedup only). |
| `allow_draft_save` | `boolean` | No | `true` | Whether respondents can save a partial response and resume later. If `false`, the "Save Draft" button is hidden in the form viewer. |
| `response_edit_policy` | `string` | No | `"no_edit"` | When submitted responses can be edited. Enum values see below. |
| `edit_time_window_hours` | `number` | Conditional | `24` | Required when `response_edit_policy` is `"time_window_edit"`. Number of hours after submission during which editing is allowed. |
| `edit_allowed_roles` | `array[string]` | Conditional | `[]` | Required when `response_edit_policy` is `"role_edit"`. List of roles permitted to edit any response (not just their own). |
| `require_login` | `boolean` | No | `true` | If `false`, the form is accessible without authentication (for `access.type = "public"` forms). If `true`, even public forms require a login. |

**`response_edit_policy` Values:**

| Value | Description |
|-------|-------------|
| `no_edit` | Submitted responses cannot be edited by anyone (except `super_admin` via DB). |
| `role_edit` | Only users with a role in `edit_allowed_roles` can edit responses. |
| `time_window_edit` | The respondent can edit their own response within `edit_time_window_hours` hours of submission. |
| `always_edit` | The respondent can always edit their own response regardless of time. |

---

## Form Access Control

Stored in `form_commits.schema.access`:

```json
"access": {
  "type": "groups",
  "allowed_org_ids": ["ObjectId1"],
  "allowed_group_ids": ["ObjectId2", "ObjectId3"],
  "allowed_user_ids": [],
  "allow_anonymous": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `string` | **Yes** | Access mode. Enum: `"public"`, `"org"`, `"groups"`, `"users"`. |
| `allowed_org_ids` | `array[ObjectId]` | Conditional | Required when `type` is `"org"`. List of org IDs whose members can access the form. Typically the form's own org. Multiple orgs can be listed (cross-org sharing). |
| `allowed_group_ids` | `array[ObjectId]` | Conditional | Required when `type` is `"groups"`. List of group IDs whose members can access. |
| `allowed_user_ids` | `array[ObjectId]` | Conditional | Required when `type` is `"users"`. Explicit list of user IDs. |
| `allow_anonymous` | `boolean` | No | `false` | Whether unauthenticated users can fill this form. Only relevant when `type` is `"public"`. |

**Access Type Behavior:**

| Type | Who Can Access | Anonymous Allowed? |
|------|---------------|-------------------|
| `public` | Anyone with the link. | Yes, if `allow_anonymous: true`. |
| `org` | Members of the specified orgs. | No (must be authenticated org member). |
| `groups` | Members of the specified groups within the org. | No. |
| `users` | Only the explicitly listed user IDs. | No. |

**Access Check Flow (ABAC — evaluated in order):**

1. `super_admin` → always allowed.
2. `org_admin` of the form's org → always allowed.
3. Check `require_login`: if `false` and user is unauthenticated, proceed to access type check.
4. Check `access.type`:
   - `public`: Allow if `allow_anonymous: true` or user is authenticated.
   - `org`: Check user's `org_memberships` against `allowed_org_ids`.
   - `groups`: Check user's group memberships against `allowed_group_ids`.
   - `users`: Check `allowed_user_ids`.
5. If none match → HTTP 403.

### Anonymous Response Handling

See [Anonymous Response Handling](#anonymous-response-handling).

---

## Question Types (Primitive Components)

All primitive question types accept these base properties (from the component schema):

| Property | Type | Description |
|----------|------|-------------|
| `label` | `string` | Question label text. |
| `placeholder` | `string` | Hint text inside the input. |
| `required` | `boolean` | Whether required. |
| `disabled` | `boolean` | Renders the input as non-interactive. |
| `readonly` | `boolean` | Input is visible but not editable (distinct from `disabled` — no grayed-out style). |
| `hint_text` | `string` | Additional guidance shown below the input. |
| `error_message` | `string` | Override error message (used when validation fails). |

### Text & Input Types

| Type | Answer Value Type | Key Properties |
|------|------------------|----------------|
| `text_input` | `string` | `max_length: number`, `min_length: number`, `pattern: string` |
| `text_area` | `string` | `max_length: number`, `rows: number` (visible row count) |
| `number_input` | `number` | `min: number`, `max: number`, `step: number`, `decimal_places: number` |
| `email_input` | `string` | Built-in email format validation. No extra properties beyond base. |
| `phone_input` | `object` `{country_code: string, number: string}` | `default_country: string` (ISO 3166-1 alpha-2 code) |
| `password_input` | `string` | `min_length: number`. Stored as plaintext in responses (it's for form data, not auth). |
| `url_input` | `string` | Built-in URL format validation. |

### Selection Types

| Type | Answer Value Type | Key Properties |
|------|------------------|----------------|
| `dropdown` | `string` (selected option value) | `options: array[{value, label}]`, `searchable: boolean` |
| `multi_select` | `array[string]` | `options: array[{value, label}]`, `min_selections: number`, `max_selections: number` |
| `radio_group` | `string` | `options: array[{value, label}]`, `layout: "horizontal"/"vertical"` |
| `checkbox` | `boolean` | `checked_label: string`, `unchecked_label: string` |
| `checkbox_group` | `array[string]` | `options: array[{value, label}]`, `min_selections: number`, `max_selections: number`, `layout: "horizontal"/"vertical"/"grid"` |
| `toggle` | `boolean` | `on_label: string`, `off_label: string` |
| `button_group` | `string` | `options: array[{value, label}]`, `multi_select: boolean` (if true, answer is `array[string]`) |

### Date & Time Types

| Type | Answer Value Type | Key Properties |
|------|------------------|----------------|
| `date_picker` | `string` (ISO 8601 date: `"YYYY-MM-DD"`) | `min_date: string`, `max_date: string`, `date_format: string` |
| `time_picker` | `string` (24h time: `"HH:MM"`) | `min_time: string`, `max_time: string` |
| `datetime_picker` | `string` (ISO 8601 datetime: `"YYYY-MM-DDTHH:MM:SS"`) | `min_datetime: string`, `max_datetime: string` |
| `date_range_picker` | `object` `{start: "YYYY-MM-DD", end: "YYYY-MM-DD"}` | `min_date: string`, `max_date: string`, `max_range_days: number` |

### Media & File Types

| Type | Answer Value Type | Key Properties |
|------|------------------|----------------|
| `file_upload` | `array[ObjectId]` (file_upload IDs) | `allowed_types: array[string]` (MIME types), `max_size_bytes: number`, `max_files: number` |
| `image_capture` | `array[ObjectId]` | `max_files: number`, `allow_gallery: boolean`, `allow_camera: boolean`, `max_size_bytes: number` |
| `signature` | `string` (base64 PNG data URL) | `stroke_color: string`, `background_color: string` |
| `audio_record` | `ObjectId` (single file_upload ID) | `max_duration_seconds: number` |

### Interactive Types

| Type | Answer Value Type | Key Properties |
|------|------------------|----------------|
| `rating` | `number` | `max_stars: number` (default 5), `allow_half: boolean`, `icon: "star"/"heart"/"thumbs"` |
| `slider` | `number` | `min: number`, `max: number`, `step: number`, `show_value: boolean`, `show_labels: boolean` |
| `number_stepper` | `number` | `min: number`, `max: number`, `step: number` |
| `color_picker` | `string` (hex color `"#RRGGBB"`) | `allow_opacity: boolean`, `presets: array[string]` |

### Location & Special Types

| Type | Answer Value Type | Key Properties |
|------|------------------|----------------|
| `location_picker` | `object` `{lat: number, lng: number, address: string}` | `show_map: boolean`, `allow_manual_entry: boolean`, `accuracy_threshold_meters: number` |
| `barcode_scanner` | `string` (decoded barcode value) | `formats: array[string]` (e.g., `["qr_code", "code_128"]`), `allow_manual_entry: boolean` |
| `fetch_button` | `null` (it's a trigger, not a data field) | `button_label: string`, `loading_label: string`, `success_label: string` |

### Display Types (Non-Input)

| Type | Answer Value | Key Properties |
|------|-------------|----------------|
| `heading` | — (no answer) | `text: string`, `level: number` (1–6, like H1–H6), `alignment: "left"/"center"/"right"` |
| `paragraph` | — (no answer) | `text: string` (supports markdown subset), `alignment: string` |
| `divider` | — (no answer) | `style: "solid"/"dashed"/"dotted"`, `thickness: number`, `color: string` |
| `image_display` | — (no answer) | `url: string`, `alt_text: string`, `width: string` (`"full"`, `"half"`, or pixel value), `caption: string` |
| `video_display` | — (no answer) | `url: string`, `autoplay: boolean`, `controls: boolean`, `caption: string` |

Display types do not generate answer entries in `form_responses.answers`.

---

## Visibility Rules — Evaluation Algorithm

### When Evaluation Happens

Visibility rules are evaluated:
1. **On form load**: Initial visibility state for all elements.
2. **On any answer change**: Re-evaluate all visibility rules for all questions that reference the changed question's `field_id`.
3. **On section navigation** (in `multi_page` / `wizard` mode): Sections are evaluated before navigating to them.

### Evaluation Algorithm

```
function evaluateVisibility(rules: VisibilityRules, answers: Map, user: User) -> boolean:
  if rules.conditions is empty:
    return true  # empty conditions = always visible

  results = []
  for condition in rules.conditions:
    results.append(evaluateCondition(condition, answers, user))

  if rules.operator == "AND":
    return all(results)
  else:  # "OR"
    return any(results)

function evaluateCondition(condition: Condition, answers: Map, user: User) -> boolean:
  if condition.type == "always_visible":
    return true

  if condition.type == "always_hidden":
    return false

  if condition.type == "role":
    return user.role in condition.roles

  if condition.type == "group":
    return any(g in user.group_ids for g in condition.group_ids)

  if condition.type == "answer":
    answer = answers.get(condition.field_id)
    return evaluateAnswerCondition(answer, condition.operator, condition.value)
```

### Important Evaluation Rules

1. **Hidden parent → children implicitly hidden**: If a Section is hidden, all its SubSections and Questions are automatically hidden regardless of their own visibility rules. Hidden elements are never rendered into the widget tree.

2. **Required + hidden**: A question that is hidden due to visibility rules is **not** required for submission, even if its `required: true`. The server validates required fields only for visible questions.

3. **Answer condition on unanswered question**: If `condition.field_id` refers to a question the user hasn't answered yet, the answer is treated as `null`. `is_empty` evaluates to `true`, all other operators evaluate to `false`.

4. **Anonymous users and role/group conditions**: `role` and `group` conditions always evaluate to `false` for anonymous users, effectively hiding role/group-restricted elements.

5. **Circular references**: The form builder prevents circular visibility references (Question A's visibility depends on Question B, which depends on Question A). Circular references in the saved schema are evaluated defensively: a maximum evaluation depth of 5 is enforced; if exceeded, the element is shown.

---

## Skip Logic

### How Jump Targets Are Resolved

Skip logic is evaluated at the **question level** — when a question with `skip_logic` is answered. The flow:

1. User answers question Q (which has `skip_logic` defined).
2. Flutter evaluates `skip_logic.conditions` against current `answers` map.
3. If conditions evaluate to `true`:
   - Determine `jump_to` type and `target_id`.
   - Mark all intermediate questions/sub-sections/sections between Q and the target as **skipped** in the local answer state (answers for skipped questions are cleared/nulled).
   - Navigate the form to the target.

### Jump Target Resolution

| `jump_to` | Resolution |
|-----------|-----------|
| `"question"` | Find the question with `id == target_id` anywhere in the form. Navigate to the page/section containing it (in multi-page mode). |
| `"sub_section"` | Find the sub-section with `id == target_id`. Navigate to the page containing it. |
| `"section"` | Find the section with `id == target_id`. In multi-page mode, navigate to that page. |
| `"end"` | Submit the form immediately (if all non-skipped required fields are answered) or jump to the Thank You page. `target_id` is ignored. |

### Edge Cases

- **Jumping backward**: Skip logic can jump backward in the form. This is unusual but valid. The form viewer allows it. Jumping backward does NOT clear answers from previously answered questions.
- **Jumping to a hidden section**: If the target section is hidden by its own `visibility_rules`, the jump is skipped and evaluation continues to the next question in sequence.
- **Jumping to an already-answered section**: The user lands on the target. Previously entered answers for that section are preserved. If the section was hidden before (and thus answers were cleared), it re-appears empty.
- **Jumping to end in a required-field form**: If non-skipped required fields remain unanswered, the form viewer prevents submission and highlights the missing fields. The `"end"` jump target only triggers form completion if all visible, non-skipped required fields have valid answers.
- **Multiple skip logic evaluations**: If Question A skips to Section C, and within Section C there's a question B with skip logic that skips to Section D, both skip logics apply in sequence. The net result: the user skips A→C, then within C skips B→D.
- **Skip logic on hidden questions**: Skip logic on a question that is itself hidden (due to visibility rules) is never evaluated. The question is treated as unanswered.

### Skipped Answers in Response Storage

Skipped questions are stored in `form_responses.answers` with:
```json
{
  "q_skipped_question_id": {
    "value": null,
    "display_value": null,
    "skipped": true,
    "answered_at": null
  }
}
```

This distinction is important for analysis nodes — they can differentiate between "not answered" (skipped) and "answered with a blank value".

---

## Calculation Definitions and Formula Engine

### Formula AST Structure

The visual formula builder in the Flutter app produces an AST (Abstract Syntax Tree) stored in `CalculationDef.formula_ast`. The AST is evaluated at runtime by the `formula_engine.py` on the backend (for server-side recalculation on submission) and by a Dart equivalent in the Flutter app (for real-time client-side updates).

### AST Node Types

All AST nodes have a `type` field discriminating their shape.

#### `literal` — A constant value

```json
{ "type": "literal", "value": 2.2046, "value_type": "number" }
```

| Field | Values | Description |
|-------|--------|-------------|
| `value` | any | The literal value. |
| `value_type` | `"number"`, `"string"`, `"boolean"` | Type of the literal. |

#### `field_ref` — Reference to another question's current answer

```json
{ "type": "field_ref", "field_id": "q_weight_kg" }
```

Resolves to the current answer value of the referenced question. If the question is unanswered or hidden, resolves to `null`.

#### `binary_op` — Binary arithmetic or comparison operation

```json
{
  "type": "binary_op",
  "op": "add",
  "left": { "type": "field_ref", "field_id": "q_a" },
  "right": { "type": "literal", "value": 10 }
}
```

| Op | Description | Input Types | Output Type |
|----|-------------|-------------|-------------|
| `add` | Left + Right | number | number |
| `subtract` | Left - Right | number | number |
| `multiply` | Left × Right | number | number |
| `divide` | Left ÷ Right | number | number (null if Right is 0) |
| `modulo` | Left % Right | integer | integer |
| `power` | Left ^ Right | number | number |
| `concat` | String concatenation | string | string |
| `equals` | Left == Right | any | boolean |
| `not_equals` | Left != Right | any | boolean |
| `greater_than` | Left > Right | number | boolean |
| `less_than` | Left < Right | number | boolean |
| `and` | Left AND Right | boolean | boolean |
| `or` | Left OR Right | boolean | boolean |

#### `unary_op` — Unary operation

```json
{
  "type": "unary_op",
  "op": "negate",
  "operand": { "type": "field_ref", "field_id": "q_value" }
}
```

| Op | Description |
|----|-------------|
| `negate` | Arithmetic negation (-x) |
| `not` | Boolean NOT |
| `abs` | Absolute value |
| `round` | Round to nearest integer |
| `floor` | Floor |
| `ceil` | Ceiling |

#### `function_call` — Named function call

```json
{
  "type": "function_call",
  "function": "if",
  "args": [
    { "type": "field_ref", "field_id": "q_condition" },
    { "type": "literal", "value": "Yes" },
    { "type": "literal", "value": "No" }
  ]
}
```

**Supported Functions:**

| Function | Args | Return | Description |
|----------|------|--------|-------------|
| `if` | `[condition, then_value, else_value]` | any | Ternary if. |
| `sum` | `[...number_refs]` | number | Sum of all arg values. Args can be field_refs. |
| `average` | `[...number_refs]` | number | Average. |
| `min` | `[...number_refs]` | number | Minimum. |
| `max` | `[...number_refs]` | number | Maximum. |
| `count_if` | `[condition_ast, ...field_refs]` | integer | Count fields where condition is true. |
| `to_number` | `[value]` | number or null | Parse string as number. |
| `to_string` | `[value]` | string | Coerce to string. |
| `date_diff_days` | `[date1, date2]` | number | Days between two date answers. |
| `date_format` | `[date, format_string]` | string | Format a date value. |
| `length` | `[value]` | number | String length or array length. |
| `lookup` | `[field_ref, key]` | any | Look up a key in an object answer (e.g., phone_input.country_code). |

### Formula Engine Evaluation

**Client-side (Dart):** The Flutter app evaluates formulas in real-time as the user fills the form. When a `field_ref` changes and a `CalculationDef` with `trigger: "on_change"` references that field, the formula is re-evaluated and the result is written to the `target_question_id`.

**Server-side (Python `formula_engine.py`):** On form submission, the server re-evaluates all `CalculationDef` formulas against the submitted answers. If the server-computed value differs from the client-submitted value (due to tampering or client bugs), the server's value takes precedence and overwrites it.

**Null propagation**: Any operation involving a `null` operand returns `null`, except:
- `if(null, then, else)` → evaluates `else`.
- `concat(null, "x")` → `"x"`.
- `sum(1, null, 2)` → `3` (nulls are ignored in aggregate functions).

---

## Fetch Action Button

The `fetch_button` question type triggers a `FetchActionDef` to pre-populate one or more fields in the form with external data.

### Source Types

#### `own_previous_response`

Fetches the authenticated user's most recent **submitted** response to this same form (the current form). 

- Offline behavior is always `"use_cache"` — the last synced response draft is used.
- The respondent must be authenticated. Anonymous users cannot use this source.
- Field mapping resolves against the previous response's `answers` map.

#### `other_form_last_response`

Fetches the authenticated user's most recent submitted response from a different form (`form_id` in `FetchActionDef`).

- The referenced form must be in the same org.
- The user must have at least `org_viewer` access to the referenced form.
- Offline behavior: configurable (`"leave_blank"`, `"block_submission"`, `"use_cache"`).
- `"use_cache"`: Uses the last cached response for the referenced form from Drift.

#### `external_url`

Makes an HTTP request to the specified `url`.

- Requires the server-side fetch proxy: the Flutter app calls `POST /api/internal/v1/fetch-action/proxy` with the `FetchActionDef`, and the backend makes the HTTP request, applies field mapping, and returns the mapped values. This avoids CORS issues on web and allows server-side caching.
- For `internet_access` restricted URLs: the proxy call fails with a configuration error if the backend is not configured to allow outbound requests.
- Offline behavior: `"leave_blank"` or `"block_submission"` (cannot use cache for external URLs unless a previous successful fetch was cached).

### Field Mapping Algorithm

For each `field_mapping` entry `{source_path, target_question_id}`:

1. Parse `source_path` using dot-notation and array index notation.
2. Traverse the source data object (response JSON or external API JSON) following the path.
3. If the path resolves to a value, write it to the `target_question_id` answer field.
4. If the path resolves to `null` or does not exist, the target field is left unchanged (not cleared).
5. Type coercion: if the source value type doesn't match the target question's answer type, attempt coercion:
   - String → Number: `parseFloat()`. If fails, leave unchanged and log a warning.
   - Number → String: `toString()`.
   - Any → Boolean: truthy/falsy conversion.
   - Mismatched complex types (e.g., string → object): leave unchanged, log warning.

### Offline Behavior

| `offline_behavior` | What Happens When Offline |
|-------------------|--------------------------|
| `leave_blank` | The fetch action is silently skipped. Target fields remain at their current values (or empty). Form submission is allowed. |
| `block_submission` | The fetch action is required. If offline, an error banner is shown: "Cannot submit — requires network for pre-fill". Submission is blocked until connectivity is restored and the fetch succeeds. |
| `use_cache` | The platform uses the last successfully fetched values (cached in Drift). If no cache exists, falls back to `leave_blank`. |

For keyed response lookup ("History"), see [17_HISTORY_LOOKUP.md](./17_HISTORY_LOOKUP.md).

---

## Repeatable Sections and Sub-Sections

### How Repetition Works

If `Section.repeatable` or `SubSection.repeatable` is `true`, the form viewer renders the section/sub-section with an "Add Another" button. Each time the user clicks "Add Another", a new iteration of the section/sub-section appears, with its own set of inputs.

The maximum number of iterations is enforced client-side (by hiding "Add Another" when `max_repeats` is reached) and server-side (by validating the response).

### How Multiple Iterations Are Stored in Responses

Repeatable data is stored in `form_responses.repeat_groups`:

```json
"repeat_groups": {
  "sec_medical_history": [
    {
      "iteration": 0,
      "answers": {
        "q_condition_name": { "value": "Hypertension", "answered_at": "ISODate" },
        "q_diagnosis_year": { "value": 2018, "answered_at": "ISODate" }
      }
    },
    {
      "iteration": 1,
      "answers": {
        "q_condition_name": { "value": "Diabetes Type 2", "answered_at": "ISODate" },
        "q_diagnosis_year": { "value": 2020, "answered_at": "ISODate" }
      }
    }
  ]
}
```

- `repeat_groups` is keyed by the `section_id` or `sub_section_id` of the repeatable element.
- Each element in the array is one iteration, with an `iteration` index (0-based) and its own `answers` map.
- The `answers` object within each iteration uses the same question IDs as the base schema.

**Non-repeatable answers**: Questions that are not part of a repeatable context remain in the top-level `form_responses.answers`. Question IDs are globally unique within a form, so there is no ambiguity.

**Nested repeatability**: A repeatable Sub-Section within a repeatable Section stores its iterations nested:
```json
"repeat_groups": {
  "sec_outer": [
    {
      "iteration": 0,
      "answers": { ... },
      "nested_repeat_groups": {
        "ssec_inner": [
          { "iteration": 0, "answers": { ... } },
          { "iteration": 1, "answers": { ... } }
        ]
      }
    }
  ]
}
```

### Min/Max Validation

| Constraint | Field | Validation |
|-----------|-------|-----------|
| Minimum iterations | `Section.min_repeats` or `SubSection.max_repeats` | Server validates that `repeat_groups[id].length >= min_repeats` on submission. If not met, returns HTTP 422 with error identifying the section. |
| Maximum iterations | `Section.max_repeats` or `SubSection.max_repeats` | Server rejects if `repeat_groups[id].length > max_repeats`. Client enforces by disabling "Add Another" at max. |

### Required Fields in Repeatable Sections

Required question validation applies **per iteration**. If `q_condition_name` is required and the user has 2 iterations but left the second one's `q_condition_name` blank, validation fails for that iteration specifically.

---

## Response Lifecycle

### States

| State | Description |
|-------|-------------|
| `draft` | Response is saved but not submitted. Stored in `response_drafts` collection (or `form_responses` with `status: "draft"` for server-side drafts). |
| `submitted` | Response has been formally submitted. |

**Note**: There is no explicit "edited" state. Edits to a submitted response are tracked in `form_responses.edit_history` but the `status` remains `"submitted"`.

### Draft State

When `settings.allow_draft_save: true`:
- Client auto-saves the partial response to Drift every 30 seconds during form fill.
- User can explicitly click "Save Draft" to push the draft to the server (`response_drafts` collection).
- The draft is identified by `(form_id, respondent_id)` — unique per user per form.
- If the user re-opens the form, the platform detects a draft exists and offers to resume or start fresh.
- Drafts expire after 30 days (`response_drafts.expires_at`, TTL index).

### Submission Flow

1. User clicks "Submit".
2. Flutter client performs client-side validation (required fields, visibility-adjusted).
3. If validation passes, `POST /api/internal/v1/forms/{form_id}/responses`.
4. Server performs:
   a. Auth check + access check.
   b. Schema re-validation (is the form still accepting responses? expiry? max_responses?).
   c. Server-side formula recalculation (overwrites client-computed values).
   d. Server-side plugin validation (if any questions use `custom` ValidationRule).
   e. Deduplication check (if `allow_multiple_submissions: false`).
   f. Assigns `submission_number` (atomic increment per form).
   g. Inserts `form_responses` document with `status: "submitted"`.
   h. Deletes the `response_drafts` entry for this user+form (if exists).
   i. Fires `response.submitted` event → notification engine + webhooks.
   j. Queues Elasticsearch indexing.
5. Server returns HTTP 201 with the response document.

### Response Edit Flow

1. If `response_edit_policy` allows editing, user sees "Edit Response" in the responses view.
2. `PATCH /api/internal/v1/forms/{form_id}/responses/{response_id}`.
3. Server validates edit permissions (policy check: time window, role check).
4. Server records the before-state in `edit_history`:
   ```json
   {
     "edited_at": "ISODate",
     "edited_by": "ObjectId",
     "before": { "answers": { ... } },
     "after": { "answers": { ... } }
   }
   ```
5. Applies the new answers (full replace of `answers` + `repeat_groups`).
6. Fires `response.edited` event.
7. Response `status` remains `"submitted"`.

---

## Anonymous Response Handling

Anonymous responses occur when `access.allow_anonymous: true` and the user is not authenticated (no JWT).

### What Data Is Captured

| Field | Value |
|-------|-------|
| `respondent_id` | `null` |
| `respondent_email` | `null` (no email captured unless the form has an `email_input` question) |
| `is_anonymous` | `true` |
| `session_id` | A UUID generated by the client at the start of the form session. Stored in local storage. |
| `metadata.ip_address` | Captured server-side from request. |
| `metadata.user_agent` | Captured server-side from request headers. |
| `metadata.device_type` | Derived from User-Agent. |

### Session Tracking

The `session_id` is used for:
1. **Draft continuity**: An anonymous user who starts a form, closes it, and returns (in the same browser session) can resume the draft (the `session_id` is stored in localStorage and sent with the draft-save request).
2. **Duplicate detection**: The platform checks if a response with the same `session_id` already exists for this form. If found and `allow_multiple_submissions: false`, returns HTTP 409.

**Important**: `session_id` is generated client-side and is NOT cryptographically verified. It provides soft deduplication for honest cases but cannot prevent determined re-submission by clearing localStorage.

### Anonymous User Restrictions

- Cannot use `own_previous_response` fetch source (no user identity).
- Cannot edit a submitted response (no identity to verify ownership).
- Cannot save drafts to the server (server-side drafts require auth). Client-side auto-save to Drift still works locally.
- Role/group visibility conditions always evaluate to `false`.
- `require_login: true` in settings overrides `allow_anonymous: true` and blocks unauthenticated access.

---

## File Upload in Forms

### Question-Level File Configuration

File upload is configured through the `properties` of the relevant question types (`file_upload`, `image_capture`, `audio_record`).

```json
{
  "id": "q_attachment",
  "type": "file_upload",
  "label": "Upload Supporting Document",
  "required": false,
  "properties": {
    "allowed_types": ["application/pdf", "image/jpeg", "image/png"],
    "max_size_bytes": 10485760,
    "max_files": 3
  }
}
```

### How Files Are Linked to Responses

1. **Upload initiation**: Client calls `POST /api/internal/v1/uploads/initiate` with file metadata. Server creates a `file_uploads` document with `status: "pending"` and returns an upload URL (tus endpoint).

2. **Chunked upload**: Client uploads file in 5MB chunks via tus protocol to `POST /api/internal/v1/uploads/tus/{upload_id}`. Each chunk advances `file_uploads.upload_offset`.

3. **Upload completion**: When all chunks are uploaded, `file_uploads.status` becomes `"uploading_complete"`. Server:
   - Runs ClamAV virus scan (async). Sets `virus_scan_status: "pending"` initially.
   - Validates MIME type against `allowed_types` from the question's properties.
   - Validates file size against `max_size_bytes`.
   - Stores at `UPLOADS_ROOT/{org_id}/{form_id}/{upload_id}/{stored_filename}` (outside web root).

4. **Response submission**: The `answers` map includes `file_ids: [ObjectId1, ObjectId2]` for file-type questions. Server validates that all listed `file_upload._id` values exist, belong to the same org, and have `virus_scan_status: "clean"`.

5. **Post-submission linking**: After response submission, `file_uploads.response_id` and `file_uploads.question_id` are set on each uploaded file.

### Virus Scan Behavior

- Files are quarantined (status `"pending"`) until virus scan completes.
- If `virus_scan_status` is `"pending"` at submission time, the submission is accepted but a background job continues scanning. If a virus is later found, the form owner is notified.
- If `virus_scan_status` is `"infected"`, the file cannot be included in a response. Attempting to submit with an infected file ID returns HTTP 422.

### File Serving

Files are never served directly from the filesystem path. All file downloads go through:
```
GET /api/internal/v1/uploads/{file_id}/download
```
This endpoint verifies that the requesting user has access to the response containing this file before streaming it.

---

## Form Templates

### What Is a Template?

A form template is a saved `form_commit.schema` that can be used as the starting point for a new form. Templates can be:
- **System templates** (`is_system: true`): Shipped with the platform, visible to all orgs.
- **Public templates** (`is_public: true`): Created by an org, visible to all orgs.
- **Org-private templates** (`is_public: false`): Created by an org, visible only within that org.
- **Project-scoped templates** (`project_id` is set): Visible only within the specified project.

### Saving a Form as a Template

**Endpoint**: `POST /api/internal/v1/forms/{form_id}/save-as-template`

**Request Body**:
```json
{
  "name": "Patient Intake Template",
  "description": "Standard template for patient intake forms.",
  "category": "Healthcare",
  "tags": ["patient", "intake", "medical"],
  "is_public": false,
  "source_branch": "main"
}
```

**Behavior**:
1. Reads the current tip commit of `source_branch`.
2. Creates a `form_templates` document with `schema` = a copy of the commit's schema (with all response IDs and form-specific IDs stripped).
3. Template question IDs are regenerated (new UUIDs) so that multiple forms created from the same template have independent question IDs.

### Instantiating from a Template

**Endpoint**: `POST /api/internal/v1/forms/from-template`

**Request Body**:
```json
{
  "template_id": "ObjectId",
  "project_id": "ObjectId",
  "name": "My New Form"
}
```

**Behavior**:
1. Reads the template's `schema`.
2. Regenerates all IDs (section IDs, sub-section IDs, question IDs) as new UUIDs.
3. Creates a new `forms` document with `template_id` set.
4. Creates the first commit on the `main` branch with the template schema and `message: "Created from template: {template_name}"`.

---

For reusable response presets used during form filling, see [18_QUICK_RESPONSES.md](./18_QUICK_RESPONSES.md).

## Cover Page and Thank You Page

### Cover Page Schema

```json
"cover_page": {
  "enabled": true,
  "title": "Patient Intake Form",
  "description": "Please fill in your details carefully. This information is confidential.",
  "image_url": "https://cdn.example.com/hospital-banner.jpg",
  "button_label": "Begin",
  "show_estimated_time": true,
  "estimated_minutes": 10
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `enabled` | `boolean` | **Yes** | `true` | Whether to show the cover page before the first section. |
| `title` | `string` | Conditional | Form name | Title text on the cover page. If omitted, uses the form's `name`. |
| `description` | `string` | No | `""` | Description/instructions shown on the cover page. Supports a limited markdown subset. |
| `image_url` | `string` or `null` | No | `null` | URL of a banner image shown at the top of the cover page. |
| `button_label` | `string` | No | `"Start"` | Label on the start button. |
| `show_estimated_time` | `boolean` | No | `false` | Whether to show an estimated completion time. |
| `estimated_minutes` | `number` | Conditional | — | Required if `show_estimated_time: true`. Shown as "Estimated time: ~X minutes". |

**Cover page rendering**: In `single_page` layout, the cover page is shown as a modal/overlay before the form body. In `multi_page` and `wizard` layouts, it is shown as a dedicated first page/screen.

If `enabled: false`, the form renders directly to the first section.

### Thank You Page Schema

```json
"thank_you_page": {
  "enabled": true,
  "title": "Thank You!",
  "message": "Your response has been recorded. Reference ID: {{response_id}}",
  "show_response_id": true,
  "redirect_url": "https://hospital.example.com/portal",
  "redirect_delay_seconds": 5
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `enabled` | `boolean` | **Yes** | `true` | Whether to show a thank-you screen after submission. |
| `title` | `string` | No | `"Thank You!"` | Title text. |
| `message` | `string` | No | `"Your response has been recorded."` | Body message. Supports `{{response_id}}` and `{{submission_number}}` template variables. Supports a limited markdown subset. |
| `show_response_id` | `boolean` | No | `false` | Whether to display the `form_responses._id` (as a reference number) on the thank-you screen. |
| `redirect_url` | `string` or `null` | No | `null` | If set, automatically redirect to this URL after submission. |
| `redirect_delay_seconds` | `number` or `null` | Conditional | `null` | Seconds to wait before redirect (allows user to see the thank-you message). Required if `redirect_url` is set. Minimum: `0`. |

If `enabled: false`, the form viewer closes or navigates away immediately after a successful submission.

---

## Multi-Page Layout

### Layout Modes

| Mode | Description |
|------|-------------|
| `single_page` | All sections are rendered on one scrollable page. Navigation between sections is by scrolling. No explicit "next" button per section. |
| `multi_page` | Each section is a separate page. The respondent uses "Next" and "Back" buttons to navigate between pages. Current page is indicated by a progress indicator. |
| `wizard` | Similar to `multi_page` but with a step-indicator at the top (numbered steps). May also render sub-sections as sub-steps. |

### How Sections Map to Pages

In `multi_page` and `wizard` modes:
- **One section = one page.** The section `title` is used as the page title.
- If a section contains multiple sub-sections, they all appear on the same page, stacked vertically.
- Sections that are hidden (by their `visibility_rules`) are skipped entirely — the progress indicator re-calculates to exclude them.

### Navigation Between Pages

**"Next" button behavior**:
1. Validates all visible, required questions on the current page.
2. Evaluates skip logic for any question on the current page that has `skip_logic`.
3. If no skip → advance to next non-hidden section.
4. If skip → jump to `target_id` section/question.

**"Back" button behavior**:
- Returns to the previous visible section.
- Does NOT re-evaluate skip logic (user navigates backward without triggering jumps).
- Answers entered on previously completed pages are preserved.

**Progress indicator**: Shows `{current_visible_section_index} / {total_visible_sections_count}`. Hidden sections are excluded. The calculation is dynamic — if a section becomes visible due to an answer change, the denominator increases.

**Section validation on "Next"**: All required questions in the current section must be answered before proceeding. This is enforced even in `single_page` mode at submission time (not at scroll-navigation time).

---

## Offline Response Collection

### How Drafts Are Stored in Drift (SQLite)

The Flutter app uses **Drift** (SQLite) for local offline storage. The offline response collection tables:

```sql
-- Drift table for offline response drafts
CREATE TABLE offline_response_drafts (
  id TEXT PRIMARY KEY,                   -- UUID
  form_id TEXT NOT NULL,
  commit_id TEXT NOT NULL,
  respondent_id TEXT,                    -- null for anonymous
  session_id TEXT NOT NULL,
  partial_answers TEXT NOT NULL,         -- JSON string of answers map
  repeat_groups TEXT,                    -- JSON string of repeat_groups
  last_saved_at INTEGER NOT NULL,        -- Unix timestamp ms
  submitted BOOLEAN NOT NULL DEFAULT 0,
  sync_pending BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE offline_form_schemas (
  form_id TEXT NOT NULL,
  commit_id TEXT NOT NULL,
  schema_json TEXT NOT NULL,             -- Full form schema JSON
  cached_at INTEGER NOT NULL,
  PRIMARY KEY (form_id, commit_id)
);
```

### Auto-Save Behavior

- Every **30 seconds** while the user is actively filling a form, Flutter writes the current `partial_answers` to the `offline_response_drafts` Drift table.
- On any significant answer change (file uploaded, section navigated), an immediate auto-save is triggered.
- Auto-save is always local (Drift) first. If online, a background sync pushes the draft to the server (`response_drafts` collection) within 60 seconds.

### Sync Behavior

**On connectivity restore:**
1. The sync engine (at `core/sync/`) detects the connectivity change via Flutter's `connectivity_plus`.
2. Queries `offline_response_drafts` where `sync_pending = true`.
3. For each pending draft:
   - If `submitted = false` → `POST /api/internal/v1/forms/{form_id}/responses/draft` (server upsert).
   - If `submitted = true` → `POST /api/internal/v1/forms/{form_id}/responses` (server submission).
4. On success → sets `sync_pending = false` in Drift.
5. On conflict (server has a newer draft) → merges using the "latest answer wins" strategy for each question (not a 3-way merge — simpler for responses).

**Offline submission**: The user can tap "Submit" while offline. This sets `submitted = true` in Drift, records `offline_submitted: true` in metadata, and queues for sync. The form viewer shows a banner: "Submitted offline — will sync when connected."

**Form schema availability offline**: The form schema is cached in `offline_form_schemas` when the form is opened. If a new version is published while the user is offline, they continue filling the old schema. On sync, the old-version response is accepted server-side and tagged `is_legacy: true`.

---

## Legacy Response Display

### What Is a Legacy Response?

A response is "legacy" when its `commit_id` does not match the current `production_branch` tip commit. This happens when:
1. A new form version is published after the response was submitted.
2. A response was submitted offline against an older cached schema.

### How Legacy Responses Are Tagged

```json
{
  "_id": "ObjectId",
  "form_id": "ObjectId",
  "commit_id": "old_commit_a3f8",
  "is_legacy": true,
  ...
}
```

`is_legacy` is set to `true` by the server whenever:
- The `commit_id` of a newly submitted response does not match `forms.branches[production_branch]` at the time of submission (e.g., a racing publish).
- An offline-submitted response is synced and the production commit has advanced since the schema was cached.

### How Legacy Responses Are Shown in the Responses Tab

In the form responses table view (in the admin/project UI):
1. Each response row shows a "Version" badge: `v{commit_short_id}` (first 6 chars of `commit_id`).
2. Legacy responses have a warning icon ⚠️ and a tooltip: "This response was submitted against an older version of the form."
3. When viewing a legacy response in detail, the platform loads the schema from the `commit_id` stored in the response, **not** the current production schema.
4. Questions that existed in the old schema but not the current one are shown with a strikethrough/deprecated indicator.
5. Questions added in the new schema that don't have data in this response are shown with a "Not collected in this version" placeholder.

---

## Backward Compatibility Algorithm

When a new form version is published, the platform must correctly display responses collected under older versions. The algorithm runs at response-detail render time.

### Input

- `response`: A `form_responses` document with its `commit_id`.
- `current_schema`: The current production schema (from `forms.branches[production_branch]`).
- `response_schema`: The schema from `form_commits` where `commit_id` = `response.commit_id`.

### Algorithm Steps

1. **Load both schemas**: Fetch `response_schema` from `form_commits` by `response.commit_id`. Fetch `current_schema` from the current production commit.

2. **Build question diff**:
   - **Questions in `response_schema` AND `current_schema`** (same `question.id`): These are stable questions. Render using current schema's question definition (label may have changed, but the ID and answer value are compatible).
   - **Questions in `response_schema` but NOT in `current_schema`**: These are removed questions. Render them using `response_schema` definition with a `[Removed in newer version]` annotation.
   - **Questions in `current_schema` but NOT in `response_schema`**: These are added questions. Render them with `[Not collected in this version]` placeholder (no answer value).

3. **Handle type changes**: If the same `question.id` has a different `type` in `response_schema` vs `current_schema`:
   - Attempt to render the stored answer value using the **response schema's type** (the type that was active when the answer was collected).
   - Show a `[Type changed in newer version]` annotation.
   - The current schema's type is used for column headers in the responses table export.

4. **Handle section/sub-section structural changes**: If sections were re-ordered or renamed, the display uses the `response_schema`'s section order to maintain correct grouping of the response's answers.

5. **Handle repeat group schema changes**: If a section was repeatable in `response_schema` but is no longer in `current_schema`, display all iterations using the `response_schema` structure. If a section became repeatable in `current_schema` but was not in `response_schema`, display its single iteration as a flat (non-grouped) set of answers.

6. **Export compatibility**: When exporting responses (CSV/Excel), the export engine unifies all response versions into a single column set:
   - Columns from the **current** schema appear for all rows.
   - Columns from **removed** questions appear as additional columns, marked with `[v{old_commit}]` suffix.
   - Rows from old-version responses have empty cells for new-schema questions.

### Caching

The platform caches the resolved display schema for `(response_id, current_commit_id)` pairs in Redis for 5 minutes, to avoid re-running the diff algorithm on every response view in the responses table.

---

*End of Form System Documentation*

> **Related documents:**  
> - [`05_PLUGIN_SYSTEM.md`](./05_PLUGIN_SYSTEM.md) — Plugin system and component schema format  
> - [`CONTEXT.md`](./CONTEXT.md) — Master architectural reference
