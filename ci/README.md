---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "2026-02-17 00:14:44 UTC"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "system clock (verification skipped)"
  auto_generated: true
---

# CI Infrastructure

> **Tier:** INFRASTRUCTURE | **Path:** `ci` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                            CI Infrastructure                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │        ci       │ ───► │  Outbound   │                  │
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

Continuous integration scripts and guardrails

**Purpose:** Provides CI/CD infrastructure, guardrails, and automated checks.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute ci tasks
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
ci/
├── __init__.py
├── ai_guardrails/__init__.py
├── ai_guardrails/runner.py
├── auto_fix_adr.py
├── auto_stub_adr_enforcement.py
├── check_adr_compliance.py
├── check_adr_enforcement_manifest.py
├── check_crypto_usage.py
├── check_dag_validation_single_point.py
├── check_datetime_utcnow.py
├── check_definition_of_done.py
├── check_dependency_patterns.py
├── check_dora_compliance.py
├── check_forbidden_imports.py
├── check_fstring_sql.py
└── ... (22 more files)
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `check_memory_bypass.py` | Represents a memory bypass violation. |
| `check_global_state.py` | Performs static analysis of Python files to detect |
| `check_schema_deprecation.py` | A single deprecated import violation. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CiService`)
- **Functions:** `snake_case` (e.g., `process_ci_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `check_memory_bypass.py` — BypassViolation

```python
class BypassViolation:
    """Represents a memory bypass violation."""

    # Key methods:

    def __init__(self, ...): ...

    def __str__(self, ...) -> str: ...

```

**Public Methods:** `__init__`, `__str__`

**Lines:** 135-146 in `check_memory_bypass.py`

### `check_global_state.py` — GlobalStateVisitor

```python
class GlobalStateVisitor:
    """Performs static analysis of Python files to detect suspicious module-level mutable state patterns, aiding in global state audit."""

    # Key methods:

    def __init__(self, ...) -> None: ...

    def visit_Assign(self, ...) -> None: ...

    def generic_visit(self, ...) -> None: ...

```

**Public Methods:** `__init__`, `visit_Assign`, `generic_visit`

**Lines:** 60-111 in `check_global_state.py`

### `check_schema_deprecation.py` — Violation

```python
class Violation:
    """A single deprecated import violation."""

    # Key methods:

```

**Lines:** 129-135 in `check_schema_deprecation.py`

### `check_report_naming.py` — NamingViolation

```python
class NamingViolation:
    """Represents a report naming violation."""

    # Key methods:

    def __init__(self, ...): ...

    def __str__(self, ...) -> str: ...

```

**Public Methods:** `__init__`, `__str__`

**Lines:** 87-95 in `check_report_naming.py`

### `check_definition_of_done.py` — DoDViolation

```python
class DoDViolation:
    """Represents a Definition of Done violation."""

    # Key methods:

    def __init__(self, ...): ...

    def __str__(self, ...) -> str: ...

```

**Public Methods:** `__init__`, `__str__`

**Lines:** 107-118 in `check_definition_of_done.py`


---

## Data Models and Contracts


### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `L9_ROOT` | `Path(__file__).parent.parent` | 22 |
| `ALLOWED_CALLERS` | `{'memory/substrate_dag.py', 'memory/subs...` | 25 |
| `ALLOWED_DIRS` | `{'tests', 'codegen', '.backup', 'current...` | 33 |
| `SKIP_DIRS` | `{'.git', '.venv', 'venv', '__pycache__',...` | 44 |
| `VALIDATION_PATTERNS` | `[re.compile('PacketValidator\\.validate\...` | 55 |
| `NOQA_MARKER` | `'# noqa: ADR-0012'` | 61 |
| `VALID_TOOL_ID_PATTERN` | `re.compile('^[a-zA-Z][a-zA-Z0-9_-]*$')` | 50 |
| `TOOL_ID_PATTERNS` | `[('f["\\\']{\\w+}\\s*\\.\\s*{\\w+', 'f-s...` | 53 |

*...and 104 more constants*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class CiRequest(BaseModel):
    """Request model for ci operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CiResponse(BaseModel):
    """Response model for ci operations."""
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

1. **Discovery:** Ci components are discovered and registered.
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
# Ci feature flags
L9_ENABLE_CI_TRACING: true  # Enable detailed tracing
L9_ENABLE_CI_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CI_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
ci:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CI_LOG_LEVEL=INFO
CI_TIMEOUT=30
CI_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def main() -> int`

No description

- **File:** `check_dag_validation_single_point.py:64`
- **Async:** No
- **Returns:** `int`

#### `def should_skip(path) -> bool`

Check if file should be skipped.

- **File:** `check_tool_naming.py:87`
- **Async:** No
- **Returns:** `bool`

#### `def check_file(filepath) -> list[dict]`

Check a single file for non-compliant tool IDs.

- **File:** `check_tool_naming.py:93`
- **Async:** No
- **Returns:** `list[dict]`

#### `def check_all_files(base_path) -> list[dict]`

Check all relevant files.

- **File:** `check_tool_naming.py:118`
- **Async:** No
- **Returns:** `list[dict]`

#### `def main()`

Performs CI check to enforce OpenAI tool ID naming conventions, ensuring only allowed characters are used.

- **File:** `check_tool_naming.py:136`
- **Async:** No


### Usage Example

```python
from ci import CiService

# Initialize
service = CiService()

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

Ci operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-17T00:14:44Z",
  "level": "INFO",
  "module": "ci",
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
| `ci_operation_duration_ms` | Histogram | Operation latency distribution |
| `ci_operation_total` | Counter | Total operations processed |
| `ci_error_total` | Counter | Total errors encountered |
| `ci_active_connections` | Gauge | Current active connections |

### Tracing

Ci emits OpenTelemetry spans:

- `ci.execute` — Root span for operation
  - `ci.validate` — Input validation
  - `ci.process` — Core processing
  - `ci.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/ci/`:
- `test_ci.py` — Core unit tests
- `test_ci_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test ci with real dependencies
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
