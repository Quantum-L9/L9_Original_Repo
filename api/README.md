---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "2026-02-17 00:14:44 UTC"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "system clock (verification skipped)"
  auto_generated: true
---

# API Gateway

> **Tier:** API | **Path:** `api` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                               API Gateway                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │       api       │ ───► │  Outbound   │                  │
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

HTTP and WebSocket interfaces for L9 Secure AI OS

**Purpose:** Exposes FastAPI endpoints for agent tasks, memory operations, and real-time communication.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- HTTP endpoint routing and handling
- WebSocket connection management
- Request/response validation
- Authentication and authorization
- Rate limiting enforcement
- Structured logging with context

### What This Module Does NOT Do

- Agent execution logic (owned by core/agents)
- Memory storage (owned by memory/)
- Tool execution (owned by core/tools)

### Inbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No inbound dependencies |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| `core/agents/executor.py` | Required dependency |
| `memory/substrate_service.py` | Required dependency |
| `runtime/websocket_orchestrator.py` | Required dependency |

---

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
├── middleware/__init__.py
├── middleware/websocket_tracing.py
├── openapi_config.py
├── os_routes.py
└── ... (35 more files)
```

| File | Purpose |
|------|---------|
| `server.py` | FastAPI app initialization, route registration (PROTECTED) |
| `auth.py` | Authentication and authorization middleware (PROTECTED) |
| `agent_routes.py` | Agent execution endpoints (/agents, /tasks) |
| `os_routes.py` | OS-level operations and health checks |
| `routes/` | Domain-specific route modules |
| `memory/router.py` | Memory API endpoints (/memory/search, /memory/ingest) |
| `tools/router.py` | Tool API endpoints (/tools/invoke) |

### Naming Conventions

- **Routes:** kebab-case paths (e.g., `/api/agent-tasks`)
- **Handlers:** `async def verb_noun()` (e.g., `async def create_task()`)
- **Request models:** `<Noun><Verb>Request` (e.g., `TaskCreateRequest`)
- **Response models:** `<Noun><Verb>Response` (e.g., `TaskCreateResponse`)

---

## Key Components

### `auth.py` — CallerIdentity

```python
class CallerIdentity:
    """Represents the identity of a caller in the authentication system, including their scope and source information."""

    # Key methods:

```

**Lines:** 51-71 in `auth.py`

### `server.py` — KernelReloadRequest

```python
class KernelReloadRequest:
    """Request body for kernel reload."""

    # Key methods:

```

**Lines:** 3040-3043 in `server.py`

### `server.py` — KernelReloadResponse

```python
class KernelReloadResponse:
    """Response from kernel reload."""

    # Key methods:

```

**Lines:** 3046-3053 in `server.py`

### `server.py` — ChatRequest

```python
class ChatRequest:
    """Represents a chat request message for the L9 Secure AI OS API."""

    # Key methods:

```

**Lines:** 3372-3388 in `server.py`

### `server.py` — ChatResponse

```python
class ChatResponse:
    """Represents a chat response message in the L9 AI OS API."""

    # Key methods:

```

**Lines:** 3391-3399 in `server.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`KernelReloadRequest`** — Request body for kernel reload.
- **`KernelReloadResponse`** — Response from kernel reload.
- **`ChatRequest`** — Represents a chat request message for the L9 Secure AI OS API.

### Exported Symbols (`__all__`)

`TraceContext`, `WebSocketTracingMiddleware`, `get_agent_executor`, `get_aios_runtime`, `get_anomaly_monitor`, `get_consolidation_service`, `get_evaluator`, `get_governance_engine`, `get_memory_state_manager`, `get_neo4j_client`

*...and 11 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `EXECUTOR_API_KEY_L` | `os.environ.get('L9_EXECUTOR_API_KEY_L')` | 44 |
| `EXECUTOR_API_KEY_C` | `os.environ.get('L9_EXECUTOR_API_KEY_C') ...` | 45 |
| `MEMORY_DSN` | `os.getenv('MEMORY_DSN', os.getenv('DATAB...` | 31 |
| `L9_NEW_AGENT_INIT` | `settings.l9_new_agent_init` | 347 |
| `L9_STAGE3_MODULES` | `settings.l9_stage3_modules` | 348 |
| `L9_GRAPH_AGENT_STATE` | `settings.l9_graph_agent_state` | 349 |
| `L9_OBSERVABILITY` | `settings.l9_observability` | 371 |
| `LOCAL_DEV` | `settings.local_dev` | 478 |

*...and 35 more constants*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class ApiRequest(BaseModel):
    """Request model for api operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class ApiResponse(BaseModel):
    """Response model for api operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Request/response schemas validated via Pydantic**
- **All logging is structured JSON with context (agent_id, task_id)**
- **WebSocket routes use websocket_orchestrator for lifecycle**
- **Rate limiting enforced via RateLimiter with Redis backend**

