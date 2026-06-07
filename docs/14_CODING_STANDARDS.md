# 14 — Coding Standards

This document establishes the styling guides, validation rules, and structural layers required for the backend and frontend codebases.

---

## 1. Python Backend Standards

### 1.1 Styling & Formats
- Conform to **PEP 8** formatting. Code formatting is enforced via `black`.
- Type hints are required on all public methods and route definitions.

### 1.2 Repository Pattern
- **Routes / Controllers** (`/routes`): Keep thin. Handle routing, request serialization, and HTTP return codes. Delegate business computations to services.
- **Services** (`/services`): Execute transactional steps. Read or write to MongoDB collections.
- **Engines** (`/engines`): House core platform algorithms (e.g. topological sorting, subprocess sandboxing).

---

## 2. Flutter / Dart Standards

### 2.1 Feature-First Directory Structure
Features are organized into distinct folders containing UI presentation and data layers:
```
lib/features/form_builder/
  presentation/
    screens/
    widgets/
    controllers/
  data/
    repositories/
    datasources/
```

### 2.2 Riverpod Architecture
- Use Riverpod state management. Avoid using local `setState` inside complex layouts.
- **Data Fetching**: Use `FutureProvider` or `AsyncNotifierProvider` to retrieve remote lists.
- **Sync/Local Operations**: Encapsulate Drift database operations inside service classes exposed by a Riverpod `Provider`.
- Maintain widget modularity by using `ConsumerWidget` or `ConsumerStatefulWidget` instead of deeply nested standard StatefulWidgets.
