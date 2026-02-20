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

# Domain Tensor Bridge

> **Tier:** SERVICES | **Path:** `domain_bridge` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                           Domain Tensor Bridge                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   domain_tens   │ ───► │  Outbound   │                  │
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

Bridge for domain-specific tensor operations and validation

**Purpose:** Provides tensor bridge infrastructure for domain-specific computations.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute domain tensor bridge tasks
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
domain_bridge/
├── __init__.py
├── agent_controller.py
├── analogical_reasoner.py
├── anomaly_handler.py
├── causal_reasoner.py
├── compliance_checker.py
├── context_enricher.py
├── decision_synthesizer.py
├── domain_context_builder.py
├── domain_packet_handler.py
├── embedding_processor.py
├── escalation_handler.py
├── governance_bridge.py
├── l9_memory_adapter.py
├── memory_bridge.py
└── ... (18 more files)
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `reasoning_engine.py` | Result from reasoning execution. |
| `reasoning_engine.py` | Multi-modal reasoning engine. |
| `l9_memory_adapter.py` | Concrete adapter wiring DTB's MemoryBridge to L9 s |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `DomainTensorBridgeService`)
- **Functions:** `snake_case` (e.g., `process_domain_bridge_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `reasoning_engine.py` — ReasoningResult

```python
class ReasoningResult:
    """Result from reasoning execution."""

    # Key methods:

```

**Lines:** 60-67 in `reasoning_engine.py`

### `reasoning_engine.py` — ReasoningEngine

```python
class ReasoningEngine:
    """Multi-modal reasoning engine."""

    # Key methods:

    def __init__(self, ...): ...

    async def initialize(self, ...) -> None: ...

    async def execute_reasoning(self, ...) -> ReasoningResult: ...

    async def apply_causal_reasoning(self, ...) -> dict[str, Any]: ...

    async def apply_analogical_reasoning(self, ...) -> dict[str, Any]: ...

```

**Public Methods:** `__init__`, `initialize`, `execute_reasoning`, `apply_causal_reasoning`, `apply_analogical_reasoning`

**Lines:** 70-260 in `reasoning_engine.py`

### `l9_memory_adapter.py` — L9MemoryAdapter

```python
class L9MemoryAdapter:
    """Concrete adapter wiring DTB's MemoryBridge to L9 services."""

    # Key methods:

    def __init__(self, ...) -> None: ...

    async def initialize(self, ...) -> None: ...

    async def get_working_memory(self, ...) -> dict[str, Any] | None: ...

    async def set_working_memory(self, ...) -> bool: ...

    async def query_episodic_memory(self, ...) -> list[EpisodicEvent]: ...

```

**Public Methods:** `__init__`, `initialize`, `get_working_memory`, `set_working_memory`, `query_episodic_memory`

**Lines:** 59-242 in `l9_memory_adapter.py`

### `embedding_processor.py` — ProcessedEmbedding

```python
class ProcessedEmbedding:
    """Processed embedding with metadata."""

    # Key methods:

```

**Lines:** 54-60 in `embedding_processor.py`

### `embedding_processor.py` — EmbeddingProcessor

```python
class EmbeddingProcessor:
    """Processes embeddings from tensor layer."""

    # Key methods:

    def process_embeddings(self, ...) -> ProcessedEmbedding: ...

    def _normalize(self, ...) -> list[float]: ...

    def compute_similarity(self, ...) -> float: ...

```

**Public Methods:** `process_embeddings`, `_normalize`, `compute_similarity`

**Lines:** 63-97 in `embedding_processor.py`


---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`AnomalyResponse`** — Response to anomaly.
- **`WorldModelBridge`** — Interface to world model layer.
- **`TestWorldModelQuery`** — Tests for world model querying.

### Exported Symbols (`__all__`)

`AgentController`, `AnalogicalReasoner`, `Analogy`, `AnomalyFlag`, `AnomalyHandler`, `AnomalyResponse`, `AnomalySeverity`, `AuditResult`, `CausalFactor`, `CausalReasoner`

*...and 43 more*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class DomainTensorBridgeRequest(BaseModel):
    """Request model for domain_bridge operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class DomainTensorBridgeResponse(BaseModel):
    """Response model for domain_bridge operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **All operations must be idempotent**
- **State changes logged to audit trail**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Domain_Tensor_Bridge components are discovered and registered.
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
# Domain_Tensor_Bridge feature flags
L9_ENABLE_DOMAIN_TENSOR_BRIDGE_TRACING: true  # Enable detailed tracing
L9_ENABLE_DOMAIN_TENSOR_BRIDGE_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_DOMAIN_TENSOR_BRIDGE_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
domain_bridge:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
DOMAIN_TENSOR_BRIDGE_LOG_LEVEL=INFO
DOMAIN_TENSOR_BRIDGE_TIMEOUT=30
DOMAIN_TENSOR_BRIDGE_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `async def process_packet(packet) -> PacketEnvelope`

Convenience function to process a packet using default controller.

- **File:** `agent_controller.py:200`
- **Async:** Yes
- **Returns:** `PacketEnvelope`

#### `def mock_packet()`

Create mock packet.

- **File:** `test_bridge_controller.py:16`
- **Async:** No

#### `def controller()`

Create controller with mocked dependencies.

- **File:** `test_bridge_controller.py:26`
- **Async:** No

#### `def memory_bridge()`

Create memory bridge with mocked substrate.

- **File:** `test_memory_integration.py:14`
- **Async:** No

#### `def controller()`

Create controller for API testing.

- **File:** `test_api_surfaces.py:13`
- **Async:** No


### Usage Example

```python
from domain_bridge import DomainTensorBridgeService

# Initialize
service = DomainTensorBridgeService()

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

Domain Tensor Bridge operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-17T00:14:44Z",
  "level": "INFO",
  "module": "domain_bridge",
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
| `domain_bridge_operation_duration_ms` | Histogram | Operation latency distribution |
| `domain_bridge_operation_total` | Counter | Total operations processed |
| `domain_bridge_error_total` | Counter | Total errors encountered |
| `domain_bridge_active_connections` | Gauge | Current active connections |

### Tracing

Domain Tensor Bridge emits OpenTelemetry spans:

- `domain_bridge.execute` — Root span for operation
  - `domain_bridge.validate` — Input validation
  - `domain_bridge.process` — Core processing
  - `domain_bridge.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/domain_bridge/`:
- `test_domain_bridge.py` — Core unit tests
- `test_domain_bridge_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test domain_bridge with real dependencies
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
