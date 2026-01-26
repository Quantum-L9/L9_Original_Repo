# ADR 0009: Circuit Breaker Resilience

## Status

Accepted

## Pattern

External calls wrapped in CircuitBreaker; open circuit returns fast failure, auto-resets after cooldown.

## Files

- `core/observability/circuit_breaker.py` - CircuitBreaker class
- `memory/substrate_service.py:146-153` - Memory DAG circuit breaker
- `api/routes/observability.py:322` - Circuit breaker status endpoint

## Circuit States

```
CLOSED ──(failures >= threshold)──> OPEN
   ↑                                  │
   │                                  │ (reset_timeout elapsed)
   │                                  ▼
   └────────(success)──────────── HALF_OPEN
```

## Configuration

```python
CircuitBreakerConfig(
    failure_threshold=5,    # Failures before opening
    window_seconds=60,      # Window for counting failures
    reset_timeout=30,       # Seconds before half-open
    name="memory_dag",      # Identifier for metrics
)
```

## Usage Pattern

```python
from core.observability.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

self._circuit_breaker = CircuitBreaker(CircuitBreakerConfig(...))

# Before operation
if self._circuit_breaker.is_open():
    return error_response("Circuit breaker open")

# On success
try:
    result = await risky_operation()
    self._circuit_breaker.record_success()
except Exception as e:
    self._circuit_breaker.record_failure(str(e))
    raise
```

## Monitored Operations

| Operation     | Circuit Breaker Name | Threshold      |
| ------------- | -------------------- | -------------- |
| Memory DAG    | `memory_dag`         | 5 failures/60s |
| Neo4j queries | `neo4j`              | 3 failures/30s |
| Redis ops     | `redis`              | 5 failures/30s |

## Rules

1. External I/O MUST use circuit breaker
2. Record success/failure after every call
3. Check `is_open()` before operation
4. Return fast failure when open (don't retry)
5. Log circuit state changes

## AI Guidance

**DO:**

- Wrap database/API calls in circuit breaker
- Use descriptive `name` for each breaker
- Log when circuit opens/closes
- Include circuit state in error responses

**DO NOT:**

- Remove circuit breakers for "performance"
- Retry when circuit is open
- Share circuit breaker across unrelated operations
- Set threshold too high (defeats purpose)
