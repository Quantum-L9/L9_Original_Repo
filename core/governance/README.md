---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "2026-01-29 03:05:45 UTC"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "system clock (verification skipped)"
  auto_generated: true
---

# Governance & Approval Gates

> **Tier:** CORE | **Path:** `core/governance` | **Owner:** Igor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                       Governance & Approval Gates                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   core_govern   │ ───► │  Outbound   │                  │
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

Policy enforcement, approval workflows, and compliance checks

**Purpose:** Enforces governance policies, manages approval gates, and ensures compliance with security rules.

**What depends on it:** `core/tools/registry_adapter.py`, `core/agents/executor.py`

---

## Responsibilities and Boundaries

### What This Module Owns

- **Core operations:** Execute core governance tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics

### What This Module Does NOT Do

- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py

### Inbound Dependencies

| Module                           | Purpose          |
| -------------------------------- | ---------------- |
| `core/tools/registry_adapter.py` | Uses this module |
| `core/agents/executor.py`        | Uses this module |

### Outbound Dependencies

| Module             | Purpose             |
| ------------------ | ------------------- |
| `config/policies/` | Required dependency |

---

## Directory Layout

```
core/governance/
├── __init__.py
├── approval_gate.py
├── approval_manager.py
├── approvals.py
├── cmts.py
├── credentials_policy.py
├── engine.py
├── loader.py
├── mistake_prevention.py
├── policy_generator.py
├── policy_registry.py
├── protected_files_policy.py
├── quick_fixes.py
├── rate_limit_policy.py
├── schemas.py
└── ... (5 more files)
```

