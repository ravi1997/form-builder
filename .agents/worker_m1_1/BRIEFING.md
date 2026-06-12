# BRIEFING — 2026-06-12T05:25:34Z

## Mission
Implement backend auth changes (group claims / evaluations) and frontend dynamic rule builder updates (ValueKey focus retention).

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /home/ravi/workspace/form-builder/.agents/worker_m1_1
- Original parent: f1a37dc4-593b-446e-89f8-57a99e76a54f
- Milestone: Milestone 1

## 🔒 Key Constraints
- CODE_ONLY network mode: No external internet access.
- No cheating: Genuine implementations only, no hardcoded expected values/tests.
- Do not make parallel edit tool calls.

## Current Parent
- Conversation ID: f1a37dc4-593b-446e-89f8-57a99e76a54f
- Updated: not yet

## Task Summary
- **What to build**:
  - Backend: Extract evaluation helpers, implement `is_user_in_group`, add group_ids inside organisation claims, implement `get_user_groups_from_claims_or_db` and integrate it.
  - Frontend: Change default rule value to 'org_viewer', extract condition rows to stateful child widget with `ValueKey` and persistent `TextEditingController` to retain focus, implement `didUpdateWidget`.
- **Success criteria**: All backend tests pass, new tests verify group claims logic; all frontend tests pass, including a new widget test for rule builder.
- **Interface contracts**: /home/ravi/workspace/form-builder/.agents/sub_orch_m1/SCOPE.md
- **Code layout**: Standard python backend and flutter frontend layout.

## Key Decisions Made
- [TBD]

## Artifact Index
- /home/ravi/workspace/form-builder/.agents/worker_m1_1/handoff.md — Handoff report for parent

## Change Tracker
- **Files modified**: None yet
- **Build status**: Untested
- **Pending issues**: None

## Quality Status
- **Build/test result**: Untested
- **Lint status**: Untested
- **Tests added/modified**: None yet

## Loaded Skills
- None
