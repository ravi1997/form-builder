# Scope: Milestone 1: Dynamic Group Membership Rules

## Architecture
- Backend: Python/Flask with MongoDB. Collections `groups` and `org_memberships`. `auth_service.py` handles group member resolution and user group lookup.
- Frontend: Flutter/Dart. `DynamicGroupRuleBuilder` widget is located at `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart`.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | Dynamic Group Membership Rules | Backend Group schema & auth_service evaluation on login/refresh; Frontend DynamicGroupRuleBuilder widget correctness and verification. | None | IN_PROGRESS |

## Interface Contracts
- Backend: JSON schema in `groups` documents with `dynamic_rule` field.
  - Evaluation during user login (`/api/auth/login`) and session refresh (`/api/auth/refresh`). The resulting group memberships should be evaluated and included in the JWT access token's organization claims as a `group_ids` list of strings inside each organization object.
- Frontend: `DynamicGroupRuleBuilder` widget to construct this JSON object.

## Detailed Implementation Plan

### Backend Changes:
1. **Refactor Rule Evaluation**:
   Refactor `evaluate_condition` and `evaluate_rule` inside `resolve_group_members` in `backend/app/services/auth_service.py` to module-level functions `evaluate_dynamic_rule_condition` and `evaluate_dynamic_rule`.
2. **Implement Optimized Membership Checker**:
   Implement `is_user_in_group(user_doc, membership, group)`:
   - Static: `mongo.db.group_members.find_one({"group_id": group["_id"], "user_id": user_doc["_id"], "is_deleted": False})` is not None.
   - Dynamic: Extract user and membership fields into `candidate = {"role": membership.get("role"), "membership_status": membership.get("status"), "email": user_doc.get("email"), "full_name": user_doc.get("full_name"), "status": user_doc.get("status")}` and evaluate using `evaluate_dynamic_rule(group.get("dynamic_rule") or {}, candidate)`.
3. **Include Group IDs in Claims**:
   In `_active_org_claims(user_id)`, query all groups in each org, check membership using `is_user_in_group`, and add them as `group_ids` (list of strings) in the organization claim.
4. **Optimize Permission Checks**:
   Add `get_user_groups_from_claims_or_db(decoded_token, org_id, user_id)` helper function. Update `evaluate_visibility_rules` and `user_has_access_to_resource` to call this helper.
5. **Add Tests**:
   Create a test `test_access_token_contains_group_ids` in `backend/tests/test_auth.py` verifying JWT token structure and permission evaluation.

### Frontend Changes:
1. **Fix Default Role**:
   Change the default rule value from `'org_member'` to `'org_viewer'` in `dynamic_group_rule_builder.dart`.
2. **Fix Focus and Cursor Issues**:
   - Extract condition rows in `DynamicGroupRuleBuilder` into a stateful child widget `DynamicGroupRuleRow` that manages its own `TextEditingController`.
   - Pass stable keys (`ValueKey`) to the child rows to preserve row state across addition/deletion.
3. **Implement parent state updates**:
   Handle `didUpdateWidget` inside `_DynamicGroupRuleBuilderState` to correctly reload the rule if the parent widget changes `initialRule`.
4. **Add Tests**:
   Write widget tests in `frontend/test/dynamic_group_rule_builder_test.dart` to verify input correctness, focus retention, and rules state update.
