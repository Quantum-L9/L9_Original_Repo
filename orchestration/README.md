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

# Unified Orchestration

> **Tier:** ORCHESTRATION | **Path:** `orchestration` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                          Unified Orchestration                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   orchestrati   │ ───► │  Outbound   │                  │
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

Unified controller, task router, and plan executor

**Purpose:** Coordinates multi-agent task execution, routing, and plan orchestration.

**What depends on it:** `api/routes/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute orchestration tasks
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
| `api/routes/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `core/agents/executor.py` | Required dependency |
| `memory/substrate_service.py` | Required dependency |

---

## Directory Layout

```
orchestration/
├── __init__.py
├── cell_orchestrator.py
├── email_task_router.py
├── input_segmenter.py
├── long_plan_graph.py
├── orchestrator_kernel.py
├── plan_executor.py
├── quantum_swarm_loader.py
├── slack_task_router.py
├── task_router.py
├── unified_controller.py
├── ws_task_router.py
```

| File | Purpose |
|------|---------|
| `unified_controller.py` | Core module (PROTECTED) |
| `task_router.py` | Core module (PROTECTED) |
| `__init__.py` | Core module (PROTECTED) |
| `quantum_swarm_loader.py` | Exception raised when swarm loading fails. |
| `quantum_swarm_loader.py` | Loads and executes quantum swarm capsules for para |
| `input_segmenter.py` | Configuration for input segmentation. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `OrchestrationService`)
- **Functions:** `snake_case` (e.g., `process_orchestration_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `quantum_swarm_loader.py` — SwarmLoaderError

```python
class SwarmLoaderError:
    """Exception raised when swarm loading fails."""
    
    # Key methods:

```

**Lines:** 50-53 in `quantum_swarm_loader.py`

### `quantum_swarm_loader.py` — QuantumSwarmLoader

```python
class QuantumSwarmLoader:
    """Loads and executes quantum swarm capsules for parallel code generation."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def load_quantum_swarm(self, ...): ...

    async def _load_capsule(self, ...): ...

    async def _warmup_cache(self, ...): ...

    async def get_stats(self, ...): ...

```

**Public Methods:** `__init__`, `load_quantum_swarm`, `_load_capsule`, `_warmup_cache`, `get_stats`

**Lines:** 56-256 in `quantum_swarm_loader.py`

### `input_segmenter.py` — SegmenterConfig

```python
class SegmenterConfig:
    """Configuration for input segmentation."""
    
    # Key methods:

```

**Lines:** 45-78 in `input_segmenter.py`

### `input_segmenter.py` — SegmentResult

```python
class SegmentResult:
    """Result of segmentation with metadata."""
    
    # Key methods:

    async def __iter__(self, ...): ...

    async def __len__(self, ...): ...

```

**Public Methods:** `__iter__`, `__len__`

**Lines:** 87-100 in `input_segmenter.py`

### `input_segmenter.py` — InputSegmenter

```python
class InputSegmenter:
    """Segments multi-part user input into atomic directives."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def segment(self, ...): ...

    async def _split_on_separators(self, ...): ...

    async def _is_separator(self, ...): ...

    async def _normalize(self, ...): ...

```

**Public Methods:** `__init__`, `segment`, `_split_on_separators`, `_is_separator`, `_normalize`

**Lines:** 108-332 in `input_segmenter.py`


---

## Data Models and Contracts

Data models are defined in `schemas.py` or inline within service classes.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class OrchestrationRequest(BaseModel):
    """Request model for orchestration operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class OrchestrationResponse(BaseModel):
    """Response model for orchestration operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Tasks are routed deterministically**
- **Plan execution is resumable**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Orchestration components are discovered and registered.
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
# Orchestration feature flags
L9_ENABLE_ORCHESTRATION_TRACING: true  # Enable detailed tracing
L9_ENABLE_ORCHESTRATION_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_ORCHESTRATION_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
orchestration:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
ORCHESTRATION_LOG_LEVEL=INFO
ORCHESTRATION_TIMEOUT=30
ORCHESTRATION_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def load_quantum_swarm(capsule_path)`

Convenience function to load and execute a quantum swarm.

- **File:** `quantum_swarm_loader.py:259`
- **Async:** Yes

#### `def get_segmenter()`

Get or create the default segmenter instance.

- **File:** `input_segmenter.py:343`
- **Async:** No

#### `def segment_input(input_text)`

Segment input using default segmenter.

- **File:** `input_segmenter.py:351`
- **Async:** No

#### `def segment_to_tasks(input_text, context)`

Segment input to task dicts using default segmenter.

- **File:** `input_segmenter.py:366`
- **Async:** No

#### `async def generate_artifact_with_llm(artifact_type, goal, constraints, context, max_tokens)`

Generate an artifact (plan, code, docs) using LLM.

- **File:** `long_plan_graph.py:58`
- **Async:** Yes


### Usage Example

```python
from orchestration import OrchestrationService

# Initialize
service = OrchestrationService()

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

Orchestration operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "orchestration",
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
| `orchestration_operation_duration_ms` | Histogram | Operation latency distribution |
| `orchestration_operation_total` | Counter | Total operations processed |
| `orchestration_error_total` | Counter | Total errors encountered |
| `orchestration_active_connections` | Gauge | Current active connections |

### Tracing

Orchestration emits OpenTelemetry spans:

- `orchestration.execute` — Root span for operation
  - `orchestration.validate` — Input validation
  - `orchestration.process` — Core processing
  - `orchestration.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/orchestration/`:
- `test_orchestration.py` — Core unit tests
- `test_orchestration_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test orchestration with real dependencies
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

- `plan_executor.py` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `unified_controller.py` — Requires human review before merge
- `task_router.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `unified_controller.py` — PROTECTED: Changes break system invariants
- `task_router.py` — PROTECTED: Changes break system invariants
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
