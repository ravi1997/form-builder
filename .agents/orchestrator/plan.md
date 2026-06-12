# Project: Form Builder Platform - Feature Implementation

## Architecture
- **Backend**: Python/Flask with MongoDB. Collections `groups`, `group_members`, `org_memberships`, `users`, `storage_quotas`, `form_responses`. Services in `app/services/` (such as `auth_service.py`, `quota_service.py`) and blueprints/routes in `app/routes/` (`auth.py`, `dashboard.py`, `forms.py`).
- **Frontend**: Flutter/Dart client. Core packages and features in `lib/features/` including auth, dashboard_builder, form_builder, and compliance/quota widgets.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | Dynamic Group Membership Rules | Implement backend `Group.py` schema expansion, dynamic rule evaluation during login/session refresh, and frontend visual `DynamicGroupRuleBuilder` widget. | None | PLANNED |
| 2 | Visual AST Formula Calculations Engine | Develop frontend AST parsing engine evaluating custom equations on submission page, conditional equations (e.g. IF/THEN), and recalculations on change. | None | PLANNED |
| 3 | Compliance Legal Holds & Quotas UI | Administrative dashboard at `/admin/compliance`, backend file storage limits and settings progressive indicator, and strict blocking of new submissions when quota exceeded. | None | PLANNED |
| 4 | Drag-and-Drop Dashboard Canvas | Construct a visual drag-and-drop workspace layout allowing positioning of analytics widgets. | None | PLANNED |

## Code Layout
- Backend: `/home/ravi/workspace/form-builder/backend`
- Frontend: `/home/ravi/workspace/form-builder/frontend`

## Interface Contracts
- Dynamic Group Rules:
  - Backend: JSON schema in `groups` documents with `dynamic_rule` field.
  - Frontend: `DynamicGroupRuleBuilder` widget to construct this JSON object.
- AST Formula Calculations Engine:
  - Frontend: AST parser evaluating mathematical/logical expressions on change events (e.g. `IF(q1 > 10, q2 * 2, q2)`).
- Compliance Holds & Quotas:
  - Backend: endpoints to get/set legal holds and fetch/validate storage usage.
  - Frontend: settings progressive indicator, and blocking UI / error states.
- Drag-and-Drop Canvas:
  - Frontend: dashboard grid canvas for layout positioning.
