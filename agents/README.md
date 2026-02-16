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

# Agent Modules

> **Tier:** AGENTS | **Path:** `agents` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                              Agent Modules                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │      agents     │ ───► │  Outbound   │                  │
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

Collection of specialized agents for different domains

**Purpose:** Houses domain-specific agents (cursor, research, architect, coder) that extend L9 capabilities.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute agents tasks
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
| `core/agents/executor.py` | Required dependency |
| `memory/substrate_service.py` | Required dependency |

---

## Directory Layout

```
agents/
├── __init__.py
├── agent_registry.py
├── architect_agent/__init__.py
├── architect_agent/architect_agent_a.py
├── architect_agent/architect_agent_b.py
├── base_agent.py
├── codegenagent/__init__.py
├── codegenagent/__main__.py
├── codegenagent/ap_generator.py
├── codegenagent/c_gmp_engine.py
├── codegenagent/codegen_agent.py
├── codegenagent/codegen_agent_engine.py
├── codegenagent/compliance_auditor.py
├── codegenagent/cursor_context_sync_engine.py
├── codegenagent/cursor_sync.py
└── ... (39 more files)
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `research_agent_impl.py` | Represents a single prompt variation for multi-per |
| `research_agent_impl.py` | Structured response from Perplexity API. |
| `research_agent_impl.py` | Result from fast synthesis (Super-Prompt Pack styl |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `AgentsService`)
- **Functions:** `snake_case` (e.g., `process_agents_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `research_agent_impl.py` — PromptVariation

```python
class PromptVariation:
    """Represents a single prompt variation for multi-perspective synthesis."""

    # Key methods:

```

**Lines:** 78-86 in `research_agent_impl.py`

### `research_agent_impl.py` — ResearchResponse

```python
class ResearchResponse:
    """Structured response from Perplexity API."""

    # Key methods:

```

**Lines:** 90-98 in `research_agent_impl.py`

### `research_agent_impl.py` — SynthesisResult

```python
class SynthesisResult:
    """Result from fast synthesis (Super-Prompt Pack style)."""

    # Key methods:

```

**Lines:** 102-111 in `research_agent_impl.py`

### `research_agent_impl.py` — DiscoveryResult

```python
class DiscoveryResult:
    """Result from deep research (Deep Workflows style)."""

    # Key methods:

```

**Lines:** 115-125 in `research_agent_impl.py`

### `research_agent_impl.py` — ResearchTask

```python
class ResearchTask:
    """Research task specification."""

    # Key methods:

```

**Lines:** 129-144 in `research_agent_impl.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`ResearchResponse`** — Structured response from Perplexity API.
- **`ResponseProcessor`** — Extracts structured insights from Perplexity responses.
- **`AgentResponse`** — Response from an agent.

### Exported Symbols (`__all__`)

`AgentConfig`, `AgentMessage`, `AgentResponse`, `AgentRole`, `ArchitectAgentA`, `ArchitectAgentB`, `AutonomyController`, `AutonomyGraduationMetrics`, `AutonomyLevel`, `BaseAgent`

*...and 78 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `PERPLEXITY_API_URL` | `'https://api.perplexity.ai/chat/completi...` | 65 |
| `PERPLEXITY_MODEL_FAST` | `'sonar-reasoning'` | 66 |
| `PERPLEXITY_MODEL_DEEP` | `'sonar-reasoning'` | 67 |
| `CODEGEN_SPECS_DIR` | `Path(__file__).parent.parent / 'codegen'...` | 69 |
| `DEFAULT_PROMPT_VARIATIONS` | `[PromptVariation(id='v1_pragmatic', name...` | 173 |
| `RESEARCH_OVERLAY_PATH` | `'config/agents/L-CTO-Research-Overlay.ya...` | 670 |
| `SYSTEM_PROMPT` | `"You are the Reflection Agent for L9, re...` | 49 |
| `SYSTEM_PROMPT` | `'You are the QA Agent for L9, responsibl...` | 49 |

*...and 50 more constants*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class AgentsRequest(BaseModel):
    """Request model for agents operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class AgentsResponse(BaseModel):
    """Response model for agents operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **All agents follow AgentInstance lifecycle**
- **Agent outputs stored as PacketEnvelope**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Agents components are discovered and registered.
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
# Agents feature flags
L9_ENABLE_AGENTS_TRACING: true  # Enable detailed tracing
L9_ENABLE_AGENTS_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_AGENTS_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
agents:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
AGENTS_LOG_LEVEL=INFO
AGENTS_TIMEOUT=30
AGENTS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def main()`

CLI entry point.

- **File:** `research_agent_impl.py:1107`
- **Async:** Yes

#### `def create_research_agent(api_key, prompt_variations) -> ResearchAgent`

Factory function to create a ResearchAgent instance.

- **File:** `research_agent_impl.py:1149`
- **Async:** No
- **Returns:** `ResearchAgent`

#### `def register_agent(name, role, category, priority)`

Decorator to register an agent class for auto-discovery.

- **File:** `agent_registry.py:63`
- **Async:** No

#### `def discover_agents(package) -> int`

Automatically discover all agents in the specified package.

- **File:** `agent_registry.py:127`
- **Async:** No
- **Returns:** `int`

#### `def get_all_agents() -> dict[str, type]`

Get all registered agent classes as a dictionary.

- **File:** `agent_registry.py:143`
- **Async:** No
- **Returns:** `dict[str, type]`


### Usage Example

```python
from agents import AgentsService

# Initialize
service = AgentsService()

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

Agents operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-14T08:25:39Z",
  "level": "INFO",
  "module": "agents",
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
| `agents_operation_duration_ms` | Histogram | Operation latency distribution |
| `agents_operation_total` | Counter | Total operations processed |
| `agents_error_total` | Counter | Total errors encountered |
| `agents_active_connections` | Gauge | Current active connections |

### Tracing

Agents emits OpenTelemetry spans:

- `agents.execute` — Root span for operation
  - `agents.validate` — Input validation
  - `agents.process` — Core processing
  - `agents.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/agents/`:
- `test_agents.py` — Core unit tests
- `test_agents_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test agents with real dependencies
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
