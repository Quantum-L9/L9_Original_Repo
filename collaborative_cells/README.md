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

# Collaborative Cells

> **Tier:** INFRASTRUCTURE | **Path:** `collaborative_cells` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                           Collaborative Cells                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   collaborati   │ ───► │  Outbound   │                  │
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

Multi-agent collaboration cells (architect, coder, reviewer)

**Purpose:** Implements multi-agent collaboration patterns for complex tasks.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute collaborative cells tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics

### What This Module Does NOT Do

- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py

### Inbound Dependencies

| Module | Purpose                 |
| ------ | ----------------------- |
| —      | No inbound dependencies |

### Outbound Dependencies

| Module         | Purpose             |
| -------------- | ------------------- |
| `core/agents/` | Required dependency |

---

## Directory Layout

```
collaborative_cells/
├── __init__.py
├── architect_cell.py
├── base_cell.py
├── cell_registry.py
├── coder_cell.py
├── reflection_cell.py
├── reviewer_cell.py
```

| File                 | Purpose                                     |
| -------------------- | ------------------------------------------- |
| `base_cell.py`       | Core module (PROTECTED)                     |
| `__init__.py`        | Core module (PROTECTED)                     |
| `reviewer_cell.py`   | Collaborative cell for code review and QA.  |
| `architect_cell.py`  | Collaborative cell for architecture design. |
| `reflection_cell.py` | Meta-reasoning cell for self-improvement.   |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CollaborativeCellsService`)
- **Functions:** `snake_case` (e.g., `process_collaborative_cells_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `reviewer_cell.py` — ReviewerCell

```python
class ReviewerCell:
    """Collaborative cell for code review and QA."""

    # Key methods:

    async def __init__(self, ...): ...

    async def _ensure_client(self, ...): ...

    async def _run_producer(self, ...): ...

    async def _run_critic(self, ...): ...

    async def _apply_revisions(self, ...): ...

```

**Public Methods:** `__init__`, `_ensure_client`, `_run_producer`, `_run_critic`, `_apply_revisions`

**Lines:** 141-401 in `reviewer_cell.py`

### `architect_cell.py` — ArchitectCell

```python
class ArchitectCell:
    """Collaborative cell for architecture design."""

    # Key methods:

    async def __init__(self, ...): ...

    async def _ensure_client(self, ...): ...

    async def _run_producer(self, ...): ...

    async def _run_critic(self, ...): ...

    async def _apply_revisions(self, ...): ...

```

**Public Methods:** `__init__`, `_ensure_client`, `_run_producer`, `_run_critic`, `_apply_revisions`

**Lines:** 140-379 in `architect_cell.py`

### `reflection_cell.py` — ReflectionCell

```python
class ReflectionCell:
    """Meta-reasoning cell for self-improvement."""

    # Key methods:

    async def __init__(self, ...): ...

    async def _ensure_client(self, ...): ...

    async def _run_producer(self, ...): ...

    async def _run_critic(self, ...): ...

    async def _apply_revisions(self, ...): ...

```

**Public Methods:** `__init__`, `_ensure_client`, `_run_producer`, `_run_critic`, `_apply_revisions`

**Lines:** 133-444 in `reflection_cell.py`

### `base_cell.py` — ConsensusStrategy

```python
class ConsensusStrategy:
    """Strategy for reaching consensus."""

    # Key methods:

```

**Lines:** 59-65 in `base_cell.py`

### `base_cell.py` — CellConfig

```python
class CellConfig:
    """Configuration for a cell."""

    # Key methods:

```

**Lines:** 69-79 in `base_cell.py`

---

## Data Models and Contracts

Data models are defined in `schemas.py` or inline within service classes.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CollaborativeCellsRequest(BaseModel):
    """Request model for collaborative_cells operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CollaborativeCellsResponse(BaseModel):
    """Response model for collaborative_cells operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Cells communicate via messages**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Collaborative_Cells components are discovered and registered.
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
# Collaborative_Cells feature flags
L9_ENABLE_COLLABORATIVE_CELLS_TRACING: true # Enable detailed tracing
L9_ENABLE_COLLABORATIVE_CELLS_METRICS: true # Enable Prometheus metrics
L9_ENABLE_COLLABORATIVE_CELLS_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
collaborative_cells:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
COLLABORATIVE_CELLS_LOG_LEVEL=INFO
COLLABORATIVE_CELLS_TIMEOUT=30
COLLABORATIVE_CELLS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def register_cell(name, category, priority)`

Decorator to register a collaborative cell.

- **File:** `cell_registry.py:63`
- **Async:** No

#### `def discover_cells(package)`

Automatically discover all collaborative cells in the specified package.

- **File:** `cell_registry.py:96`
- **Async:** No

#### `def get_all_cells()`

Get all registered collaborative cells.

- **File:** `cell_registry.py:112`
- **Async:** No

#### `def get_cells_by_category(category)`

Get all collaborative cells in a specific category.

- **File:** `cell_registry.py:131`
- **Async:** No

#### `def get_cell_snapshot()`

Get a snapshot of all registered cells for observability.

- **File:** `cell_registry.py:151`
- **Async:** No

### Usage Example

```python
from collaborative_cells import CollaborativeCellsService

# Initialize
service = CollaborativeCellsService()

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

Collaborative Cells operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "collaborative_cells",
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

| Metric                                      | Type      | Description                    |
| ------------------------------------------- | --------- | ------------------------------ |
| `collaborative_cells_operation_duration_ms` | Histogram | Operation latency distribution |
| `collaborative_cells_operation_total`       | Counter   | Total operations processed     |
| `collaborative_cells_error_total`           | Counter   | Total errors encountered       |
| `collaborative_cells_active_connections`    | Gauge     | Current active connections     |

### Tracing

Collaborative Cells emits OpenTelemetry spans:

- `collaborative_cells.execute` — Root span for operation
  - `collaborative_cells.validate` — Input validation
  - `collaborative_cells.process` — Core processing
  - `collaborative_cells.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/collaborative_cells/`:

- `test_collaborative_cells.py` — Core unit tests
- `test_collaborative_cells_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test collaborative_cells with real dependencies
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

- `architect_cell.py` — Application logic, safe to modify
- `coder_cell.py` — Application logic, safe to modify
- `reviewer_cell.py` — Application logic, safe to modify
- `reflection_cell.py` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `base_cell.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `base_cell.py` — PROTECTED: Changes break system invariants
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
