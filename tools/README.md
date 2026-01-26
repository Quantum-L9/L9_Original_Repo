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

# Development Tools

> **Tier:** INFRASTRUCTURE | **Path:** `tools` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                            Development Tools                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │      tools      │ ───► │  Outbound   │                  │
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

Development and maintenance tools

**Purpose:** Provides CLI tools for development, debugging, and maintenance.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute tools tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics

### What This Module Does NOT Do

- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py

### Inbound Dependencies

| Module | Purpose                 |
| ------ | ----------------------- |
| —      | No inbound dependencies |

### Outbound Dependencies

| Module | Purpose                  |
| ------ | ------------------------ |
| —      | No outbound dependencies |

---

## Directory Layout

```
tools/
├── __init__.py
├── adr/__init__.py
├── adr/adr_cli.py
├── adr/adr_compliance_check_enhanced.py
├── adr/adr_enforcer.py
├── adr/adr_generator.py
├── adr/adr_indexer.py
├── adr/adr_scanner.py
├── adr/adr_validator.py
├── architecture_reports/__init__.py
├── architecture_reports/architecture_report.py
├── architecture_reports/async_function_map_report.py
├── architecture_reports/class_definitions_report.py
├── architecture_reports/config.py
├── architecture_reports/config_files_report.py
└── ... (22 more files)
```

| File              | Purpose                       |
| ----------------- | ----------------------------- |
| `__init__.py`     | Core module (PROTECTED)       |
| `mac_protocol.py` | Mac protocol message schema.  |
| `mac_protocol.py` | Mac protocol response schema. |
| `mac_protocol.py` | Component                     |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `ToolsService`)
- **Functions:** `snake_case` (e.g., `process_tools_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `mac_protocol.py` — MacMessage

```python
class MacMessage:
    """Mac protocol message schema."""

    # Key methods:

```

**Lines:** 33-54 in `mac_protocol.py`

### `mac_protocol.py` — MacResponse

```python
class MacResponse:
    """Mac protocol response schema."""

    # Key methods:

```

**Lines:** 57-77 in `mac_protocol.py`

### `mac_protocol.py` — Config

```python
class Config:
    """No description"""

    # Key methods:

```

**Lines:** 45-54 in `mac_protocol.py`

### `mac_protocol.py` — Config

```python
class Config:
    """No description"""

    # Key methods:

```

**Lines:** 68-77 in `mac_protocol.py`

### `adr_enforcer.py` — Violation

```python
class Violation:
    """Represents a single ADR violation."""

    # Key methods:

    async def to_dict(self, ...): ...

```

**Public Methods:** `to_dict`

**Lines:** 41-54 in `adr_enforcer.py`

---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`MacResponse`** — Mac protocol response schema.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ToolsRequest(BaseModel):
    """Request model for tools operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class ToolsResponse(BaseModel):
    """Response model for tools operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **All operations must be idempotent**
- **State changes logged to audit trail**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Tools components are discovered and registered.
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
# Tools feature flags
L9_ENABLE_TOOLS_TRACING: true # Enable detailed tracing
L9_ENABLE_TOOLS_METRICS: true # Enable Prometheus metrics
L9_ENABLE_TOOLS_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
tools:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
TOOLS_LOG_LEVEL=INFO
TOOLS_TIMEOUT=30
TOOLS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def load_gitignore_patterns()`

Load and parse .gitignore patterns.

- **File:** `export_repo_indexes.py:75`
- **Async:** No

#### `def is_ignored(rel_path, patterns, is_dir)`

Check if a path matches any gitignore pattern.

- **File:** `export_repo_indexes.py:93`
- **Async:** No

#### `def generate_tree()`

Generate tree.txt using actual directory structure, respecting .gitignore.

- **File:** `export_repo_indexes.py:119`
- **Async:** No

#### `def generate_api_surfaces()`

Map all callable interfaces across different API surface types.

- **File:** `export_repo_indexes.py:166`
- **Async:** No

#### `def generate_entrypoints()`

Identify app entrypoints with useful metadata.

- **File:** `export_repo_indexes.py:217`
- **Async:** No

### Usage Example

```python
from tools import ToolsService

# Initialize
service = ToolsService()

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

Tools operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "tools",
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

| Metric                        | Type      | Description                    |
| ----------------------------- | --------- | ------------------------------ |
| `tools_operation_duration_ms` | Histogram | Operation latency distribution |
| `tools_operation_total`       | Counter   | Total operations processed     |
| `tools_error_total`           | Counter   | Total errors encountered       |
| `tools_active_connections`    | Gauge     | Current active connections     |

### Tracing

Tools emits OpenTelemetry spans:

- `tools.execute` — Root span for operation
  - `tools.validate` — Input validation
  - `tools.process` — Core processing
  - `tools.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/tools/`:

- `test_tools.py` — Core unit tests
- `test_tools_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test tools with real dependencies
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
