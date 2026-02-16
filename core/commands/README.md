---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "2026-02-14 08:25:39 UTC"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "worldtimeapi.org (drift: 1.5s)"
  auto_generated: true
---

# Command System

> **Tier:** CORE | **Path:** `core/commands` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                              Command System                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_comman   │ ───► │  Outbound   │                  │
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

Command pattern implementation for agent actions

**Purpose:** Implements command pattern for undoable/auditable actions.

**What depends on it:** `core/agents/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core commands tasks
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
| — | No outbound dependencies |

---

## Directory Layout

```
core/commands/
├── __init__.py
├── executor.py
├── intent_extractor.py
├── parser.py
├── schemas.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `schemas.py` | Recognized structured command types. |
| `schemas.py` | Intent categories for NLP extraction. |
| `schemas.py` | Risk level for command execution. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreCommandsService`)
- **Functions:** `snake_case` (e.g., `process_core_commands_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `schemas.py` — CommandType

```python
class CommandType:
    """Recognized structured command types."""

    # Key methods:

```

**Lines:** 48-57 in `schemas.py`

### `schemas.py` — IntentType

```python
class IntentType:
    """Intent categories for NLP extraction."""

    # Key methods:

```

**Lines:** 60-71 in `schemas.py`

### `schemas.py` — RiskLevel

```python
class RiskLevel:
    """Risk level for command execution."""

    # Key methods:

```

**Lines:** 74-80 in `schemas.py`

### `schemas.py` — Command

```python
class Command:
    """Structured command parsed from Igor input."""

    # Key methods:

    def requires_confirmation(self, ...) -> bool: ...

```

**Public Methods:** `requires_confirmation`

**Lines:** 83-103 in `schemas.py`

### `schemas.py` — NLPPrompt

```python
class NLPPrompt:
    """Natural language prompt requiring intent extraction."""

    # Key methods:

```

**Lines:** 106-111 in `schemas.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`IntentModel`** — Extracted intent from NLP text.

### Exported Symbols (`__all__`)

`Command`, `CommandExecutor`, `CommandResult`, `CommandType`, `ConfirmationResult`, `IntentModel`, `IntentType`, `NLPPrompt`, `RiskLevel`, `confirm_intent`

*...and 5 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `COMMAND_PATTERNS` | `{'propose_gmp': re.compile('^@[Ll]\\s+pr...` | 158 |
| `INTENT_EXTRACTION_PROMPT` | `'You are an intent extraction system for...` | 61 |

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class CoreCommandsRequest(BaseModel):
    """Request model for core_commands operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreCommandsResponse(BaseModel):
    """Response model for core_commands operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Commands are serializable**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Commands components are discovered and registered.
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
# Core_Commands feature flags
L9_ENABLE_CORE_COMMANDS_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_COMMANDS_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_COMMANDS_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_commands:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_COMMANDS_LOG_LEVEL=INFO
CORE_COMMANDS_TIMEOUT=30
CORE_COMMANDS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def parse_command(text)`

Parse Igor input into structured Command or NLPPrompt.

- **File:** `__init__.py:42`
- **Async:** No

#### `def is_l_command(text) -> bool`

Check if text appears to be an @L command.

- **File:** `__init__.py:49`
- **Async:** No
- **Returns:** `bool`

#### `async def extract_intent(nlp_prompt, openai_client)`

Extract intent from natural language prompt.

- **File:** `__init__.py:56`
- **Async:** Yes

#### `async def confirm_intent(intent, user_context, slack_client)`

Request Igor confirmation for high-risk commands.

- **File:** `__init__.py:63`
- **Async:** Yes

#### `async def execute_command(command, user_id, context)`

Execute a structured command.

- **File:** `__init__.py:70`
- **Async:** Yes


### Usage Example

```python
from core.commands import CoreCommandsService

# Initialize
service = CoreCommandsService()

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

Core Commands operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-14T08:25:39Z",
  "level": "INFO",
  "module": "core.commands",
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
| `core_commands_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_commands_operation_total` | Counter | Total operations processed |
| `core_commands_error_total` | Counter | Total errors encountered |
| `core_commands_active_connections` | Gauge | Current active connections |

### Tracing

Core Commands emits OpenTelemetry spans:

- `core_commands.execute` — Root span for operation
  - `core_commands.validate` — Input validation
  - `core_commands.process` — Core processing
  - `core_commands.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_commands/`:
- `test_core_commands.py` — Core unit tests
- `test_core_commands_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_commands with real dependencies
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
