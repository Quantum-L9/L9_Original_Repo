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

# Secrets Management

> **Tier:** CORE | **Path:** `core/secrets` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                            Secrets Management                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_secret   │ ───► │  Outbound   │                  │
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

Secure secrets handling and storage

**Purpose:** Manages secrets securely with encryption at rest.

**What depends on it:** `core/security/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core secrets tasks
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
| `core/security/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No outbound dependencies |

---

## Directory Layout

```
core/secrets/
├── __init__.py
├── aws_secrets_client.py
├── env_secrets_client.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `vault.py` | Core module (PROTECTED) |
| `aws_secrets_client.py` | AWS Secrets Manager client with caching and env fa |
| `env_secrets_client.py` | Secrets client that reads from environment variabl |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreSecretsService`)
- **Functions:** `snake_case` (e.g., `process_core_secrets_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `aws_secrets_client.py` — AwsSecretsClient

```python
class AwsSecretsClient:
    """AWS Secrets Manager client with caching and env fallback."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def provider_name(self, ...): ...

    async def _build_secret_name(self, ...): ...

    async def _is_cache_valid(self, ...): ...

    async def get_secret(self, ...): ...

```

**Public Methods:** `__init__`, `provider_name`, `_build_secret_name`, `_is_cache_valid`, `get_secret`

**Lines:** 61-337 in `aws_secrets_client.py`

### `env_secrets_client.py` — EnvSecretsClient

```python
class EnvSecretsClient:
    """Secrets client that reads from environment variables."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def provider_name(self, ...): ...

    async def _build_env_key(self, ...): ...

    async def get_secret(self, ...): ...

    async def set_secret(self, ...): ...

```

**Public Methods:** `__init__`, `provider_name`, `_build_env_key`, `get_secret`, `set_secret`

**Lines:** 49-159 in `env_secrets_client.py`


---

## Data Models and Contracts

Data models are defined in `schemas.py` or inline within service classes.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreSecretsRequest(BaseModel):
    """Request model for core_secrets operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreSecretsResponse(BaseModel):
    """Response model for core_secrets operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Secrets never logged in plaintext**
- **Secrets encrypted at rest**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Secrets components are discovered and registered.
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
# Core_Secrets feature flags
L9_ENABLE_CORE_SECRETS_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_SECRETS_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_SECRETS_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_secrets:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_SECRETS_LOG_LEVEL=INFO
CORE_SECRETS_TIMEOUT=30
CORE_SECRETS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def get_secrets_client()`

Get or create the secrets client singleton.

- **File:** `__init__.py:76`
- **Async:** No

#### `def reset_secrets_client()`

Reset singleton for testing.

- **File:** `__init__.py:138`
- **Async:** No

#### `def get_secret(key)`

Convenience function to get a secret value.

- **File:** `__init__.py:155`
- **Async:** No

#### `def get_secret_or_env(key, default)`

Get secret from configured provider, with explicit env fallback.

- **File:** `__init__.py:168`
- **Async:** No


### Usage Example

```python
from core.secrets import CoreSecretsService

# Initialize
service = CoreSecretsService()

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

Core Secrets operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "core.secrets",
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
| `core_secrets_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_secrets_operation_total` | Counter | Total operations processed |
| `core_secrets_error_total` | Counter | Total errors encountered |
| `core_secrets_active_connections` | Gauge | Current active connections |

### Tracing

Core Secrets emits OpenTelemetry spans:

- `core_secrets.execute` — Root span for operation
  - `core_secrets.validate` — Input validation
  - `core_secrets.process` — Core processing
  - `core_secrets.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_secrets/`:
- `test_core_secrets.py` — Core unit tests
- `test_core_secrets_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_secrets with real dependencies
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
- `vault.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `__init__.py` — PROTECTED: Changes break system invariants
- `vault.py` — PROTECTED: Changes break system invariants

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
