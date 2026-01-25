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

# LLM Clients

> **Tier:** CORE | **Path:** `core/llm` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                               LLM Clients                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │     core_llm    │ ───► │  Outbound   │                  │
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

LLM provider clients and abstraction layer

**Purpose:** Provides unified interface for LLM providers (OpenAI, Anthropic, etc.).

**What depends on it:** `core/agents/executor.py`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core llm tasks
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

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `config/` | Required dependency |

---

## Directory Layout

```
core/llm/
├── __init__.py
├── llm_service.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `llm_service.py` | LLMService implementation using OpenAI API. |
| `llm_service.py` | Mock LLMService for testing. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreLlmService`)
- **Functions:** `snake_case` (e.g., `process_core_llm_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `llm_service.py` — OpenAILLMService

```python
class OpenAILLMService:
    """LLMService implementation using OpenAI API."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def _get_client(self, ...): ...

    async def complete(self, ...): ...

    async def chat(self, ...): ...

    async def embed(self, ...): ...

```

**Public Methods:** `__init__`, `_get_client`, `complete`, `chat`, `embed`

**Lines:** 65-283 in `llm_service.py`

### `llm_service.py` — MockLLMService

```python
class MockLLMService:
    """Mock LLMService for testing."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def complete(self, ...): ...

    async def chat(self, ...): ...

    async def embed(self, ...): ...

```

**Public Methods:** `__init__`, `complete`, `chat`, `embed`

**Lines:** 286-344 in `llm_service.py`


---

## Data Models and Contracts

Data models are defined in `schemas.py` or inline within service classes.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreLlmRequest(BaseModel):
    """Request model for core_llm operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreLlmResponse(BaseModel):
    """Response model for core_llm operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **API keys from environment only**
- **All requests have timeouts**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Llm components are discovered and registered.
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
# Core_Llm feature flags
L9_ENABLE_CORE_LLM_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_LLM_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_LLM_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_llm:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_LLM_LOG_LEVEL=INFO
CORE_LLM_TIMEOUT=30
CORE_LLM_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def get_default_model()`

Get the default chat model.

- **File:** `llm_service.py:60`
- **Async:** No

#### `def create_llm_service(provider, api_key)`

Factory function to create LLMService implementation.

- **File:** `llm_service.py:347`
- **Async:** No


### Usage Example

```python
from core.llm import CoreLlmService

# Initialize
service = CoreLlmService()

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

Core Llm operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "core.llm",
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
| `core_llm_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_llm_operation_total` | Counter | Total operations processed |
| `core_llm_error_total` | Counter | Total errors encountered |
| `core_llm_active_connections` | Gauge | Current active connections |

### Tracing

Core Llm emits OpenTelemetry spans:

- `core_llm.execute` — Root span for operation
  - `core_llm.validate` — Input validation
  - `core_llm.process` — Core processing
  - `core_llm.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_llm/`:
- `test_core_llm.py` — Core unit tests
- `test_core_llm_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_llm with real dependencies
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
