# Comprehensive Properties Panel Audit

This document consolidates the live browser audit of the form builder's section properties panel and related form flow. It captures what was verified in the UI, the defects found while editing each tab, and the UX improvements that would make the panel more usable and less error-prone.

## Scope

Verified in the live app:
- Project dashboard
- Forms tab
- Form dashboard
- Form editor
- Section properties panel

Audited tabs:
- General
- Layout
- Style
- Logic
- Visibility
- Behavior
- A11y
- Analytics
- Advanced

## Environment Notes

- Frontend was accessed in Chrome through `agent-browser`.
- The app was reloaded and reauthenticated during the session.
- The section properties panel was inspected on the `test form` editor page with the section selected.
- Browser command pacing was reduced during the session as requested.

## Executive Summary

The section properties panel is partially functional today, but it has uneven quality across tabs.

Working well:
- `Layout` and `Visibility` controls respond to user input.

Major usability issues:
- `General` text fields append typed content into the existing value instead of clearly replacing the prior content.
- `Style` hex inputs append text and can create invalid concatenated values like `#FFFFFF#F0F0F0`.
- `Logic` is effectively empty and the main action is disabled.
- `Behavior`, `A11y`, `Analytics`, and `Advanced` are empty shells in the current build.

The most important product issue is that the panel exposes tabs that are not yet meaningful while also providing input patterns that are easy to misuse.

## Verified Page Flow

1. Opened the project dashboard.
2. Opened `test project`.
3. Switched to the `Forms` tab.
4. Opened `test form`.
5. Clicked `Edit form`.
6. Selected the section in the editor canvas.
7. Opened the section properties panel.

## Tab-by-Tab Audit

### General

Observed controls:
- Section title
- Description
- Help text
- Order

What worked:
- The fields are editable.
- Changes can be saved without an immediate validation error.

Issues:
- Typing into the title field appended text rather than replacing the existing value cleanly.
- The same append behavior was observed when editing the description and help text fields.
- The order field accepted input, but the interaction does not feel guarded or polished.

UX recommendations:
- Clear or select the current value when a field receives focus.
- Add visible save feedback.
- Add lightweight validation for `Order`.
- Provide a reset-to-default action for long text fields.

### Layout

Observed controls:
- Layout preset selector
- Grid columns slider
- Hidden section toggle
- Repeatable section toggle

What worked:
- Layout presets changed correctly.
- The slider updated the grid column value.
- The hidden and repeatable toggles responded correctly.

Issues:
- The grid slider is not self-explanatory enough without a stronger label and preview.
- The hidden section toggle can create a confusing experience if changed accidentally.

UX recommendations:
- Show the resulting column count more prominently.
- Add a brief preview or diagram of each layout preset.
- Explain the effect of hiding or repeating a section before the user commits the change.

### Style

Observed controls:
- Background color
- Border color
- Corner radius slider
- Section padding slider

What worked:
- The radius and padding sliders updated correctly.

Issues:
- Hex color fields appended input instead of replacing the current value.
- The resulting values could become invalid concatenations.
- No real color picker was exposed in this section flow.
- There was no live preview beyond the canvas reacting indirectly.

UX recommendations:
- Replace raw hex entry with a color picker or a combined picker-plus-text control.
- Validate hex values immediately.
- Allow a clear/reset action on each color field.
- Show a live visual preview of style changes.

### Logic

Observed controls:
- Empty state
- Disabled `Add rule` action

What worked:
- The tab loads without crashing.

Issues:
- The tab is effectively non-functional.
- The user sees a rule area but cannot actually add a rule.

UX recommendations:
- Either implement rule creation or hide the tab until it is usable.
- If the feature is still stubbed, show a clear explanation instead of a disabled control.
- Add a starter template for the first rule.

### Visibility

Observed controls:
- Show on mobile
- Show on tablet
- Show on desktop
- Environment selector with options including `All environments` and `Preview only`

What worked:
- The visibility toggles responded correctly.
- The environment selection responded correctly.

