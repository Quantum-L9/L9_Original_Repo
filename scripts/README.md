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

# Automation Scripts

> **Tier:** INFRASTRUCTURE | **Path:** `scripts` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                            Automation Scripts                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │     scripts     │ ───► │  Outbound   │                  │
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

Automation and utility scripts

**Purpose:** Houses automation scripts for deployment, maintenance, and development.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute scripts tasks
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
scripts/
├── __init__.py
├── agents/neo4j_merge_agent_nodes.py
├── agents/neo4j_unify_relationships.py
├── agents/run_bootstrap_l_graph.py
├── agents/verify_agent_executor.py
├── audit/audit_api_signatures.py
├── audit/audit_shared_core.py
├── audit/categorize_dead_code.py
├── audit/ensure_logger_instantiated.py
├── audit/find_dead_code.py
├── audit/generate_gmp_todos.py
├── audit/inject_dora_complete.py
├── audit/inject_dora_multiformat_complete.py
├── audit/resolve_dead_code_refs.py
├── audit/run_all.py
└── ... (76 more files)
```

| File | Purpose |
|------|---------|
| `generate_gmp_report.py` | A single TODO item from Phase 0. |
| `generate_gmp_report.py` | A change made during implementation. |
| `generate_gmp_report.py` | A validation gate result. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `ScriptsService`)
- **Functions:** `snake_case` (e.g., `process_scripts_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `generate_gmp_report.py` — TodoItem

```python
class TodoItem:
    """A single TODO item from Phase 0."""

    # Key methods:

```

**Lines:** 85-93 in `generate_gmp_report.py`

### `generate_gmp_report.py` — ChangeItem

```python
class ChangeItem:
    """A change made during implementation."""

    # Key methods:

```

**Lines:** 97-103 in `generate_gmp_report.py`

### `generate_gmp_report.py` — ValidationResult

```python
class ValidationResult:
    """A validation gate result."""

    # Key methods:

```

**Lines:** 107-112 in `generate_gmp_report.py`

### `generate_gmp_report.py` — PhaseStatus

```python
class PhaseStatus:
    """Status of a GMP phase."""

    # Key methods:

```

**Lines:** 116-121 in `generate_gmp_report.py`

### `generate_gmp_report.py` — GMPReportData

```python
class GMPReportData:
    """All data needed to generate a GMP report."""

    # Key methods:

```

**Lines:** 125-142 in `generate_gmp_report.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`ParameterSchema`** — Parameter schema for MCP.
- **`MCPSchema`** — MCP tool schema.

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `REPO_ROOT` | `Path(os.getenv('L9_REPO_ROOT', '/Users/i...` | 70 |
| `REPORTS_DIR` | `REPO_ROOT / 'reports' / 'GMP Reports'` | 71 |
| `WORKFLOW_STATE_PATH` | `REPO_ROOT / 'workflow_state.md'` | 72 |
| `VALID_TIERS` | `['KERNEL_TIER', 'RUNTIME_TIER', 'INFRA_T...` | 74 |
| `VALID_ACTIONS` | `['CREATE', 'INSERT', 'REPLACE', 'DELETE'...` | 75 |
| `VALID_STATUSES` | `['✅ COMPLETE', '⚠️ PARTIAL', '❌ FAILED']` | 76 |
| `SKIP_DIRS` | `{'tests', 'current_work', 'codegen', 'ig...` | 48 |
| `REASON_MAP` | `{'FastAPI/ASGI route handler requires as...` | 61 |

*...and 227 more constants*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class ScriptsRequest(BaseModel):
    """Request model for scripts operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class ScriptsResponse(BaseModel):
    """Response model for scripts operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Scripts must be idempotent where possible**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Scripts components are discovered and registered.
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
# Scripts feature flags
L9_ENABLE_SCRIPTS_TRACING: true  # Enable detailed tracing
L9_ENABLE_SCRIPTS_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_SCRIPTS_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
scripts:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
SCRIPTS_LOG_LEVEL=INFO
SCRIPTS_TIMEOUT=30
SCRIPTS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def parse_todo(s) -> TodoItem`

Parse a TODO string: 'T1|file|lines|action|description'.

- **File:** `generate_gmp_report.py:432`
- **Async:** No
- **Returns:** `TodoItem`

#### `def parse_change(s) -> ChangeItem`

Parse a CHANGE string: 'file|lines|action|description'.

- **File:** `generate_gmp_report.py:449`
- **Async:** No
- **Returns:** `ChangeItem`

#### `def parse_validation(s) -> ValidationResult`

Parse a VALIDATION string: 'gate|result' or 'gate|result|details'.

- **File:** `generate_gmp_report.py:464`
- **Async:** No
- **Returns:** `ValidationResult`

#### `def interactive_mode() -> GMPReportData`

Interactive mode to collect GMP data.

- **File:** `generate_gmp_report.py:476`
- **Async:** No
- **Returns:** `GMPReportData`

#### `def from_json_file(path) -> GMPReportData`

Load GMP data from a JSON file.

- **File:** `generate_gmp_report.py:552`
- **Async:** No
- **Returns:** `GMPReportData`


### Usage Example

```python
from scripts import ScriptsService

# Initialize
service = ScriptsService()

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

Scripts operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-17T00:14:44Z",
  "level": "INFO",
  "module": "scripts",
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
| `scripts_operation_duration_ms` | Histogram | Operation latency distribution |
| `scripts_operation_total` | Counter | Total operations processed |
| `scripts_error_total` | Counter | Total errors encountered |
| `scripts_active_connections` | Gauge | Current active connections |

### Tracing

Scripts emits OpenTelemetry spans:

- `scripts.execute` — Root span for operation
  - `scripts.validate` — Input validation
  - `scripts.process` — Core processing
  - `scripts.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/scripts/`:
- `test_scripts.py` — Core unit tests
- `test_scripts_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test scripts with real dependencies
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
- `**/*.sh` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- None

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- None

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
