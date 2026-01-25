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

# Configuration

> **Tier:** INFRASTRUCTURE | **Path:** `config` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                              Configuration                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │      config     │ ───► │  Outbound   │                  │
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

Dependency injection, settings, and configuration management

**Purpose:** Manages application configuration, DI container, and settings.

**What depends on it:** `all modules`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute config tasks
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
| `all modules` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No outbound dependencies |

---

## Directory Layout

```
config/
├── __init__.py
├── ai_eval_settings.py
├── cursor_langgraph_config.py
├── di_async_config.py
├── di_config.py
├── di_runtime_config.py
├── memory_substrate_settings.py
├── research_settings.py
├── rls_config.py
├── schemas/__init__.py
├── settings.py
```

| File | Purpose |
|------|---------|
| `di_config.py` | Core module (PROTECTED) |
| `settings.py` | Core module (PROTECTED) |
| `__init__.py` | Core module (PROTECTED) |
| `di_runtime_config.py` | Raised when DI config loading or validation fails. |
| `di_runtime_config.py` | Load DI configuration from YAML with environment v |
| `rls_config.py` | RLS Configuration with deterministic UUID generati |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `ConfigService`)
- **Functions:** `snake_case` (e.g., `process_config_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `di_runtime_config.py` — DIConfigError

```python
class DIConfigError:
    """Raised when DI config loading or validation fails."""
    
    # Key methods:

```

**Lines:** 64-67 in `di_runtime_config.py`

### `di_runtime_config.py` — DIRuntimeConfigLoader

```python
class DIRuntimeConfigLoader:
    """Load DI configuration from YAML with environment variable interpolation."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def load(self, ...): ...

    async def _interpolate_env_vars(self, ...): ...

    async def _get_default_config(self, ...): ...

    async def get_memory_substrate_config(self, ...): ...

```

**Public Methods:** `__init__`, `load`, `_interpolate_env_vars`, `_get_default_config`, `get_memory_substrate_config`

**Lines:** 70-300 in `di_runtime_config.py`

### `rls_config.py` — RLSConfig

```python
class RLSConfig:
    """RLS Configuration with deterministic UUID generation."""
    
    # Key methods:

    async def tenant_uuid(self, ...): ...

    async def org_uuid(self, ...): ...

    async def user_uuid(self, ...): ...

```

**Public Methods:** `tenant_uuid`, `org_uuid`, `user_uuid`

**Lines:** 76-111 in `rls_config.py`

### `rls_config.py` — Config

```python
class Config:
    """No description"""
    
    # Key methods:

```

**Lines:** 93-96 in `rls_config.py`

### `ai_eval_settings.py` — HallucinationSettings

```python
class HallucinationSettings:
    """Hallucination detection settings."""
    
    # Key methods:

```

**Lines:** 41-58 in `ai_eval_settings.py`


---

## Data Models and Contracts

Data models are defined in `schemas.py` or inline within service classes.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ConfigRequest(BaseModel):
    """Request model for config operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class ConfigResponse(BaseModel):
    """Response model for config operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Settings loaded from environment**
- **DI container is singleton**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Config components are discovered and registered.
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
# Config feature flags
L9_ENABLE_CONFIG_TRACING: true  # Enable detailed tracing
L9_ENABLE_CONFIG_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CONFIG_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
config:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CONFIG_LOG_LEVEL=INFO
CONFIG_TIMEOUT=30
CONFIG_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def get_runtime_config_loader(config_path)`

Get or create singleton DI runtime config loader.

- **File:** `di_runtime_config.py:310`
- **Async:** No

#### `def reset_runtime_config_loader()`

Reset singleton loader (for testing).

- **File:** `di_runtime_config.py:335`
- **Async:** No

#### `def generate_deterministic_uuid(identifier)`

Generate a deterministic UUID from a string identifier.

- **File:** `rls_config.py:58`
- **Async:** No

#### `def get_rls_config()`

Get or create RLS config singleton. CACHED.

- **File:** `rls_config.py:115`
- **Async:** No

#### `def get_rls_uuids()`

Get RLS UUIDs for PostgreSQL RLS session variables.

- **File:** `rls_config.py:130`
- **Async:** No


### Usage Example

```python
from config import ConfigService

# Initialize
service = ConfigService()

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

Config operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "config",
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
| `config_operation_duration_ms` | Histogram | Operation latency distribution |
| `config_operation_total` | Counter | Total operations processed |
| `config_error_total` | Counter | Total errors encountered |
| `config_active_connections` | Gauge | Current active connections |

### Tracing

Config emits OpenTelemetry spans:

- `config.execute` — Root span for operation
  - `config.validate` — Input validation
  - `config.process` — Core processing
  - `config.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/config/`:
- `test_config.py` — Core unit tests
- `test_config_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test config with real dependencies
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

- `agents/**` — Application logic, safe to modify
- `patterns/**` — Application logic, safe to modify
- `policies/**` — Application logic, safe to modify
- `schemas/**` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `di_config.py` — Requires human review before merge
- `settings.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `di_config.py` — PROTECTED: Changes break system invariants
- `settings.py` — PROTECTED: Changes break system invariants
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
