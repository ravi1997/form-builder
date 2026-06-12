# 18 -- Quick Responses / Response Presets

> **Authoritative scope**: This document defines "Quick Responses" as reusable response templates for forms.
> **Reframe**: These are not sample data fixtures. They are user-managed response presets for testing, demos, internal QA, and repeatable entry flows.
> **Important distinction**: Do not confuse this feature with the existing form-template feature or the backend `ResponseTemplate` model used for export/notification formatting.

---

## Table of Contents

1. [Overview](#overview)
2. [Placement and Ownership](#placement-and-ownership)
3. [Template Metadata Model](#template-metadata-model)
4. [Creation and Management Flows](#creation-and-management-flows)
5. [Selection Behavior](#selection-behavior)
6. [Conflict Handling](#conflict-handling)
7. [Discovery and Organization](#discovery-and-organization)
8. [Permissions and Visibility](#permissions-and-visibility)
9. [UX Behavior](#ux-behavior)
10. [Validation and Edge Cases](#validation-and-edge-cases)
11. [Related Features](#related-features)
12. [Patient Example](#patient-example)
13. [MVP Scope vs Deferred Scope](#mvp-scope-vs-deferred-scope)
14. [Decision Log](#decision-log)

---

## Overview

Quick Responses are reusable response presets that can be applied while filling a form or building a response draft.

They are meant for:

- testing form flows
- demos
- internal QA
- frequently repeated internal data entry
- user-created presets for common responses

They are **not**:

- form templates
- submission settings
- draft records
- analytics fixtures
- audit timelines

The feature is form-facing. It helps authors and internal users prefill answers, but it does not change how responses are stored after submission.

---

## Placement and Ownership

Quick Responses is a **form-level** feature.

### Where it lives

- **Form-level properties panel**
  - A dedicated `Quick Responses` tab manages the template library for the current form.
  - This is the primary management surface.

- **Submission-time picker**
  - In the live form / response entry UI, a compact picker or drawer allows the user to select one or more templates before final submission.
  - This is the application surface, not the management surface.

### What it is not

- Not a question-level property
- Not a section-level setting
- Not a per-field default-value editor

### Ownership rule

- The form owns the Quick Responses library and its policy defaults.
- Individual templates belong to the form's org/project scope and are visible according to template visibility rules.
- Template application is always scoped to the current form schema and current response draft.

---

## Template Metadata Model

Each template must have:

- `name`
- `tags`

Recommended additional metadata:

- `description`
- `owner_user_id`
- `visibility`
- `updated_at`

Optional but useful:

- `usage_type`
- `created_at`
- `archived_at`
- `source_form_id`
- `source_commit_id`

### Proposed schema

```json
{
  "id": "tmpl_01J0ABCDEF1234567890",
  "org_id": "603d4a259c6b8c2c5c994510",
  "project_id": "603d4a259c6b8c2c5c994520",
  "name": "Cardiology QA Preset",
  "description": "Pre-filled values used for internal flow testing.",
  "tags": ["qa", "cardiology", "demo"],
  "usage_type": "testing",
  "visibility": "private",
  "owner_user_id": "603d4a259c6b8c2c5c994530",
  "field_values": {
    "q_patient_name": {
      "value": "Jane Doe",
      "display_value": "Jane Doe"
    },
    "q_patient_id": {
      "value": "PAT-10293",
      "display_value": "PAT-10293"
    }
  },
  "source_form_id": "603d4a259c6b8c2c5c994550",
  "source_commit_id": "a3f8c2d1e0b7",
  "created_at": "2026-06-07T10:15:00Z",
  "updated_at": "2026-06-07T10:45:00Z",
  "archived_at": null
}
```

### Field meanings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `string` | required | Human-readable template name. Max 255 chars. |
| `tags` | `array[string]` | required | Required for filtering/discovery. Must contain at least one tag. |
| `description` | `string` | `""` | Optional short explanation. Useful for QA/demo notes. |
| `owner_user_id` | `ObjectId` | required | User who created the template. |
| `visibility` | `string` | `"private"` | Scope of who can see and use the template. Enum: `private`, `project`, `org`, `system`. |
| `updated_at` | `ISODate` | auto | Last modified timestamp used for recency sorting. |
| `usage_type` | `string` | `"preset"` | Coarse grouping label. Enum: `preset`, `testing`, `demo`, `qa`, `other`. |
| `field_values` | `object` | required | Canonical answer snapshot keyed by question ID or canonical field key. |
| `source_form_id` | `ObjectId` or `null` | `null` | Provenance only. Identifies the source form used to create the template. |
| `source_commit_id` | `string` or `null` | `null` | Provenance only. Identifies the source commit version. |

### Storage rule

- The template stores **field-level presets** only.
- Section-level grouping is a display concern, not a storage primitive.
- Metadata-only templates are not allowed in MVP because they do not help prefill a response.
- The stored `field_values` object uses the same canonical answer shape the form runtime already understands.

---

## Creation and Management Flows

### Create template

Templates can be created from:

- the current response draft
- a filled demo state in the form viewer
- a blank template editor
- duplication of an existing template

The creation flow should ask for:

- name
- tags
- description
- visibility
- usage type

### Edit template

Editors can update:

- name
- tags
- description
- visibility, if allowed by permissions
- field_values

Editing a template updates `updated_at`.

### Duplicate template

Duplicate copies:

- name
- description
- tags
- visibility
- usage type
- field values

The duplicate should open in an editor so the user can rename or adapt it.

### Archive template

Archive is a reversible hide action:

- archived templates do not appear in the default picker
- archived templates remain recoverable by the owner or an admin

### Delete template

Delete is destructive and should require explicit confirmation.

- personal templates can be deleted by the owner
- shared templates can be deleted by the owner only if they have write permission, or by project/org admins
- if hard delete is too risky for MVP, deletion may be implemented as soft delete with an archive restore path

### Promote template

Users can promote a personal template to a shared scope when permissions allow:

- `private` -> `project`
- `private` -> `org`

Promotion should preserve the original owner unless the admin explicitly transfers ownership.

---

## Selection Behavior

### Multi-select support

- One or more templates may be selected.
- Templates are applied as a batch to a draft before submission.
- The selection UI should show a live preview of which fields will be filled.

### Apply semantics

- Templates are applied only when the user presses `Apply`.
- Application fills the draft but does not submit it.
- Manual edits after application win over template values.
- Templates do not keep reapplying automatically after the draft changes.

### Safe merge rule

The MVP merge rule is simple:

- only non-overlapping templates can be applied together
- templates never overwrite each other
- templates do not overwrite existing non-empty draft values

This is the safest and easiest rule for users because it avoids hidden precedence behavior.

---

## Conflict Handling

### Template-to-template conflict

If two selected templates touch the same field:

- block apply
- show the conflicting field names
- require the user to deselect one of the templates

### Template-to-draft conflict

If a selected template would populate a field that already has a manual value in the current draft:

- treat that field as a conflict
- do not overwrite the user's value
- disable apply until the draft is cleared or the template is removed

### Incompatible schema conflict

If a template references a field that does not exist in the current form:

- show a compatibility warning
- disable direct apply for that template in the current form
- allow the user to duplicate and adapt the template

### Why this rule set

- no surprise overwrites
- no hidden priority order
- no silent partial data loss
- easier to explain in the UI

---

## Discovery and Organization

### Required discovery tools

- search by name
- search by description
- search by tags
- filter by creator
- filter by usage type
- filter by visibility
- filter by archived state
- sort by recency

### Recommended UI grouping

- **Tags**: chips and filter pills
- **Creator**: `Mine`, `Shared`, `All`
- **Usage type**: `Preset`, `QA`, `Demo`, `Testing`
- **Recency**: default sort by `updated_at desc`

### Tag rules

- tags are normalized to lowercase
- tags are trimmed of whitespace
- duplicate tags on the same template are removed
- tags are used both for filtering and for quick discovery
- tags should be short and meaningful, e.g. `qa`, `demo`, `cardiology`, `admission`

---

## Permissions and Visibility

### Who can create templates

- authenticated users who can access the form
- by default, the template they create is private

### Who can use templates

- users who can open the form and can see the template's visibility scope
- if the form is anonymous/public, template use should be hidden unless shared templates are explicitly enabled for that workflow

### Who can edit templates

- private templates: owner only
- project templates: owner and project editors/admins
- org templates: owner and org admins
- system templates: admins only

### Who can delete/archive templates

- same access model as edit, with destructive delete reserved for owners/admins

### Admin powers

- org admins can manage all templates in their org
- platform admins can manage system templates and all org templates

---

## UX Behavior

### Management tab layout

The `Quick Responses` tab should stay compact:

- top area: search bar + filters
- main area: template cards or a list
- side or modal: template editor

Each template card should surface:

- name
- tags
- visibility badge
- usage type badge
- owner
- last updated time
- quick actions: apply, edit, duplicate, archive, delete

### Submission-time picker

When the user is filling a form:

- the picker should be compact and obvious
- selected templates should appear as chips
- the apply button should show how many fields will be filled
- if a template is incompatible, it should be clearly disabled

### Creation UX

Use a modal or side drawer for creation and editing.

Reason:

- it keeps the tab readable
- it reduces accidental clutter
- it makes field values and metadata easy to review in one place

---

## Validation and Edge Cases

### Validation rules

- `name` is required
- `tags` are required and must contain at least one non-empty tag
- tags must be unique within a template
- template fields must map to valid fields in the source form when saved
- unsupported field types should be rejected at save time
- hidden or invalid values should be surfaced before the template is saved

### Edge cases

- **Multiple templates selected with overlapping fields**: block apply and show the conflict.
- **Template references a field that no longer exists**: mark template incompatible and disable apply until duplicated/adapted.
- **Template tags are empty or duplicated**: reject empty tags, dedupe duplicates automatically.
- **Template deleted after being selected**: keep the draft values already applied, but mark the selection stale and disable re-apply.
- **Template created for one form but reused in another incompatible form**: show a compatibility warning and require duplication/adaptation rather than silent partial application.

### Compatibility principle

- incompatible templates should be visible enough to understand
- they should not be silently applied
- users should not lose manual data because of template reuse

---

## Related Features

Quick Responses must stay distinct from:

- **Form templates**: those are schema templates used to create new forms
- **Draft handling**: drafts are per-response session state, not reusable presets
- **Submission settings**: these affect submit behavior, not preset content
- **Analytics or test fixtures**: these are reporting or synthetic-data concerns
- **Existing `ResponseTemplate` model**: that model is for export/notification formatting, not response presets

The feature is specifically about reusable response content.

---

## Patient Example

### Example setup

An internal QA user is testing a patient intake form.

They create two private templates:

1. `Adult Demographics`
   - tags: `qa`, `demo`, `adult`
   - fills `patient_name`, `date_of_birth`, `gender`

2. `Visit Context`
   - tags: `qa`, `visit`, `cardiology`
   - fills `department`, `visit_reason`, `triage_level`

### Safe multi-select

The user selects both templates in the picker.

Because the templates touch different fields:

- they can be applied together
- no values are overwritten
- the merged draft contains all fields from both templates

### Unsafe multi-select

If the user also selects `Pediatric Demographics`, which touches `date_of_birth` and `gender` again:

- the picker shows a conflict
- apply is disabled
- the user must remove one template before continuing

---

## MVP Scope vs Deferred Scope

### MVP

Ship first:

- named templates
- required tags
- description
- owner
- visibility
- updated_at
- create
- edit
- delete
- duplicate
- archive
- personal templates private by default
- project/org sharing for promoted templates
- one or more templates selected
- non-overlapping templates only
- search/filter/sort by tags, creator, usage type, recency
- compatibility warnings for missing fields

### Deferred

Postpone:

- approval workflows
- template versioning
- rich conflict resolution engine
- cross-form remapping assistant
- automatic field priority rules
- analytics on template usage
- public template marketplaces
- system-curated template packs

---

## Decision Log

- Quick Responses is a **form-level** feature, not a question-level property.
- Templates are **response presets**, not form templates.
- Personal templates are **private by default**.
- `name` and `tags` are required.
- The MVP merge rule is **non-overlapping only**.
- Templates do **not** overwrite existing draft values.
- `updated_at` is the primary recency signal.
- Incompatible templates are **warned and blocked**, not silently partially applied.

