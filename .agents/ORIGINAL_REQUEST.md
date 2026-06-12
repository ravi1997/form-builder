# Original User Request

## Initial Request — 2026-06-12T05:20:19Z

Implement the remaining four major feature areas in the Form Builder Platform: Dynamic Group Membership Rules, Visual AST Formula Calculations Engine, Compliance Holds UI & Storage Quota indicators, and the Drag-and-Drop Dashboard Canvas.

Working directory: /home/ravi/workspace/form-builder
Integrity mode: benchmark

## Requirements

### R1. Dynamic Group Membership Rules
- Implement backend `Group.py` schema expansion to support JSON-based dynamic membership query filters.
- Evaluate rules dynamically in real-time during user login/session refresh on the backend.
- Develop a frontend visual `DynamicGroupRuleBuilder` widget for configuring filters.

### R2. Visual AST Formula Calculations Engine
- Develop a frontend AST parsing engine that evaluates custom mathematical and logical expressions on the form submission page.
- Support complex conditional equations (e.g. IF/THEN statements, logical operators).
- Dynamically trigger recalculations of dependant fields when inputs change.

### R3. Compliance Legal Holds & Quotas UI
- Create an administrative dashboard at `/admin/compliance` to apply or release retention holds.
- Integrate backend file storage limits and show a storage usage progressive indicator on settings dashboards.
- Strictly block all new submissions when organization storage quota is exceeded.

### R4. Drag-and-Drop Dashboard Canvas
- Construct a visual drag-and-drop workspace layout allowing positioning of analytics widgets.

## Acceptance Criteria

### Verification
- [ ] All code modifications must compile cleanly and pass static analysis checks (`flutter analyze`).
- [ ] AST Formula Engine correctly resolves conditional equations like `IF(q1 > 10, q2 * 2, q2)` on change events.
- [ ] Storage quota enforcement returns block responses and displays error alert states when submissions are attempted over limit.
