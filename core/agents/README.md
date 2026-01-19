# Agents Subsystem

## Overview

The **Agents Subsystem** is the Agent execution runtime for L9 Secure AI OS. It Orchestrates agent task execution, kernel loading, tool dispatch, and memory integration.

**What depends on it:** `api/agent_routes.py`, `runtime/task_queue.py`

## Responsibilities and Boundaries

### What This Module Owns

- See key components below for detailed responsibilities

### What This Module Does NOT Do

- Operations handled by other subsystems (see dependencies)

### Dependencies

| Direction | Module | Purpose |
|-----------|--------|---------|
| **Outbound** | `memory/substrate_service.py` | Required dependency |
| **Outbound** | `core/tools/registry_adapter.py` | Required dependency |
| **Outbound** | `runtime/kernel_loader.py` | Required dependency |
| **Inbound** | `api/agent_routes.py` | Uses this module |
| **Inbound** | `runtime/task_queue.py` | Uses this module |

## Directory Layout

```
core/agents/
├── __init__.py
├── adaptive_prompting.py
├── agent_instance.py
├── bootstrap/__init__.py
├── bootstrap/bootstrap_metrics.py
├── bootstrap/orchestrator.py
├── bootstrap/phase_0_validate.py
├── bootstrap/phase_1_load_kernels.py
├── bootstrap/phase_2_instantiate.py
├── bootstrap/phase_3_bind_kernels.py
├── bootstrap/phase_4_load_identity.py
├── bootstrap/phase_5_bind_tools.py
├── bootstrap/phase_6_wire_governance.py
├── bootstrap/phase_7_verify_and_lock.py
├── executor.py
└── ... (12 more files)
```

## Key Components

### `prompt_builder.py` — KernelAwareAgent

```python
class KernelAwareAgent:
    """Protocol for agents with loaded kernels."""
```

**Methods:** `get_kernel_section`

### `registry.py` — AgentRegistry

```python
class AgentRegistry:
    """Registry for agent configurations."""
```

**Methods:** `__init__`, `_load_sync`, `_load_agent_file`, `_parse_agent_config`, `load_from_directory`

### `agent_instance.py` — AgentInstance

```python
class AgentInstance:
    """Represents a running agent instance."""
```

**Methods:** `__init__`, `instance_id`, `config`, `task`, `state`

### `kernel_registry.py` — KernelAwareAgentRegistry

```python
class KernelAwareAgentRegistry:
    """Agent registry that integrates kernel loading."""
```

**Methods:** `__init__`, `_initialize_with_kernels`, `_initialize_fallback`, `get_agent_config`, `agent_exists`

### `schemas.py` — ExecutorState

```python
class ExecutorState:
    """State machine states for the executor loop."""
```


## Data Models and Contracts

See `schemas.py` or data model files in this subsystem.

### Invariants

- **Agent IDs are UUIDv4 or registered agent names**
- **All agent tasks emit PacketEnvelope to memory substrate**
- **Kernel stack loaded via KernelLoader before execution**
- **Tool access mediated by RegistryAdapter with capability checks**
- **High-risk tools require Igor approval before dispatch**

## Configuration

### Feature Flags

```yaml
# Subsystem-specific feature flags
L9_ENABLE_AGENTS_TRACING: true
```

### Environment Variables

```bash
AGENTS_LOG_LEVEL=INFO
```

## API Surface (Public)

See key components for public API details.

## Observability

### Logging

Agents operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-18T07:50:15Z",
  "level": "INFO",
  "module": "core.agents",
  "message": "Operation completed",
  "correlation_id": "corr-xyz789"
}
```

### Metrics

- `agents_operation_duration_ms` — Operation latency (histogram)
- `agents_operation_total` — Total operations (counter)
- `agents_error_rate` — Error percentage (gauge)

## Testing

### Unit Tests

Located in `tests/core_agents/`:
- `test_agents.py` — Unit tests

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

- `adaptive_prompting.py` — Application logic
- `selfreflection.py` — Application logic
- `prompt_builder.py` — Application logic
- `bootstrap/**` — Application logic
- `graph_state/**` — Application logic

### ⚠️ Restricted Scopes (requires human review)

- Schema changes
- Feature flag logic

### ❌ Forbidden Scopes (never modify without approval)

- `executor.py` — PROTECTED
- `registry.py` — PROTECTED
- `__init__.py` — PROTECTED

### Required Pre-Reading

1. `README-L9_ARCHITECTURE.md` — System architecture
2. `docs/CURSOR-RUNBOOK.md` — AI collaboration rules
3. This file — Subsystem contracts

---

*L9 Secure AI OS — Agents Subsystem*
*Generated: 2026-01-18*
