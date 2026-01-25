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

# CodeGen Agent

> **Tier:** AGENTS | **Path:** `codegenagent` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                              CodeGen Agent                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   codegenagen   │ ───► │  Outbound   │                  │
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

Code generation agent and specifications

**Purpose:** Implements code generation agent with YAML specs.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute codegenagent tasks
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
| `core/agents/` | Required dependency |

---

## Directory Layout

```
codegenagent/
├── __init__.py
├── c_gmp_engine.py
├── codegen_agent.py
├── extract_yaml_specs.py
├── file_emitter.py
├── meta_loader.py
├── readme_generator.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `c_gmp_engine.py` | Exception raised when code generation fails. |
| `c_gmp_engine.py` | Code Generation and Mathematical Processing Engine |
| `meta_loader.py` | Exception raised when meta loading fails. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CodegenagentService`)
- **Functions:** `snake_case` (e.g., `process_codegenagent_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `c_gmp_engine.py` — CGMPEngineError

```python
class CGMPEngineError:
    """Exception raised when code generation fails."""
    
    # Key methods:

```

**Lines:** 31-33 in `c_gmp_engine.py`

### `c_gmp_engine.py` — CGMPEngine

```python
class CGMPEngine:
    """Code Generation and Mathematical Processing Engine."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def expand_code_blocks(self, ...): ...

    async def _is_mathematical(self, ...): ...

    async def _expand_mathematical(self, ...): ...

    async def _expand_template(self, ...): ...

```

**Public Methods:** `__init__`, `expand_code_blocks`, `_is_mathematical`, `_expand_mathematical`, `_expand_template`

**Lines:** 36-442 in `c_gmp_engine.py`

### `meta_loader.py` — MetaLoaderError

```python
class MetaLoaderError:
    """Exception raised when meta loading fails."""
    
    # Key methods:

```

**Lines:** 31-33 in `meta_loader.py`

### `meta_loader.py` — MetaLoader

```python
class MetaLoader:
    """Loads and validates YAML meta specifications."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def load_meta(self, ...): ...

    async def load_as_contract(self, ...): ...

    async def validate_meta(self, ...): ...

    async def load_all_specs(self, ...): ...

```

**Public Methods:** `__init__`, `load_meta`, `load_as_contract`, `validate_meta`, `load_all_specs`

**Lines:** 36-306 in `meta_loader.py`

### `readme_generator.py` — ReadmeSection

```python
class ReadmeSection:
    """A single section of a README document."""
    
    # Key methods:

```

**Lines:** 30-35 in `readme_generator.py`


---

## Data Models and Contracts

Data models are defined in `schemas.py` or inline within service classes.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CodegenagentRequest(BaseModel):
    """Request model for codegenagent operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CodegenagentResponse(BaseModel):
    """Response model for codegenagent operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Generated code must pass linting**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Codegenagent components are discovered and registered.
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
# Codegenagent feature flags
L9_ENABLE_CODEGENAGENT_TRACING: true  # Enable detailed tracing
L9_ENABLE_CODEGENAGENT_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CODEGENAGENT_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
codegenagent:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CODEGENAGENT_LOG_LEVEL=INFO
CODEGENAGENT_TIMEOUT=30
CODEGENAGENT_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def load_meta(path)`

Load a YAML meta specification.

- **File:** `meta_loader.py:311`
- **Async:** No

#### `def load_as_contract(path)`

Load a YAML meta specification as MetaContract.

- **File:** `meta_loader.py:325`
- **Async:** No

#### `def is_patch(yaml_content, filename)`

Determine if a YAML spec is a patch.

- **File:** `extract_yaml_specs.py:33`
- **Async:** No

#### `def extract_yaml_blocks(content)`

Extract all '''yaml blocks from the content.

- **File:** `extract_yaml_specs.py:52`
- **Async:** No

#### `def sanitize_filename(filename)`

Convert a path-like filename to a safe filename.

- **File:** `extract_yaml_specs.py:96`
- **Async:** No


### Usage Example

```python
from codegenagent import CodegenagentService

# Initialize
service = CodegenagentService()

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

Codegenagent operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "codegenagent",
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
| `codegenagent_operation_duration_ms` | Histogram | Operation latency distribution |
| `codegenagent_operation_total` | Counter | Total operations processed |
| `codegenagent_error_total` | Counter | Total errors encountered |
| `codegenagent_active_connections` | Gauge | Current active connections |

### Tracing

Codegenagent emits OpenTelemetry spans:

- `codegenagent.execute` — Root span for operation
  - `codegenagent.validate` — Input validation
  - `codegenagent.process` — Core processing
  - `codegenagent.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/codegenagent/`:
- `test_codegenagent.py` — Core unit tests
- `test_codegenagent_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test codegenagent with real dependencies
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
- `**/*.yaml` — Application logic, safe to modify

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
