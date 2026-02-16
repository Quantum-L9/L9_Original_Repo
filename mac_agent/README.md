---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "2026-02-14 08:25:39 UTC"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "worldtimeapi.org (drift: 1.5s)"
  auto_generated: true
---

# Mac Agent

> **Tier:** AGENTS | **Path:** `mac_agent` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                Mac Agent                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │    mac_agent    │ ───► │  Outbound   │                  │
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

Mac automation agent for system tasks and WebSocket communication

**Purpose:** Executes Mac automation tasks via WebSocket connection to L9 server.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute mac agent tasks
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
| `runtime/websocket_orchestrator.py` | Required dependency |

---

## Directory Layout

```
mac_agent/
├── __init__.py
├── config.py
├── executor.py
├── helpers/__init__.py
├── helpers/logging.py
├── runner.py
├── websocket_client.py
```

| File | Purpose |
|------|---------|
| `executor.py` | Core module (PROTECTED) |
| `__init__.py` | Core module (PROTECTED) |
| `config.py` | Configuration for Mac Agent V2. |
| `websocket_client.py` | Configuration for the Mac Agent WebSocket client. |
| `websocket_client.py` | Event type constants matching server EventType enu |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `MacAgentService`)
- **Functions:** `snake_case` (e.g., `process_mac_agent_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `config.py` — MacAgentConfig

```python
class MacAgentConfig:
    """Configuration for Mac Agent V2."""

    # Key methods:

    def __init__(self, ...): ...

```

**Public Methods:** `__init__`

**Lines:** 36-81 in `config.py`

### `websocket_client.py` — AgentConfig

```python
class AgentConfig:
    """Configuration for the Mac Agent WebSocket client."""

    # Key methods:

    def from_env(self, ...) -> AgentConfig: ...

```

**Public Methods:** `from_env`

**Lines:** 85-132 in `websocket_client.py`

### `websocket_client.py` — EventType

```python
class EventType:
    """Event type constants matching server EventType enum."""

    # Key methods:

```

**Lines:** 140-149 in `websocket_client.py`

### `websocket_client.py` — TaskExecutor

```python
class TaskExecutor:
    """Task executor for Mac Agent."""

    # Key methods:

    def __init__(self, ...): ...

    def running_count(self, ...) -> int: ...

    async def execute(self, ...) -> dict[str, Any]: ...

    async def _execute_shell(self, ...) -> dict[str, Any]: ...

    async def _execute_browser(self, ...) -> dict[str, Any]: ...

```

**Public Methods:** `__init__`, `running_count`, `execute`, `_execute_shell`, `_execute_browser`

**Lines:** 243-596 in `websocket_client.py`

### `websocket_client.py` — MacAgentClient

```python
class MacAgentClient:
    """Persistent WebSocket client for L9 Mac Agent."""

    # Key methods:

    def __init__(self, ...): ...

    async def run(self, ...) -> None: ...

    async def shutdown(self, ...) -> None: ...

    def is_connected(self, ...) -> bool: ...

    async def _connect_and_run(self, ...) -> None: ...

```

**Public Methods:** `__init__`, `run`, `shutdown`, `is_connected`, `_connect_and_run`

**Lines:** 604-1038 in `websocket_client.py`


---

## Data Models and Contracts


### Exported Symbols (`__all__`)

`AgentConfig`, `AutomationExecutor`, `EventType`, `MacAgentClient`, `TaskExecutor`

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `L9_BASE_URL` | `config.l9_base_url` | 65 |
| `L9_API_KEY` | `config.l9_api_key` | 66 |
| `POLL_INTERVAL` | `4` | 67 |

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class MacAgentRequest(BaseModel):
    """Request model for mac_agent operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class MacAgentResponse(BaseModel):
    """Response model for mac_agent operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Shell commands require approval for destructive ops**
- **WebSocket connection auto-reconnects**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Mac_Agent components are discovered and registered.
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
# Mac_Agent feature flags
L9_ENABLE_MAC_AGENT_TRACING: true  # Enable detailed tracing
L9_ENABLE_MAC_AGENT_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_MAC_AGENT_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
mac_agent:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
MAC_AGENT_LOG_LEVEL=INFO
MAC_AGENT_TIMEOUT=30
MAC_AGENT_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def execute_command(command) -> tuple[str, str]`

Execute a shell command locally (legacy support).

- **File:** `runner.py:70`
- **Async:** No
- **Returns:** `tuple[str, str]`

#### `async def execute_steps(task) -> dict`

Execute automation steps using Playwright.

- **File:** `runner.py:110`
- **Async:** Yes
- **Returns:** `dict`

#### `def format_result(result) -> str`

Format execution result as string for API.

- **File:** `runner.py:134`
- **Async:** No
- **Returns:** `str`

#### `async def poll_and_execute()`

Main polling loop (file-based task system).

- **File:** `runner.py:157`
- **Async:** Yes

#### `def main()`

Entry point.

- **File:** `runner.py:371`
- **Async:** No


### Usage Example

```python
from mac_agent import MacAgentService

# Initialize
service = MacAgentService()

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

Mac Agent operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-14T08:25:39Z",
  "level": "INFO",
  "module": "mac_agent",
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
| `mac_agent_operation_duration_ms` | Histogram | Operation latency distribution |
| `mac_agent_operation_total` | Counter | Total operations processed |
| `mac_agent_error_total` | Counter | Total errors encountered |
| `mac_agent_active_connections` | Gauge | Current active connections |

### Tracing

Mac Agent emits OpenTelemetry spans:

- `mac_agent.execute` — Root span for operation
  - `mac_agent.validate` — Input validation
  - `mac_agent.process` — Core processing
  - `mac_agent.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/mac_agent/`:
- `test_mac_agent.py` — Core unit tests
- `test_mac_agent_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test mac_agent with real dependencies
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

- `websocket_client.py` — Application logic, safe to modify
- `runner.py` — Application logic, safe to modify
- `config.py` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `executor.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `executor.py` — PROTECTED: Changes break system invariants
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
