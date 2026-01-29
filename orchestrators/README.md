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

# Pattern Orchestrators

> **Tier:** ORCHESTRATION | **Path:** `orchestrators` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                          Pattern Orchestrators                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   orchestrato   │ ───► │  Outbound   │                  │
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

Domain-specific orchestration patterns for agents, memory, reasoning, and world model

**Purpose:** Provides specialized orchestration patterns for different execution domains.

**What depends on it:** `api/routes/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute orchestrators tasks
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
| `api/routes/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `orchestration/unified_controller.py` | Required dependency |
| `core/agents/executor.py` | Required dependency |

---

## Directory Layout

```
orchestrators/
├── __init__.py
├── action_tool/__init__.py
├── action_tool/interface.py
├── action_tool/orchestrator.py
├── action_tool/validator.py
├── agent_execution/__init__.py
├── agent_execution/interface.py
├── agent_execution/orchestrator.py
├── agent_execution/task_queue.py
├── evolution/__init__.py
├── evolution/apply_engine.py
├── evolution/interface.py
├── evolution/orchestrator.py
├── memory/__init__.py
├── memory/housekeeping.py
└── ... (26 more files)
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `ws_bridge.py` | Phase 3: Configuration for the WS bridge. |
| `ws_bridge.py` | Phase 3: Extensible event router with handler regi |
| `validator.py` | Result of tool validation. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `OrchestratorsService`)
- **Functions:** `snake_case` (e.g., `process_orchestrators_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `ws_bridge.py` — WSBridgeConfig

```python
class WSBridgeConfig:
    """Phase 3: Configuration for the WS bridge."""

    # Key methods:

    def __init__(self, ...): ...

```

**Public Methods:** `__init__`

**Lines:** 233-253 in `ws_bridge.py`

### `ws_bridge.py` — WSEventRouter

```python
class WSEventRouter:
    """Phase 3: Extensible event router with handler registration."""

    # Key methods:

    def __init__(self, ...): ...

    def register_handler(self, ...) -> None: ...

    def route(self, ...) -> TaskEnvelope | None: ...

```

**Public Methods:** `__init__`, `register_handler`, `route`

**Lines:** 256-278 in `ws_bridge.py`

### `validator.py` — ValidationResult

```python
class ValidationResult:
    """Result of tool validation."""

    # Key methods:

    def __init__(self, ...): ...

    def to_dict(self, ...) -> dict[str, Any]: ...

```

**Public Methods:** `__init__`, `to_dict`

**Lines:** 50-77 in `validator.py`

### `validator.py` — Validator

```python
class Validator:
    """Validator for ActionTool Orchestrator."""

    # Key methods:

    def __init__(self, ...): ...

    async def _get_registry(self, ...) -> Any | None: ...

    async def process(self, ...) -> dict[str, Any]: ...

    async def validate_tool(self, ...) -> ValidationResult: ...

    def _assess_safety_level(self, ...) -> str: ...

```

**Public Methods:** `__init__`, `_get_registry`, `process`, `validate_tool`, `_assess_safety_level`

**Lines:** 80-248 in `validator.py`

### `interface.py` — ToolSafetyLevel

```python
class ToolSafetyLevel:
    """Tool safety levels."""

    # Key methods:

```

**Lines:** 37-42 in `interface.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`ActionToolRequest`** — Request to action_tool orchestrator.
- **`ActionToolResponse`** — Response from action_tool orchestrator.
- **`MemoryRequest`** — Request to memory orchestrator.

### Exported Symbols (`__all__`)

`ActionToolOrchestrator`, `ActionToolRequest`, `ActionToolResponse`, `AdapterNode`, `AgentExecutionOrchestrator`, `AgentExecutionRequest`, `AgentExecutionResponse`, `ApplyEngine`, `Blueprint`, `BlueprintAdapter`

*...and 63 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `HIGH_RISK_TOOLS` | `get_high_risk_tools()` | 45 |
| `IGOR_APPROVAL_REQUIRED` | `get_igor_approval_tools()` | 46 |
| `SAFE_TOOLS` | `get_safe_tools()` | 47 |
| `DEFAULT_MAX_RETRIES` | `3` | 50 |
| `INITIAL_BACKOFF_SECONDS` | `1.0` | 51 |
| `MAX_BACKOFF_SECONDS` | `30.0` | 52 |
| `BACKOFF_MULTIPLIER` | `2.0` | 53 |
| `TASKS_DIR` | `Path(os.path.expanduser('~/.l9/mac_tasks...` | 69 |

*...and 2 more constants*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class OrchestratorsRequest(BaseModel):
    """Request model for orchestrators operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class OrchestratorsResponse(BaseModel):
    """Response model for orchestrators operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Orchestrators emit structured packets**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Orchestrators components are discovered and registered.
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
# Orchestrators feature flags
L9_ENABLE_ORCHESTRATORS_TRACING: true  # Enable detailed tracing
L9_ENABLE_ORCHESTRATORS_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_ORCHESTRATORS_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
orchestrators:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
ORCHESTRATORS_LOG_LEVEL=INFO
ORCHESTRATORS_TIMEOUT=30
ORCHESTRATORS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def register_orchestrator(name, domain, category, priority)`

Decorator to register an orchestrator class for auto-discovery.

- **File:** `orchestrator_registry.py:65`
- **Async:** No

#### `def discover_orchestrators(package) -> int`

Automatically discover all orchestrators in the specified package.

- **File:** `orchestrator_registry.py:117`
- **Async:** No
- **Returns:** `int`

#### `def get_all_orchestrators() -> dict[str, type]`

Get all registered orchestrator classes as a dictionary.

- **File:** `orchestrator_registry.py:133`
- **Async:** No
- **Returns:** `dict[str, type]`

#### `def get_orchestrators_by_domain(domain) -> dict[str, type]`

Get all orchestrator classes in a specific domain.

- **File:** `orchestrator_registry.py:160`
- **Async:** No
- **Returns:** `dict[str, type]`

#### `def get_orchestrators_by_category(category) -> dict[str, type]`

Get all orchestrator classes in a specific category.

- **File:** `orchestrator_registry.py:185`
- **Async:** No
- **Returns:** `dict[str, type]`


### Usage Example

```python
from orchestrators import OrchestratorsService

# Initialize
service = OrchestratorsService()

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

Orchestrators operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "orchestrators",
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
| `orchestrators_operation_duration_ms` | Histogram | Operation latency distribution |
| `orchestrators_operation_total` | Counter | Total operations processed |
| `orchestrators_error_total` | Counter | Total errors encountered |
| `orchestrators_active_connections` | Gauge | Current active connections |

### Tracing

Orchestrators emits OpenTelemetry spans:

- `orchestrators.execute` — Root span for operation
  - `orchestrators.validate` — Input validation
  - `orchestrators.process` — Core processing
  - `orchestrators.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/orchestrators/`:
- `test_orchestrators.py` — Core unit tests
- `test_orchestrators_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test orchestrators with real dependencies
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

- `agent_execution/**` — Application logic, safe to modify
- `memory/**` — Application logic, safe to modify
- `reasoning/**` — Application logic, safe to modify
- `world_model/**` — Application logic, safe to modify
- `pattern/**` — Application logic, safe to modify

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
