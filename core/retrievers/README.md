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

# Retrieval Strategies

> **Tier:** CORE | **Path:** `core/retrievers` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                           Retrieval Strategies                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_retrie   │ ───► │  Outbound   │                  │
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

Memory and knowledge retrieval strategies

**Purpose:** Implements various retrieval strategies for memory search.

**What depends on it:** `core/agents/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core retrievers tasks
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
| `core/agents/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `memory/` | Required dependency |

---

## Directory Layout

```
core/retrievers/
├── __init__.py
├── substrate_retriever.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `substrate_retriever.py` | LangChain retriever wrapper over MemorySubstrateSe |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreRetrieversService`)
- **Functions:** `snake_case` (e.g., `process_core_retrievers_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `substrate_retriever.py` — SubstrateRetriever

```python
class SubstrateRetriever:
    """LangChain retriever wrapper over MemorySubstrateService.semantic_search."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def _aget_relevant_documents(self, ...): ...

    async def _get_relevant_documents(self, ...): ...

```

**Public Methods:** `__init__`, `_aget_relevant_documents`, `_get_relevant_documents`

**Lines:** 41-94 in `substrate_retriever.py`


---

## Data Models and Contracts

Data models are defined in `schemas.py` or inline within service classes.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreRetrieversRequest(BaseModel):
    """Request model for core_retrievers operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreRetrieversResponse(BaseModel):
    """Response model for core_retrievers operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Retrievers return ranked results**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Retrievers components are discovered and registered.
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
# Core_Retrievers feature flags
L9_ENABLE_CORE_RETRIEVERS_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_RETRIEVERS_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_RETRIEVERS_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_retrievers:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_RETRIEVERS_LOG_LEVEL=INFO
CORE_RETRIEVERS_TIMEOUT=30
CORE_RETRIEVERS_ENABLED=true
```

---

## API Surface (Public)

See key components for public API details.

### Usage Example

```python
from core.retrievers import CoreRetrieversService

# Initialize
service = CoreRetrieversService()

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

Core Retrievers operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "core.retrievers",
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
| `core_retrievers_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_retrievers_operation_total` | Counter | Total operations processed |
| `core_retrievers_error_total` | Counter | Total errors encountered |
| `core_retrievers_active_connections` | Gauge | Current active connections |

### Tracing

Core Retrievers emits OpenTelemetry spans:

- `core_retrievers.execute` — Root span for operation
  - `core_retrievers.validate` — Input validation
  - `core_retrievers.process` — Core processing
  - `core_retrievers.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_retrievers/`:
- `test_core_retrievers.py` — Core unit tests
- `test_core_retrievers_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_retrievers with real dependencies
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
