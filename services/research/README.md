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

# Research Service

> **Tier:** SERVICES | **Path:** `services/research` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                             Research Service                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   services_re   │ ───► │  Outbound   │                  │
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

Research graph, LangGraph integration, and insight extraction

**Purpose:** Provides research workflow orchestration with LangGraph and insight extraction.

**What depends on it:** `agents/research_agent/`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute services research tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics

### What This Module Does NOT Do

- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py

### Inbound Dependencies

| Module                   | Purpose          |
| ------------------------ | ---------------- |
| `agents/research_agent/` | Uses this module |

### Outbound Dependencies

| Module                        | Purpose             |
| ----------------------------- | ------------------- |
| `memory/substrate_service.py` | Required dependency |

---

## Directory Layout

```
services/research/
├── __init__.py
├── agents/__init__.py
├── agents/base_agent.py
├── agents/critic_agent.py
├── agents/planner_agent.py
├── agents/researcher_agent.py
├── graph_persistence.py
├── graph_runtime.py
├── graph_state.py
├── insight_extractor.py
├── memory_adapter.py
├── research_api.py
├── research_graph.py
├── tools/__init__.py
├── tools/perplexity_client.py
└── ... (2 more files)
```

| File                | Purpose                                       |
| ------------------- | --------------------------------------------- |
| `research_graph.py` | Core module (PROTECTED)                       |
| `__init__.py`       | Core module (PROTECTED)                       |
| `graph_state.py`    | Single step in a research plan.               |
| `graph_state.py`    | Evidence gathered by a researcher.            |
| `graph_state.py`    | Shared state across all research graph nodes. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `ServicesResearchService`)
- **Functions:** `snake_case` (e.g., `process_services_research_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `graph_state.py` — ResearchStep

```python
class ResearchStep:
    """Single step in a research plan."""

    # Key methods:

```

**Lines:** 44-53 in `graph_state.py`

### `graph_state.py` — Evidence

```python
class Evidence:
    """Evidence gathered by a researcher."""

    # Key methods:

```

**Lines:** 56-63 in `graph_state.py`

### `graph_state.py` — ResearchGraphState

```python
class ResearchGraphState:
    """Shared state across all research graph nodes."""

    # Key methods:

```

**Lines:** 66-148 in `graph_state.py`

### `graph_runtime.py` — ResearchGraphRuntime

```python
class ResearchGraphRuntime:
    """Runtime for managing research graph execution."""

    # Key methods:

    def __init__(self, ...): ...

    async def initialize(self, ...) -> None: ...

    async def shutdown(self, ...) -> None: ...

    async def execute(self, ...) -> dict[str, Any]: ...

    async def resume(self, ...) -> dict[str, Any] | None: ...

```

**Public Methods:** `__init__`, `initialize`, `shutdown`, `execute`, `resume`

**Lines:** 47-179 in `graph_runtime.py`

### `graph_persistence.py` — FindingType

```python
class FindingType:
    """Types of research findings."""

    # Key methods:

```

**Lines:** 66-74 in `graph_persistence.py`

---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`ResearchRequest`** — Request model for research endpoint.
- **`ResearchResponse`** — Response model for research endpoint.
- **`ResearchStatusResponse`** — Response model for research status endpoint.

### Exported Symbols (`__all__`)

`BaseAgent`, `BaseTool`, `CriticAgent`, `Evidence`, `FindingType`, `GraphPersistenceConfig`, `HTTPTool`, `MockSearchTool`, `PerplexityClient`, `PerplexityModel`

_...and 31 more_

### Module Constants

| Constant                       | Value                                         | Line |
| ------------------------------ | --------------------------------------------- | ---- |
| `CREATE_FINDING_QUERY`         | `'\nCREATE (f:ResearchFinding {\n    id: ...` | 114  |
| `LINK_FINDING_TO_QUERY_QUERY`  | `'\nMATCH (f:ResearchFinding {id: $findin...` | 130  |
| `LINK_FINDING_TO_AGENT_QUERY`  | `'\nMATCH (f:ResearchFinding {id: $findin...` | 138  |
| `GET_FINDINGS_BY_TYPE_QUERY`   | `'\nMATCH (f:ResearchFinding)\nWHERE f.fi...` | 145  |
| `GET_FINDINGS_FOR_QUERY_QUERY` | `'\nMATCH (q:ResearchQuery {query: $query...` | 161  |
| `PERPLEXITY_RETRY_CONFIG`      | `AsyncRetryConfig(max_retries=3, base_bac...` | 56   |
| `RESEARCHER_SYSTEM_PROMPT`     | `'You are a research agent. Your job is t...` | 40   |
| `PLANNER_SYSTEM_PROMPT`        | `'You are a research planning agent. Your...` | 39   |

_...and 1 more constants_

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ServicesResearchRequest(BaseModel):
    """Request model for services_research operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class ServicesResearchResponse(BaseModel):
    """Response model for services_research operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Research state is persisted**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Services_Research components are discovered and registered.
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
# Services_Research feature flags
L9_ENABLE_SERVICES_RESEARCH_TRACING: true # Enable detailed tracing
L9_ENABLE_SERVICES_RESEARCH_METRICS: true # Enable Prometheus metrics
L9_ENABLE_SERVICES_RESEARCH_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
services_research:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
SERVICES_RESEARCH_LOG_LEVEL=INFO
SERVICES_RESEARCH_TIMEOUT=30
SERVICES_RESEARCH_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def create_initial_state(query, thread_id, request_id, user_id) -> ResearchGraphState`

Create an initial research graph state from a query.

- **File:** `graph_state.py:151`
- **Async:** No
- **Returns:** `ResearchGraphState`

#### `def get_runtime() -> ResearchGraphRuntime`

Get or create runtime singleton.

- **File:** `graph_runtime.py:191`
- **Async:** No
- **Returns:** `ResearchGraphRuntime`

#### `async def init_runtime(database_url) -> ResearchGraphRuntime`

Initialize runtime with database URL.

- **File:** `graph_runtime.py:199`
- **Async:** Yes
- **Returns:** `ResearchGraphRuntime`

#### `async def shutdown_runtime() -> None`

Shutdown runtime.

- **File:** `graph_runtime.py:206`
- **Async:** Yes
- **Returns:** `None`

#### `async def planning_node(state) -> ResearchGraphState`

Planning node - Decompose query into research steps.

- **File:** `research_graph.py:66`
- **Async:** Yes
- **Returns:** `ResearchGraphState`

### Usage Example

```python
from services.research import ServicesResearchService

# Initialize
service = ServicesResearchService()

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

Services Research operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "services.research",
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

| Metric                                    | Type      | Description                    |
| ----------------------------------------- | --------- | ------------------------------ |
| `services_research_operation_duration_ms` | Histogram | Operation latency distribution |
| `services_research_operation_total`       | Counter   | Total operations processed     |
| `services_research_error_total`           | Counter   | Total errors encountered       |
| `services_research_active_connections`    | Gauge     | Current active connections     |

### Tracing

Services Research emits OpenTelemetry spans:

- `services_research.execute` — Root span for operation
  - `services_research.validate` — Input validation
  - `services_research.process` — Core processing
  - `services_research.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/services_research/`:

- `test_services_research.py` — Core unit tests
- `test_services_research_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test services_research with real dependencies
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

- `agents/**` — Application logic, safe to modify
- `tools/**` — Application logic, safe to modify
- `insight_extractor.py` — Application logic, safe to modify
- `memory_adapter.py` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `research_graph.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `research_graph.py` — PROTECTED: Changes break system invariants
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
