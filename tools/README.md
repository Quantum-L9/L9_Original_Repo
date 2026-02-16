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

| Module | Purpose |
|--------|---------|
| — | No inbound dependencies |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No outbound dependencies |

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
├── adr/docstring_injector.py
├── architecture_reports/__init__.py
├── architecture_reports/architecture_report.py
├── architecture_reports/async_function_map_report.py
├── architecture_reports/class_definitions_report.py
├── architecture_reports/config.py
└── ... (46 more files)
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `mac_protocol.py` | Mac protocol message schema. |
| `mac_protocol.py` | Mac protocol response schema. |
| `track_mypy_progress.py` | Type coverage data for a single module. |

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

**Lines:** 34-66 in `mac_protocol.py`

### `mac_protocol.py` — MacResponse

```python
class MacResponse:
    """Mac protocol response schema."""

    # Key methods:

```

**Lines:** 69-100 in `mac_protocol.py`

### `track_mypy_progress.py` — ModuleCoverage

```python
class ModuleCoverage:
    """Type coverage data for a single module."""

    # Key methods:

```

**Lines:** 36-46 in `track_mypy_progress.py`

### `adr_enforcer.py` — Violation

```python
class Violation:
    """Represents a single ADR violation."""

    # Key methods:

    def to_dict(self, ...) -> dict: ...

```

**Public Methods:** `to_dict`

**Lines:** 83-101 in `adr_enforcer.py`

### `adr_enforcer.py` — ValidationReport

```python
class ValidationReport:
    """Comprehensive validation report."""

    # Key methods:

    def to_dict(self, ...) -> dict: ...

```

**Public Methods:** `to_dict`

**Lines:** 105-130 in `adr_enforcer.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`MacResponse`** — Mac protocol response schema.
- **`Schema`** — Schema definition for artifact classification.

### Exported Symbols (`__all__`)

`ConceptExtractor`, `ConceptReview`, `ConceptYAML`, `DocumentClassifier`, `ExtractedConcept`, `FileScanner`, `GenerationResult`, `KnowledgeHarvester`, `L9Compiler`, `L9SpecGenerator`

*...and 9 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `SCRIPT_VERSION` | `'3.0.0'` | 51 |
| `REPO_DIR` | `_REPO_ROOT` | 56 |
| `REPO_NAME` | `os.path.basename(os.path.abspath(REPO_DI...` | 57 |
| `REPO_INDEX_DIR` | `os.path.join(_REPO_ROOT, 'reports/repo-i...` | 58 |
| `DROPBOX_EXPORT_DIR` | `os.getenv('L9_DROPBOX_EXPORT_DIR', os.pa...` | 59 |
| `ICLOUD_EXPORT_DIR` | `os.getenv('L9_ICLOUD_EXPORT_DIR', os.pat...` | 63 |
| `SKIP_DIRS` | `{'.git', '__pycache__', '.venv', 'venv',...` | 76 |
| `REQUIRED_SECTIONS` | `['# ADR-', '## Status', '## Context', '#...` | 33 |

*...and 26 more constants*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

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
L9_ENABLE_TOOLS_TRACING: true  # Enable detailed tracing
L9_ENABLE_TOOLS_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_TOOLS_AUDIT: true    # Enable audit logging
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

- **File:** `export_repo_indexes.py:92`
- **Async:** No

#### `def is_ignored(rel_path, patterns, is_dir)`

Check if a path matches any gitignore pattern.

- **File:** `export_repo_indexes.py:110`
- **Async:** No

#### `def generate_meta_header(index_name) -> str`

Generate a standard meta header for every index file.

- **File:** `export_repo_indexes.py:163`
- **Async:** No
- **Returns:** `str`

#### `def walk_python_files()`

Walk repo yielding (fpath, rel_path) for every non-ignored .py file.

- **File:** `export_repo_indexes.py:192`
- **Async:** No

#### `def walk_all_files()`

Walk repo yielding (fpath, rel_path, is_dir) for every non-ignored file.

- **File:** `export_repo_indexes.py:221`
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
  "timestamp": "2026-02-14T08:25:39Z",
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

| Metric | Type | Description |
|--------|------|-------------|
| `tools_operation_duration_ms` | Histogram | Operation latency distribution |
| `tools_operation_total` | Counter | Total operations processed |
| `tools_error_total` | Counter | Total errors encountered |
| `tools_active_connections` | Gauge | Current active connections |

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
