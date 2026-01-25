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
├── codegenagent/CodeGenAgent Engine.py
├── codegenagent/__init__.py
├── codegenagent/__main__.py
├── codegenagent/ap_generator.py
├── codegenagent/c_gmp_engine.py
├── codegenagent/codegen_agent.py
├── codegenagent/compliance_auditor.py
├── codegenagent/cursor_context_sync_engine.py
├── codegenagent/cursor_sync.py
└── ... (35 more files)
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

**Lines:** 77-85 in `research_agent_impl.py`

### `research_agent_impl.py` — ResearchResponse

```python
class ResearchResponse:
    """Structured response from Perplexity API."""
    
    # Key methods:

```

**Lines:** 89-97 in `research_agent_impl.py`

### `research_agent_impl.py` — SynthesisResult

```python
class SynthesisResult:
    """Result from fast synthesis (Super-Prompt Pack style)."""
    
    # Key methods:

```

**Lines:** 101-110 in `research_agent_impl.py`

### `research_agent_impl.py` — DiscoveryResult

```python
class DiscoveryResult:
    """Result from deep research (Deep Workflows style)."""
    
    # Key methods:

```

**Lines:** 114-124 in `research_agent_impl.py`

### `research_agent_impl.py` — ResearchTask

```python
class ResearchTask:
    """Research task specification."""
    
    # Key methods:

```

**Lines:** 128-143 in `research_agent_impl.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`ResearchResponse`** — Structured response from Perplexity API.
- **`ResponseProcessor`** — Extracts structured insights from Perplexity responses.
- **`AgentResponse`** — Response from an agent.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

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

- **File:** `research_agent_impl.py:1070`
- **Async:** Yes

#### `def create_research_agent(api_key, prompt_variations)`

Factory function to create a ResearchAgent instance.

- **File:** `research_agent_impl.py:1112`
- **Async:** No

#### `def register_agent(name, role, category, priority)`

Decorator to register an agent class for auto-discovery.

- **File:** `agent_registry.py:63`
- **Async:** No

#### `def discover_agents(package)`

Automatically discover all agents in the specified package.

- **File:** `agent_registry.py:115`
- **Async:** No

#### `def get_all_agents()`

Get all registered agent classes as a dictionary.

- **File:** `agent_registry.py:131`
- **Async:** No


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
  "timestamp": "2026-01-25T19:42:30Z",
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
