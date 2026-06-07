# 09 — Flutter JSON UI Engine & Component Library

> **Authoritative reference for all primitive components, the rendering pipeline, form state
> management, formula builder, and the composition system.**  
> Audience: Flutter engineers implementing the JSON UI Engine and any AI agent generating code for it.

---

## Table of Contents

1. [JSON UI Engine Architecture](#1-json-ui-engine-architecture)
2. [Rendering Pipeline](#2-rendering-pipeline)
3. [Value Model](#3-value-model)
4. [Form State Management (Riverpod)](#4-form-state-management-riverpod)
5. [Validation Engine](#5-validation-engine)
6. [Visibility Rule Engine](#6-visibility-rule-engine)
7. [Primitive Components — Complete Reference](#7-primitive-components--complete-reference)
   - 7.1 Text & Input group
   - 7.2 Selection group
   - 7.3 Date & Time group
   - 7.4 Media & Files group
   - 7.5 Interactive group
   - 7.6 Location & Special group
   - 7.7 Display (non-input) group
8. [Composition System](#8-composition-system)
9. [Formula Builder & Engine](#9-formula-builder--engine)
10. [Fetch Action Button](#10-fetch-action-button)

---

## 1. JSON UI Engine Architecture

### 1.1 Overview

The **JSON UI Engine** is a declarative widget-rendering subsystem that lives in
`frontend/lib/shared/json_ui_engine/`. It receives a `component_schema` JSON document
(originating from `component_schemas` MongoDB collection, cached locally in Drift), resolves
every primitive reference inside the schema, and emits a Flutter widget tree that can collect
answers and report them upward via callbacks.

The engine is **concept-agnostic**: the same code path handles form fields (concept =
`form_field`), analysis node configuration panels (concept = `analysis_node`), and dashboard
widget property editors (concept = `dashboard_widget`). The caller is responsible for wrapping
the emitted widgets in the appropriate container (e.g., a form card, a node config drawer).

### 1.2 Engine Entry Point

```dart
/// lib/shared/json_ui_engine/json_ui_engine.dart

class JsonUiEngine {
  /// Renders a complete component from its schema.
  ///
  /// [schema]         – ComponentSchema object (deserialized from JSON).
  /// [currentValues]  – Map<property_key, AnswerValue> of current answers for
  ///                    pre-population (e.g., when editing a draft).
  /// [onValueChanged] – Callback invoked whenever any primitive reports a new value.
  ///                    Carries the property_key and the new AnswerValue.
  /// [onValidationChanged] – Callback invoked when the validity state of any
  ///                         primitive changes.
  /// [formContext]    – Provides current form state (other field answers, user role,
  ///                    group membership) for visibility and formula evaluation.
  /// [readOnly]       – If true, all primitives are rendered in read-only mode.
  Widget render({
    required ComponentSchema schema,
    required Map<String, AnswerValue> currentValues,
    required void Function(String propertyKey, AnswerValue value) onValueChanged,
    required void Function(String propertyKey, bool isValid) onValidationChanged,
    required FormContext formContext,
    bool readOnly = false,
  });
}
```

### 1.3 Directory Structure

```
frontend/lib/shared/json_ui_engine/
  json_ui_engine.dart          ← Public API (entry point)
  models/
    component_schema.dart      ← ComponentSchema, PrimitiveRef, PropertyDef
    answer_value.dart          ← AnswerValue (typed value + display_value)
    form_context.dart          ← FormContext passed to all widgets
    validation_rule.dart       ← ValidationRule (mirrors backend model)
    visibility_rule.dart       ← VisibilityRules, Condition
  renderers/
    primitive_renderer.dart    ← Dispatches primitive type → widget class
  primitives/
    text_input.dart
    text_area.dart
    number_input.dart
    email_input.dart
    phone_input.dart
    password_input.dart
    url_input.dart
    dropdown.dart
    multi_select.dart
    radio_group.dart
    checkbox.dart
    checkbox_group.dart
    toggle.dart
    button_group.dart
    date_picker.dart
    time_picker.dart
    datetime_picker.dart
    date_range_picker.dart
    file_upload.dart
    image_capture.dart
    signature.dart
    audio_record.dart
    rating.dart
    slider_input.dart
    number_stepper.dart
    color_picker.dart
    location_picker.dart
    barcode_scanner.dart
    fetch_button.dart
    heading.dart
    paragraph.dart
    divider_widget.dart
    image_display.dart
    video_display.dart
  composition/
    composition_renderer.dart  ← Renders multi-primitive compositions
    composition_validator.dart ← Cross-field composition validation
  formula/
    formula_engine.dart        ← AST evaluator
    formula_builder_modal.dart ← Visual builder UI
  validation/
    validation_engine.dart     ← ValidationRule evaluation
  visibility/
    visibility_engine.dart     ← VisibilityRules evaluation
```

---

## 2. Rendering Pipeline

The rendering pipeline transforms a `component_schema` JSON object into a live Flutter widget
tree in six discrete stages.

### Stage 1 — Schema Deserialization

```
Raw JSON (from Drift cache)
       ↓
ComponentSchema.fromJson(json)
       ↓
ComponentSchema {
  type: String,
  displayName: String,
  concept: ConceptType,
  composition: List<PrimitiveRef>,
  properties: List<PropertyDef>,
  offlineSupport: bool,
  previewSchema: Map<String, dynamic>
}
```

`ComponentSchema` is a Dart freeze'd immutable class. Deserialization is done once and the
result is stored in a Riverpod `StateProvider<ComponentSchema>`.

### Stage 2 — PrimitiveRef Resolution

Each entry in `composition` is a `PrimitiveRef`:

```dart
class PrimitiveRef {
  final String primitive;       // e.g., "text_input"
  final String propertyKey;     // e.g., "value" — maps this primitive's output
                                // to the parent component's answer field
  final String? labelFromProperty; // property key whose value is used as label
  final VisibilityRules? visibility; // conditional visibility of this primitive
  final Map<String, dynamic> staticProperties; // merged with question.properties
}
```

Resolution process:
1. Look up `primitive` string in `PrimitiveRegistry` (a compile-time Map<String, PrimitiveBuilder>).
2. Merge `schema.properties` values from the question's `properties` object (author-configured)
   with `PrimitiveRef.staticProperties` (schema-configured). Question-level values win.
3. Resolve `labelFromProperty`: look up the named property key in the merged properties and use
   its string value as the label for this primitive.
4. If the primitive is not found in the registry, render an `UnknownPrimitiveWidget` placeholder.

### Stage 3 — Widget Instantiation

`PrimitiveRenderer.build(PrimitiveRef ref, ResolvedProps props)` dispatches to the correct
primitive widget class via a switch-on-string. Each primitive widget is a `ConsumerStatefulWidget`
(Riverpod-aware) that:
- Reads its initial value from the `currentValues` map using `ref.propertyKey`.
- Subscribes to `FormStateNotifier` to receive external value updates (e.g., formula-driven).

### Stage 4 — Property Binding

Resolved properties are passed as named parameters to each primitive widget constructor. Every
primitive accepts the **standard property set** plus its own type-specific properties (see §7).

Standard properties (all primitives):

| Property Key      | Type    | Default | Description |
|-------------------|---------|---------|-------------|
| `label`           | String  | `""`    | Field label displayed above the primitive |
| `placeholder`     | String  | `""`    | Hint text inside the input |
| `required`        | Boolean | `false` | Whether a non-empty answer is mandatory |
| `disabled`        | Boolean | `false` | Input is shown but not interactive |
| `readonly`        | Boolean | `false` | Input is shown as text, not interactive |
| `hint_text`       | String  | `""`    | Secondary help text below the input |
| `error_message`   | String  | `""`    | Override for the validation error message |
| `ui_overrides`    | Object  | `{}`    | Per-primitive rendering tweaks (see each component) |

### Stage 5 — Value Callback Chain

When the user interacts with a primitive:

```
User interaction
       ↓
Primitive widget internal state change
       ↓
Primitive calls: onChanged(AnswerValue newValue)
       ↓
PrimitiveRenderer invokes: onValueChanged(ref.propertyKey, newValue)
       ↓
CompositionRenderer aggregates: all property_key values → ComponentAnswerMap
       ↓
FormStateNotifier.updateAnswer(questionId, ComponentAnswerMap)
       ↓
Riverpod propagates state to:
  • Formula engine re-evaluation
  • Visibility engine re-evaluation
  • Validation engine re-evaluation (if touched)
```

### Stage 6 — Composition Output Assembly

For a composed component with multiple primitives, `CompositionRenderer` maintains a
`Map<String, AnswerValue>` keyed by `propertyKey`. When any inner primitive fires
`onValueChanged`, the map is updated and the assembled `ComponentAnswerMap` is reported upward.

---

## 3. Value Model

### 3.1 AnswerValue

Every primitive produces an `AnswerValue`. This is the universal currency of the engine.

```dart
@freezed
class AnswerValue with _$AnswerValue {
  const factory AnswerValue({
    required dynamic value,         // Typed value (see table below)
    required String displayValue,   // Human-readable string for UI display
    List<String>? fileIds,          // ObjectId strings for file_uploads (file-type primitives)
    DateTime? answeredAt,           // Set when answer is first committed
    int? iterationIndex,            // For repeatable sections
  }) = _AnswerValue;

  factory AnswerValue.empty() => const AnswerValue(value: null, displayValue: '');
  factory AnswerValue.fromJson(Map<String, dynamic> json) => _$AnswerValueFromJson(json);
}
```

### 3.2 Value Types by Primitive Category

| Primitive(s) | `value` Dart Type | Example `displayValue` |
|---|---|---|
| `text_input`, `text_area`, `email_input`, `url_input`, `password_input` | `String` | `"john@example.com"` |
| `number_input`, `number_stepper`, `slider` | `num` (int or double) | `"42"` or `"3.14"` |
| `phone_input` | `Map{country_code, number}` | `"+91 9876543210"` |
| `dropdown`, `radio_group`, `button_group` | `String` (option value) | `"Option Label"` |
| `multi_select`, `checkbox_group` | `List<String>` (option values) | `"A, B, C"` |
| `checkbox`, `toggle` | `bool` | `"Yes"` or `"No"` |
| `date_picker` | `String` ISO-8601 date `"YYYY-MM-DD"` | `"15 Jan 2026"` |
| `time_picker` | `String` `"HH:MM"` (24-hr) | `"14:30"` |
| `datetime_picker` | `String` ISO-8601 datetime | `"15 Jan 2026, 14:30"` |
| `date_range_picker` | `Map{start: String, end: String}` | `"10 Jan – 20 Jan 2026"` |
| `file_upload`, `image_capture`, `audio_record` | `List<String>` (upload IDs) | `"3 files"` |
| `signature` | `String` (base64 PNG or upload ID) | `"Signature captured"` |
| `rating` | `int` (1..max_stars) | `"4 / 5"` |
| `color_picker` | `String` hex `"#RRGGBB"` | `"#FF5733"` |
| `location_picker` | `Map{lat: double, lng: double, address: String?}` | `"28.6139° N, 77.2090° E"` |
| `barcode_scanner` | `String` (raw barcode text) | `"4006381333931"` |
| `heading`, `paragraph`, `divider`, `image_display`, `video_display` | `null` | `""` (display-only) |

### 3.3 ComponentAnswerMap

For a composed component (e.g., a `patient_info` component composed of `text_input` +
`date_picker` + `phone_input`), the top-level answer stored in `form_responses.answers` is a
`Map<String, AnswerValue>` keyed by `propertyKey`:

```json
{
  "patient_name":  { "value": "John Doe",      "display_value": "John Doe" },
  "dob":           { "value": "1990-05-15",    "display_value": "15 May 1990" },
  "phone":         { "value": { "country_code": "+91", "number": "9876543210" },
                     "display_value": "+91 9876543210" }
}
```

For a non-composed component (single primitive), the answer is stored as a single `AnswerValue`
directly (not a map).

---

## 4. Form State Management (Riverpod)

### 4.1 Provider Graph

```
FormSchemaProvider (StateProvider<FormSchema>)
       │
       ├─► FormStateNotifier (StateNotifierProvider<FormStateNotifier, FormState>)
       │         │
       │         ├─► answerMap: Map<questionId, AnswerValue>
       │         ├─► touchedFields: Set<questionId>
       │         ├─► validationErrors: Map<questionId, List<String>>
       │         └─► isSubmitting: bool
       │
       ├─► VisibilityProvider (Provider<Map<String, bool>>)
       │       ← derived from FormState.answerMap + formContext
       │
       ├─► FormulaResultProvider (FutureProvider<Map<questionId, AnswerValue>>)
       │       ← computed from FormState.answerMap
       │
       └─► FormSubmitProvider (FutureProvider<SubmitResult>)
```

### 4.2 FormState Data Class

```dart
@freezed
class FormState with _$FormState {
  const factory FormState({
    required String formId,
    required String commitId,      // Version the user is filling
    required Map<String, AnswerValue> answerMap,
    required Set<String> touchedFields,
    required Map<String, List<String>> validationErrors,
    @Default(false) bool isSubmitting,
    @Default(false) bool isDirty,  // Any unsaved changes?
    String? draftId,               // If a draft exists locally
    DateTime? lastSavedAt,
  }) = _FormState;
}
```

### 4.3 FormStateNotifier API

```dart
class FormStateNotifier extends StateNotifier<FormState> {

  /// Called by CompositionRenderer whenever a primitive changes value.
  void updateAnswer(String questionId, AnswerValue value);

  /// Called when a field loses focus — marks field as touched
  /// so validation errors become visible.
  void markTouched(String questionId);

  /// Called by formula engine to push a computed value (read-only write).
  void applyFormulaResult(String questionId, AnswerValue value);

  /// Persist current answers to Drift offline_drafts table.
  Future<void> saveDraft();

  /// Load answers from a previously saved draft.
  Future<void> loadDraft(String draftId);

  /// Reset all answers, touched state, errors.
  void reset();

  /// Validate all fields (used before submission).
  /// Returns true if form-level validation passes.
  bool validateAll();

  /// Submit the form — serializes answers, calls API or queues offline.
  Future<SubmitResult> submit();
}
```

### 4.4 Draft Auto-Save

Auto-save fires every **30 seconds** when `FormState.isDirty == true`, and also on app
backgrounding (via `WidgetsBindingObserver.didChangeAppLifecycleState`). The draft is written
to the Drift `offline_drafts` table (see §10 of 10_OFFLINE_SYNC.md) and, if online, also
`PUT /api/internal/v1/forms/{formId}/draft`.

### 4.5 Repeatable Section State

Repeatable sections maintain a separate list of `FormState` instances, one per iteration, keyed
by `{sectionId}_{iterationIndex}`. The `FormStateNotifier` aggregates these into the
`repeat_groups` field on submission.

---

## 5. Validation Engine

### 5.1 ValidationRule Model

Each question in the form schema may carry a `validation_rules` array. Each rule:

```dart
@freezed
class ValidationRule with _$ValidationRule {
  const factory ValidationRule({
    required ValidationRuleType type,
    dynamic value,          // Numeric/string threshold, regex pattern, or null
    required String message, // Error message to show the user
  }) = _ValidationRule;
}

enum ValidationRuleType {
  min,          // Numeric minimum (number_input, slider, rating, number_stepper)
  max,          // Numeric maximum
  minLength,    // Minimum character count (text_input, text_area, email_input, etc.)
  maxLength,    // Maximum character count
  pattern,      // Regex pattern string
  custom,       // Reserved for plugin-provided validation
}
```

Additionally, every component with `required: true` in its standard properties is treated as an
implicit `required` validation rule with a default message `"This field is required"`.

### 5.2 Field-Level Validation

Validation is evaluated by `ValidationEngine.validate(AnswerValue answer, List<ValidationRule> rules)`:

```dart
class ValidationEngine {
  /// Returns a list of error messages. Empty list means valid.
  List<String> validate(AnswerValue answer, List<ValidationRule> rules, bool required) {
    final errors = <String>[];

    // 1. Required check (first, before other rules)
    if (required && _isEmpty(answer)) {
      errors.add('This field is required');
      return errors; // No further rules evaluated if empty and required
    }

    // 2. Skip other rules if value is empty and field is not required
    if (_isEmpty(answer)) return errors;

    // 3. Apply type-specific rules
    for (final rule in rules) {
      switch (rule.type) {
        case ValidationRuleType.min:
          if (_toNum(answer) < (rule.value as num)) errors.add(rule.message);
        case ValidationRuleType.max:
          if (_toNum(answer) > (rule.value as num)) errors.add(rule.message);
        case ValidationRuleType.minLength:
          if (_toString(answer).length < (rule.value as int)) errors.add(rule.message);
        case ValidationRuleType.maxLength:
          if (_toString(answer).length > (rule.value as int)) errors.add(rule.message);
        case ValidationRuleType.pattern:
          if (!RegExp(rule.value as String).hasMatch(_toString(answer))) errors.add(rule.message);
        case ValidationRuleType.custom:
          // Delegated to plugin engine — not evaluated client-side
          break;
      }
    }
    return errors;
  }

  bool _isEmpty(AnswerValue a) =>
      a.value == null ||
      (a.value is String && (a.value as String).isEmpty) ||
      (a.value is List && (a.value as List).isEmpty);
}
```

### 5.3 When Validation Runs

| Trigger | Behavior |
|---|---|
| Field loses focus (`onFocusLost`) | Validate only that field; show error if `touchedFields` contains it |
| `FormStateNotifier.updateAnswer()` | Re-validate only if field is already in `touchedFields` |
| `FormStateNotifier.validateAll()` | Mark all fields touched; validate all; return bool |
| Form submit button pressed | Calls `validateAll()` first; blocks submission if any errors |

### 5.4 Error Display

Each primitive widget observes `formStateProvider.select((s) => s.validationErrors[questionId])`.
When the list is non-empty, the widget renders an `ErrorText` widget below the input using the
platform's error style (red text, `Theme.of(context).inputDecorationTheme.errorStyle`). Multiple
errors are joined with newlines.

### 5.5 Form-Level Validation

Before submission, `validateAll()` iterates every visible question (visibility is checked first
— hidden questions are excluded from validation). It returns `false` if any `validationErrors`
entry is non-empty after evaluation.

Additionally, the server re-validates all answers on `POST /api/internal/v1/forms/{formId}/responses`
using the same rules stored in the schema. This prevents bypass of client-side validation.

---

## 6. Visibility Rule Engine

### 6.1 VisibilityRules Model

```dart
@freezed
class VisibilityRules with _$VisibilityRules {
  const factory VisibilityRules({
    required LogicalOperator operator,    // AND | OR
    required List<Condition> conditions,
  }) = _VisibilityRules;
}

@freezed
class Condition with _$Condition {
  const factory Condition.role({ required List<String> roles }) = RoleCondition;
  const factory Condition.group({ required List<String> groupIds }) = GroupCondition;
  const factory Condition.answer({
    required String fieldId,
    required AnswerOperator operator,
    dynamic value,
  }) = AnswerCondition;
  const factory Condition.alwaysVisible() = AlwaysVisibleCondition;
  const factory Condition.alwaysHidden() = AlwaysHiddenCondition;
}

enum LogicalOperator { and, or }

enum AnswerOperator {
  equals, notEquals, contains, greaterThan, lessThan,
  inList, notInList, isEmpty, isNotEmpty
}
```

### 6.2 Evaluation Algorithm

`VisibilityEngine.evaluate(VisibilityRules rules, FormContext ctx, FormState state) → bool`

```
if conditions is empty → return true (visible by default)

for each Condition c:
  result[c] = evaluateCondition(c, ctx, state)

if operator == AND: return result.every((r) => r == true)
if operator == OR:  return result.any((r) => r == true)
```

**Condition evaluation:**

| Condition type | Evaluation |
|---|---|
| `alwaysVisible` | `true` |
| `alwaysHidden` | `false` |
| `role` | `ctx.userRole` is in `roles` list |
| `group` | `ctx.userGroupIds` intersects `groupIds` |
| `answer` | Compare `state.answerMap[fieldId].value` with `value` using `operator` |

For `answer` conditions, if the referenced `fieldId` has no answer yet (null or empty), the
comparison is treated as follows:
- `isEmpty` → `true`
- `isNotEmpty` → `false`
- All other operators → `false` (field not yet answered; hide the dependent field)

### 6.3 Real-Time Reactivity

`VisibilityProvider` is a `Provider<Map<String, bool>>` that `watch`es `FormStateNotifier`.
Every answer change invalidates this provider. Riverpod re-evaluates the provider synchronously
on the UI thread. Each question widget uses:

```dart
final isVisible = ref.watch(
  visibilityProvider.select((map) => map[questionId] ?? true)
);
if (!isVisible) return const SizedBox.shrink();
```

This means visibility updates happen within a single frame after the triggering field changes.

### 6.4 Section and Sub-section Visibility

Sections and sub-sections also carry `visibility_rules`. The section widget evaluates its own
visibility. If a section is hidden, all its questions are implicitly hidden and excluded from
validation and submission.

---

## 7. Primitive Components — Complete Reference

> **Standard properties** (`label`, `placeholder`, `required`, `disabled`, `readonly`,
> `hint_text`, `error_message`, `ui_overrides`) are accepted by every primitive and are not
> repeated in each component's property table.
>
> **Offline support**: Unless explicitly noted as ❌ offline, all primitives work fully offline.
> Components marked ⚠️ partial offline degrade gracefully.

---

### 7.1 Text & Input Group

---

#### `text_input`

**Flutter Widget**: `TextField` with `TextInputAction.next`, single line.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `max_length` | `int` | `null` | Maximum character count; shows counter if set |
| `min_length` | `int` | `null` | Minimum character count (validation only) |
| `autocorrect` | `bool` | `true` | Enable device autocorrect |
| `capitalization` | `enum[none\|words\|sentences\|characters]` | `sentences` | Text capitalization |
| `keyboard_type` | `enum[text\|multiline\|number\|phone\|email\|url]` | `text` | Mobile keyboard type |
| `prefix_text` | `String` | `""` | Static prefix inside input (e.g., currency symbol) |
| `suffix_text` | `String` | `""` | Static suffix inside input |
| `show_character_count` | `bool` | `false` | Show remaining characters below field |

**Value produced**: `AnswerValue { value: String, displayValue: String }`

**Validation options**: `min`, `max` (length), `min_length`, `max_length`, `pattern`, `required`

**Offline**: ✅ Full support

**Accessibility**: 
- `Semantics` widget wraps with `label`, `hint`, `textField: true`
- Supports screen reader (TalkBack/VoiceOver) — label is read before the input
- ARIA equivalent: `<input type="text" aria-label="..." aria-required="..." aria-describedby="hint">`

**Example `component_schema` usage**:

```json
{
  "type": "patient_name_field",
  "concept": "form_field",
  "composition": [
    {
      "primitive": "text_input",
      "property_key": "value",
      "label_from_property": "label",
      "static_properties": {
        "capitalization": "words",
        "max_length": 100,
        "keyboard_type": "text"
      }
    }
  ],
  "properties": [
    { "key": "label", "type": "string", "default": "Patient Name", "required": true },
    { "key": "placeholder", "type": "string", "default": "Enter full name" }
  ]
}
```

---

#### `text_area`

**Flutter Widget**: `TextField` with `maxLines: null`, `minLines: 3`, `expands: false`,
`TextInputAction.newline`.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `min_rows` | `int` | `3` | Minimum visible rows |
| `max_rows` | `int` | `8` | Maximum rows before scroll |
| `max_length` | `int` | `null` | Max character count |
| `show_character_count` | `bool` | `true` | Show character counter |

**Value produced**: `AnswerValue { value: String, displayValue: String }`

**Validation options**: `min_length`, `max_length`, `pattern`, `required`

**Offline**: ✅ Full support

**Accessibility**: Same as `text_input`. ARIA: `<textarea aria-label="..." aria-required="...">`

---

#### `number_input`

**Flutter Widget**: `TextField` with `keyboardType: TextInputType.numberWithOptions(decimal: true)`,
filtered by `FilteringTextInputFormatter`.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `min` | `num` | `null` | Minimum allowed value |
| `max` | `num` | `null` | Maximum allowed value |
| `step` | `num` | `1` | Step increment (informational; enforced on stepper only) |
| `decimal_places` | `int` | `2` | Max decimal places; `0` = integer only |
| `allow_negative` | `bool` | `false` | Allow negative numbers |
| `prefix_text` | `String` | `""` | e.g., `"₹"` or `"$"` |
| `suffix_text` | `String` | `""` | e.g., `"kg"` or `"%"` |
| `thousands_separator` | `bool` | `false` | Show thousands separator in display |

**Value produced**: `AnswerValue { value: num (int if decimal_places==0, double otherwise), displayValue: String }`

**Validation options**: `min`, `max`, `required`

**Offline**: ✅ Full support

**Accessibility**: `Semantics(label: label, value: currentValue.toString())`. ARIA: `<input type="number" min max>`

---

#### `email_input`

**Flutter Widget**: `TextField` with `keyboardType: TextInputType.emailAddress`,
`autocorrect: false`, `enableSuggestions: true`.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `validate_format` | `bool` | `true` | Auto-apply RFC 5322 email regex validation |
| `max_length` | `int` | `254` | Max characters (RFC 5321 limit) |
| `allow_multiple` | `bool` | `false` | Accept comma-separated list of emails |

**Value produced**: `AnswerValue { value: String (single) or List<String> (if allow_multiple), displayValue: String }`

**Validation options**: `required`, `pattern` (overrides built-in format check), `max_length`

**Offline**: ✅ Full support

**Accessibility**: ARIA: `<input type="email" autocomplete="email">`

---

#### `phone_input`

**Flutter Widget**: Custom widget composing a `DropdownButton` (country code, with flag emoji)
and a `TextField` (number part). Uses `intl_phone_number_input` package conventions.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `default_country_code` | `String` | `"IN"` | ISO 3166-1 alpha-2 country code |
| `allowed_country_codes` | `List<String>` | `[]` (all) | Restrict picker to these countries |
| `validate_format` | `bool` | `true` | Validate number format for selected country |
| `show_flag` | `bool` | `true` | Show country flag in picker |

**Value produced**:
```json
{
  "value": { "country_code": "+91", "number": "9876543210", "e164": "+919876543210" },
  "display_value": "+91 9876543210"
}
```

**Validation options**: `required`, `validate_format` (built-in)

**Offline**: ✅ Full support (country list is bundled)

**Accessibility**: Each sub-widget has its own `Semantics`. ARIA: `<input type="tel" autocomplete="tel">`

---

#### `password_input`

**Flutter Widget**: `TextField` with `obscureText: true`. Toggle button reveals/hides text.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `show_toggle` | `bool` | `true` | Show the eye icon to reveal password |
| `min_length` | `int` | `8` | Minimum password length |
| `require_uppercase` | `bool` | `false` | Must contain uppercase letter |
| `require_number` | `bool` | `false` | Must contain a digit |
| `require_special` | `bool` | `false` | Must contain a special character |
| `show_strength_meter` | `bool` | `false` | Display password strength indicator |

**Value produced**: `AnswerValue { value: String, displayValue: "••••••••" }`

> ⚠️ The raw password value is **never stored** in `form_responses.answers` on the server.
> This primitive is only used in auth-adjacent forms (e.g., registration flows), where the
> value is transmitted securely and not persisted as a response.

**Validation options**: `min_length`, `max_length`, `pattern`, `required`

**Offline**: ✅ Full support

**Accessibility**: Toggle button has `Semantics(label: 'Show password')`. ARIA: `<input type="password">`

---

#### `url_input`

**Flutter Widget**: `TextField` with `keyboardType: TextInputType.url`.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `validate_format` | `bool` | `true` | Auto-apply URL regex (http/https) |
| `allowed_schemes` | `List<String>` | `["http","https"]` | e.g., restrict to `["https"]` |
| `show_preview` | `bool` | `false` | Show URL favicon/title preview (online only) |
| `max_length` | `int` | `2048` | Max URL length |

**Value produced**: `AnswerValue { value: String, displayValue: String }`

**Validation options**: `required`, `pattern`, `max_length`

**Offline**: ✅ Full (preview feature is ⚠️ online-only if `show_preview: true`)

**Accessibility**: ARIA: `<input type="url" autocomplete="url">`

---

### 7.2 Selection Group

---

#### `dropdown`

**Flutter Widget**: Custom `DropdownFormField` built on `DropdownButton<String>` wrapped in
`FormField` for validation integration. On mobile, opens a bottom sheet for long option lists
(> 7 options).

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `options` | `List<{value: String, label: String, disabled?: bool}>` | `[]` | Option list |
| `allow_search` | `bool` | `false` | Show search filter inside dropdown |
| `use_bottom_sheet` | `bool` | `auto` | Force bottom sheet on all platforms |
| `empty_option_label` | `String` | `"Select..."` | Placeholder entry at top of list |
| `options_source` | `enum[static\|formula\|fetch]` | `static` | Where options come from |
| `options_formula_ast` | `Object` | `null` | Formula AST when `options_source == formula` |

**Value produced**: `AnswerValue { value: String (option.value), displayValue: String (option.label) }`

**Validation options**: `required`

**Offline**: ✅ Full for `static` options. `formula` options evaluated offline. `fetch` options: ⚠️ requires connectivity.

**Accessibility**: `Semantics(button: true, label: currentLabel)`. ARIA: `<select aria-label="...">`

**Example**:
```json
{
  "primitive": "dropdown",
  "property_key": "gender",
  "static_properties": {
    "options": [
      { "value": "male",   "label": "Male" },
      { "value": "female", "label": "Female" },
      { "value": "other",  "label": "Other" },
      { "value": "prefer_not_to_say", "label": "Prefer not to say" }
    ],
    "empty_option_label": "Select gender"
  }
}
```

---

#### `multi_select`

**Flutter Widget**: Custom `MultiSelectFormField` — a tappable chip-wrapped list that opens a
full-screen or modal multi-select checklist.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `options` | `List<{value, label, disabled?}>` | `[]` | Same format as `dropdown` |
| `min_selections` | `int` | `0` | Minimum required selections |
| `max_selections` | `int` | `null` | Maximum allowed selections |
| `display_style` | `enum[chips\|count\|list]` | `chips` | How selected values show on the field |
| `allow_search` | `bool` | `false` | Search filter in picker |
| `options_source` | `enum[static\|formula\|fetch]` | `static` | Same as `dropdown` |

**Value produced**: `AnswerValue { value: List<String>, displayValue: "A, B, C" }`

**Validation options**: `required` (at least 1), `min` (mapped to `min_selections`), `max` (mapped to `max_selections`)

**Offline**: ✅ Full for `static`. ⚠️ Same as `dropdown` for `fetch`.

**Accessibility**: Each option checkbox is individually labelled. ARIA: group of `<input type="checkbox">` inside `<fieldset>`.

---

#### `radio_group`

**Flutter Widget**: `Column` of `RadioListTile<String>` widgets.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `options` | `List<{value, label, disabled?}>` | `[]` | Option list |
| `layout` | `enum[vertical\|horizontal\|grid]` | `vertical` | Layout of radio items |
| `columns` | `int` | `2` | Used when `layout == grid` |
| `options_source` | `enum[static\|formula\|fetch]` | `static` | Same as `dropdown` |

**Value produced**: `AnswerValue { value: String, displayValue: String (label) }`

**Validation options**: `required`

**Offline**: ✅ Full for `static`.

**Accessibility**: Wrapped in `Semantics(label: groupLabel)`. ARIA: `<fieldset><legend>...</legend>` + `<input type="radio">` per option.

---

#### `checkbox`

**Flutter Widget**: `CheckboxListTile` with a single boolean value.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `check_label` | `String` | `""` | Label shown next to checkbox (distinct from field `label`) |
| `value_when_checked` | `String` | `"true"` | Value stored when checked |
| `value_when_unchecked` | `String` | `"false"` | Value stored when unchecked |
| `tri_state` | `bool` | `false` | Allow indeterminate state |

**Value produced**: `AnswerValue { value: bool, displayValue: "Yes" or "No" }`

**Validation options**: `required` (validates `value == true` — "must be checked")

**Offline**: ✅ Full

**Accessibility**: `Semantics(toggled: value, label: checkLabel)`. ARIA: `<input type="checkbox" aria-label="...">`.

---

#### `checkbox_group`

**Flutter Widget**: `Column` of `CheckboxListTile` widgets. Semantically a group.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `options` | `List<{value, label, disabled?}>` | `[]` | Checkbox items |
| `min_selections` | `int` | `0` | Min required checked |
| `max_selections` | `int` | `null` | Max allowed checked |
| `layout` | `enum[vertical\|horizontal\|grid]` | `vertical` | Layout |
| `columns` | `int` | `2` | Columns for `grid` layout |
| `options_source` | `enum[static\|formula\|fetch]` | `static` | Same as `dropdown` |

**Value produced**: `AnswerValue { value: List<String> (checked values), displayValue: "A, B" }`

**Validation options**: `required`, `min`, `max`

**Offline**: ✅ Full

**Accessibility**: ARIA: `<fieldset>` + `<input type="checkbox">` per option.

---

#### `toggle`

**Flutter Widget**: `SwitchListTile`.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `on_label` | `String` | `"On"` | Label shown when toggled on |
| `off_label` | `String` | `"Off"` | Label shown when toggled off |
| `initial_value` | `bool` | `false` | Default state |

**Value produced**: `AnswerValue { value: bool, displayValue: "On" or "Off" }`

**Validation options**: `required` (validates `value == true`)

**Offline**: ✅ Full

**Accessibility**: `Semantics(toggled: value)`. ARIA: `<input type="checkbox" role="switch">`.

---

#### `button_group`

**Flutter Widget**: Flutter Material `SegmentedButton<String>` (single-select mode).

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `options` | `List<{value, label, icon?: String}>` | `[]` | Segment options |
| `allow_deselect` | `bool` | `false` | Allow tapping again to deselect |
| `show_icons` | `bool` | `false` | Show icon in each segment |
| `layout` | `enum[horizontal\|wrap]` | `horizontal` | Wrap to multiple rows if needed |

**Value produced**: `AnswerValue { value: String or null, displayValue: String (label) }`

**Validation options**: `required`

**Offline**: ✅ Full

**Accessibility**: Each button has `Semantics(selected: isSelected)`. ARIA: `role="group"` + `<button aria-pressed="true/false">`.

---

### 7.3 Date & Time Group

---

#### `date_picker`

**Flutter Widget**: Opens `showDatePicker` (Material 3 calendar). Displays selected date in a
`TextFormField` (read-only tap target).

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `min_date` | `String` | `null` | ISO-8601 earliest selectable date |
| `max_date` | `String` | `null` | ISO-8601 latest selectable date |
| `initial_date` | `String` | `"today"` | `"today"` or ISO-8601 string |
| `date_format` | `String` | `"dd MMM yyyy"` | Display format (intl package pattern) |
| `first_day_of_week` | `enum[monday\|sunday]` | `monday` | Calendar week start |
| `selectable_weekdays` | `List<int>` | `[1,2,3,4,5,6,7]` | 1=Monday…7=Sunday |

**Value produced**: `AnswerValue { value: "YYYY-MM-DD", displayValue: "15 Jan 2026" }`

**Validation options**: `min` (mapped to min_date), `max` (mapped to max_date), `required`

**Offline**: ✅ Full

**Accessibility**: `Semantics(label: label, value: displayValue)`. ARIA: `<input type="date">`.

---

#### `time_picker`

**Flutter Widget**: Opens `showTimePicker` (Material 3 clock or input mode). Displays in a
`TextFormField`.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `use_24_hour` | `bool` | `true` | 24-hour vs AM/PM format |
| `min_time` | `String` | `null` | `"HH:MM"` earliest selectable time |
| `max_time` | `String` | `null` | `"HH:MM"` latest selectable time |
| `minute_interval` | `int` | `1` | Step for minute selector (1, 5, 10, 15, 30) |
| `initial_time` | `String` | `"now"` | `"now"` or `"HH:MM"` |

**Value produced**: `AnswerValue { value: "HH:MM", displayValue: "14:30" or "2:30 PM" }`

**Validation options**: `required`

**Offline**: ✅ Full

**Accessibility**: ARIA: `<input type="time">`.

---

#### `datetime_picker`

**Flutter Widget**: Custom widget composing `date_picker` + `time_picker` side-by-side or
sequentially. Produces a combined ISO-8601 datetime string.

**Properties**: Union of `date_picker` and `time_picker` properties plus:

| Key | Type | Default | Description |
|---|---|---|---|
| `layout` | `enum[row\|column\|separate_pickers]` | `row` | Display arrangement |
| `timezone` | `String` | `"Asia/Kolkata"` | IANA timezone; stored in UTC; displayed in local |

**Value produced**: `AnswerValue { value: "2026-01-15T14:30:00Z" (UTC ISO-8601), displayValue: "15 Jan 2026, 14:30" }`

**Validation options**: `required`

**Offline**: ✅ Full

---

#### `date_range_picker`

**Flutter Widget**: Opens `showDateRangePicker` (Material 3). Displays start and end dates.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `min_date` | `String` | `null` | ISO-8601 earliest date |
| `max_date` | `String` | `null` | ISO-8601 latest date |
| `min_range_days` | `int` | `null` | Minimum number of days in range |
| `max_range_days` | `int` | `null` | Maximum number of days in range |
| `date_format` | `String` | `"dd MMM yyyy"` | Display format |
| `allow_same_day` | `bool` | `true` | Whether start == end is valid |

**Value produced**:
```json
{
  "value": { "start": "2026-01-10", "end": "2026-01-20" },
  "display_value": "10 Jan – 20 Jan 2026"
}
```

**Validation options**: `required`, `min` (min_range_days), `max` (max_range_days)

**Offline**: ✅ Full

**Accessibility**: Both dates are individually announced. ARIA: two `<input type="date">` with labels.

---

### 7.4 Media & Files Group

---

#### `file_upload`

**Flutter Widget**: Custom `FileUploadWidget` using `file_picker` package. Shows upload
progress via `LinearProgressIndicator`. Completed uploads show as removable chips.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `allowed_types` | `List<enum[pdf\|image\|video\|any]>` | `["any"]` | MIME filter |
| `max_files` | `int` | `1` | Maximum file count |
| `max_size_bytes` | `int` | per system_config | Per-file size limit |
| `show_preview` | `bool` | `true` | Show thumbnail for images |
| `upload_immediately` | `bool` | `true` | Upload as soon as file selected vs on submit |
| `accept_camera` | `bool` | `false` | Show camera as source option |

**Value produced**: `AnswerValue { value: List<String> (upload IDs), fileIds: List<String>, displayValue: "2 files" }`

**Validation options**: `required`, `max` (maps to max_files)

**Offline**: ⚠️ Partial — file is stored locally (in app temp dir). Upload is queued to the offline queue. `upload_immediately: true` is effectively `false` when offline. Resumable via tus protocol on reconnect.

**Accessibility**: Drop zone has `Semantics(label: "File upload area")`. Button announces "Tap to select file". ARIA: `<input type="file">`.

---

#### `image_capture`

**Flutter Widget**: `ImageCaptureWidget` using `image_picker` package. Source options: Camera,
Gallery, or both.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `source` | `enum[camera\|gallery\|both]` | `both` | Allowed image sources |
| `max_images` | `int` | `1` | Maximum images |
| `max_width` | `int` | `1920` | Resize on capture (pixels) |
| `max_height` | `int` | `1080` | Resize on capture (pixels) |
| `image_quality` | `int` | `85` | JPEG quality 0–100 |
| `allow_crop` | `bool` | `false` | Show crop UI after selection |

**Value produced**: `AnswerValue { value: List<String> (upload IDs), fileIds: List<String>, displayValue: "1 image" }`

**Validation options**: `required`, `max` (max_images)

**Offline**: ⚠️ Same as `file_upload`. Images compressed locally before queuing.

**Accessibility**: Camera trigger button: `Semantics(label: "Take photo")`. Gallery: `Semantics(label: "Choose from gallery")`. ARIA: equivalent to `<input type="file" accept="image/*" capture>`.

---

#### `signature`

**Flutter Widget**: `SignatureWidget` using `signature` package. Renders a canvas where user
draws with finger or stylus.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `pen_color` | `String` | `"#000000"` | Stroke color (hex) |
| `pen_width` | `double` | `2.0` | Stroke width in logical pixels |
| `background_color` | `String` | `"#FFFFFF"` | Canvas background |
| `canvas_height` | `int` | `200` | Canvas height in logical pixels |
| `export_format` | `enum[base64\|upload_id]` | `upload_id` | How signature is stored |
| `show_clear_button` | `bool` | `true` | Allow user to clear and redo |

**Value produced**: 
- If `export_format == base64`: `AnswerValue { value: "data:image/png;base64,iVBO...", displayValue: "Signature captured" }`
- If `export_format == upload_id`: `AnswerValue { value: String (upload ID), fileIds: [uploadId], displayValue: "Signature captured" }`

**Validation options**: `required` (checks canvas is non-empty)

**Offline**: ✅ Full (base64 stored inline; upload_id queued)

**Accessibility**: Canvas has `Semantics(label: "Signature pad. Draw your signature here.")`. Provides a "Clear" button.

---

#### `audio_record`

**Flutter Widget**: `AudioRecordWidget` using `record` package. Shows record/stop/playback
controls. Displays waveform visualization during recording.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `max_duration_seconds` | `int` | `300` | 5-minute default limit |
| `audio_format` | `enum[aac\|mp3\|wav]` | `aac` | Recording format |
| `sample_rate` | `int` | `44100` | Audio sample rate |
| `allow_playback` | `bool` | `true` | Show playback controls after recording |
| `show_duration` | `bool` | `true` | Show elapsed/remaining time |

**Value produced**: `AnswerValue { value: String (upload ID), fileIds: [uploadId], displayValue: "Audio: 1m 23s" }`

**Validation options**: `required`

**Offline**: ⚠️ Records and stores locally; upload queued via tus.

**Accessibility**: Record/stop/play buttons each have descriptive `Semantics`. ARIA: `<audio controls>` equivalent + labeled buttons.

---

### 7.5 Interactive Group

---

#### `rating`

**Flutter Widget**: `RatingBarWidget` using `flutter_rating_bar` package. Renders star (or
custom icon) row.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `max_stars` | `int` | `5` | Number of stars to display |
| `allow_half` | `bool` | `false` | Allow half-star ratings |
| `icon` | `enum[star\|heart\|thumb_up\|circle]` | `star` | Icon shape |
| `active_color` | `String` | `"#FFC107"` | Filled icon color (hex) |
| `inactive_color` | `String` | `"#E0E0E0"` | Empty icon color |
| `show_label` | `bool` | `true` | Show numeric value next to stars |
| `initial_rating` | `num` | `0` | Default rating (0 = no rating) |

**Value produced**: `AnswerValue { value: num (0..max_stars), displayValue: "4 / 5" }`

**Validation options**: `required` (value > 0), `min`, `max`

**Offline**: ✅ Full

**Accessibility**: `Semantics(label: "$value out of $maxStars stars")`. ARIA: `role="radiogroup"` + `<input type="radio">` per star.

---

#### `slider`

**Flutter Widget**: Material `Slider` widget.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `min` | `num` | `0` | Minimum slider value |
| `max` | `num` | `100` | Maximum slider value |
| `step` | `num` | `1` | Snap increment |
| `show_value` | `bool` | `true` | Show current value label above thumb |
| `show_min_max_labels` | `bool` | `true` | Show min/max at ends |
| `track_color` | `String` | theme | Active track color |
| `thumb_color` | `String` | theme | Thumb color |
| `divisions` | `int` | `null` | Force discrete stops (auto-calculated from step) |

**Value produced**: `AnswerValue { value: num, displayValue: "42" }`

**Validation options**: `min`, `max`, `required`

**Offline**: ✅ Full

**Accessibility**: Slider thumb announces current value continuously. `Semantics(slider: true, value: "$value", increasedValue: ..., decreasedValue: ...)`. ARIA: `<input type="range">`.

---

#### `number_stepper`

**Flutter Widget**: Custom row: `IconButton(-)` + `Text(value)` + `IconButton(+)`. Long-press
on buttons initiates continuous increment/decrement.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `min` | `num` | `0` | Minimum value |
| `max` | `num` | `null` | Maximum value |
| `step` | `num` | `1` | Increment/decrement step |
| `decimal_places` | `int` | `0` | Decimal precision |
| `prefix_text` | `String` | `""` | Display prefix |
| `suffix_text` | `String` | `""` | Display suffix |

**Value produced**: `AnswerValue { value: num, displayValue: "5" }`

**Validation options**: `min`, `max`, `required`

**Offline**: ✅ Full

**Accessibility**: `Semantics(label: "Decrement $label")` / `"Increment $label"`. ARIA: `role="spinbutton" aria-valuemin aria-valuemax aria-valuenow`.

---

#### `color_picker`

**Flutter Widget**: Opens a bottom sheet with `flutter_colorpicker` package. Shows a
color spectrum + hex input. Displays selected color as a filled swatch on the field.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `allow_opacity` | `bool` | `false` | Include alpha/opacity control |
| `preset_colors` | `List<String>` | `[]` | Quick-select color swatches (hex) |
| `picker_type` | `enum[spectrum\|slider\|block]` | `spectrum` | Color picker UI style |
| `initial_color` | `String` | `"#000000"` | Default color |

**Value produced**: `AnswerValue { value: "#RRGGBB" or "#AARRGGBB" if opacity, displayValue: "#FF5733" }`

**Validation options**: `required`

**Offline**: ✅ Full

**Accessibility**: Selected color swatch has `Semantics(label: "Selected color: ${hex}")`. ARIA: custom role with hex value announced.

---

### 7.6 Location & Special Group

---

#### `location_picker`

**Flutter Widget**: `LocationPickerWidget` using `geolocator` + `flutter_map` (OpenStreetMap
tiles). Shows a map with a draggable pin. "Use current location" button triggers GPS.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `default_lat` | `double` | `28.6139` | Default map center latitude (New Delhi) |
| `default_lng` | `double` | `77.2090` | Default map center longitude |
| `default_zoom` | `double` | `13.0` | Initial map zoom level |
| `capture_address` | `bool` | `true` | Reverse-geocode coordinates to address string |
| `show_map` | `bool` | `true` | Display map widget (vs GPS-only mode) |
| `accuracy` | `enum[low\|medium\|high\|best]` | `medium` | GPS accuracy level |
| `allowed_radius_km` | `double` | `null` | Restrict to within N km of default_lat/lng |
| `map_provider` | `enum[osm\|google]` | `osm` | Map tile provider |

**Value produced**:
```json
{
  "value": {
    "lat": 28.6139, "lng": 77.2090,
    "address": "India Gate, New Delhi, 110001, India",
    "accuracy_meters": 5.2
  },
  "display_value": "India Gate, New Delhi (28.6139, 77.2090)"
}
```

**Validation options**: `required`

**Offline**: ⚠️ GPS capture works offline. Map tiles are not cached by default (OSM tiles require connectivity). Coordinates captured offline display as lat/lng only (no address reverse-geocoding). Set `show_map: false` for fully offline GPS capture.

**Accessibility**: "Use current location" button: `Semantics(label: "Get my current GPS location")`. ARIA: map is `aria-hidden`; coordinate values are read from a visually-hidden text element.

---

#### `barcode_scanner`

**Flutter Widget**: `BarcodeScannerWidget` using `mobile_scanner` package. Opens camera
fullscreen with overlay frame. On web, opens file upload fallback.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `formats` | `List<enum[qr\|ean13\|ean8\|code128\|code39\|upc_a\|upc_e\|aztec\|data_matrix]>` | `["qr","ean13","code128"]` | Accepted barcode formats |
| `scan_once` | `bool` | `true` | Auto-close after first scan |
| `allow_manual_entry` | `bool` | `true` | Fallback text input to type the code |
| `flash_enabled` | `bool` | `false` | Default flashlight state |
| `show_gallery_option` | `bool` | `false` | Pick image from gallery to scan |

**Value produced**: `AnswerValue { value: String (decoded text), displayValue: "4006381333931" }`

**Validation options**: `required`, `pattern` (validate barcode format/checksum)

**Offline**: ✅ Full (camera/scanning is device-local; no network needed)

**Accessibility**: Camera preview has `Semantics(label: "Barcode scanner camera preview")`. Scan success is announced via `SemanticsService.announce()`. ARIA: camera is `aria-hidden`; result field announces value.

---

#### `fetch_button`

**Flutter Widget**: `ElevatedButton` that triggers a `FetchActionDef`. Renders loading spinner
during fetch and fills target fields on success. Full details in §10.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `button_label` | `String` | `"Fetch Data"` | Button text |
| `button_icon` | `String` | `"download"` | Material icon name |
| `style` | `enum[elevated\|outlined\|text]` | `elevated` | Button visual style |
| `fetch_action` | `FetchActionDef` | `required` | Action definition (from question.fetch_action) |
| `show_loading_text` | `String` | `"Loading..."` | Text shown during loading |
| `show_success_snackbar` | `bool` | `true` | Show snackbar on success |
| `show_error_dialog` | `bool` | `true` | Show dialog on error |

**Value produced**: `null` (this primitive does not produce a value itself; it fills other fields)

**Validation options**: None (not an input)

**Offline**: See §10 — depends on `fetch_action.offline_behavior`

**Accessibility**: Button has `Semantics(button: true, label: buttonLabel)`. During loading: `Semantics(label: "Loading, please wait")`.

---

### 7.7 Display (Non-Input) Group

Display primitives do not produce values. They have `value: null` and `displayValue: ""`.
They are excluded from validation, required checks, and answer serialization.

---

#### `heading`

**Flutter Widget**: `Text` with `Theme.of(context).textTheme.headlineSmall` or configurable style.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `text` | `String` | `""` | Heading content (supports basic markdown: **bold**, *italic*) |
| `level` | `enum[h1\|h2\|h3\|h4]` | `h2` | Semantic heading level |
| `alignment` | `enum[left\|center\|right]` | `left` | Text alignment |
| `color` | `String` | theme | Text color (hex) |
| `font_size` | `double` | `null` | Override font size |
| `padding` | `List<double>` | `[0,0,8,0]` | `[top, right, bottom, left]` in logical pixels |

**Offline**: ✅ Full

**Accessibility**: `Semantics(header: true)`. ARIA: `<h1>` … `<h4>` matching the `level`.

---

#### `paragraph`

**Flutter Widget**: `MarkdownBody` from `flutter_markdown` package (subset of Markdown).

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `text` | `String` | `""` | Paragraph content (supports Markdown) |
| `alignment` | `enum[left\|center\|right\|justify]` | `left` | Text alignment |
| `color` | `String` | theme | Text color |
| `font_size` | `double` | `null` | Override font size |
| `padding` | `List<double>` | `[0,0,8,0]` | Padding |
| `selectable` | `bool` | `false` | Allow text selection/copy |

**Offline**: ✅ Full

**Accessibility**: `Semantics(label: plainText)` where `plainText` is the Markdown stripped of formatting. ARIA: `<p>`.

---

#### `divider`

**Flutter Widget**: `Divider` with configurable thickness and padding.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `thickness` | `double` | `1.0` | Line thickness |
| `color` | `String` | `"#E0E0E0"` | Line color |
| `indent` | `double` | `0` | Left indent |
| `end_indent` | `double` | `0` | Right indent |
| `height` | `double` | `24` | Total widget height (includes vertical padding) |

**Offline**: ✅ Full

**Accessibility**: `ExcludeSemantics` wraps it — purely decorative. ARIA: `<hr aria-hidden="true">`.

---

#### `image_display`

**Flutter Widget**: `CachedNetworkImage` (from `cached_network_image` package) for URLs;
`Image.file` for local paths.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `src` | `String` | `required` | URL or relative server path to image |
| `alt_text` | `String` | `""` | Alt text for accessibility |
| `fit` | `enum[contain\|cover\|fill\|fitWidth\|fitHeight]` | `contain` | Image fit mode |
| `height` | `double` | `null` | Fixed height (auto if null) |
| `width` | `double` | `null` | Fixed width (full width if null) |
| `border_radius` | `double` | `0` | Corner radius in logical pixels |
| `show_loading_indicator` | `bool` | `true` | Shimmer while loading |

**Offline**: ⚠️ Images from URLs are cached on first load. Not available offline if never previously loaded.

**Accessibility**: `Semantics(image: true, label: altText)`. ARIA: `<img alt="...">`.

---

#### `video_display`

**Flutter Widget**: `VideoPlayerWidget` using `video_player` + `chewie` packages for controls.

**Properties**:

| Key | Type | Default | Description |
|---|---|---|---|
| `src` | `String` | `required` | URL or server path to video |
| `auto_play` | `bool` | `false` | Start playing automatically |
| `loop` | `bool` | `false` | Loop video |
| `show_controls` | `bool` | `true` | Show play/pause/seek controls |
| `aspect_ratio` | `double` | `16/9` | Video aspect ratio |
| `muted` | `bool` | `false` | Start muted |
| `poster_url` | `String` | `null` | Thumbnail URL before play |

**Offline**: ⚠️ Not available offline unless the server-path asset has been previously cached.

**Accessibility**: `Semantics(label: "Video player: $label")`. Controls individually labelled. ARIA: `<video controls aria-label="...">`.

---

## 8. Composition System

### 8.1 What is a Composed Component?

A **composed component** is a `component_schema` whose `composition` array contains **two or
more** `PrimitiveRef` entries. Each `PrimitiveRef` maps a primitive widget to a specific
`property_key` in the parent component's answer object.

Example: A `blood_pressure` component composed of:
- `number_input` → `property_key: "systolic"`
- `number_input` → `property_key: "diastolic"`

The final answer stored for the question would be:
```json
{
  "systolic":  { "value": 120, "display_value": "120 mmHg" },
  "diastolic": { "value": 80,  "display_value": "80 mmHg" }
}
```

### 8.2 How `property_key` Works

Each `PrimitiveRef` in the `composition` array has a `property_key` string. When the primitive
fires `onChanged`:

1. `CompositionRenderer` receives `(propertyKey, newValue)`.
2. It updates its internal `Map<String, AnswerValue> _primitiveValues` at `[propertyKey]`.
3. It calls `widget.onValueChanged(componentPropertyKey, ComponentAnswerMap(_primitiveValues))`.

The top-level `componentPropertyKey` (used in `FormStateNotifier`) is the `question.id` from the
form schema.

### 8.3 Rendering Composed Components

`CompositionRenderer` renders each `PrimitiveRef` in order:

```dart
class CompositionRenderer extends ConsumerStatefulWidget {
  final List<PrimitiveRef> refs;
  final Map<String, AnswerValue> initialValues;
  final void Function(Map<String, AnswerValue>) onChanged;
  final FormContext formContext;
  final bool readOnly;
}
```

Each `PrimitiveRef` is rendered with:
- Its own `visibility` rules evaluated independently against `FormContext + current state`
- Its own `label` resolved from `label_from_property`
- Merged properties (schema defaults + question instance overrides)

If a `PrimitiveRef.visibility` evaluates to `false`, the primitive is hidden via
`SizedBox.shrink()` and its `property_key` is **excluded** from the `ComponentAnswerMap`.

### 8.4 Composition Validation

Composition validation checks whether all **required** primitives within the composition have
answered. A primitive is required if:
1. Its `PrimitiveRef` has `required: true` in `static_properties`, **or**
2. The parent component schema's `PropertyDef` for that `property_key` has `required: true`.

`CompositionValidator.validate(Map<String, AnswerValue> values, List<PrimitiveRef> refs) → Map<String, List<String>> errors`

The returned error map is keyed by `property_key`. Each key maps to a list of error messages
for that primitive. This map is merged into `FormStateNotifier.validationErrors` using the
format `"${questionId}.${propertyKey}"` as the key.

### 8.5 Nested Compositions

**Nested compositions are not supported** in the current design. A `PrimitiveRef.primitive`
must always reference a primitive component type (a leaf in the registry). It cannot reference
another composite `component_type`. This restriction is enforced at schema validation time
(on the backend, when a `component_schema` is saved) and again at render time in
`PrimitiveRenderer` (unknown types fall back to `UnknownPrimitiveWidget`).

**Rationale**: Nested compositions create unbounded recursion in the rendering pipeline and
ambiguity in the answer structure. The current primitives are expressive enough without nesting.
If nesting is required in the future, a separate design review must occur.

---

## 9. Formula Builder & Engine

### 9.1 Overview

The **Formula Builder** is a modal UI (`FormulaBuilderModal`) that allows form designers to
visually construct a computation formula. The output is stored as a `formula_ast` JSON object
in `CalculationDef.formula_ast`. At form-fill time, `FormulaEngine.evaluate()` traverses the
AST and produces a result that is applied to a target question's answer.

### 9.2 Formula AST Node Types

All AST nodes share a discriminated union shape: `{ "node_type": "...", ... }`.

#### Literal Node

```json
{
  "node_type": "literal",
  "value_type": "string|number|boolean|date|null",
  "value": "any"
}
```

| Field | Description |
|---|---|
| `value_type` | Data type of the literal value |
| `value` | The literal value (`"hello"`, `42`, `true`, `"2026-01-15"`, `null`) |

#### Reference Node

```json
{
  "node_type": "reference",
  "field_id": "question_uuid",
  "sub_key": "systolic"
}
```

| Field | Description |
|---|---|
| `field_id` | UUID of the question in the same form |
| `sub_key` | Optional — for composed components, which `property_key` to extract |
| `form_id` | Optional ObjectId — for cross-form references (see §9.9) |

#### Operation Node

```json
{
  "node_type": "operation",
  "op": "add",
  "operands": [ <AstNode>, <AstNode>, ... ]
}
```

**Supported operations**:

| `op` | Operand count | Input types | Output type | Description |
|---|---|---|---|---|
| `add` | 2+ | `number` | `number` | Sum of all operands |
| `subtract` | 2 | `number` | `number` | `operands[0] - operands[1]` |
| `multiply` | 2+ | `number` | `number` | Product of all operands |
| `divide` | 2 | `number` | `number` | `operands[0] / operands[1]`; produces `null` if divisor is 0 |
| `concat` | 2+ | `string` | `string` | Concatenates all string operands |
| `if_else` | 3 | `boolean, any, any` | `any` | `operands[0] ? operands[1] : operands[2]` |
| `round` | 1–2 | `number, number?` | `number` | Round `operands[0]` to `operands[1]` decimal places (default 0) |
| `abs` | 1 | `number` | `number` | Absolute value |
| `min` | 2+ | `number` | `number` | Minimum of all operands |
| `max` | 2+ | `number` | `number` | Maximum of all operands |
| `count` | 1 | `array` | `number` | Count of non-null items in array |
| `sum` | 1 | `array` | `number` | Sum of all numeric items in array |
| `equals` | 2 | `any` | `boolean` | Strict equality |
| `not_equals` | 2 | `any` | `boolean` | Strict inequality |
| `greater_than` | 2 | `number\|date` | `boolean` | `operands[0] > operands[1]` |
| `less_than` | 2 | `number\|date` | `boolean` | `operands[0] < operands[1]` |
| `and` | 2+ | `boolean` | `boolean` | Logical AND |
| `or` | 2+ | `boolean` | `boolean` | Logical OR |
| `not` | 1 | `boolean` | `boolean` | Logical NOT |
| `date_diff` | 3 | `date, date, string` | `number` | Difference between two dates in `operands[2]` units (`"days"\|"months"\|"years"`) |
| `to_string` | 1 | `any` | `string` | Coerce value to string |
| `to_number` | 1 | `string\|boolean` | `number` | Coerce to number; non-numeric strings produce `null` |
| `length` | 1 | `string\|array` | `number` | String length or array length |
| `upper` | 1 | `string` | `string` | Uppercase |
| `lower` | 1 | `string` | `string` | Lowercase |
| `contains` | 2 | `string\|array, any` | `boolean` | Substring or array inclusion check |

### 9.3 Example Formula AST

**Formula: `BMI = weight_kg / (height_m * height_m)`, rounded to 1 decimal place**

```json
{
  "node_type": "operation",
  "op": "round",
  "operands": [
    {
      "node_type": "operation",
      "op": "divide",
      "operands": [
        { "node_type": "reference", "field_id": "q_weight_uuid" },
        {
          "node_type": "operation",
          "op": "multiply",
          "operands": [
            { "node_type": "reference", "field_id": "q_height_uuid" },
            { "node_type": "reference", "field_id": "q_height_uuid" }
          ]
        }
      ]
    },
    { "node_type": "literal", "value_type": "number", "value": 1 }
  ]
}
```

### 9.4 Visual Formula Builder (FormulaBuilderModal)

The `FormulaBuilderModal` is a full-screen modal dialog that allows drag-and-drop assembly of
AST nodes. The UI has three panels:

**Left panel — Node Palette**:
- "Literal" block (shows sub-types: number, text, boolean)
- "Field Reference" block (shows a searchable list of form questions by label)
- "Operation" blocks grouped by category (Math, Logic, Text, Date, Array)

**Center panel — Builder Canvas**:
- Nodes can be dragged from palette into the canvas
- Each node renders as a card with its type label and input slots for operands
- Operand slots are typed drop-zones (highlighted in green when a compatible node is dragged)
- A node tree represents the formula AST
- The root node determines the output type

**Right panel — Preview**:
- Shows a real-time preview of the formula evaluation using sample/current values
- Shows the generated formula in a human-readable expression format (e.g., `round(q1 / (q2 * q2), 1)`)
- Shows type errors in red if operand types don't match

**Serialization**: The canvas node graph is serialized to the `formula_ast` JSON structure on Save.
The modal receives an optional existing `formula_ast` to pre-populate on edit.

### 9.5 FormulaEngine Evaluation Algorithm

```dart
class FormulaEngine {
  /// Evaluates a formula AST against the current form state.
  ///
  /// Returns FormulaResult { value: dynamic, error: String? }
  /// If [value] is null and [error] is null, it means a referenced field
  /// has no answer yet (deferred evaluation).
  FormulaResult evaluate(
    Map<String, dynamic> ast,
    FormState state,
    { String? contextFormId }
  );
}
```

**Evaluation steps**:

1. Determine `node_type`.
2. **`literal`**: Return `ast['value']` coerced to `ast['value_type']`.
3. **`reference`**:
   a. Look up `field_id` in `state.answerMap`.
   b. If not found and `form_id` is present → cross-form reference (see §9.9).
   c. If answer is `null` or empty → return `FormulaResult(value: null)` (deferred).
   d. If `sub_key` is present → extract `answerValue.value[sub_key]`.
   e. Return the extracted value.
4. **`operation`**:
   a. Recursively evaluate each operand.
   b. If any operand is deferred (value is null) → propagate deferral: return `FormulaResult(value: null)`.
   c. If any operand has an error → propagate error.
   d. Apply the operation.
   e. Return `FormulaResult(value: result)`.

### 9.6 Supported Data Types in Formulas

| Type | Dart representation | Notes |
|---|---|---|
| `string` | `String` | UTF-8, any length |
| `number` | `num` (`int` or `double`) | IEEE 754 double precision |
| `boolean` | `bool` | `true` / `false` |
| `date` | `String` ISO-8601 `"YYYY-MM-DD"` | Date-only; comparisons use lexicographic sort |
| `array` | `List<dynamic>` | From `checkbox_group`, `multi_select`, repeatable sections |
| `null` | `null` | Represents unanswered/deferred values |

### 9.7 Error Handling

| Error condition | Behavior |
|---|---|
| Referenced `field_id` not in form schema | Compile-time error shown in formula builder; field highlighted in red |
| Referenced field not yet answered | Deferred — formula returns `null`; target field shows no value (blank) |
| Division by zero | Returns `null` (not an error); target field shows blank |
| Type mismatch (e.g., `add(string, number)`) | Returns `FormulaResult(error: "Type mismatch: cannot add string and number")` |
| `to_number` on non-numeric string | Returns `null` |
| `date_diff` with invalid unit | Returns `FormulaResult(error: "Invalid date unit: must be days, months, or years")` |
| Cross-form data not yet synced | Returns `null` (deferred, as if field not answered) |

When `FormulaResult.error` is non-null, the target question renders an error message below it:
`"Formula error: ${result.error}"`. This is shown instead of (not in addition to) the field's
normal validation error.

### 9.8 CalculationDef — When Formulas Fire

```dart
class CalculationDef {
  final CalculationTrigger trigger;  // on_change | on_load
  final Map<String, dynamic> formulaAst;
  final String targetQuestionId;
}
```

| `trigger` | When it fires |
|---|---|
| `on_change` | Immediately whenever any `reference` field in the AST changes value |
| `on_load` | Once when the form section first renders (and on_change subsequently) |

The `FormulaResultProvider` is a `Provider<Map<String, AnswerValue>>` that:
1. Watches `FormStateNotifier`.
2. Finds all `CalculationDef` entries across all visible questions.
3. Evaluates each formula.
4. Returns a map of `targetQuestionId → computed AnswerValue`.

The target question widget observes this provider and:
- If `formula_ast` is set on the question, the field is rendered **read-only** (user cannot edit
  a formula-computed field).
- The computed value is applied via `FormStateNotifier.applyFormulaResult()`.

### 9.9 Cross-Form Data References

A `reference` node with `form_id` set references data from another form the user has previously
submitted:

```json
{
  "node_type": "reference",
  "form_id": "60f1a2b3c4d5e6f7a8b9c0d1",
  "field_id": "q_allergies_uuid"
}
```

**Resolution algorithm**:
1. `FormulaEngine` detects `form_id != null`.
2. Looks up the latest submitted response for the user in the Drift `form_responses` table for
   that `form_id`.
3. Extracts the answer for `field_id`.
4. If no response found → returns `null` (deferred).
5. If the referenced form schema version has changed and the `field_id` no longer exists in
   the latest schema → returns `FormulaResult(error: "Field no longer exists in referenced form")`.

Cross-form references are read-only. The formula engine never writes to other forms.

---

## 10. Fetch Action Button

The `fetch_button` primitive triggers a `FetchActionDef` to pre-populate other form fields
from an external source. This section documents all source types, states, and offline behavior.

### 10.1 FetchActionDef Model

```dart
class FetchActionDef {
  final FetchSource source;            // own_previous_response | other_form_last_response | external_url
  final String? formId;                // Required for other_form_last_response (ObjectId string)
  final String? url;                   // Required for external_url
  final HttpMethod? method;            // GET | POST (for external_url)
  final Map<String, String>? headers;  // HTTP headers (for external_url)
  final String? bodyTemplate;          // JSON template string for POST body (supports {{field_id}} interpolation)
  final List<FieldMapping> fieldMapping; // Maps source JSON paths to target question IDs
  final OfflineBehavior offlineBehavior; // leave_blank | block_submission | use_cache
}

class FieldMapping {
  final String sourcePath;       // JSONPath expression (e.g., "data.patient.name")
  final String targetQuestionId; // UUID of form question to populate
}
```

### 10.2 Source Type: `own_previous_response`

**Use case**: Pre-fill fields from the current user's last submission of this same form.

**Request construction** (internal API):
```
GET /api/internal/v1/forms/{formId}/responses/my-last
Authorization: Bearer {jwt}
```

**Response**: The latest `form_response` document for `(form_id, respondent_id)` where
`status == submitted`.

**Field mapping algorithm**:
1. Receive response JSON.
2. For each `FieldMapping` in `fieldMapping`:
   a. Evaluate `sourcePath` as a JSONPath against `response.answers`.
   b. Resolve the value (may be an `AnswerValue` object).
   c. Find the target question in the current form by `targetQuestionId`.
   d. Convert the resolved value to the target question's expected `AnswerValue` type.
   e. Call `FormStateNotifier.updateAnswer(targetQuestionId, convertedValue)`.
3. Fields not matched by any `FieldMapping` are left untouched.

**Type conversion rules**:
- If source and target primitive types match → copy `value` and `displayValue` directly.
- `String → number`: `num.tryParse(value)` — null if non-numeric.
- `number → String`: `value.toString()`.
- `List<String> → String`: `value.join(', ')`.
- `String → List<String>`: wrap in list `[value]`.
- All other cross-type conversions: skip (log warning) and leave target field unchanged.

**Offline behavior**:
| `offline_behavior` | Action |
|---|---|
| `leave_blank` | Silently do nothing; no error shown |
| `block_submission` | Show error: "Cannot submit offline — required data could not be fetched" |
| `use_cache` | Query Drift `form_responses` table for last local response; apply mapping |

### 10.3 Source Type: `other_form_last_response`

**Use case**: Pull data from a different form. E.g., pull patient demographics from a
registration form into a clinical follow-up form.

**Request construction** (internal API):
```
GET /api/internal/v1/forms/{fetchAction.formId}/responses/my-last
Authorization: Bearer {jwt}
```

**Field mapping algorithm**: Identical to §10.2.

**Offline behavior**: Same options as §10.2. `use_cache` queries Drift `form_responses` for the
referenced `form_id`.

**Access control**: The user must have at minimum `org_viewer` role for the org that owns the
referenced form, AND the form's `access.type` must allow the user. The backend validates this
before returning the response. If unauthorized, the API returns `403 Forbidden` and the button
shows: `"You do not have access to the referenced form data"`.

### 10.4 Source Type: `external_url`

**Use case**: Fetch data from an external REST API endpoint. E.g., lookup a patient by hospital
ID from a hospital information system.

**Request construction**:
```
Method: fetchAction.method (GET or POST)
URL:    fetchAction.url (supports {{field_id}} template interpolation)
Headers: fetchAction.headers (merged with { "Content-Type": "application/json" } for POST)
Body:   fetchAction.bodyTemplate with {{field_id}} tokens replaced by current answer values
```

**URL interpolation**:
`fetchAction.url` may contain `{{question_uuid}}` tokens. Before the request, each token is
replaced with `formState.answerMap[question_uuid]?.displayValue ?? ''`.

Example:
```
url: "https://his.aiims.edu/api/patients/{{q_hospital_id_uuid}}"
```
becomes:
```
https://his.aiims.edu/api/patients/AIIMS-2026-001234
```

**Body template interpolation**: Same token replacement, with URL-encoding omitted (raw values
inserted into JSON). The `bodyTemplate` must be a valid JSON string after substitution.

**Response parsing**:
- Expects a JSON response body.
- `FieldMapping.sourcePath` uses dot-notation JSONPath (e.g., `"patient.name"`, `"data[0].age"`).
- Arrays in the path are supported for index access only (no wildcards).
- If the path doesn't exist in the response → skip that mapping (log warning).

**HTTP error handling**:
| HTTP status | Behavior |
|---|---|
| 200–299 | Proceed with field mapping |
| 400–499 | Show error dialog: "Request failed: HTTP {status}" |
| 500–599 | Show error dialog: "Server error at data source. Try again." |
| Timeout (> 30s) | Show error dialog: "Request timed out" |

**Security note**: `external_url` calls are made **from the Flutter client directly** (not
proxied through the platform backend) unless the question's FetchActionDef is configured with
`proxy: true` (a future feature). Form designers must be trusted users (org_editor+) to
configure `external_url` actions, because they can direct client HTTP calls.

**Offline behavior**:
| `offline_behavior` | Action |
|---|---|
| `leave_blank` | Do nothing offline |
| `block_submission` | Block submission with error |
| `use_cache` | Use last successful fetch result cached in Drift `fetch_cache` table (keyed by `question_id + last_known_url`) |

### 10.5 UI States

The `fetch_button` primitive renders four distinct visual states:

| State | Visual | Semantics |
|---|---|---|
| **Idle** | Button with label and icon | Normal tappable button |
| **Loading** | Button disabled + `CircularProgressIndicator` inside + loading text | `Semantics(label: "Loading, please wait")` |
| **Success** | Brief green checkmark animation → returns to idle; optional snackbar | Snackbar: "Data loaded successfully" |
| **Error** | Error dialog or inline red text below button | Error message from §10.4 |

State transitions:
```
Idle → (user taps) → Loading → (API call completes) → Success or Error → Idle
```

During **Loading**, all other form inputs remain interactive (fetch does not block the form).
The button itself is disabled to prevent double-tap.

### 10.6 Offline Queue for Fetch Results

When `use_cache` is the offline behavior:

- After every **successful** fetch, the result JSON is written to a Drift `fetch_cache` table:
  ```
  fetch_cache (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id    TEXT NOT NULL,
    cache_key      TEXT NOT NULL,   -- hash of (source, url, resolved_params)
    result_json    TEXT NOT NULL,   -- raw JSON response body
    fetched_at     INTEGER NOT NULL -- Unix ms timestamp
  )
  ```
- On next fetch attempt while offline → query by `(question_id, cache_key)` → apply cached result.
- Cache entries expire after 24 hours (stale cache older than 24h is treated as no cache).
- Cache is per-device and per-user (stored in the user's Drift database).

---

*End of 09_COMPONENT_LIBRARY.md*