---

## Execution and Lifecycle

### Startup

1. **App creation:** FastAPI app initialized.
2. **Middleware:** CORS, auth, logging middleware registered.
3. **Routes:** All routers mounted to app.
4. **Lifespan:** Startup events connect to Redis, PostgreSQL.


### Main Execution

1. **Request:** Receive HTTP/WebSocket request.
2. **Auth:** Validate JWT token (if required).
3. **Rate check:** Verify rate limit not exceeded.
4. **Dispatch:** Route to handler, execute, return response.


### Shutdown

1. **Drain:** Stop accepting new requests.
2. **Pending:** Wait for in-flight requests to complete.
3. **Cleanup:** Close database pools, Redis connections.
4. **Log:** Emit graceful shutdown event.


### Background Tasks

Background tasks via Starlette BackgroundTasks for non-blocking operations.

---

## Configuration

### Feature Flags

```yaml
# Api feature flags
L9_ENABLE_API_TRACING: true  # Enable detailed tracing
L9_ENABLE_API_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_API_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
api:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
API_LOG_LEVEL=INFO
API_TIMEOUT=30
API_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def verify_api_key(authorization) -> CallerIdentity`

Verify API key and return caller identity.

- **File:** `auth.py:74`
- **Async:** No
- **Returns:** `CallerIdentity`

#### `async def verify_api_key_with_rate_limit(request, authorization) -> CallerIdentity`

Verify API key with rate limiting protection.

- **File:** `auth.py:107`
- **Async:** Yes
- **Returns:** `CallerIdentity`

#### `async def os_health()`

Health check for OS layer.

- **File:** `os_routes.py:46`
- **Async:** Yes

#### `async def os_status()`

System status endpoint.

- **File:** `os_routes.py:53`
- **Async:** Yes

#### `async def os_readiness()`

Readiness probe endpoint.

- **File:** `os_routes.py:67`
- **Async:** Yes


### Usage Example

```python
# HTTP Example
import httpx

async with httpx.AsyncClient() as client:
    # Execute an agent task
    response = await client.post(
        "http://localhost:8000/api/agents/researcher/execute",
        json={
            "goal": "Analyze AI market trends",
            "context": {"recent_data": [...]},
        },
        headers={"Authorization": "Bearer <token>"},
    )
    result = response.json()
    print(result["output"])

# WebSocket Example
import websockets

async with websockets.connect("ws://localhost:8000/ws") as ws:
    await ws.send(json.dumps({
        "type": "agent.execute",
        "agent_id": "researcher",
        "goal": "Find AI trends",
    }))
    response = await ws.recv()
    print(json.loads(response))
```


---

## Observability

### Logging

Api operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-17T00:14:44Z",
  "level": "INFO",
  "module": "api",
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
| `api_operation_duration_ms` | Histogram | Operation latency distribution |
| `api_operation_total` | Counter | Total operations processed |
| `api_error_total` | Counter | Total errors encountered |
| `api_active_connections` | Gauge | Current active connections |

### Tracing

Api emits OpenTelemetry spans:

- `api.execute` — Root span for operation
  - `api.validate` — Input validation
  - `api.process` — Core processing
  - `api.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/api/`:
- `test_api.py` — Core unit tests
- `test_api_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test api with real dependencies
- Test cross-subsystem interactions
- Test failure scenarios and recovery

### Known Edge Cases

1. **Invalid request body** — Pydantic validation fails → 422 with validation errors
1. **Authentication failure** — Invalid/expired JWT → 401 Unauthorized
1. **Rate limit exceeded** — Too many requests → 429 with retry-after header
1. **Agent timeout** — Agent execution exceeds timeout → 504 Gateway Timeout
1. **WebSocket disconnect** — Client disconnects unexpectedly → cleanup resources, log event

---

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

- `routes/**` — Application logic, safe to modify
- `agent_routes.py` — Application logic, safe to modify
- `os_routes.py` — Application logic, safe to modify
- `memory/**` — Application logic, safe to modify
- `tools/**` — Application logic, safe to modify
- `tests/**` — Application logic, safe to modify
- `docs/**` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `server.py` — Requires human review before merge
- `auth.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `server.py` — PROTECTED: Changes break system invariants
- `auth.py` — PROTECTED: Changes break system invariants
- `__init__.py` — PROTECTED: Changes break system invariants

### Required Pre-Reading

1. [`README-L9_ARCHITECTURE.md`](README-L9_ARCHITECTURE.md)
2. [`docs/CURSOR-RUNBOOK.md`](docs/CURSOR-RUNBOOK.md)
3. [`api/README.md`](api/README.md)

### Change Policy

All changes proposed by AI tools must:
1. Be scoped PRs with clear commit messages
2. Include tests (unit + integration where applicable)
3. Update documentation if APIs change
4. Respect feature flags for gradual rollout
5. Get human approval for restricted scopes
