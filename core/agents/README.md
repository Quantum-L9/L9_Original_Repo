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

# Agent Execution Runtime

> **Tier:** CORE | **Path:** `core/agents` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                         Agent Execution Runtime                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_agents   │ ───► │  Outbound   │                  │
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

Agent executor, runtime, registry, and task lifecycle management

**Purpose:** Orchestrates agent task execution, kernel loading, tool dispatch, and memory integration.

**What depends on it:** `api/agent_routes.py`, `runtime/task_queue.py`, `orchestrators/agent_execution/`

---

## Responsibilities and Boundaries

### What This Module Owns

- Agent execution model (start, run, shutdown)
- Kernel registry and discovery
- Agent lifecycle management
- Context propagation (correlation_id, user, execution context)
- Tool dispatch coordination via RegistryAdapter

### What This Module Does NOT Do

- Tool execution logic (owned by core/tools)
- Memory persistence (owned by memory/)
- Network/WebSocket communication (owned by runtime/)
- Authentication (owned by api/auth.py)

### Inbound Dependencies

| Module | Purpose |
|--------|---------|
| `api/agent_routes.py` | Uses this module |
| `runtime/task_queue.py` | Uses this module |
| `orchestrators/agent_execution/` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `memory/substrate_service.py` | Required dependency |
| `core/tools/registry_adapter.py` | Required dependency |
| `runtime/kernel_loader.py` | Required dependency |

---

## Directory Layout

```
core/agents/
├── __init__.py
├── adaptive_prompting.py
├── agent_instance.py
├── bootstrap/__init__.py
├── bootstrap/bootstrap_metrics.py
├── bootstrap/models.py
├── bootstrap/orchestrator.py
├── bootstrap/phase_0_validate.py
├── bootstrap/phase_1_load_kernels.py
├── bootstrap/phase_2_instantiate.py
├── bootstrap/phase_3_bind_kernels.py
├── bootstrap/phase_4_load_identity.py
├── bootstrap/phase_5_bind_tools.py
├── bootstrap/phase_6_wire_governance.py
├── bootstrap/phase_7_verify_and_lock.py
└── ... (24 more files)
```

| File | Purpose |
|------|---------|
| `executor.py` | Core agent execution loop, context management, and signal handling (PROTECTED) |
| `registry.py` | Agent type registry and discovery (PROTECTED) |
| `aios_runtime.py` | AIOS runtime wrapper for agent execution (PROTECTED) |
| `agent_instance.py` | Agent instance lifecycle and state management |
| `prompt_builder.py` | Dynamic prompt construction from kernels and context |
| `schemas.py` | Pydantic models for agent requests/responses |
| `adaptive_prompting.py` | Context-aware prompt adaptation strategies |
| `selfreflection.py` | Agent self-reflection and metacognition |

### Naming Conventions

- **Agent classes:** `<Name>Agent` (e.g., `ResearcherAgent`)
- **Executor classes:** `<Name>Executor` or `AgentExecutorService`
- **Config models:** `<Name>Config` (e.g., `AgentConfig`)
- **Request/Response:** `<Operation>Request`, `<Operation>Response`

---

## Key Components

### `prompt_builder.py` — KernelAwareAgent

```python
class KernelAwareAgent:
    """Protocol for agents with loaded kernels."""

    # Key methods:

    def get_kernel_section(self, ...) -> str | None: ...

```

**Public Methods:** `get_kernel_section`

**Lines:** 100-108 in `prompt_builder.py`

### `registry.py` — AgentRegistry

```python
class AgentRegistry:
    """Registry for agent configurations."""

    # Key methods:

    def __init__(self, ...): ...

    def _load_sync(self, ...) -> None: ...

    def _load_agent_file(self, ...) -> None: ...

    def _parse_agent_config(self, ...) -> AgentConfig | None: ...

    async def load_from_directory(self, ...) -> int: ...

```

**Public Methods:** `__init__`, `_load_sync`, `_load_agent_file`, `_parse_agent_config`, `load_from_directory`

**Lines:** 86-483 in `registry.py`

### `agent_instance.py` — AgentInstance

```python
class AgentInstance:
    """Represents a running agent instance."""

    # Key methods:

    def __init__(self, ...): ...

    def instance_id(self, ...) -> UUID: ...

    def config(self, ...) -> AgentConfig: ...

    def task(self, ...) -> AgentTask: ...

    def state(self, ...) -> ExecutorState: ...

```

