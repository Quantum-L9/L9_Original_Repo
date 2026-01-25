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

# Research Agent

> **Tier:** AGENTS | **Path:** `agents/research_agent` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                              Research Agent                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   agents_rese   │ ───► │  Outbound   │                  │
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

Autonomous research agent with web search and analysis capabilities

**Purpose:** Conducts autonomous research using web search, analysis, and memory integration.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute agents research tasks
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
| `services/research/` | Required dependency |
| `memory/substrate_service.py` | Required dependency |

---

## Directory Layout

```
agents/research_agent/
├── __init__.py
├── research_facade.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `AgentsResearchService`)
- **Functions:** `snake_case` (e.g., `process_agents_research_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

See source files for component details.

---

## Data Models and Contracts

See source files for data model definitions.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AgentsResearchRequest(BaseModel):
    """Request model for agents_research operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class AgentsResearchResponse(BaseModel):
    """Response model for agents_research operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Research results stored as packets**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Agents_Research components are discovered and registered.
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
# Agents_Research feature flags
L9_ENABLE_AGENTS_RESEARCH_TRACING: true  # Enable detailed tracing
L9_ENABLE_AGENTS_RESEARCH_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_AGENTS_RESEARCH_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
agents_research:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
AGENTS_RESEARCH_LOG_LEVEL=INFO
AGENTS_RESEARCH_TIMEOUT=30
AGENTS_RESEARCH_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def run_research(query, user_id, deep)`

Run a research query through the full LangGraph pipeline.

- **File:** `research_facade.py:32`
- **Async:** Yes

#### `async def run_quick_research(query, model)`

Run a quick Perplexity query without the full pipeline.

- **File:** `research_facade.py:76`
- **Async:** Yes

#### `def generate_superprompt(path, template, title)`

Generate a superprompt for Perplexity by extracting facts from code.

- **File:** `research_facade.py:121`
- **Async:** No

#### `def extract_facts(path)`

Extract code facts from a module using AST parsing.

- **File:** `research_facade.py:185`
- **Async:** No

#### `def save_perplexity_output(content, project, filename)`

Save Perplexity output to the research results folder.

- **File:** `research_facade.py:278`
- **Async:** No


### Usage Example

```python
from agents.research_agent import AgentsResearchService

# Initialize
service = AgentsResearchService()

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

Agents Research operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "agents.research_agent",
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
| `agents_research_operation_duration_ms` | Histogram | Operation latency distribution |
| `agents_research_operation_total` | Counter | Total operations processed |
| `agents_research_error_total` | Counter | Total errors encountered |
| `agents_research_active_connections` | Gauge | Current active connections |

### Tracing

Agents Research emits OpenTelemetry spans:

- `agents_research.execute` — Root span for operation
  - `agents_research.validate` — Input validation
  - `agents_research.process` — Core processing
  - `agents_research.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/agents_research_agent/`:
- `test_agents_research.py` — Core unit tests
- `test_agents_research_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test agents_research with real dependencies
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

- `research_facade.py` — Application logic, safe to modify
- `perplexity_client.py` — Application logic, safe to modify

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
