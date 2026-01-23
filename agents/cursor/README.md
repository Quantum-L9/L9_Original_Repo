# Cursor Module

## Overview

The **Cursor Module** is the module at `agents/cursor`. It provides functionality as documented in the key components below.

**What depends on it:** External clients

## Responsibilities and Boundaries

### What This Module Owns

- See key components below for detailed responsibilities

### What This Module Does NOT Do

- Operations handled by other subsystems (see dependencies)

### Dependencies

| Direction | Module | Purpose |
|-----------|--------|---------|
| — | — | No external dependencies |

## Directory Layout

```
agents/cursor/
├── __init__.py
├── cursor_client.py
├── cursor_memory_client.py
├── cursor_memory_kernel.py
├── cursor_neo4j_query.py
├── extractors/__init__.py
├── extractors/cursor_action_extractor.py
├── gmp-v2-prompts/GMP-Engine.py
├── gmp_meta_learning.py
├── integrations/__init__.py
├── integrations/cursor_executor.py
├── integrations/cursor_gateway.py
├── integrations/cursor_langgraph.py
├── scripts/__init__.py
├── scripts/cursor_check_mistakes.py
```

## Key Components

### `cursor_client.py` — CursorClient

```python
class CursorClient:
    """Client for Cursor remote API."""
```

**Methods:** `__init__`, `_request`, `send_code`, `send_command`, `health_check`

### `gmp_meta_learning.py` — AutonomyLevel

```python
class AutonomyLevel:
    """Graduated autonomy levels in GMP v2.0."""
```

### `gmp_meta_learning.py` — GMPExecutionResult

```python
class GMPExecutionResult:
    """Results from a completed GMP execution."""
```

### `gmp_meta_learning.py` — LearnedHeuristic

```python
class LearnedHeuristic:
    """A heuristic pattern learned from prior executions."""
```

**Methods:** `__hash__`

### `gmp_meta_learning.py` — AutonomyGraduationMetrics

```python
class AutonomyGraduationMetrics:
    """Tracks metrics for autonomy level graduation."""
```


## Data Models and Contracts

See `schemas.py` or data model files in this subsystem.

### Invariants

- **No invariants defined**

## Configuration

### Feature Flags

```yaml
# Subsystem-specific feature flags
L9_ENABLE_AGENTS_CURSOR_TRACING: true
```

### Environment Variables

```bash
AGENTS_CURSOR_LOG_LEVEL=INFO
```

## API Surface (Public)

See key components for public API details.

## Observability

### Logging

Agents_cursor operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-18T07:52:23Z",
  "level": "INFO",
  "module": "agents.cursor",
  "message": "Operation completed",
  "correlation_id": "corr-xyz789"
}
```

### Metrics

- `agents_cursor_operation_duration_ms` — Operation latency (histogram)
- `agents_cursor_operation_total` — Total operations (counter)
- `agents_cursor_error_rate` — Error percentage (gauge)

## Testing

### Unit Tests

Located in `tests/agents_cursor/`:
- `test_agents_cursor.py` — Unit tests

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

- `**/*.py` — Application logic

### ⚠️ Restricted Scopes (requires human review)

- Schema changes
- Feature flag logic

### ❌ Forbidden Scopes (never modify without approval)

- `__init__.py` — PROTECTED

### Required Pre-Reading

1. `README-L9_ARCHITECTURE.md` — System architecture
2. `docs/CURSOR-RUNBOOK.md` — AI collaboration rules
3. This file — Subsystem contracts

---

*L9 Secure AI OS — Cursor Module*
*Generated: 2026-01-18*
