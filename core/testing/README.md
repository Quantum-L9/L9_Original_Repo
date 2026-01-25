---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "2026-01-25 19:42:30 UTC"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "system clock (UNVERIFIED - no API response)"
  auto_generated: true
---

# Testing Utilities

> **Tier:** CORE | **Path:** `core/testing` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                            Testing Utilities                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_testin   │ ───► │  Outbound   │                  │
│  │ Dependencies│      │   Module    │      │ Dependencies│                  │
│  └─────────────┘      └─────────────┘      └─────────────┘                  │
│                              │                                              │
│                              ▼                                              │
│                    ┌─────────────────┐                                      │
│                    │  Memory/Audit   │                                      │
│                    │   Substrate     │                                      │
│                    └─────────────────┘                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Overview

Test utilities, fixtures, and mocks

**Purpose:** Provides testing infrastructure for subsystem tests.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core testing tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics

### What This Module Does NOT Do

- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py

### Inbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No inbound dependencies |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No outbound dependencies |

---

## Directory Layout

```
core/testing/
├── __init__.py
├── test_agent.py
├── test_executor.py
├── test_generator.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `test_generator.py` | Generates tests from code proposals. |
| `test_agent.py` | Result of test agent execution. |
| `test_agent.py` | Agent that generates and executes tests for code p |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreTestingService`)
- **Functions:** `snake_case` (e.g., `process_core_testing_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `test_generator.py` — TestGenerator

```python
class TestGenerator:
    """Generates tests from code proposals."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def generate_unit_tests(self, ...): ...

    async def generate_integration_tests(self, ...): ...

    async def _generate_function_tests(self, ...): ...

    async def _generate_class_tests(self, ...): ...

```

**Public Methods:** `__init__`, `generate_unit_tests`, `generate_integration_tests`, `_generate_function_tests`, `_generate_class_tests`

**Lines:** 46-279 in `test_generator.py`

### `test_agent.py` — TestAgentResult

```python
class TestAgentResult:
    """Result of test agent execution."""
    
    # Key methods:

    async def to_dict(self, ...): ...

```

**Public Methods:** `to_dict`

**Lines:** 50-82 in `test_agent.py`

### `test_agent.py` — TestAgent

```python
class TestAgent:
    """Agent that generates and executes tests for code proposals."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def validate_proposal(self, ...): ...

    async def _build_test_file(self, ...): ...

    async def _generate_recommendations(self, ...): ...

    async def _store_results(self, ...): ...

```

**Public Methods:** `__init__`, `validate_proposal`, `_build_test_file`, `_generate_recommendations`, `_store_results`

**Lines:** 85-291 in `test_agent.py`

### `test_executor.py` — TestResult

```python
class TestResult:
    """Result of a single test."""
    
    # Key methods:

```

**Lines:** 53-60 in `test_executor.py`

### `test_executor.py` — TestResults

```python
class TestResults:
    """Results of a test run."""
    
    # Key methods:

    async def to_dict(self, ...): ...

```

**Public Methods:** `to_dict`

**Lines:** 64-101 in `test_executor.py`


---

## Data Models and Contracts

Data models are defined in `schemas.py` or inline within service classes.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreTestingRequest(BaseModel):
    """Request model for core_testing operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreTestingResponse(BaseModel):
    """Response model for core_testing operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **All operations must be idempotent**
- **State changes logged to audit trail**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Testing components are discovered and registered.
2. **Configuration:** Settings loaded from environment and config files.
3. **Dependencies:** Required services (Redis, PostgreSQL, etc.) are connected.
4. **Initialization:** Internal state is initialized; ready for requests.

### Main Execution

1. **Request received:** Validate input against schema.
2. **Processing:** Execute core logic with appropriate error handling.
3. **State updates:** Persist any state changes atomically.
4. **Response:** Return structured response with timing metadata.

### Shutdown

1. **Graceful stop:** Stop accepting new requests.
2. **Drain:** Complete in-flight operations (with timeout).
3. **Cleanup:** Release resources, close connections.
4. **Log:** Emit shutdown complete event.

### Background Tasks

No background tasks. Operations are request-driven.

---

## Configuration

### Feature Flags

```yaml
# Core_Testing feature flags
L9_ENABLE_CORE_TESTING_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_TESTING_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_TESTING_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_testing:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_TESTING_LOG_LEVEL=INFO
CORE_TESTING_TIMEOUT=30
CORE_TESTING_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def generate_unit_tests(code_proposal, module_name)`

Convenience function to generate unit tests.

- **File:** `test_generator.py:282`
- **Async:** No

#### `def generate_integration_tests(code_proposal, dependencies, module_name)`

Convenience function to generate integration tests.

- **File:** `test_generator.py:299`
- **Async:** No

#### `async def spawn_test_agent(task_id, code_proposal, substrate_service, dependencies)`

Spawn a test agent to validate a code proposal.

- **File:** `test_agent.py:294`
- **Async:** Yes

#### `async def run_tests_in_sandbox(test_code, source_code, env_config)`

Convenience function to run tests in sandbox.

- **File:** `test_executor.py:306`
- **Async:** Yes


### Usage Example

```python
from core.testing import CoreTestingService

# Initialize
service = CoreTestingService()

# Execute operation
result = await service.execute(
    request_id="req-001",
    data={"key": "value"},
    correlation_id="corr-xyz789",
)

print(result.success)  # True
print(result.duration_ms)  # 125.5
```

---

## Observability

### Logging

Core Testing operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "core.testing",
  "message": "Operation completed",
  "correlation_id": "corr-xyz789",
  "agent_id": "agent-001",
  "duration_ms": 125
}
```

**Log Levels:**
- `DEBUG` — Detailed execution steps (off in production)
- `INFO` — Lifecycle events, successful operations
- `WARNING` — Timeouts, resource warnings, recoverable errors
- `ERROR` — Failures, exceptions, unrecoverable errors

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `core_testing_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_testing_operation_total` | Counter | Total operations processed |
| `core_testing_error_total` | Counter | Total errors encountered |
| `core_testing_active_connections` | Gauge | Current active connections |

### Tracing

Core Testing emits OpenTelemetry spans:

- `core_testing.execute` — Root span for operation
  - `core_testing.validate` — Input validation
  - `core_testing.process` — Core processing
  - `core_testing.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_testing/`:
- `test_core_testing.py` — Core unit tests
- `test_core_testing_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_testing with real dependencies
- Test cross-subsystem interactions
- Test failure scenarios and recovery

### Known Edge Cases

1. **Timeout:** Operation exceeds deadline → Return partial result with timeout status.
2. **Invalid input:** Schema validation fails → Return 400 with validation errors.
3. **Dependency unavailable:** Required service down → Retry with exponential backoff, then fail gracefully.
4. **Resource exhaustion:** Memory/connections exceeded → Reject new requests, log alert.

---

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

- `**/*.py` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `__init__.py` — PROTECTED: Changes break system invariants

### Required Pre-Reading

1. [`README-L9_ARCHITECTURE.md`](README-L9_ARCHITECTURE.md)
2. [`docs/CURSOR-RUNBOOK.md`](docs/CURSOR-RUNBOOK.md)

### Change Policy

All changes proposed by AI tools must:
1. Be scoped PRs with clear commit messages
2. Include tests (unit + integration where applicable)
3. Update documentation if APIs change
4. Respect feature flags for gradual rollout
5. Get human approval for restricted scopes
