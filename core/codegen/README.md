---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "2026-02-17 00:14:44 UTC"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "system clock (verification skipped)"
  auto_generated: true
---

# Code Generation Core

> **Tier:** CORE | **Path:** `core/codegen` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                           Code Generation Core                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_codege   │ ───► │  Outbound   │                  │
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

Code generation utilities and templates

**Purpose:** Provides code generation infrastructure for dynamic code creation.

**What depends on it:** `ir_engine/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core codegen tasks
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
| `ir_engine/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No outbound dependencies |

---

## Directory Layout

```
core/codegen/
├── __init__.py
├── cli.py
├── compiler/module_compiler.py
├── compiler/module_compiler_v2.py
├── gatekeeper/codegen_gatekeeper.py
├── gatekeeper/codegen_gatekeeper_v2.py
├── spec/__init__.py
├── spec/spec_normalizer_v2.py
├── utilities.py
├── wire_executor.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `wire_executor.py` | Component |
| `wire_executor.py` | Component |
| `wire_executor.py` | Component |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreCodegenService`)
- **Functions:** `snake_case` (e.g., `process_core_codegen_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `wire_executor.py` — StepStatus

```python
class StepStatus:
    """No description"""

    # Key methods:

```

**Lines:** 88-93 in `wire_executor.py`

### `wire_executor.py` — RefStatus

```python
class RefStatus:
    """No description"""

    # Key methods:

```

**Lines:** 96-99 in `wire_executor.py`

### `wire_executor.py` — Reference

```python
class Reference:
    """No description"""

    # Key methods:

```

**Lines:** 103-108 in `wire_executor.py`

### `wire_executor.py` — WireAction

```python
class WireAction:
    """No description"""

    # Key methods:

```

**Lines:** 112-119 in `wire_executor.py`

### `wire_executor.py` — WireState

```python
class WireState:
    """No description"""

    # Key methods:

    def to_dict(self, ...) -> dict: ...

    def from_dict(self, ...) -> WireState: ...

```

**Public Methods:** `to_dict`, `from_dict`

**Lines:** 123-141 in `wire_executor.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`MetadataModel`** — Validated metadata section
- **`GovernanceModel`** — Validated governance section
- **`SystemModel`** — Validated system section

### Exported Symbols (`__all__`)

`BlindSpot`, `CodeGenGatekeeperAgent`, `CodeGenOutput`, `CompilationResult`, `ContractType`, `ModuleCompiler`, `NormalizedSpec`, `ResearchFinding`, `SpecNormalizer`, `SpecParseError`

*...and 1 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `REPO_ROOT` | `Path(__file__).parent.parent.parent` | 69 |
| `REPORT_GENERATOR` | `REPO_ROOT / 'scripts' / 'generate_gmp_re...` | 70 |
| `STATE_FILE` | `REPO_ROOT / '.wire_executor_state.json'` | 71 |
| `PROTECTED_FILES` | `{'core/agents/executor.py', 'runtime/web...` | 74 |
| `STEP_ORDER` | `['discovery', 'analysis', 'plan', 'execu...` | 148 |
| `TEMPLATE_AGENT_CORE` | `'"""\n{{metadata.name}} - L9 Agent\n{{de...` | 64 |
| `TEMPLATE_CONFIG` | `'"""\n{{metadata.name}} - Configuration\...` | 304 |
| `TEMPLATE_MODELS` | `'"""\n{{metadata.name}} - Data Models\n"...` | 329 |

*...and 2 more constants*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class CoreCodegenRequest(BaseModel):
    """Request model for core_codegen operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreCodegenResponse(BaseModel):
    """Response model for core_codegen operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Generated code must be valid Python**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Codegen components are discovered and registered.
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
# Core_Codegen feature flags
L9_ENABLE_CORE_CODEGEN_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_CODEGEN_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_CODEGEN_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_codegen:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_CODEGEN_LOG_LEVEL=INFO
CORE_CODEGEN_TIMEOUT=30
CORE_CODEGEN_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def cli()`

Unified CodeGen System - Generate production-ready code from specs

- **File:** `cli.py:24`
- **Async:** No

#### `def generate(input, type, output, research, min_confidence)`

Generate code from a spec file

- **File:** `cli.py:49`
- **Async:** No

#### `def validate(files)`

Validate generated code

- **File:** `cli.py:120`
- **Async:** No

#### `def research(query)`

Research a topic using Perplexity

- **File:** `cli.py:173`
- **Async:** No

#### `def main()`

No description

- **File:** `wire_executor.py:731`
- **Async:** No


### Usage Example

```python
from core.codegen import CoreCodegenService

# Initialize
service = CoreCodegenService()

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

Core Codegen operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-17T00:14:44Z",
  "level": "INFO",
  "module": "core.codegen",
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
| `core_codegen_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_codegen_operation_total` | Counter | Total operations processed |
| `core_codegen_error_total` | Counter | Total errors encountered |
| `core_codegen_active_connections` | Gauge | Current active connections |

### Tracing

Core Codegen emits OpenTelemetry spans:

- `core_codegen.execute` — Root span for operation
  - `core_codegen.validate` — Input validation
  - `core_codegen.process` — Core processing
  - `core_codegen.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_codegen/`:
- `test_core_codegen.py` — Core unit tests
- `test_core_codegen_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_codegen with real dependencies
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
