---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "2026-01-29 03:05:45 UTC"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "system clock (verification skipped)"
  auto_generated: true
---

# Evaluation Framework

> **Tier:** CORE | **Path:** `core/evaluation` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                           Evaluation Framework                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_evalua   │ ───► │  Outbound   │                  │
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

Agent and output evaluation framework

**Purpose:** Evaluates agent performance and output quality.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core evaluation tasks
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
core/evaluation/
├── __init__.py
├── eval_sets.py
├── evaluator.py
```

| File           | Purpose                           |
| -------------- | --------------------------------- |
| `__init__.py`  | Core module (PROTECTED)           |
| `evaluator.py` | Single evaluation case            |
| `evaluator.py` | Collection of evaluation examples |
| `evaluator.py` | Result of evaluation run          |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreEvaluationService`)
- **Functions:** `snake_case` (e.g., `process_core_evaluation_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `evaluator.py` — EvaluationExample

```python
class EvaluationExample:
    """Single evaluation case"""

    # Key methods:

```

**Lines:** 48-55 in `evaluator.py`

### `evaluator.py` — EvaluationSet

```python
class EvaluationSet:
    """Collection of evaluation examples"""

    # Key methods:

```

**Lines:** 59-64 in `evaluator.py`

### `evaluator.py` — EvaluationResult

```python
class EvaluationResult:
    """Result of evaluation run"""

    # Key methods:

    def task_success_rate(self, ...) -> float: ...

```

**Public Methods:** `task_success_rate`

**Lines:** 68-89 in `evaluator.py`

### `evaluator.py` — Evaluator

```python
class Evaluator:
    """Evaluation service for agent performance"""

    # Key methods:

    def __init__(self, ...): ...

    def define_eval_set(self, ...) -> None: ...

    async def run_eval(self, ...) -> EvaluationResult: ...

    def _compute_tool_accuracy(self, ...) -> float: ...

    async def _judge_output(self, ...) -> float: ...

```

**Public Methods:** `__init__`, `define_eval_set`, `run_eval`, `_compute_tool_accuracy`, `_judge_output`

**Lines:** 92-451 in `evaluator.py`

### `evaluator.py` — RegressionError

```python
class RegressionError:
    """Raised when eval results regress beyond thresholds"""

    # Key methods:

```

**Lines:** 454-457 in `evaluator.py`

---

## Data Models and Contracts

### Exported Symbols (`__all__`)

`ALL_EVAL_SETS`, `CODE_ANALYSIS_EXAMPLES`, `EVAL_SET_DESCRIPTIONS`, `EvaluationExample`, `EvaluationResult`, `EvaluationSet`, `Evaluator`, `INFORMATION_RETRIEVAL_EXAMPLES`, `MEMORY_OPERATIONS_EXAMPLES`, `MULTI_TOOL_EXAMPLES`

_...and 3 more_

### Module Constants

| Constant                         | Value                                         | Line |
| -------------------------------- | --------------------------------------------- | ---- |
| `INFORMATION_RETRIEVAL_EXAMPLES` | `[EvaluationExample(input_text='What is t...` | 51   |
| `CODE_ANALYSIS_EXAMPLES`         | `[EvaluationExample(input_text='What does...` | 110  |
| `MULTI_TOOL_EXAMPLES`            | `[EvaluationExample(input_text='Search fo...` | 171  |
| `MEMORY_OPERATIONS_EXAMPLES`     | `[EvaluationExample(input_text='Remember ...` | 230  |
| `ALL_EVAL_SETS`                  | `{'information_retrieval': INFORMATION_RE...` | 329  |
| `EVAL_SET_DESCRIPTIONS`          | `{'information_retrieval': 'Web search, f...` | 336  |

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreEvaluationRequest(BaseModel):
    """Request model for core_evaluation operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreEvaluationResponse(BaseModel):
    """Response model for core_evaluation operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Evaluation results are stored as packets**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Evaluation components are discovered and registered.
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
# Core_Evaluation feature flags
L9_ENABLE_CORE_EVALUATION_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_EVALUATION_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_EVALUATION_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_evaluation:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_EVALUATION_LOG_LEVEL=INFO
CORE_EVALUATION_TIMEOUT=30
CORE_EVALUATION_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def load_default_eval_sets(evaluator) -> None`

Load all default evaluation sets into an evaluator instance.

- **File:** `eval_sets.py:289`
- **Async:** No
- **Returns:** `None`

#### `async def ci_eval_gate(agent_id, eval_set_name, evaluator, thresholds) -> None`

Block PRs that regress eval scores

- **File:** `evaluator.py:460`
- **Async:** Yes
- **Returns:** `None`

### Usage Example

```python
from core.evaluation import CoreEvaluationService

# Initialize
service = CoreEvaluationService()

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

Core Evaluation operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "core.evaluation",
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

| Metric                                  | Type      | Description                    |
| --------------------------------------- | --------- | ------------------------------ |
| `core_evaluation_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_evaluation_operation_total`       | Counter   | Total operations processed     |
| `core_evaluation_error_total`           | Counter   | Total errors encountered       |
| `core_evaluation_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Evaluation emits OpenTelemetry spans:

- `core_evaluation.execute` — Root span for operation
  - `core_evaluation.validate` — Input validation
  - `core_evaluation.process` — Core processing
  - `core_evaluation.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_evaluation/`:

- `test_core_evaluation.py` — Core unit tests
- `test_core_evaluation_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_evaluation with real dependencies
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
