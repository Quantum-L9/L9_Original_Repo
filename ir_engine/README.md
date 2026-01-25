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

# IR Compilation Engine

> **Tier:** SERVICES | **Path:** `ir_engine` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                          IR Compilation Engine                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │    ir_engine    │ ───► │  Outbound   │                  │
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

Intermediate representation compiler and semantic compilation

**Purpose:** Compiles meta-specifications to intermediate representation for execution.

**What depends on it:** `orchestrators/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute ir engine tasks
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
| `orchestrators/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No outbound dependencies |

---

## Directory Layout

```
ir_engine/
├── __init__.py
├── compile_meta_to_ir.py
├── constraint_challenger.py
├── deliberation_cell.py
├── ir_generator.py
├── ir_schema.py
├── ir_to_plan_adapter.py
├── ir_to_python.py
├── ir_validator.py
├── meta_ir.py
├── schema_validator.py
├── semantic_compiler.py
├── simulation_router.py
```

| File | Purpose |
|------|---------|
| `ir_generator.py` | Core module (PROTECTED) |
| `semantic_compiler.py` | Core module (PROTECTED) |
| `__init__.py` | Core module (PROTECTED) |
| `meta_ir.py` | Module tier classification (0-7). |
| `meta_ir.py` | Team responsible for the module. |
| `meta_ir.py` | Which service the module runs in. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `IrEngineService`)
- **Functions:** `snake_case` (e.g., `process_ir_engine_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `meta_ir.py` — ModuleTier

```python
class ModuleTier:
    """Module tier classification (0-7)."""
    
    # Key methods:

```

**Lines:** 77-87 in `meta_ir.py`

### `meta_ir.py` — OwnershipTeam

```python
class OwnershipTeam:
    """Team responsible for the module."""
    
    # Key methods:

```

**Lines:** 90-97 in `meta_ir.py`

### `meta_ir.py` — ServiceType

```python
class ServiceType:
    """Which service the module runs in."""
    
    # Key methods:

```

**Lines:** 100-106 in `meta_ir.py`

### `meta_ir.py` — StartupPhase

```python
class StartupPhase:
    """When the module starts relative to others."""
    
    # Key methods:

```

**Lines:** 109-114 in `meta_ir.py`

### `meta_ir.py` — CallableFrom

```python
class CallableFrom:
    """Who can call this module."""
    
    # Key methods:

```

**Lines:** 117-121 in `meta_ir.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`SchemaValidationError`** — Raised when schema validation fails.
- **`SchemaValidator`** — Validates YAML specs against Module-Spec-v2.4.0 constraints.
- **`SimulationRequest`** — Request to simulate an IR graph.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class IrEngineRequest(BaseModel):
    """Request model for ir_engine operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class IrEngineResponse(BaseModel):
    """Response model for ir_engine operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **IR schema is versioned**
- **Compilation is deterministic**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Ir_Engine components are discovered and registered.
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
# Ir_Engine feature flags
L9_ENABLE_IR_ENGINE_TRACING: true  # Enable detailed tracing
L9_ENABLE_IR_ENGINE_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_IR_ENGINE_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
ir_engine:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
IR_ENGINE_LOG_LEVEL=INFO
IR_ENGINE_TIMEOUT=30
IR_ENGINE_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def validate_schema(yaml_path, strict)`

Validate a YAML schema file.

- **File:** `schema_validator.py:397`
- **Async:** No

#### `def validate_and_parse(yaml_path, strict)`

Validate and parse a YAML schema file.

- **File:** `schema_validator.py:414`
- **Async:** No

#### `def compile_meta_to_ir(yaml_path)`

Compile a YAML meta specification to IR.

- **File:** `compile_meta_to_ir.py:533`
- **Async:** No

#### `def compile_contract_to_ir(contract)`

Compile a MetaContract to IR.

- **File:** `compile_meta_to_ir.py:547`
- **Async:** No

#### `def compile_ir_to_python(ir)`

Compile ModuleIR to Python source files.

- **File:** `ir_to_python.py:954`
- **Async:** No


### Usage Example

```python
from ir_engine import IrEngineService

# Initialize
service = IrEngineService()

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

Ir Engine operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "ir_engine",
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
| `ir_engine_operation_duration_ms` | Histogram | Operation latency distribution |
| `ir_engine_operation_total` | Counter | Total operations processed |
| `ir_engine_error_total` | Counter | Total errors encountered |
| `ir_engine_active_connections` | Gauge | Current active connections |

### Tracing

Ir Engine emits OpenTelemetry spans:

- `ir_engine.execute` — Root span for operation
  - `ir_engine.validate` — Input validation
  - `ir_engine.process` — Core processing
  - `ir_engine.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/ir_engine/`:
- `test_ir_engine.py` — Core unit tests
- `test_ir_engine_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test ir_engine with real dependencies
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

- `ir_schema.py` — Application logic, safe to modify
- `ir_validator.py` — Application logic, safe to modify
- `ir_to_python.py` — Application logic, safe to modify
- `ir_to_plan_adapter.py` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `ir_generator.py` — Requires human review before merge
- `semantic_compiler.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `ir_generator.py` — PROTECTED: Changes break system invariants
- `semantic_compiler.py` — PROTECTED: Changes break system invariants
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
