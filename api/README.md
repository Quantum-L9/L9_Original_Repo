# API Subsystem

## Overview

The **API Subsystem** is the HTTP and WebSocket interfaces for L9 Secure AI OS. It Exposes FastAPI endpoints for agent tasks, memory operations, and real-time communication.

**What depends on it:** External clients

## Responsibilities and Boundaries

### What This Module Owns

- See key components below for detailed responsibilities

### What This Module Does NOT Do

- Operations handled by other subsystems (see dependencies)

### Dependencies

| Direction | Module | Purpose |
|-----------|--------|---------|
| **Outbound** | `core/agents/executor.py` | Required dependency |
| **Outbound** | `memory/substrate_service.py` | Required dependency |

## Directory Layout

```
api/
├── __init__.py
├── agent_routes.py
├── auth.py
├── db.py
├── dependencies.py
├── e2e_slack_audit.py
├── llm.py
├── memory/__init__.py
├── memory/cache.py
├── memory/graph.py
├── memory/router.py
├── os_routes.py
├── routes/__init__.py
├── routes/commands.py
├── routes/compliance.py
└── ... (27 more files)
```

## Key Components

### `server.py` — KernelReloadRequest

```python
class KernelReloadRequest:
    """Request body for kernel reload."""
```

### `server.py` — KernelReloadResponse

```python
class KernelReloadResponse:
    """Response from kernel reload."""
```

### `server.py` — ChatRequest

```python
class ChatRequest:
    """No description"""
```

### `server.py` — ChatResponse

```python
class ChatResponse:
    """No description"""
```

### `server.py` — LChatRequest

```python
class LChatRequest:
    """Request for L-CTO agent chat via AgentExecutorService."""
```


## Data Models and Contracts

See `schemas.py` or data model files in this subsystem.

### Invariants

- **Request/response schemas validated via Pydantic**
- **All logging is structured JSON with context (agent_id, task_id)**
- **WebSocket routes use websocket_orchestrator for lifecycle**
- **Rate limiting enforced via RateLimiter with Redis backend**

## Configuration

### Feature Flags

```yaml
# Subsystem-specific feature flags
L9_ENABLE_API_TRACING: true
```

### Environment Variables

```bash
API_LOG_LEVEL=INFO
```

## API Surface (Public)

See key components for public API details.

## Observability

### Logging

Api operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-18T07:50:15Z",
  "level": "INFO",
  "module": "api",
  "message": "Operation completed",
  "correlation_id": "corr-xyz789"
}
```

### Metrics

- `api_operation_duration_ms` — Operation latency (histogram)
- `api_operation_total` — Total operations (counter)
- `api_error_rate` — Error percentage (gauge)

## Testing

### Unit Tests

Located in `tests/api/`:
- `test_api.py` — Unit tests

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

- `routes/*.py` — Application logic
- `agent_routes.py` — Application logic
- `os_routes.py` — Application logic
- `memory/*.py` — Application logic

### ⚠️ Restricted Scopes (requires human review)

- Schema changes
- Feature flag logic

### ❌ Forbidden Scopes (never modify without approval)

- `server.py` — PROTECTED
- `auth.py` — PROTECTED
- `__init__.py` — PROTECTED

### Required Pre-Reading

1. `README-L9_ARCHITECTURE.md` — System architecture
2. `docs/CURSOR-RUNBOOK.md` — AI collaboration rules
3. This file — Subsystem contracts

---

*L9 Secure AI OS — API Subsystem*
*Generated: 2026-01-18*