| File                  | Purpose                                            |
| --------------------- | -------------------------------------------------- |
| `approval_manager.py` | Core module (PROTECTED)                            |
| `policy_engine.py`    | Core module (PROTECTED)                            |
| `__init__.py`         | Core module (PROTECTED)                            |
| `quick_fixes.py`      | A quick fix pattern.                               |
| `quick_fixes.py`      | Result of applying a fix.                          |
| `quick_fixes.py`      | Executable quick-fix engine with auto-remediation. |

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `CoreGovernanceService`)
- **Functions:** `snake_case` (e.g., `process_core_governance_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods

---

## Key Components

### `quick_fixes.py` — QuickFix

```python
class QuickFix:
    """A quick fix pattern."""

    # Key methods:

```

**Lines:** 53-73 in `quick_fixes.py`

### `quick_fixes.py` — FixResult

```python
class FixResult:
    """Result of applying a fix."""

    # Key methods:

```

**Lines:** 77-85 in `quick_fixes.py`

### `quick_fixes.py` — QuickFixEngine

```python
class QuickFixEngine:
    """Executable quick-fix engine with auto-remediation."""

    # Key methods:

    def __init__(self, ...) -> None: ...

    def _load_default_fixes(self, ...) -> list[QuickFix]: ...

    def fixes(self, ...) -> list[QuickFix]: ...

    def add_fix(self, ...) -> None: ...

    def diagnose(self, ...) -> list[QuickFix]: ...

```

**Public Methods:** `__init__`, `_load_default_fixes`, `fixes`, `add_fix`, `diagnose`

**Lines:** 88-335 in `quick_fixes.py`

### `approvals.py` — ApprovalManager

```python
class ApprovalManager:
    """Manages approval of high-risk tasks."""

    # Key methods:

    def __init__(self, ...): ...

    def requires_approval(self, ...) -> bool: ...

    def get_high_risk_tools(self, ...) -> list[str]: ...

    async def request_approval(self, ...) -> str: ...

    async def _notify_slack(self, ...) -> None: ...

```

**Public Methods:** `__init__`, `requires_approval`, `get_high_risk_tools`, `request_approval`, `_notify_slack`

**Lines:** 75-525 in `approvals.py`

### `approval_gate.py` — EscalationResult

```python
class EscalationResult:
    """Result of escalation to Igor."""

    # Key methods:

```

**Lines:** 52-59 in `approval_gate.py`

---

## Data Models and Contracts

The following data models define the contracts for this subsystem:

- **`ApprovalRequest`** — Request for Igor approval of high-risk operation
- **`EvaluationRequest`** — Request to evaluate governance policies for an action.

### Exported Symbols (`__all__`)

`ADRLoadResult`, `ApprovalDecision`, `ApprovalManager`, `ApprovalRequest`, `ApprovalStatus`, `CMTSService`, `Condition`, `ConditionOperator`, `CredentialRecord`, `CredentialRotationPolicy`

_...and 58 more_

### Module Constants

| Constant              | Value                                         | Line |
| --------------------- | --------------------------------------------- | ---- |
| `PROTECTED_BY_LCTO`   | `get_lcto_controlled_files()`                 | 202  |
| `SUBSYSTEM_PROTECTED` | `get_subsystem_protected_files()`             | 203  |
| `ALL_PROTECTED`       | `get_all_protected_files()`                   | 204  |
| `HIGH_RISK_TOOLS`     | `get_high_risk_tools_with_descriptions()`     | 72   |
| `FILE_PATTERNS`       | `{'auth': ['api/auth\\.py', 'core/.*auth....` | 46   |
| `KEYWORD_PATTERNS`    | `{'auth': ['\\bauth\\w*\\b', '\\blogin\\b...` | 78   |
| `SUBSYSTEM_PRIORITY`  | `['auth', 'tools', 'memory_retrieval', 'c...` | 115  |
| `HIGH_RISK_TOOLS`     | `get_high_risk_tools()`                       | 262  |

_...and 3 more constants_

### Key Schemas

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CoreGovernanceRequest(BaseModel):
    """Request model for core_governance operations."""
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class CoreGovernanceResponse(BaseModel):
    """Response model for core_governance operations."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```

### Invariants

- **High-risk operations require explicit approval**
- **All policy violations are logged**
- **Approval tokens have expiration**

---

## Execution and Lifecycle

### Startup

1. **Discovery:** Core_Governance components are discovered and registered.
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
# Core_Governance feature flags
L9_ENABLE_CORE_GOVERNANCE_TRACING: true # Enable detailed tracing
L9_ENABLE_CORE_GOVERNANCE_METRICS: true # Enable Prometheus metrics
L9_ENABLE_CORE_GOVERNANCE_AUDIT: true # Enable audit logging
```

### Tuning Parameters

```yaml
core_governance:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100
```

### Environment Variables

```bash
CORE_GOVERNANCE_LOG_LEVEL=INFO
CORE_GOVERNANCE_TIMEOUT=30
CORE_GOVERNANCE_ENABLED=true
```

---

## API Surface (Public)

### Public Functions

#### `def create_quick_fix_engine() -> QuickFixEngine`

Create a QuickFixEngine instance with default fixes.

- **File:** `quick_fixes.py:339`
- **Async:** No
- **Returns:** `QuickFixEngine`

#### `def get_lcto_controlled_files() -> set[str]`

Get set of LCTO-controlled file paths.

- **File:** `protected_files_policy.py:124`
- **Async:** No
- **Returns:** `set[str]`

#### `def get_subsystem_protected_files() -> dict[str, set[str]]`

Get subsystem-protected files by subsystem name.

- **File:** `protected_files_policy.py:135`
- **Async:** No
- **Returns:** `dict[str, set[str]]`

#### `def get_all_protected_files() -> set[str]`

Get all protected file paths.

- **File:** `protected_files_policy.py:146`
- **Async:** No
- **Returns:** `set[str]`

#### `def is_protected(file_path) -> bool`

Check if a file is protected.

- **File:** `protected_files_policy.py:159`
- **Async:** No
- **Returns:** `bool`

### Usage Example

```python
from core.governance import CoreGovernanceService

# Initialize
service = CoreGovernanceService()

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

Core Governance operations emit structured JSON logs:

```json
{
  "timestamp": "2026-01-29T03:05:45Z",
  "level": "INFO",
  "module": "core.governance",
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

| Metric                                  | Type      | Description                    |
| --------------------------------------- | --------- | ------------------------------ |
| `core_governance_operation_duration_ms` | Histogram | Operation latency distribution |
| `core_governance_operation_total`       | Counter   | Total operations processed     |
| `core_governance_error_total`           | Counter   | Total errors encountered       |
| `core_governance_active_connections`    | Gauge     | Current active connections     |

### Tracing

Core Governance emits OpenTelemetry spans:

- `core_governance.execute` — Root span for operation
  - `core_governance.validate` — Input validation
  - `core_governance.process` — Core processing
  - `core_governance.persist` — State persistence (if applicable)

---

## Testing

### Unit Tests

Located in `tests/core_governance/`:

- `test_core_governance.py` — Core unit tests
- `test_core_governance_integration.py` — Integration tests (if applicable)

### Integration Tests

Located in `tests/integration/`:

- Test core_governance with real dependencies
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

- `credentials_policy.py` — Application logic, safe to modify
- `violation_tracker.py` — Application logic, safe to modify

### ⚠️ Restricted Scopes (requires human review)

- `approval_manager.py` — Requires human review before merge
- `policy_engine.py` — Requires human review before merge
- `__init__.py` — Requires human review before merge

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

- `approval_manager.py` — PROTECTED: Changes break system invariants
- `policy_engine.py` — PROTECTED: Changes break system invariants
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
