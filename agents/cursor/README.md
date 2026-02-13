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

# Cursor Agent

> **Tier:** AGENTS | **Path:** `agents/cursor` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                               Cursor Agent                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   agents_curs   │ ───► │  Outbound   │                  │
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

Cursor IDE integration agent with memory client

**Purpose:** Provides Cursor IDE integration for memory operations and context injection.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute agents cursor tasks
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

| Module                        | Purpose             |
| ----------------------------- | ------------------- |
| `mcp_memory/`                 | Required dependency |
| `memory/substrate_service.py` | Required dependency |

---

## Directory Layout

```
agents/cursor/
├── GMP-v2.0-Perplex-Py-Scripts/script.py
├── GMP-v2.0-Perplex-Py-Scripts/script_1.py
├── GMP-v2.0-Perplex-Py-Scripts/script_2.py
├── GMP-v2.0-Perplex-Py-Scripts/script_3.py
├── GMP-v2.0-Perplex-Py-Scripts/script_4.py
├── __init__.py
├── cursor_client.py
├── cursor_memory_client.py
├── cursor_memory_kernel.py
├── cursor_neo4j_query.py
├── extractors/__init__.py
├── extractors/cursor_action_extractor.py
├── gmp_meta_learning.py
├── integrations/__init__.py
├── integrations/cursor_executor.py
└── ... (4 more files)
```

| File                   | Purpose                                 |
| ---------------------- | --------------------------------------- |
| `__init__.py`          | Core module (PROTECTED)                 |
| `cursor_client.py`     | Client for Cursor remote API.           |
| `gmp_meta_learning.py` | Graduated autonomy levels in GMP v2.0.  |
| `gmp_meta_learning.py` | Results from a completed GMP execution. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `AgentsCursorService`)
- **Functions:** `snake_case` (e.g., `process_agents_cursor_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `cursor_client.py` — CursorClient

```python
class CursorClient:
    """Client for Cursor remote API."""

    # Key methods:

    def __init__(self, ...): ...

    def _request(self, ...) -> dict[str, Any]: ...

    def send_code(self, ...) -> dict[str, Any]: ...

    def send_command(self, ...) -> dict[str, Any]: ...

    def health_check(self, ...) -> dict[str, Any]: ...

```

**Public Methods:** `__init__`, `_request`, `send_code`, `send_command`, `health_check`

**Lines:** 36-99 in `cursor_client.py`

### `gmp_meta_learning.py` — AutonomyLevel

```python
class AutonomyLevel:
    """Graduated autonomy levels in GMP v2.0."""

    # Key methods:

```

**Lines:** 62-68 in `gmp_meta_learning.py`

### `gmp_meta_learning.py` — GMPExecutionResult

```python
class GMPExecutionResult:
    """Results from a completed GMP execution."""

    # Key methods:

```

**Lines:** 71-102 in `gmp_meta_learning.py`

### `gmp_meta_learning.py` — LearnedHeuristic

```python
class LearnedHeuristic:
    """A heuristic pattern learned from prior executions."""

    # Key methods:

    def __hash__(self, ...): ...

```

**Public Methods:** `__hash__`

**Lines:** 105-128 in `gmp_meta_learning.py`

### `gmp_meta_learning.py` — AutonomyGraduationMetrics

```python
class AutonomyGraduationMetrics:
    """Tracks metrics for autonomy level graduation."""

    # Key methods:

```

**Lines:** 131-152 in `gmp_meta_learning.py`

---

## Data Models and Contracts

### Exported Symbols (`__all__`)

`AutonomyController`, `AutonomyGraduationMetrics`, `AutonomyLevel`, `CursorClient`, `CursorMemoryKernel`, `GMPExecutionResult`, `GMPMetaLearningEngine`, `LearnedHeuristic`, `Lesson`, `SessionState`

_...and 4 more_

### Module Constants

| Constant                   | Value                                         | Line |
| -------------------------- | --------------------------------------------- | ---- |
| `SCHEMA_VERSION`           | `'2.0.0'`                                     | 97   |
| `SUPPORTED_VERSIONS`       | `['1.0.0', '1.0.1', '1.1.0', '1.1.1', '2....` | 98   |
| `CURSOR_SESSION_NAMESPACE` | `uuid.UUID('a1b2c3d4-e5f6-7890-abcd-ef123...` | 105  |
| `L9_API_URL`               | `os.getenv('L9_API_URL', 'http://mcp.quan...` | 140  |
| `MCP_URL`                  | `os.getenv('MCP_URL', 'http://mcp.quantum...` | 142  |
| `L9_EXECUTOR_API_KEY`      | `os.getenv('MCP_API_KEY_C') or os.getenv(...` | 145  |
| `VPS_NEO4J_URL`            | `'http://127.0.0.1:7474'`                     | 66   |
| `LOCAL_NEO4J_URL`          | `'http://localhost:7474'`                     | 67   |

_...and 15 more constants_

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AgentsCursorRequest(BaseModel):
    """Request model for agents_cursor operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class AgentsCursorResponse(BaseModel):
    """Response model for agents_cursor operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Memory client uses MCP protocol**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Agents_Cursor components are discovered and registered.
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
# Agents_Cursor feature flags
L9_ENABLE_AGENTS_CURSOR_TRACING: true # Enable detailed tracing
L9_ENABLE_AGENTS_CURSOR_METRICS: true # Enable Prometheus metrics
L9_ENABLE_AGENTS_CURSOR_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
agents_cursor:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
AGENTS_CURSOR_LOG_LEVEL=INFO
AGENTS_CURSOR_TIMEOUT=30
AGENTS_CURSOR_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def main()`

Example demonstrating GMP v2.0 learning engine (async).

- **File:** `gmp_meta_learning.py:801`
- **Async:** Yes

#### `def get_daily_session_id() -> str`

Generate deterministic session UUID based on current date.

- **File:** `cursor_memory_client.py:108`
- **Async:** No
- **Returns:** `str`

#### `def compute_content_hash(payload) -> str`

Compute SHA-256 content hash for PacketEnvelope v2.0 integrity.

- **File:** `cursor_memory_client.py:120`
- **Async:** No
- **Returns:** `str`

#### `def mcp_call_tool(tool_name, arguments) -> dict`

Call MCP tool via /mcp/call endpoint.

- **File:** `cursor_memory_client.py:157`
- **Async:** No
- **Returns:** `dict`

#### `def api_request(method, path, data) -> dict`

Direct HTTP API request (FALLBACK ONLY).

- **File:** `cursor_memory_client.py:199`
- **Async:** No
- **Returns:** `dict`

### Usage Example

```python
from agents.cursor import AgentsCursorService

# Initialize
service = AgentsCursorService()

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

Agents Cursor operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "agents.cursor",
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

| Metric                                | Type      | Description                    |
| ------------------------------------- | --------- | ------------------------------ |
| `agents_cursor_operation_duration_ms` | Histogram | Operation latency distribution |
| `agents_cursor_operation_total`       | Counter   | Total operations processed     |
| `agents_cursor_error_total`           | Counter   | Total errors encountered       |
| `agents_cursor_active_connections`    | Gauge     | Current active connections     |

### Tracing

Agents Cursor emits OpenTelemetry spans:

- `agents_cursor.execute` — Root span for operation
  - `agents_cursor.validate` — Input validation
  - `agents_cursor.process` — Core processing
  - `agents_cursor.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/agents_cursor/`:

- `test_agents_cursor.py` — Core unit tests
- `test_agents_cursor_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test agents_cursor with real dependencies
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

- `cursor_memory_client.py` — Application logic, safe to modify
- `context_sync.py` — Application logic, safe to modify

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
