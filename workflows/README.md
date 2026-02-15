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

# Workflow Engine

> **Tier:** INFRASTRUCTURE | **Path:** `workflows` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                             Workflow Engine                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │    workflows    │ ───► │  Outbound   │                  │
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

DAG-based workflow execution engine with session management

**Purpose:** Provides workflow orchestration using directed acyclic graphs (DAGs) for multi-step operations like harvest-deploy, refactoring, and session management.

**What depends on it:** `api/routes/`

---

## Responsibilities and Boundaries

### What This Module Owns

- Workflow definition parsing (YAML)
- DAG execution ordering
- State persistence across runs
- Session lifecycle management
- Checkpoint and recovery

### What This Module Does NOT Do

- Agent execution (owned by core/agents)
- Memory storage (owned by memory/)
- File harvesting logic (owned by nodes)

### Inbound Dependencies

| Module | Purpose |
|--------|---------|
| `api/routes/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `memory/substrate_service.py` | Required dependency |
| `core/agents/executor.py` | Required dependency |

---

## Directory Layout

```
workflows/
├── __init__.py
├── dags/__init__.py
├── dags/component_audit_dag.py
├── dags/confirm_wiring_dag.py
├── dags/dag_authoring_dag.py
├── dags/gmp/__init__.py
├── dags/gmp/executor.py
├── dags/gmp/graph.py
├── dags/gmp/nodes/__init__.py
├── dags/gmp/nodes/core.py
├── dags/gmp/routing.py
├── dags/gmp/state.py
├── dags/gmp_execution_dag.py
├── dags/gmp_langgraph_executor.py
├── dags/harvest_deploy_dag.py
└── ... (27 more files)
```

| File | Purpose |
|------|---------|
| `state.py` | Workflow state management and persistence (PROTECTED) |
| `runner.py` | Workflow execution engine (PROTECTED) |
| `harvest_deploy.py` | Harvest-to-deploy workflow implementation |
| `nodes/extract.py` | Extraction node for content harvesting |
| `nodes/validate.py` | Validation node for quality checks |
| `nodes/deploy.py` | Deployment node for output generation |
| `nodes/inject.py` | Context injection node |
| `nodes/checkpoint.py` | Checkpoint node for state persistence |
| `nodes/report.py` | Report generation node |
| `session/interface.py` | Session interface definition |
| `session/registry.py` | Session registry and discovery |
| `defs/harvest-deploy.yaml` | Harvest-deploy workflow definition |
| `defs/workflow-template.yaml` | Template for new workflows |

### Naming Conventions

- **Workflow defs:** kebab-case YAML files (e.g., `harvest-deploy.yaml`)
- **Node modules:** snake_case Python files (e.g., `extract.py`)
- **Node functions:** `execute_<action>()` pattern
- **DAG classes:** `<Name>DAG` (e.g., `RefactoringDAG`)

---

## Key Components

### `runner.py` — StepStatus

```python
class StepStatus:
    """Status of a workflow step."""

    # Key methods:

```

**Lines:** 75-83 in `runner.py`

### `runner.py` — StepType

```python
class StepType:
    """Type of workflow step."""

    # Key methods:

```

**Lines:** 86-96 in `runner.py`

### `runner.py` — StepResult

```python
class StepResult:
    """Result of executing a step."""

    # Key methods:

```

**Lines:** 100-107 in `runner.py`

### `runner.py` — Step

```python
class Step:
    """A single step in the workflow DAG."""

    # Key methods:

```

**Lines:** 111-122 in `runner.py`

### `runner.py` — WorkflowState

```python
class WorkflowState:
    """Persistent state of a workflow execution."""

    # Key methods:

