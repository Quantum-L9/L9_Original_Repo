# ADR 0024: Resilience Mixin Pattern

## Status

Accepted

## Pattern

Protocol + Mixin for adding Circuit Breaker, Dead Letter Queue, and Retry to components via Dependency Inversion Principle (DIP).

## Context

L9 has resilience infrastructure (`CircuitBreaker`, `DeadLetterQueue`, `RetryPolicy`) but only `SubstrateDagOrchestrator` uses all three. Other components need the same pattern. Manually adding ~40 lines of retry/CB/DLQ logic to each component is error-prone and violates DRY.

Using DIP via Protocol + Mixin reduces boilerplate from ~40 lines to ~5 lines per component.

## Files

- `core/resilience/protocols.py` - ResilientService protocol
- `core/resilience/mixin.py` - ResilienceMixin class
- `core/resilience/__init__.py` - Exports
- `memory/substrate_dag_wrapper.py` - Reference implementation
- `core/observability/circuit_breaker.py` - CircuitBreaker class
- `memory/dead_letter.py` - DeadLetterQueue class

## Protocol Definition

```python
class ResilientService(Protocol):
    """Contract for services that support resilience patterns."""
    _circuit_breaker: Optional["CircuitBreaker"]
    _dlq: Optional["DeadLetterQueue"]
    _retry_policy: Optional["RetryPolicy"]
```

## Mixin Usage

```python
from core.resilience import ResilienceMixin
from memory.substrate_dag_wrapper import RetryPolicy

class IngestionPipeline(ResilienceMixin):
    def __init__(self, circuit_breaker=None, dlq=None, retry_policy=None):
        self._circuit_breaker = circuit_breaker
        self._dlq = dlq
        self._retry_policy = retry_policy or RetryPolicy()

    async def ingest(self, envelope):
        return await self.with_resilience(
            operation=lambda: self._do_ingest(envelope),
            envelope=envelope.model_dump(),
            operation_name="ingest_packet"
        )
```

## with_resilience() Flow

```
1. Check circuit breaker → fast-fail if open (DLQ envelope)
2. Execute operation
3. On success → record with circuit breaker, return result
4. On failure → record failure, retry with exponential backoff
5. On exhaustion → DLQ envelope, raise exception
```

## Components to Apply

| Component             | File                                  | Priority |
| --------------------- | ------------------------------------- | -------- |
| IngestionPipeline     | `memory/ingestion.py`                 | HIGH     |
| WebSocketOrchestrator | `orchestration/unified_controller.py` | HIGH     |
| SemanticService       | `memory/substrate_semantic.py`        | MEDIUM   |
| GraphAdapter          | `graph_adapter/graph_runtime.py`      | MEDIUM   |

## Rules

1. New resilient services MUST inherit `ResilienceMixin`
2. Constructor MUST accept `circuit_breaker`, `dlq`, `retry_policy`
3. Critical operations MUST call `with_resilience()`
4. DLQ envelope MUST be serializable (dict or model_dump())
5. Operation name MUST be descriptive for logging

## AI Guidance

**DO:**

- Inherit `ResilienceMixin` for services needing resilience
- Pass dependencies via constructor (DI)
- Use descriptive `operation_name` for metrics/logging
- Test with mocked `_circuit_breaker` and `_dlq`

**DO NOT:**

- Implement retry/CB/DLQ logic manually in components
- Skip DLQ for "non-critical" operations (all failures need audit)
- Share single circuit breaker across unrelated operations
- Remove mixin inheritance for "simplicity"

## Related ADRs

- [ADR-0009: Circuit Breaker Resilience](0009-circuit-breaker-resilience.md) - CB pattern this extends
- [ADR-0002: TYPE_CHECKING Pattern](0002-circular-import-prevention.md) - Import pattern for protocols
