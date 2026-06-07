# 16 — Testing Policy

This document defines testing expectations, coverage limits, mocking practices, and automated validation patterns.

---

## 1. Test Coverage Goals

We require a minimum test coverage of **80%** across both the backend and frontend components.

| Component | Target Coverage | Tooling |
|---|---|---|
| **Python Backend** | 80% (Services, Routes, Calculations) | `pytest` + `pytest-cov` |
| **Flutter Frontend** | 70% (Data mapping, JSON UI Engine) | `flutter test` |

---

## 2. Backend Testing Conventions

- **Database Mocking**: Avoid testing against live production databases. Use `mongomock` inside pytest fixtures to mock MongoDB in memory.
- **Queue Stubbing**: Celery tasks are tested synchronously by setting `CELERY_TASK_ALWAYS_EAGER = True`.

Example test fixture mapping:
```python
# conftest.py
import pytest
import mongomock

@pytest.fixture
def mock_db():
    client = mongomock.MongoClient()
    return client.form_builder
```

---

## 3. Flutter Testing Conventions

- **JSON UI Engine Verification**: Write unit tests supplying arbitrary JSON schemas and assert that the generated Flutter element tree contains correct field instances.
- **Golden Tests**: Run pixel-perfect comparison tests for key input widgets (e.g. date pickers, signature fields) to avoid layout degradation between Flutter framework updates.
- **Integration Tests**: Leverage `integration_test` to simulate offline record insertion and verify synchronization queues execute successfully upon mock server reconnection.
