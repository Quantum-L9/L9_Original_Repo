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

# Telemetry

> **Tier:** INFRASTRUCTURE | **Path:** `telemetry` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                Telemetry                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │    telemetry    │ ───► │  Outbound   │                  │
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

Metrics collection and emission

**Purpose:** Collects and emits telemetry data for monitoring and alerting.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute telemetry tasks
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
| `core/observability/` | Required dependency |

---

## Directory Layout

```
telemetry/
├── __init__.py
├── calibration_dashboard.py
├── memory_metrics.py
├── slack_metrics.py
```

| File | Purpose |
|------|---------|
| `__init__.py` | Core module (PROTECTED) |
| `calibration_dashboard.py` | Calibration quality metrics |
| `calibration_dashboard.py` | Monitoring and visualization for probabilistic gov |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `TelemetryService`)
- **Functions:** `snake_case` (e.g., `process_telemetry_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `calibration_dashboard.py` — CalibrationMetrics

```python
class CalibrationMetrics:
    """Calibration quality metrics"""

    # Key methods:

```

**Lines:** 97-107 in `calibration_dashboard.py`

### `calibration_dashboard.py` — CalibrationDashboard

```python
class CalibrationDashboard:
    """Monitoring and visualization for probabilistic governance."""

    # Key methods:

    def __init__(self, ...): ...

    def _load_decisions(self, ...): ...

    def generate_weekly_report(self, ...) -> str: ...

    def _calculate_metrics(self, ...) -> CalibrationMetrics: ...

    def _calculate_ece(self, ...) -> float: ...

```

**Public Methods:** `__init__`, `_load_decisions`, `generate_weekly_report`, `_calculate_metrics`, `_calculate_ece`

**Lines:** 110-565 in `calibration_dashboard.py`


---

## Data Models and Contracts


### Exported Symbols (`__all__`)

`PROMETHEUS_AVAILABLE`, `init_metrics`, `init_slack_metrics`, `record_aios_call`, `record_idempotent_hit`, `record_latency`, `record_memory_dedup`, `record_memory_enrichment`, `record_memory_ingest`, `record_memory_poison_suspect`

*...and 15 more*

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class TelemetryRequest(BaseModel):
    """Request model for telemetry operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class TelemetryResponse(BaseModel):
    """Response model for telemetry operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Metrics are Prometheus-compatible**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Telemetry components are discovered and registered.
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
# Telemetry feature flags
L9_ENABLE_TELEMETRY_TRACING: true  # Enable detailed tracing
L9_ENABLE_TELEMETRY_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_TELEMETRY_AUDIT: true    # Enable audit logging
```

### Tuning Parameters

```yaml
telemetry:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
TELEMETRY_LOG_LEVEL=INFO
TELEMETRY_TIMEOUT=30
TELEMETRY_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def generate_weekly_report()`

Entry point for scheduled weekly report generation

- **File:** `calibration_dashboard.py:568`
- **Async:** No

#### `def record_memory_write(segment, status, duration_seconds) -> None`

Record a memory write operation.

- **File:** `memory_metrics.py:269`
- **Async:** No
- **Returns:** `None`

#### `def record_memory_search(segment, hit_count, search_type) -> None`

Record a memory search operation.

- **File:** `memory_metrics.py:293`
- **Async:** No
- **Returns:** `None`

#### `def record_tool_invocation(tool_id, status, duration_ms) -> None`

Record a tool invocation.

- **File:** `memory_metrics.py:316`
- **Async:** No
- **Returns:** `None`

#### `def set_memory_substrate_health(healthy) -> None`

Set the memory substrate health gauge.

- **File:** `memory_metrics.py:339`
- **Async:** No
- **Returns:** `None`


### Usage Example

```python
from telemetry import TelemetryService

# Initialize
service = TelemetryService()

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

Telemetry operations emit structured JSON logs:

```json
{
  "timestamp": "2026-02-14T08:25:39Z",
  "level": "INFO",
  "module": "telemetry",
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
| `telemetry_operation_duration_ms` | Histogram | Operation latency distribution |
| `telemetry_operation_total` | Counter | Total operations processed |
| `telemetry_error_total` | Counter | Total errors encountered |
| `telemetry_active_connections` | Gauge | Current active connections |

### Tracing

Telemetry emits OpenTelemetry spans:

- `telemetry.execute` — Root span for operation
  - `telemetry.validate` — Input validation
  - `telemetry.process` — Core processing
  - `telemetry.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/telemetry/`:
- `test_telemetry.py` — Core unit tests
- `test_telemetry_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test telemetry with real dependencies
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
