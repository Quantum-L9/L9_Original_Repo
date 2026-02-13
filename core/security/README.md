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

# Security & Authentication

> **Tier:** CORE | **Path:** `core/security` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                        Security & Authentication                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_securi   │ ───► │  Outbound   │                  │
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

Authentication, authorization, secrets management, and security policies

**Purpose:** Manages authentication, authorization, secrets, and security policy enforcement.

**What depends on it:** `api/auth.py`, `api/middleware/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core security tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics

### What This Module Does NOT Do

- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py

### Inbound Dependencies

| Module            | Purpose          |
| ----------------- | ---------------- |
| `api/auth.py`     | Uses this module |
| `api/middleware/` | Uses this module |

### Outbound Dependencies

| Module                      | Purpose             |
| --------------------------- | ------------------- |
| `config/policies/security/` | Required dependency |

---

## Directory Layout

```
core/security/
├── __init__.py
├── path_safety.py
├── permission_graph.py
```

| File                  | Purpose                                            |
| --------------------- | -------------------------------------------------- |
| `auth_service.py`     | Core module (PROTECTED)                            |
| `secrets_manager.py`  | Core module (PROTECTED)                            |
| `__init__.py`         | Core module (PROTECTED)                            |
| `permission_graph.py` | RBAC permission graph backed by Neo4j.             |
| `path_safety.py`      | Raised when a user-controlled path fails safety va |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreSecurityService`)
- **Functions:** `snake_case` (e.g., `process_core_security_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `permission_graph.py` — PermissionGraph

```python
class PermissionGraph:
    """RBAC permission graph backed by Neo4j."""

    # Key methods:

    async def _get_neo4j(self, ...): ...

    async def create_user(self, ...) -> bool: ...

    async def get_user(self, ...) -> dict[str, Any] | None: ...

    async def create_role(self, ...) -> bool: ...

    async def grant_permission_to_role(self, ...) -> bool: ...

```

**Public Methods:** `_get_neo4j`, `create_user`, `get_user`, `create_role`, `grant_permission_to_role`

**Lines:** 49-348 in `permission_graph.py`

### `path_safety.py` — PathSafetyError

```python
class PathSafetyError:
    """Raised when a user-controlled path fails safety validation."""

    # Key methods:

    def __str__(self, ...) -> str: ...

```

**Public Methods:** `__str__`

**Lines:** 52-59 in `path_safety.py`

---

## Data Models and Contracts

### Exported Symbols (`__all__`)

`PathSafetyError`, `PermissionGraph`, `can_access`, `get_user_permissions`, `grant_permission`, `grant_role`, `resolve_base_dir`, `revoke_role`, `safe_resolve_path`, `safe_resolve_path_async`

_...and 1 more_

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreSecurityRequest(BaseModel):
    """Request model for core_security operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreSecurityResponse(BaseModel):
    """Response model for core_security operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Secrets never logged in plaintext**
- **All auth tokens validated before use**
- **Failed auth attempts are rate-limited**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Security components are discovered and registered.
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
# Core_Security feature flags
L9_ENABLE_CORE_SECURITY_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_SECURITY_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_SECURITY_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_security:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_SECURITY_LOG_LEVEL=INFO
CORE_SECURITY_TIMEOUT=30
CORE_SECURITY_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def grant_role(user_id, role_id) -> bool`

Assign a role to a user.

- **File:** `permission_graph.py:356`
- **Async:** Yes
- **Returns:** `bool`

#### `async def revoke_role(user_id, role_id) -> bool`

Revoke a role from a user.

- **File:** `permission_graph.py:361`
- **Async:** Yes
- **Returns:** `bool`

#### `async def grant_permission(role_id, permission_id) -> bool`

Grant a permission to a role.

- **File:** `permission_graph.py:366`
- **Async:** Yes
- **Returns:** `bool`

#### `async def can_access(user_id, resource_id) -> bool`

Check if user can access a resource.

- **File:** `permission_graph.py:371`
- **Async:** Yes
- **Returns:** `bool`

#### `async def get_user_permissions(user_id) -> list[str]`

Get all permissions for a user.

- **File:** `permission_graph.py:376`
- **Async:** Yes
- **Returns:** `list[str]`

### Usage Example

```python
from core.security import CoreSecurityService

# Initialize
service = CoreSecurityService()

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

Core Security operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "core.security",
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
| `core_security_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_security_operation_total`       | Counter   | Total operations processed     |
| `core_security_error_total`           | Counter   | Total errors encountered       |
| `core_security_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Security emits OpenTelemetry spans:

- `core_security.execute` — Root span for operation
  - `core_security.validate` — Input validation
  - `core_security.process` — Core processing
  - `core_security.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_security/`:

- `test_core_security.py` — Core unit tests
- `test_core_security_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_security with real dependencies
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

- `token_validator.py` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `auth_service.py` — Requires human review before merge
- `secrets_manager.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `auth_service.py` — PROTECTED: Changes break system invariants
- `secrets_manager.py` — PROTECTED: Changes break system invariants
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