Issues:
- The panel is cramped vertically.
- The environment selector options are too dense for quick scanning.
- The section does not summarize visibility state in a concise way.

UX recommendations:
- Add a compact summary of the selected visibility state.
- Group device toggles into a single responsive visibility block.
- Improve spacing and option hierarchy in the environment selector.

### Behavior

Observed state:
- No meaningful controls visible in the current build.

Issues:
- This tab appears to be an empty shell.

UX recommendations:
- Hide the tab until it has actual behavior settings.
- If it is intentionally empty, explain why and what is planned.

### A11y

Observed state:
- No meaningful controls visible in the current build.

Issues:
- This tab appears to be an empty shell.

UX recommendations:
- Hide the tab until accessibility settings are implemented.
- Alternatively, add a small set of high-value accessibility controls.

### Analytics

Observed state:
- No meaningful controls visible in the current build.

Issues:
- This tab appears to be an empty shell.

UX recommendations:
- Hide the tab until analytics settings exist.
- If it is a placeholder, label it explicitly as planned functionality.

### Advanced

Observed state:
- No meaningful controls visible in the current build.

Issues:
- This tab appears to be an empty shell.

UX recommendations:
- Hide the tab until advanced controls are implemented.
- Avoid exposing empty surfaces that increase cognitive load.

## Reproduction Notes

### General text append issue
1. Open the section properties panel.
2. Go to `General`.
3. Click into the section title field.
4. Type a new value.
5. Observe that the new text appends instead of replacing the existing content cleanly.

### Style hex append issue
1. Open the section properties panel.
2. Go to `Style`.
3. Click into the background color or border color field.
4. Type a new hex value.
5. Observe that the typed value appends to the existing hex string instead of replacing it.

### Layout toggle and slider verification
1. Open the section properties panel.
2. Go to `Layout`.
3. Switch between preset layout options.
4. Drag the grid columns slider.
5. Toggle hidden/repeatable state.
6. Confirm the canvas updates and the panel remains usable.

### Visibility toggle verification
1. Open the section properties panel.
2. Go to `Visibility`.
3. Toggle device visibility settings.
4. Change the environment option.
5. Confirm the selected values update.

## Severity Ranking

### High

- `Style` color fields append text and can create invalid values.
- `Logic` is exposed but non-functional, which creates dead-end UI.
- Empty tabs (`Behavior`, `A11y`, `Analytics`, `Advanced`) are visible but not useful.

### Medium

- `General` text input behavior is awkward and error-prone.
- `Visibility` is functional but cramped and lacks a clear summary.

### Low

- `Layout` works but would benefit from stronger affordances and preview help.

## UX Improvement Summary by Tab

- `General`: improve text replacement behavior, validation, and save feedback.
- `Layout`: add preset previews, clearer slider labels, and explain hidden/repeatable consequences.
- `Style`: use a color picker, validate hex strings, and show live preview.
- `Logic`: implement the first rule flow or hide the tab.
- `Visibility`: simplify spacing and add a concise visibility summary.
- `Behavior`: implement controls or hide the tab.
- `A11y`: implement controls or hide the tab.
- `Analytics`: implement controls or hide the tab.
- `Advanced`: implement controls or hide the tab.

## Product Recommendation

The panel should not expose empty or non-functional tabs in production. If a tab is intentionally deferred, hide it or mark it clearly as planned. For editable controls, favor safer interaction models:
- pickers over raw hex strings,
- replace-friendly text inputs over append-prone fields,
- visible previews over hidden state,
- explicit empty states over disabled dead ends.

## Conclusion

The section properties panel is usable in parts, but the current UX is inconsistent. `Layout` and `Visibility` are the strongest tabs today. `Style` and `Logic` need the most attention, and the empty tabs should not be visible as-is. The most immediate user-facing fixes are:
- replace the color inputs with a picker or validated input flow,
- fix the text append behavior in `General`,
- either implement or hide `Logic`, `Behavior`, `A11y`, `Analytics`, and `Advanced`.
