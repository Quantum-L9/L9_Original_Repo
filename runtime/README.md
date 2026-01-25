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

# Runtime Services

> **Tier:** CORE | **Path:** `runtime` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                             Runtime Services                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │     runtime     │ ───► │  Outbound   │                  │
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

Task queue, Redis client, rate limiter, kernel loader, and background workers

**Purpose:** Provides core runtime services including task queuing, caching, rate limiting, and kernel loading.

**What depends on it:** `core/agents/executor.py`, `api/server.py`, `memory/substrate_service.py`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute runtime tasks
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
| `core/agents/executor.py` | Uses this module |
| `api/server.py` | Uses this module |
| `memory/substrate_service.py` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `config/di_config.py` | Required dependency |

---

## Directory Layout

```
runtime/
├── __init__.py
├── auth_rate_limiter.py
├── background_tasks.py
├── construct_enhancer.py
├── dora.py
├── execution_gate.py
├── git_tool.py
├── gmp_approval.py
├── gmp_tool.py
├── gmp_worker.py
├── introspection.py
├── kernel_config_loader.py
├── kernel_loader.py
├── kernel_state.py
├── l_tools.py
└── ... (18 more files)
```

| File | Purpose |
|------|---------|
| `kernel_loader.py` | Core module (PROTECTED) |
| `task_queue.py` | Core module (PROTECTED) |
| `redis_client.py` | Core module (PROTECTED) |
| `__init__.py` | Core module (PROTECTED) |
| `dora.py` | Metrics captured during execution. |
| `dora.py` | Execution graph (nodes/edges for call flow visuali |
| `dora.py` | The DORA Block schema (L9_TRACE_TEMPLATE). |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `RuntimeService`)
- **Functions:** `snake_case` (e.g., `process_runtime_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `dora.py` — DoraMetrics

```python
class DoraMetrics:
    """Metrics captured during execution."""
    
    # Key methods:

```

**Lines:** 69-75 in `dora.py`

### `dora.py` — DoraGraph

```python
class DoraGraph:
    """Execution graph (nodes/edges for call flow visualization)."""
    
    # Key methods:

```

**Lines:** 79-83 in `dora.py`

### `dora.py` — DoraTraceBlock

```python
class DoraTraceBlock:
    """The DORA Block schema (L9_TRACE_TEMPLATE)."""
    
    # Key methods:

    async def to_dict(self, ...): ...

    async def create(self, ...): ...

    async def _sanitize_for_json(self, ...): ...

```

**Public Methods:** `to_dict`, `create`, `_sanitize_for_json`

**Lines:** 87-164 in `dora.py`

### `response_renderer.py` — ResponseRenderer

```python
class ResponseRenderer:
    """Render responses with the 5-section GODMODE template."""
    
    # Key methods:

    async def render(self, ...): ...

    async def _format_confidence(self, ...): ...

    async def _format_kernel_status(self, ...): ...

    async def render_minimal(self, ...): ...

    async def render_escalation(self, ...): ...

```

**Public Methods:** `render`, `_format_confidence`, `_format_kernel_status`, `render_minimal`, `render_escalation`

**Lines:** 54-262 in `response_renderer.py`

### `response_renderer.py` — ResponseBuilder

```python
class ResponseBuilder:
    """Builder pattern for constructing responses."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def opening(self, ...): ...

    async def section(self, ...): ...

    async def confidence(self, ...): ...

    async def from_claims(self, ...): ...

```

**Public Methods:** `__init__`, `opening`, `section`, `confidence`, `from_claims`

**Lines:** 270-345 in `response_renderer.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`ResponseRenderer`** — Render responses with the 5-section GODMODE template.
- **`ResponseBuilder`** — Builder pattern for constructing responses.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RuntimeRequest(BaseModel):
    """Request model for runtime operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class RuntimeResponse(BaseModel):
    """Response model for runtime operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **All external calls have explicit timeouts**
- **Redis operations are atomic where required**
- **Kernel YAML files are validated on load**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Runtime components are discovered and registered.
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
# Runtime feature flags
L9_ENABLE_RUNTIME_TRACING: true  # Enable detailed tracing
L9_ENABLE_RUNTIME_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_RUNTIME_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
runtime:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
RUNTIME_LOG_LEVEL=INFO
RUNTIME_TIMEOUT=30
RUNTIME_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def gmp_run_tool(gmp_markdown, repo_root, caller, metadata)`

GMP run tool implementation.

- **File:** `gmp_tool.py:45`
- **Async:** Yes

#### `def format_dora_block_python(trace)`

Format DORA block for Python files.

- **File:** `dora.py:188`
- **Async:** No

#### `def update_dora_block_in_file(file_path, trace)`

Update the DORA block at the end of a file.

- **File:** `dora.py:215`
- **Async:** No

#### `def l9_traced(func)`

Decorator to trace function execution for DORA Block.

- **File:** `dora.py:285`
- **Async:** No

#### `async def emit_executor_trace(task_id, task_name, agent_id, inputs, outputs, duration_ms, errors, patterns, source_file)`

Create and emit a DORA trace from the executor.

- **File:** `dora.py:445`
- **Async:** Yes


### Usage Example

```python
from runtime import RuntimeService

# Initialize
service = RuntimeService()

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

Runtime operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "runtime",
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
| `runtime_operation_duration_ms` | Histogram | Operation latency distribution |
| `runtime_operation_total` | Counter | Total operations processed |
| `runtime_error_total` | Counter | Total errors encountered |
| `runtime_active_connections` | Gauge | Current active connections |

### Tracing

Runtime emits OpenTelemetry spans:

- `runtime.execute` — Root span for operation
  - `runtime.validate` — Input validation
  - `runtime.process` — Core processing
  - `runtime.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/runtime/`:
- `test_runtime.py` — Core unit tests
- `test_runtime_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test runtime with real dependencies
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

- `rate_limiter.py` — Application logic, safe to modify
- `superprompt_emitter.py` — Application logic, safe to modify
- `websocket_orchestrator.py` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `kernel_loader.py` — Requires human review before merge
- `task_queue.py` — Requires human review before merge
- `redis_client.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `kernel_loader.py` — PROTECTED: Changes break system invariants
- `task_queue.py` — PROTECTED: Changes break system invariants
- `redis_client.py` — PROTECTED: Changes break system invariants
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