```

**Lines:** 126-136 in `runner.py`


---

## Data Models and Contracts


### Exported Symbols (`__all__`)

`COMPONENT_AUDIT_DAG`, `CONFIRM_WIRING_DAG`, `DAG_AUTHORING_DAG`, `GMPLangGraphExecutor`, `GMPPhase`, `GMPState`, `GMP_EXECUTION_DAG`, `GateType`, `HARVEST_DEPLOY_DAG`, `INSPECT_DAG`

*...and 40 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `REPO_ROOT` | `Path(__file__).parent.parent` | 63 |
| `REPORT_GENERATOR` | `REPO_ROOT / 'scripts' / 'generate_gmp_re...` | 64 |
| `STATE_FILE` | `REPO_ROOT / '.harvest_executor_state.jso...` | 65 |
| `HARVEST_DIR` | `REPO_ROOT / 'current_work' / 'harvested'` | 66 |
| `SUPPORTED_LANGUAGES` | `{'python': ('.py', True), 'py': ('.py', ...` | 71 |
| `STEP_ORDER` | `['read_document', 'parse_code_blocks', '...` | 157 |
| `REPO_ROOT` | `Path(__file__).parent.parent` | 64 |
| `REPORT_GENERATOR` | `REPO_ROOT / 'scripts' / 'generate_gmp_re...` | 65 |

*...and 43 more constants*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class WorkflowsRequest(BaseModel):
    """Request model for workflows operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class WorkflowsResponse(BaseModel):
    """Response model for workflows operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Workflow state is persisted between runs**
- **DAG nodes execute in topological order**
- **Session state is serializable**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Workflows components are discovered and registered.
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
# Workflows feature flags
L9_ENABLE_WORKFLOWS_TRACING: true  # Enable detailed tracing
L9_ENABLE_WORKFLOWS_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_WORKFLOWS_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
workflows:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
WORKFLOWS_LOG_LEVEL=INFO
WORKFLOWS_TIMEOUT=30
WORKFLOWS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def main()`

Main entry point for the L9 DAG Workflow Runner that initializes argument parsing and executes workflows.

- **File:** `runner.py:743`
- **Async:** No

#### `def main()`

No description

- **File:** `harvest_executor.py:807`
- **Async:** No

#### `def main()`

No description

- **File:** `migrate_executor.py:654`
- **Async:** No

#### `def main()`

No description

- **File:** `use_harvest_executor.py:583`
- **Async:** No

#### `def main()`

No description

- **File:** `gmp_executor.py:898`
- **Async:** No


### Usage Example

```python
from workflows import WorkflowsService

# Initialize
service = WorkflowsService()

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

Workflows operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-14T08:25:39Z",
  "level": "INFO",
  "module": "workflows",
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
| `workflows_operation_duration_ms` | Histogram | Operation latency distribution |
| `workflows_operation_total` | Counter | Total operations processed |
| `workflows_error_total` | Counter | Total errors encountered |
| `workflows_active_connections` | Gauge | Current active connections |

### Tracing

Workflows emits OpenTelemetry spans:

- `workflows.execute` — Root span for operation
  - `workflows.validate` — Input validation
  - `workflows.process` — Core processing
  - `workflows.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/workflows/`:
- `test_workflows.py` — Core unit tests
- `test_workflows_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test workflows with real dependencies
- Test cross-subsystem interactions
- Test failure scenarios and recovery

### Known Edge Cases

1. **Node failure** — Node raises exception → workflow halts, state preserved for retry
1. **Session timeout** — Session exceeds timeout → checkpoint state, emit warning
1. **Circular dependency** — DAG validation catches cycles → reject workflow definition

---

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

- `nodes/**` — Application logic, safe to modify
- `defs/**` — Application logic, safe to modify
- `session/**` — Application logic, safe to modify
- `harvest_deploy.py` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `__init__.py` — Requires human review before merge
- `state.py` — Requires human review before merge
- `runner.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `__init__.py` — PROTECTED: Changes break system invariants
- `state.py` — PROTECTED: Changes break system invariants
- `runner.py` — PROTECTED: Changes break system invariants

### Required Pre-Reading

1. [`workflows/defs/workflow-template.yaml`](workflows/defs/workflow-template.yaml)

### Change Policy

All changes proposed by AI tools must:
1. Be scoped PRs with clear commit messages
2. Include tests (unit + integration where applicable)
3. Update documentation if APIs change
4. Respect feature flags for gradual rollout
5. Get human approval for restricted scopes