**Public Methods:** `__init__`, `instance_id`, `config`, `task`, `state`

**Lines:** 107-815 in `agent_instance.py`

### `kernel_registry.py` — KernelAwareAgentRegistry

```python
class KernelAwareAgentRegistry:
    """Agent registry that integrates kernel loading."""

    # Key methods:

    def __init__(self, ...): ...

    def _initialize_with_kernels(self, ...) -> None: ...

    def _initialize_fallback(self, ...) -> None: ...

    def get_agent_config(self, ...) -> AgentConfig | None: ...

    def agent_exists(self, ...) -> bool: ...

```

**Public Methods:** `__init__`, `_initialize_with_kernels`, `_initialize_fallback`, `get_agent_config`, `agent_exists`

**Lines:** 60-240 in `kernel_registry.py`

### `schemas.py` — ExecutorState

```python
class ExecutorState:
    """State machine states for the executor loop."""

    # Key methods:

```

**Lines:** 74-82 in `schemas.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`ToolCallRequest`** — Request to dispatch a tool call.
- **`DuplicateTaskResponse`** — Response when a duplicate task is detected.

### Exported Symbols (`__all__`)

`ACTIVE_BOOTSTRAPS`, `AGENT_EXECUTOR_NAMESPACE`, `AGENT_LABEL`, `AIOSResult`, `AIOSResultType`, `AIOSRuntime`, `AgentBootstrapContext`, `AgentBootstrapError`, `AgentBootstrapOrchestrator`, `AgentConfig`

*...and 125 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `SAFETY_PREFIX` | `'\n## IMMUTABLE GOVERNANCE CONSTRAINTS\n...` | 57 |
| `USE_KERNELS` | `os.getenv('L9_USE_KERNELS', 'true').lowe...` | 56 |
| `DEFAULT_CONFIG_DIR` | `'config/agents'` | 78 |
| `DEFAULT_AGENT_ID` | `'l9-standard-v1'` | 79 |
| `USE_KERNELS` | `os.getenv('L9_USE_KERNELS', 'true').lowe...` | 57 |
| `AGENT_EXECUTOR_NAMESPACE` | `uuid5(NAMESPACE_DNS, 'agent.executor.l9....` | 67 |
| `ITERATION_THRESHOLD` | `int(os.environ.get('L9_REFLECTION_ITERAT...` | 59 |
| `TOKEN_THRESHOLD` | `int(os.environ.get('L9_REFLECTION_TOKEN_...` | 62 |

*...and 51 more constants*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class CoreAgentsRequest(BaseModel):
    """Request model for core_agents operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreAgentsResponse(BaseModel):
    """Response model for core_agents operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Agent IDs are UUIDv4 or registered agent names**
- **All agent tasks emit PacketEnvelope to memory substrate**
- **Kernel stack loaded via KernelLoader before execution**
- **Tool access mediated by RegistryAdapter with capability checks**
- **High-risk tools require Igor approval before dispatch**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Agent name resolved via `AgentRegistry.get_agent()`.
2. **Manifest loading:** YAML config parsed and validated.
3. **Kernel instantiation:** Kernel instance created (lightweight).
4. **Context creation:** ExecutionContext initialized with correlation_id, user, deadline.


### Main Execution

1. **Planning:** Kernel calls LLM to plan next action.
2. **Tool invocation:** If plan calls tool, dispatched via RegistryAdapter.
3. **Memory updates:** Agent reads recent memory and writes findings.
4. **Iteration:** Repeat until goal achieved or timeout/max-steps.


### Shutdown

1. **Finalization:** Kernel writes remaining state to memory.
2. **Logging:** Execution trace emitted as structured JSON.
3. **Cleanup:** Context released, resources freed.
4. **Result:** AgentResult returned to caller.


### Background Tasks

None. Agents are synchronous from task queue worker perspective.

---

## Configuration

### Feature Flags

```yaml
# Core_Agents feature flags
L9_ENABLE_CORE_AGENTS_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_AGENTS_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_AGENTS_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_agents:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_AGENTS_LOG_LEVEL=INFO
CORE_AGENTS_TIMEOUT=30
CORE_AGENTS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def generate_adaptive_context(patterns) -> str`

