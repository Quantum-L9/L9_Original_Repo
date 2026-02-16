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

# Core Schemas

> **Tier:** CORE | **Path:** `core/schemas` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                               Core Schemas                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_schema   │ ───► │  Outbound   │                  │
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

JSON schemas and validation utilities

**Purpose:** Provides schema validation for configurations and data.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core schemas tasks
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
| — | No outbound dependencies |

---

## Directory Layout

```
core/schemas/
├── __init__.py
├── capabilities.py
├── event_stream.py
├── hypergraph.py
├── l_tools.py
├── packet_envelope.py
├── packet_envelope_v2.py
├── research_factory_models.py
├── research_factory_nodes.py
├── research_factory_state.py
├── schema_registry.py
├── tasks.py
├── tests/__init__.py
├── tests/test_discriminators.py
├── tests/test_packet_envelope.py
└── ... (5 more files)
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `packet_envelope.py` | Kind of packet for routing/classification. |
| `packet_envelope.py` | Token usage tracking for LLM calls. |
| `packet_envelope.py` | Simple text content wrapper. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreSchemasService`)
- **Functions:** `snake_case` (e.g., `process_core_schemas_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `packet_envelope.py` — PacketKind

```python
class PacketKind:
    """Kind of packet for routing/classification."""

    # Key methods:

```

**Lines:** 85-93 in `packet_envelope.py`

### `packet_envelope.py` — TokenUsage

```python
class TokenUsage:
    """Token usage tracking for LLM calls."""

    # Key methods:

```

**Lines:** 101-108 in `packet_envelope.py`

### `packet_envelope.py` — SimpleContent

```python
class SimpleContent:
    """Simple text content wrapper."""

    # Key methods:

```

**Lines:** 111-117 in `packet_envelope.py`

### `packet_envelope.py` — StructuredReasoningBlock

```python
class StructuredReasoningBlock:
    """Structured reasoning output from LLM."""

    # Key methods:

```

**Lines:** 120-128 in `packet_envelope.py`

### `packet_envelope.py` — PacketConfidence

```python
class PacketConfidence:
    """Confidence score and rationale for a packet."""

    # Key methods:

```

**Lines:** 136-144 in `packet_envelope.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`SemanticSearchRequest`** — Request to search semantic memory.
- **`InvalidSchemaVersionError`** — Raised when a schema version is malformed or unsupported.
- **`_SchemaRegistry`** — Central registry for PacketEnvelope schema versions and upcasters.

### Exported Symbols (`__all__`)

`AgentCapabilities`, `AgentHandshake`, `AgentHeartbeat`, `AgentTask`, `Capability`, `CapabilityViolation`, `DEFAULT_ARCHITECT_CAPABILITIES`, `DEFAULT_CODER_CAPABILITIES`, `DEFAULT_L_CAPABILITIES`, `DEFAULT_READER_CAPABILITIES`

*...and 62 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `SCHEMA_VERSION` | `'1.0.1'` | 132 |
| `MODULE_VERSION` | `'1.0.0'` | 133 |
| `GENERATED_BY` | `'L9_MASTER_SCHEMA_EXTRACTOR v3.0'` | 134 |
| `SOURCE_SCHEMAS` | `['Memory.yaml (packet_envelope.v1.0.1, a...` | 135 |
| `DEFAULT_READER_CAPABILITIES` | `AgentCapabilities(agent_id='default_read...` | 221 |
| `DEFAULT_CODER_CAPABILITIES` | `AgentCapabilities(agent_id='default_code...` | 231 |
| `DEFAULT_ARCHITECT_CAPABILITIES` | `AgentCapabilities(agent_id='default_arch...` | 246 |
| `DEFAULT_L_CAPABILITIES` | `AgentCapabilities(agent_id='L', capabili...` | 260 |

*...and 6 more constants*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class CoreSchemasRequest(BaseModel):
    """Request model for core_schemas operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreSchemasResponse(BaseModel):
    """Response model for core_schemas operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Schemas are JSON Schema compliant**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Schemas components are discovered and registered.
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
# Core_Schemas feature flags
L9_ENABLE_CORE_SCHEMAS_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_SCHEMAS_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_SCHEMAS_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_schemas:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_SCHEMAS_LOG_LEVEL=INFO
CORE_SCHEMAS_TIMEOUT=30
CORE_SCHEMAS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def pass_1_plan_queries(state) -> ResearchState`

Pass 1 — Derive research plan from job specification.

- **File:** `research_factory_nodes.py:75`
- **Async:** Yes
- **Returns:** `ResearchState`

#### `async def pass_2_build_superprompts(state) -> ResearchState`

Pass 2 — Construct optimized prompts from query plan.

- **File:** `research_factory_nodes.py:154`
- **Async:** Yes
- **Returns:** `ResearchState`

#### `async def pass_3_execute_retrieval(state, retrieval_backend) -> ResearchState`

Pass 3 — Call research backend(s) with superprompts.

- **File:** `research_factory_nodes.py:223`
- **Async:** Yes
- **Returns:** `ResearchState`

#### `async def pass_4_extract_results(state, extraction_backend) -> ResearchState`

Pass 4 — Transform raw JSON into validated objects.

- **File:** `research_factory_nodes.py:291`
- **Async:** Yes
- **Returns:** `ResearchState`

#### `async def pass_5_integrate_results(state) -> ResearchState`

Pass 5 — Persist output to hypergraph and world model.

- **File:** `research_factory_nodes.py:369`
- **Async:** Yes
- **Returns:** `ResearchState`


### Usage Example

```python
from core.schemas import CoreSchemasService

# Initialize
service = CoreSchemasService()

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

Core Schemas operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-14T08:25:39Z",
  "level": "INFO",
  "module": "core.schemas",
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
| `core_schemas_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_schemas_operation_total` | Counter | Total operations processed |
| `core_schemas_error_total` | Counter | Total errors encountered |
| `core_schemas_active_connections` | Gauge | Current active connections |

### Tracing

Core Schemas emits OpenTelemetry spans:

- `core_schemas.execute` — Root span for operation
  - `core_schemas.validate` — Input validation
  - `core_schemas.process` — Core processing
  - `core_schemas.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_schemas/`:
- `test_core_schemas.py` — Core unit tests
- `test_core_schemas_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_schemas with real dependencies
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
