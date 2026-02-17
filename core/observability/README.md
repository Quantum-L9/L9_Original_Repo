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

# Observability

> **Tier:** CORE | **Path:** `core/observability` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                              Observability                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_observ   │ ───► │  Outbound   │                  │
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

Metrics, tracing, and structured logging

**Purpose:** Provides observability infrastructure for metrics, tracing, and logging.

**What depends on it:** `all modules`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core observability tasks
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
| `all modules` | Uses this module |

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
| — | No outbound dependencies |

---

## Directory Layout

```
core/observability/
├── __init__.py
├── aggregation.py
├── circuit_breaker.py
├── config.py
├── context_strategies.py
├── exporters.py
├── failures.py
├── instrumentation.py
├── jaeger_exporter.py
├── l9_integration.py
├── models.py
├── observability_context.py
├── prometheus_exporter.py
├── security_alerts.py
├── security_metrics.py
└── ... (1 more files)
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `prometheus_exporter.py` | Exports Five-Tier Observability metrics to Prometh |
| `jaeger_exporter.py` | Exports spans to Jaeger via OTLP. |
| `service.py` | Main service for observability subsystem. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreObservabilityService`)
- **Functions:** `snake_case` (e.g., `process_core_observability_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `prometheus_exporter.py` — ObservabilityPrometheusExporter

```python
class ObservabilityPrometheusExporter:
    """Exports Five-Tier Observability metrics to Prometheus."""

    # Key methods:

    def __init__(self, ...): ...

    def record_tech_debt_finding(self, ...) -> None: ...

    def record_tech_debt_fix(self, ...) -> None: ...

    def update_noqa_debt(self, ...) -> None: ...

    def record_span(self, ...) -> None: ...

```

**Public Methods:** `__init__`, `record_tech_debt_finding`, `record_tech_debt_fix`, `update_noqa_debt`, `record_span`

**Lines:** 46-355 in `prometheus_exporter.py`

### `jaeger_exporter.py` — JaegerExporter

```python
class JaegerExporter:
    """Exports spans to Jaeger via OTLP."""

    # Key methods:

    def __init__(self, ...): ...

    def export_span(self, ...) -> None: ...

    def _map_span_kind(self, ...) -> Any: ...

    def export(self, ...) -> None: ...

    async def export_async(self, ...) -> None: ...

```

**Public Methods:** `__init__`, `export_span`, `_map_span_kind`, `export`, `export_async`

**Lines:** 58-239 in `jaeger_exporter.py`

### `service.py` — ObservabilityService

```python
class ObservabilityService:
    """Main service for observability subsystem."""

    # Key methods:

    def __init__(self, ...): ...

    def _setup_logging(self, ...) -> None: ...

    def get(self, ...) -> Optional['ObservabilityService']: ...

    def set_global(self, ...) -> None: ...

    async def initialize_exporters(self, ...) -> None: ...

```

**Public Methods:** `__init__`, `_setup_logging`, `get`, `set_global`, `initialize_exporters`

**Lines:** 50-374 in `service.py`

### `aggregation.py` — MetricsAggregator

```python
class MetricsAggregator:
    """Aggregates spans into SRE metrics and KPIs."""

    # Key methods:

    def compute_sre_metrics(self, ...) -> dict[str, Any]: ...

    def compute_agent_kpis(self, ...) -> dict[str, float]: ...

    def detect_regressions(self, ...) -> list[dict[str, Any]]: ...

    def compute_cost_breakdown(self, ...) -> dict[str, float]: ...

```

**Public Methods:** `compute_sre_metrics`, `compute_agent_kpis`, `detect_regressions`, `compute_cost_breakdown`

**Lines:** 39-188 in `aggregation.py`

### `aggregation.py` — KPITracker

```python
class KPITracker:
    """Tracks KPI history for trending and alerting."""

    # Key methods:

    def __init__(self, ...): ...

    def record_kpi(self, ...) -> None: ...

    def get_trend(self, ...) -> str | None: ...

    def get_alerts(self, ...) -> list[dict[str, Any]]: ...

```

**Public Methods:** `__init__`, `record_kpi`, `get_trend`, `get_alerts`

**Lines:** 191-258 in `aggregation.py`


---

## Data Models and Contracts


### Exported Symbols (`__all__`)

`AdaptiveStrategySelector`, `AgentKPI`, `AgentTrajectorySpan`, `AsyncSpanExporter`, `CircuitBreaker`, `CircuitBreakerConfig`, `CircuitBreakerState`, `CircuitOpenError`, `CompositeExporter`, `ConsoleExporter`

*...and 56 more*

### Module Constants

| Constant | Value | Line |
|----------|-------|------|
| `T` | `TypeVar('T')` | 46 |
| `FAILURE_RECOVERY_MAP` | `{FailureClass.TOOL_TIMEOUT: [Remediation...` | 229 |

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class CoreObservabilityRequest(BaseModel):
    """Request model for core_observability operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreObservabilityResponse(BaseModel):
    """Response model for core_observability operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **All logs are structured JSON**
- **Metrics follow Prometheus conventions**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Observability components are discovered and registered.
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
# Core_Observability feature flags
L9_ENABLE_CORE_OBSERVABILITY_TRACING: true  # Enable detailed tracing
L9_ENABLE_CORE_OBSERVABILITY_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_CORE_OBSERVABILITY_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
core_observability:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_OBSERVABILITY_LOG_LEVEL=INFO
CORE_OBSERVABILITY_TIMEOUT=30
CORE_OBSERVABILITY_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def get_exporter() -> ObservabilityPrometheusExporter | None`

Get the global Prometheus exporter instance.

- **File:** `prometheus_exporter.py:362`
- **Async:** No
- **Returns:** `ObservabilityPrometheusExporter | None`

#### `def initialize_exporter() -> ObservabilityPrometheusExporter | None`

Initialize the global Prometheus exporter.

- **File:** `prometheus_exporter.py:367`
- **Async:** No
- **Returns:** `ObservabilityPrometheusExporter | None`

#### `def get_jaeger_exporter() -> JaegerExporter | None`

Get the global Jaeger exporter instance.

- **File:** `jaeger_exporter.py:246`
- **Async:** No
- **Returns:** `JaegerExporter | None`

#### `def initialize_jaeger_exporter(jaeger_endpoint, service_name) -> JaegerExporter | None`

Initialize the global Jaeger exporter.

- **File:** `jaeger_exporter.py:251`
- **Async:** No
- **Returns:** `JaegerExporter | None`

#### `async def initialize_observability(config, substrate_service) -> ObservabilityService`

Initialize and return global observability service.

- **File:** `service.py:377`
- **Async:** Yes
- **Returns:** `ObservabilityService`


### Usage Example

```python
from core.observability import CoreObservabilityService

# Initialize
service = CoreObservabilityService()

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

Core Observability operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-17T00:14:44Z",
  "level": "INFO",
  "module": "core.observability",
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
| `core_observability_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_observability_operation_total` | Counter | Total operations processed |
| `core_observability_error_total` | Counter | Total errors encountered |
| `core_observability_active_connections` | Gauge | Current active connections |

### Tracing

Core Observability emits OpenTelemetry spans:

- `core_observability.execute` — Root span for operation
  - `core_observability.validate` — Input validation
  - `core_observability.process` — Core processing
  - `core_observability.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_observability/`:
- `test_core_observability.py` — Core unit tests
- `test_core_observability_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_observability with real dependencies
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
