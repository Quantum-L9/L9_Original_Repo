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

# Simulation Engine

> **Tier:** INFRASTRUCTURE | **Path:** `simulation` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                            Simulation Engine                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │    simulation   │ ───► │  Outbound   │                  │
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

Simulation and testing infrastructure

**Purpose:** Provides simulation infrastructure for testing and validation.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute simulation tasks
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
simulation/
├── __init__.py
├── outcome_evaluator.py
├── scenario_loader.py
├── simulation_engine.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `outcome_evaluator.py` | Types of evaluation criteria. |
| `outcome_evaluator.py` | Evaluation verdicts. |
| `outcome_evaluator.py` | A single evaluation criterion. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `SimulationService`)
- **Functions:** `snake_case` (e.g., `process_simulation_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `outcome_evaluator.py` — CriterionType

```python
class CriterionType:
    """Types of evaluation criteria."""

    # Key methods:

```

**Lines:** 50-57 in `outcome_evaluator.py`

### `outcome_evaluator.py` — EvaluationVerdict

```python
class EvaluationVerdict:
    """Evaluation verdicts."""

    # Key methods:

```

**Lines:** 60-65 in `outcome_evaluator.py`

### `outcome_evaluator.py` — EvaluationCriteria

```python
class EvaluationCriteria:
    """A single evaluation criterion."""

    # Key methods:

    def evaluate(self, ...) -> tuple[bool, float]: ...

```

**Public Methods:** `evaluate`

**Lines:** 69-112 in `outcome_evaluator.py`

### `outcome_evaluator.py` — CriterionResult

```python
class CriterionResult:
    """Result of evaluating a single criterion."""

    # Key methods:

```

**Lines:** 116-124 in `outcome_evaluator.py`

### `outcome_evaluator.py` — EvaluationResult

```python
class EvaluationResult:
    """Complete evaluation result."""

    # Key methods:

    def to_dict(self, ...) -> dict[str, Any]: ...

```

**Public Methods:** `to_dict`

**Lines:** 128-159 in `outcome_evaluator.py`


---

## Data Models and Contracts


### Exported Symbols (`__all__`)

`EvaluationCriteria`, `EvaluationResult`, `OutcomeEvaluator`, `Scenario`, `ScenarioLoader`, `ScenarioType`, `SimulationConfig`, `SimulationEngine`, `SimulationMetrics`, `SimulationRun`

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SimulationRequest(BaseModel):
    """Request model for simulation operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class SimulationResponse(BaseModel):
    """Response model for simulation operations."""
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

1. **Discovery:** Simulation components are discovered and registered.
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
# Simulation feature flags
L9_ENABLE_SIMULATION_TRACING: true  # Enable detailed tracing
L9_ENABLE_SIMULATION_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_SIMULATION_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
simulation:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
SIMULATION_LOG_LEVEL=INFO
SIMULATION_TIMEOUT=30
SIMULATION_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def set_memory_substrate(substrate) -> None`

Set the memory substrate for packet emission.

- **File:** `simulation_engine.py:65`
- **Async:** No
- **Returns:** `None`


### Usage Example

```python
from simulation import SimulationService

# Initialize
service = SimulationService()

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

Simulation operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "simulation",
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
| `simulation_operation_duration_ms` | Histogram | Operation latency distribution |
| `simulation_operation_total` | Counter | Total operations processed |
| `simulation_error_total` | Counter | Total errors encountered |
| `simulation_active_connections` | Gauge | Current active connections |

### Tracing

Simulation emits OpenTelemetry spans:

- `simulation.execute` — Root span for operation
  - `simulation.validate` — Input validation
  - `simulation.process` — Core processing
  - `simulation.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/simulation/`:
- `test_simulation.py` — Core unit tests
- `test_simulation_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test simulation with real dependencies
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
