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

# Background Workers

> **Tier:** INFRASTRUCTURE | **Path:** `workers` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                            Background Workers                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │     workers     │ ───► │  Outbound   │                  │
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

Background job workers for async processing

**Purpose:** Executes background jobs for anomaly detection, remediation, and monitoring.

**What depends on it:** External clients

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute workers tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics

### What This Module Does NOT Do

- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py

### Inbound Dependencies

| Module | Purpose                 |
| ------ | ----------------------- |
| —      | No inbound dependencies |

### Outbound Dependencies

| Module                  | Purpose             |
| ----------------------- | ------------------- |
| `runtime/task_queue.py` | Required dependency |

---

## Directory Layout

```
workers/
├── __init__.py
├── anomaly_classifier.py
├── anomaly_response_monitor.py
├── remediation_engine.py
├── violation_patterns.py
├── violation_tracker_service.py
```

| File                    | Purpose                           |
| ----------------------- | --------------------------------- |
| `__init__.py`           | Core module (PROTECTED)           |
| `anomaly_classifier.py` | Anomaly severity levels.          |
| `anomaly_classifier.py` | Types of anomalies detected.      |
| `anomaly_classifier.py` | A rule for classifying anomalies. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `WorkersService`)
- **Functions:** `snake_case` (e.g., `process_workers_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `anomaly_classifier.py` — AnomalySeverity

```python
class AnomalySeverity:
    """Anomaly severity levels."""

    # Key methods:

```

**Lines:** 60-65 in `anomaly_classifier.py`

### `anomaly_classifier.py` — AnomalyType

```python
class AnomalyType:
    """Types of anomalies detected."""

    # Key methods:

```

**Lines:** 68-75 in `anomaly_classifier.py`

### `anomaly_classifier.py` — ClassificationRule

```python
class ClassificationRule:
    """A rule for classifying anomalies."""

    # Key methods:

```

**Lines:** 84-90 in `anomaly_classifier.py`

### `anomaly_classifier.py` — AnomalyClassifierRequest

```python
class AnomalyClassifierRequest:
    """Input request for AnomalyClassifier."""

    # Key methods:

```

**Lines:** 93-111 in `anomaly_classifier.py`

### `anomaly_classifier.py` — ClassificationResult

```python
class ClassificationResult:
    """Result of anomaly classification."""

    # Key methods:

```

**Lines:** 114-123 in `anomaly_classifier.py`

---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`AnomalyClassifierRequest`** — Input request for AnomalyClassifier.
- **`AnomalyClassifierResponse`** — Output response from AnomalyClassifier.
- **`ViolationPatternsRequest`** — Input request for ViolationPatterns.

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class WorkersRequest(BaseModel):
    """Request model for workers operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class WorkersResponse(BaseModel):
    """Response model for workers operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **Workers are idempotent**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Workers components are discovered and registered.
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
# Workers feature flags
L9_ENABLE_WORKERS_TRACING: true # Enable detailed tracing
L9_ENABLE_WORKERS_METRICS: true # Enable Prometheus metrics
L9_ENABLE_WORKERS_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
workers:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
WORKERS_LOG_LEVEL=INFO
WORKERS_TIMEOUT=30
WORKERS_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def create_anomaly_classifier(custom_rules)`

Factory function to create AnomalyClassifier.

- **File:** `anomaly_classifier.py:421`
- **Async:** No

#### `def create_violation_patterns(custom_patterns)`

Factory function to create ViolationPatterns.

- **File:** `violation_patterns.py:445`
- **Async:** No

#### `def create_remediation_engine(rollback_endpoint, escalation_endpoint)`

Factory function to create RemediationEngine.

- **File:** `remediation_engine.py:481`
- **Async:** No

#### `def create_violation_tracker_service(pattern_matcher, mcp_enabled)`

Factory function to create ViolationTrackerService.

- **File:** `violation_tracker_service.py:560`
- **Async:** No

#### `def create_anomaly_response_monitor(classifier, remediation_engine, poll_interval_seconds)`

Factory function to create AnomalyResponseMonitor.

- **File:** `anomaly_response_monitor.py:541`
- **Async:** No

### Usage Example

```python
from workers import WorkersService

# Initialize
service = WorkersService()

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

Workers operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-25T19:42:30Z",
  "level": "INFO",
  "module": "workers",
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

| Metric                          | Type      | Description                    |
| ------------------------------- | --------- | ------------------------------ |
| `workers_operation_duration_ms` | Histogram | Operation latency distribution |
| `workers_operation_total`       | Counter   | Total operations processed     |
| `workers_error_total`           | Counter   | Total errors encountered       |
| `workers_active_connections`    | Gauge     | Current active connections     |

### Tracing

Workers emits OpenTelemetry spans:

- `workers.execute` — Root span for operation
  - `workers.validate` — Input validation
  - `workers.process` — Core processing
  - `workers.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/workers/`:

- `test_workers.py` — Core unit tests
- `test_workers_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test workers with real dependencies
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