Generate adaptive context from governance patterns.

- **File:** `adaptive_prompting.py:47`
- **Async:** No
- **Returns:** `str`

#### `async def get_adaptive_context_for_tool(tool_name) -> str`

Get adaptive context for a specific tool.

- **File:** `adaptive_prompting.py:183`
- **Async:** Yes
- **Returns:** `str`

#### `async def get_world_model_context_for_agent(agent_name) -> str`

Get world model context for an agent.

- **File:** `adaptive_prompting.py:210`
- **Async:** Yes
- **Returns:** `str`

#### `async def get_combined_adaptive_context(tool_name, agent_name, include_world_model) -> str`

Get combined adaptive context including governance patterns and world model.

- **File:** `adaptive_prompting.py:234`
- **Async:** Yes
- **Returns:** `str`

#### `async def get_test_failure_context(task_id) -> str`

Get adaptive context from test failures for a task.

- **File:** `adaptive_prompting.py:266`
- **Async:** Yes
- **Returns:** `str`


### Usage Example

```python
from core.agents import AgentRegistry, ExecutionContext
from uuid import uuid4
from datetime import datetime, timedelta, timezone

registry = AgentRegistry()
researcher = registry.get_agent("researcher")

result = await researcher.execute(
    agent_id="researcher-001",
    goal="Find top 3 AI breakthroughs in 2025",
    memory_context={"recent_findings": [...]},
    tools_available=["search_web", "fetch_url"],
    context=ExecutionContext(
        correlation_id=str(uuid4()),
        user_id="user-123",
        deadline=datetime.now(timezone.utc) + timedelta(minutes=10),
        token_budget_remaining=100000,
    ),
)

print(result.output)  # Agent's findings
print(result.tool_invocations)  # Tools called
```


---

## Observability

### Logging

Core Agents operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-14T08:25:39Z",
  "level": "INFO",
  "module": "core.agents",
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
| `core_agents_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_agents_operation_total` | Counter | Total operations processed |
| `core_agents_error_total` | Counter | Total errors encountered |
| `core_agents_active_connections` | Gauge | Current active connections |

### Tracing

Core Agents emits OpenTelemetry spans:

- `core_agents.execute` — Root span for operation
  - `core_agents.validate` — Input validation
  - `core_agents.process` — Core processing
  - `core_agents.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_agents/`:
- `test_core_agents.py` — Core unit tests
- `test_core_agents_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_agents with real dependencies
- Test cross-subsystem interactions
- Test failure scenarios and recovery

### Known Edge Cases

1. **Token exhaustion** — Agent hits token budget mid-execution → returns partial result with 'incomplete' status
1. **Tool unavailable** — Requested tool not in agent's capability set → logged warning, agent continues without tool
1. **Memory timeout** — Memory substrate query times out → agent continues with cached context
1. **Deadline exceeded** — Execution time exceeds deadline → agent interrupted, partial result returned
1. **Kernel load failure** — Kernel YAML invalid → agent fails fast with clear error message

---

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

- `adaptive_prompting.py` — Application logic, safe to modify
- `selfreflection.py` — Application logic, safe to modify
- `prompt_builder.py` — Application logic, safe to modify
- `agent_instance.py` — Application logic, safe to modify
- `bootstrap/**` — Application logic, safe to modify
- `graph_state/**` — Application logic, safe to modify
- `tests/**` — Application logic, safe to modify
- `docs/**` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `executor.py` — Requires human review before merge
- `registry.py` — Requires human review before merge
- `aios_runtime.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `executor.py` — PROTECTED: Changes break system invariants
- `registry.py` — PROTECTED: Changes break system invariants
- `__init__.py` — PROTECTED: Changes break system invariants

### Required Pre-Reading

1. [`README-L9_ARCHITECTURE.md`](README-L9_ARCHITECTURE.md)
2. [`docs/CURSOR-RUNBOOK.md`](docs/CURSOR-RUNBOOK.md)
3. [`core/agents/README.md`](core/agents/README.md)

### Change Policy

All changes proposed by AI tools must:
1. Be scoped PRs with clear commit messages
2. Include tests (unit + integration where applicable)
3. Update documentation if APIs change
4. Respect feature flags for gradual rollout
5. Get human approval for restricted scopes
