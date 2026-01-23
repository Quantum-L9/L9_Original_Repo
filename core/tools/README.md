# Tools Subsystem

## Overview

The **Tools Subsystem** is the Tool registry and dispatch for L9 Secure AI OS. It Manages tool definitions, capability enforcement, and safe tool invocation.

**What depends on it:** `core/agents/executor.py`

## Responsibilities and Boundaries

### What This Module Owns

- See key components below for detailed responsibilities

### What This Module Does NOT Do

- Operations handled by other subsystems (see dependencies)

### Dependencies

| Direction | Module | Purpose |
|-----------|--------|---------|
| **Outbound** | `runtime/l_tools.py` | Required dependency |
| **Outbound** | `core/governance/approval_manager.py` | Required dependency |
| **Inbound** | `core/agents/executor.py` | Uses this module |

## Directory Layout

```
core/tools/
├── __init__.py
├── agent_self_modify.py
├── base_registry.py
├── memory_tools.py
├── reflection_tools.py
├── registry_adapter.py
├── research_tools.py
├── sanitizer.py
├── symbolic_tool.py
├── tool_audit.py
├── tool_embeddings.py
├── tool_graph.py
```

## Key Components

### `tool_embeddings.py` — ToolEmbeddingResult

```python
class ToolEmbeddingResult:
    """Result from tool embedding search."""
```

### `sanitizer.py` — ToolInputSanitizationError

```python
class ToolInputSanitizationError:
    """Raised when tool input cannot be sanitized/validated."""
```

**Methods:** `__init__`

### `sanitizer.py` — ToolInputSanitizerConfig

```python
class ToolInputSanitizerConfig:
    """No description"""
```

### `sanitizer.py` — ToolInputSanitizer

```python
class ToolInputSanitizer:
    """Centralized input sanitization for tool arguments."""
```

**Methods:** `__init__`, `sanitize`, `_sanitize_value`, `_enforce_resource_limits`, `_exceeds_depth`

### `tool_audit.py` — ToolAuditEntry

```python
class ToolAuditEntry:
    """Record of single tool execution"""
```

**Methods:** `__post_init__`


## Data Models and Contracts

See `schemas.py` or data model files in this subsystem.

### Invariants

- **Tool names must exist in L_TOOLS_DEFINITIONS registry**
- **Destructive tools require explicit approval gates**
- **All tool executions logged to PacketEnvelope audit trail**
- **Tool dispatch respects AgentCapabilities enum**

## Configuration

### Feature Flags

```yaml
# Subsystem-specific feature flags
L9_ENABLE_TOOLS_TRACING: true
```

### Environment Variables

```bash
TOOLS_LOG_LEVEL=INFO
```

## API Surface (Public)

See key components for public API details.

## Observability

### Logging

Tools operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-18T07:50:15Z",
  "level": "INFO",
  "module": "core.tools",
  "message": "Operation completed",
  "correlation_id": "corr-xyz789"
}
```

### Metrics

- `tools_operation_duration_ms` — Operation latency (histogram)
- `tools_operation_total` — Total operations (counter)
- `tools_error_rate` — Error percentage (gauge)

## Testing

### Unit Tests

Located in `tests/core_tools/`:
- `test_tools.py` — Unit tests

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

- `sanitizer.py` — Application logic
- `memory_tools.py` — Application logic
- `research_tools.py` — Application logic
- `reflection_tools.py` — Application logic

### ⚠️ Restricted Scopes (requires human review)

- Schema changes
- Feature flag logic

### ❌ Forbidden Scopes (never modify without approval)

- `registry_adapter.py` — PROTECTED
- `tool_graph.py` — PROTECTED
- `__init__.py` — PROTECTED

### Required Pre-Reading

1. `README-L9_ARCHITECTURE.md` — System architecture
2. `docs/CURSOR-RUNBOOK.md` — AI collaboration rules
3. This file — Subsystem contracts

---

*L9 Secure AI OS — Tools Subsystem*
*Generated: 2026-01-18*
