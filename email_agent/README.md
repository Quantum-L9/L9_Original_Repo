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

# Email Agent

> **Tier:** AGENTS | **Path:** `email_agent` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                               Email Agent                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   email_agent   │ ───► │  Outbound   │                  │
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

Gmail integration agent for email triage and processing

**Purpose:** Handles email triage, OAuth authentication, and email-to-task conversion.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute email agent tasks
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

---

## Directory Layout

```
email_agent/
├── __init__.py
├── client.py
├── config.py
├── credentials.py
├── gmail_client.py
├── oauth_server.py
├── parser.py
├── router.py
├── triage.py
```

| File | Purpose |
|------|---------|
| `credentials.py` | Core module (PROTECTED) |
| `__init__.py` | Core module (PROTECTED) |
| `config.py` | Configuration for a Gmail account. |
| `gmail_client.py` | Gmail API client wrapper with multi-account suppor |
| `oauth_server.py` | HTTP handler for OAuth flow. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `EmailAgentService`)
- **Functions:** `snake_case` (e.g., `process_email_agent_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `config.py` — AccountConfig

```python
class AccountConfig:
    """Configuration for a Gmail account."""
    
    # Key methods:

    async def __post_init__(self, ...): ...

    async def tokens_file(self, ...): ...

    async def client_secret_file(self, ...): ...

    async def attachments_dir(self, ...): ...

```

**Public Methods:** `__post_init__`, `tokens_file`, `client_secret_file`, `attachments_dir`

**Lines:** 49-78 in `config.py`

### `gmail_client.py` — GmailClient

```python
class GmailClient:
    """Gmail API client wrapper with multi-account support."""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def _authenticate(self, ...): ...

    async def list_messages(self, ...): ...

    async def get_message(self, ...): ...

    async def send_email(self, ...): ...

```

**Public Methods:** `__init__`, `_authenticate`, `list_messages`, `get_message`, `send_email`

**Lines:** 104-668 in `gmail_client.py`

### `oauth_server.py` — OAuthHandler

```python
class OAuthHandler:
    """HTTP handler for OAuth flow."""
    
    # Key methods:

    async def do_GET(self, ...): ...

    async def handle_start(self, ...): ...

    async def handle_callback(self, ...): ...

    async def log_message(self, ...): ...

```

**Public Methods:** `do_GET`, `handle_start`, `handle_callback`, `log_message`

**Lines:** 57-184 in `oauth_server.py`

### `parser.py` — HTMLToTextParser

```python
class HTMLToTextParser:
    """No description"""
    
    # Key methods:

    async def __init__(self, ...): ...

    async def handle_starttag(self, ...): ...

    async def handle_endtag(self, ...): ...

    async def handle_data(self, ...): ...

    async def get_text(self, ...): ...

```

**Public Methods:** `__init__`, `handle_starttag`, `handle_endtag`, `handle_data`, `get_text`

**Lines:** 266-303 in `parser.py`

### `router.py` — QueryRequest

```python
class QueryRequest:
    """Request model for email query."""
    
    # Key methods:

```

**Lines:** 93-97 in `router.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`QueryRequest`** — Request model for email query.
- **`GetRequest`** — Request model for getting email.
- **`DraftRequest`** — Request model for email draft.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EmailAgentRequest(BaseModel):
    """Request model for email_agent operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class EmailAgentResponse(BaseModel):
    """Response model for email_agent operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **OAuth tokens refreshed automatically**
- **Credentials never logged**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Email_Agent components are discovered and registered.
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
# Email_Agent feature flags
L9_ENABLE_EMAIL_AGENT_TRACING: true  # Enable detailed tracing
L9_ENABLE_EMAIL_AGENT_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_EMAIL_AGENT_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
email_agent:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
EMAIL_AGENT_LOG_LEVEL=INFO
EMAIL_AGENT_TIMEOUT=30
EMAIL_AGENT_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def get_account_config(account)`

Get account configuration by name.

- **File:** `config.py:130`
- **Async:** No

#### `def ensure_dirs(account)`

Ensure all required directories exist.

- **File:** `config.py:148`
- **Async:** No

#### `def load_client_secrets(account)`

Load OAuth client secrets.

- **File:** `credentials.py:61`
- **Async:** No

#### `def create_flow(redirect_uri, account)`

Create OAuth2 flow for Gmail authentication.

- **File:** `credentials.py:96`
- **Async:** No

#### `def exchange_code_for_tokens(authorization_code, redirect_uri, account)`

Exchange authorization code for access/refresh tokens.

- **File:** `credentials.py:134`
- **Async:** No


### Usage Example

```python
from email_agent import EmailAgentService

# Initialize
service = EmailAgentService()

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

Email Agent operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "email_agent",
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
| `email_agent_operation_duration_ms` | Histogram | Operation latency distribution |
| `email_agent_operation_total` | Counter | Total operations processed |
| `email_agent_error_total` | Counter | Total errors encountered |
| `email_agent_active_connections` | Gauge | Current active connections |

### Tracing

Email Agent emits OpenTelemetry spans:

- `email_agent.execute` — Root span for operation
  - `email_agent.validate` — Input validation
  - `email_agent.process` — Core processing
  - `email_agent.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/email_agent/`:
- `test_email_agent.py` — Core unit tests
- `test_email_agent_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test email_agent with real dependencies
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

- `gmail_client.py` — Application logic, safe to modify
- `parser.py` — Application logic, safe to modify
- `triage.py` — Application logic, safe to modify
- `router.py` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `credentials.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `credentials.py` — PROTECTED: Changes break system invariants
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
