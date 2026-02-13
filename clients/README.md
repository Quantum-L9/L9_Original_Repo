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

# API Clients

> **Tier:** INFRASTRUCTURE | **Path:** `clients` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                               API Clients                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │     clients     │ ───► │  Outbound   │                  │
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

Client implementations for external APIs

**Purpose:** Provides client implementations for external API communication.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute clients tasks
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

| Module | Purpose                  |
| ------ | ------------------------ |
| —      | No outbound dependencies |

---

## Directory Layout

```
clients/
├── __init__.py
├── memory_client.py
├── world_model_client.py
```

| File               | Purpose                              |
| ------------------ | ------------------------------------ |
| `__init__.py`      | Core module (PROTECTED)              |
| `memory_client.py` | Input structure for packet writes.   |
| `memory_client.py` | Response from packet write endpoint. |
| `memory_client.py` | Request for semantic search.         |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `ClientsService`)
- **Functions:** `snake_case` (e.g., `process_clients_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `memory_client.py` — PacketEnvelopeIn

```python
class PacketEnvelopeIn:
    """Input structure for packet writes."""

    # Key methods:

```

**Lines:** 74-91 in `memory_client.py`

### `memory_client.py` — PacketWriteResult

```python
class PacketWriteResult:
    """Response from packet write endpoint."""

    # Key methods:

```

**Lines:** 94-108 in `memory_client.py`

### `memory_client.py` — SemanticSearchRequest

```python
class SemanticSearchRequest:
    """Request for semantic search."""

    # Key methods:

```

**Lines:** 111-120 in `memory_client.py`

### `memory_client.py` — SemanticHit

```python
class SemanticHit:
    """Single semantic search result."""

    # Key methods:

```

**Lines:** 123-128 in `memory_client.py`

### `memory_client.py` — SemanticSearchResult

```python
class SemanticSearchResult:
    """Response from semantic search endpoint."""

    # Key methods:

```

**Lines:** 131-135 in `memory_client.py`

---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`SemanticSearchRequest`** — Request for semantic search.
- **`WorldModelClient`** — Async HTTP client for L9 World Model API.

### Exported Symbols (`__all__`)

`MemoryClient`, `PacketWriteResult`, `get_memory_client`

### Module Constants

| Constant              | Value                         | Line |
| --------------------- | ----------------------------- | ---- |
| `VPS_MEMORY_URL`      | `'http://l9-memory-api:8080'` | 61   |
| `DOCKER_FALLBACK_URL` | `'http://l9-api:8000'`        | 62   |
| `DEFAULT_BASE_URL`    | `VPS_MEMORY_URL`              | 64   |
| `DEFAULT_TIMEOUT`     | `30.0`                        | 65   |
| `FALLBACK_ENABLED`    | `True`                        | 66   |
| `DEFAULT_BASE_URL`    | `'http://l9-api:8000'`        | 75   |
| `DEFAULT_TIMEOUT`     | `30.0`                        | 76   |

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ClientsRequest(BaseModel):
    """Request model for clients operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class ClientsResponse(BaseModel):
    """Response model for clients operations."""
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

1. **Discovery:** Clients components are discovered and registered.
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
# Clients feature flags
L9_ENABLE_CLIENTS_TRACING: true # Enable detailed tracing
L9_ENABLE_CLIENTS_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CLIENTS_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
clients:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CLIENTS_LOG_LEVEL=INFO
CLIENTS_TIMEOUT=30
CLIENTS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def get_memory_client() -> MemoryClient`

Get or create singleton MemoryClient instance.

- **File:** `memory_client.py:628`
- **Async:** No
- **Returns:** `MemoryClient`

#### `async def close_memory_client() -> None`

Close the singleton memory client.

- **File:** `memory_client.py:641`
- **Async:** Yes
- **Returns:** `None`

#### `def get_world_model_client() -> WorldModelClient`

Get or create singleton client.

- **File:** `world_model_client.py:470`
- **Async:** No
- **Returns:** `WorldModelClient`

#### `async def close_world_model_client() -> None`

Close singleton client.

- **File:** `world_model_client.py:478`
- **Async:** Yes
- **Returns:** `None`

### Usage Example

```python
from clients import ClientsService

# Initialize
service = ClientsService()

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

Clients operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "clients",
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

| Metric                          | Type      | Description                    |
| ------------------------------- | --------- | ------------------------------ |
| `clients_operation_duration_ms` | Histogram | Operation latency distribution |
| `clients_operation_total`       | Counter   | Total operations processed     |
| `clients_error_total`           | Counter   | Total errors encountered       |
| `clients_active_connections`    | Gauge     | Current active connections     |

### Tracing

Clients emits OpenTelemetry spans:

- `clients.execute` — Root span for operation
  - `clients.validate` — Input validation
  - `clients.process` — Core processing
  - `clients.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/clients/`:

- `test_clients.py` — Core unit tests
- `test_clients_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test clients with real dependencies
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
