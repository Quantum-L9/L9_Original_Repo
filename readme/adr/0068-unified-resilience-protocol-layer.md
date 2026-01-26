# ADR 0068: Unified Resilience Protocol Layer

## Status

Accepted

## Pattern

All resilience patterns (retry, rate limiting, connection pooling, error handling, validation) use Protocol-based abstractions with concrete `Standard*` implementations and decorators.

## Files

- `core/protocols/retry_protocols.py` - Retry with backoff
- `core/protocols/rate_limiting_protocols.py` - Rate limiting
- `core/protocols/connection_protocols.py` - Connection pooling
- `core/protocols/error_handling_protocols.py` - Structured error handling
- `core/protocols/validation_protocols.py` - Input validation
- `core/models/l9_base_model.py` - Unified Pydantic base
- `core/observability/observability_context.py` - W3C trace context

## Import Block

```python
from core.protocols import (
    # Retry
    RetryProtocol,
    StandardRetryHandler,
    RetryPolicy,
    BackoffStrategy,
    with_retry,

    # Rate Limiting
    RateLimitingProtocol,
    StandardRateLimiter,
    RateLimitPolicy,
    RateLimitStrategy,
    RateLimitExceededError,
    rate_limited,

    # Connection Pool
    ConnectionPoolProtocol,
    StandardConnectionPool,
    ConnectionState,

    # Error Handling
    ErrorHandlingProtocol,
    StandardErrorHandler,
    ErrorContext,
    ErrorSeverity,
    ErrorCategory,
    with_error_handling,

    # Validation
    ValidationProtocol,
    StandardValidator,
    ValidationResult,
    ValidationError,
    validate_input,
)

from core.models import L9BaseModel
from core.observability import observability_context, span, get_trace_id
```

## Decorator Quick Reference

| Decorator                            | Purpose                       | Raises                          |
| ------------------------------------ | ----------------------------- | ------------------------------- |
| `@with_retry(policy)`                | Retry on failure with backoff | Last exception after exhaustion |
| `@rate_limited(limiter, key)`        | Enforce rate limits           | `RateLimitExceededError`        |
| `@validate_input(validator, schema)` | Validate function inputs      | `ValidationError`               |
| `@with_error_handling(handler)`      | Structured error capture      | Re-raises after logging         |

## Usage Examples

### Retry with Backoff

```python
from core.protocols import with_retry, RetryPolicy, BackoffStrategy

policy = RetryPolicy(
    max_retries=3,
    initial_delay=0.5,
    max_delay=30.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL,
    retry_on=(ConnectionError, TimeoutError),
)

@with_retry(policy=policy)
async def fetch_external_api(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### Rate Limiting

```python
from core.protocols import rate_limited, StandardRateLimiter, RateLimitPolicy

limiter = StandardRateLimiter(
    policy=RateLimitPolicy(
        max_requests=100,
        window_seconds=60,
    )
)

@rate_limited(limiter=limiter, key_func=lambda user_id: f"user:{user_id}")
async def process_request(user_id: str, data: dict) -> dict:
    return await handle_request(data)
```

### Connection Pool

```python
from core.protocols import StandardConnectionPool

pool = StandardConnectionPool(
    factory=create_db_connection,
    min_size=5,
    max_size=20,
    max_idle_seconds=300,
)

await pool.initialize()

async with pool.acquire() as conn:
    result = await conn.execute("SELECT * FROM users")

await pool.close()
```

### Error Handling

```python
from core.protocols import with_error_handling, StandardErrorHandler

handler = StandardErrorHandler()

@with_error_handling(handler=handler)
async def risky_operation(data: dict) -> dict:
    # Errors automatically logged with context
    return await process(data)
```

### Validation

```python
from core.protocols import validate_input, StandardValidator

validator = StandardValidator()

schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "age": {"type": "integer", "minimum": 0},
    },
    "required": ["name"],
}

@validate_input(validator=validator, schema=schema)
async def create_user(data: dict) -> dict:
    # data guaranteed to match schema
    return await save_user(data)
```

### Observability Context

```python
from core.observability import observability_context, span, get_trace_id

async with observability_context(operation="process_request"):
    trace_id = get_trace_id()

    async with span("fetch_data"):
        data = await fetch()

    async with span("transform"):
        result = transform(data)
```

## Anti-Pattern Examples

```python
# ❌ WRONG — Manual retry loop (use @with_retry)
for i in range(3):
    try:
        result = await fetch()
        break
    except Exception:
        await asyncio.sleep(i * 2)

# ❌ WRONG — Manual rate limiting (use @rate_limited)
if redis.incr(key) > limit:
    raise Exception("Rate limited")

# ❌ WRONG — Bare try/except (use @with_error_handling)
try:
    result = await risky()
except Exception as e:
    logger.error(str(e))
    raise

# ❌ WRONG — Manual validation (use @validate_input)
if "name" not in data:
    raise ValueError("Missing name")

# ✅ CORRECT — Use decorators
@with_retry(policy=retry_policy)
@rate_limited(limiter=limiter, key_func=get_user_key)
@with_error_handling(handler=error_handler)
@validate_input(validator=validator, schema=user_schema)
async def create_user(data: dict) -> dict:
    return await save_user(data)
```

## Protocol Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    core/protocols/                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────┐   │
│  │ RetryProtocol   │───▶│ StandardRetryHandler        │   │
│  └─────────────────┘    │ + @with_retry decorator     │   │
│                         └─────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────┐   │
│  │ RateLimitingProtocol│───▶│ StandardRateLimiter     │   │
│  └─────────────────────┘    │ + @rate_limited         │   │
│                             └─────────────────────────┘   │
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────┐   │
│  │ ConnectionPoolProto │───▶│ StandardConnectionPool  │   │
│  └─────────────────────┘    └─────────────────────────┘   │
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────┐   │
│  │ ErrorHandlingProto  │───▶│ StandardErrorHandler    │   │
│  └─────────────────────┘    │ + @with_error_handling  │   │
│                             └─────────────────────────┘   │
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────┐   │
│  │ ValidationProtocol  │───▶│ StandardValidator       │   │
│  └─────────────────────┘    │ + @validate_input       │   │
│                             └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Rules

1. ALL external I/O MUST use `@with_retry`
2. ALL public APIs MUST use `@rate_limited`
3. ALL user input MUST use `@validate_input`
4. ALL error-prone operations SHOULD use `@with_error_handling`
5. Use `Standard*` implementations unless custom behavior needed
6. Decorators can be stacked (order: retry → rate_limit → error → validate)
7. Configure policies via dataclasses, not magic strings

## Supersedes

- **ADR-0018** (Async Retry Pattern) — Now use `@with_retry` decorator

## AI Guidance

**DO:**

- Use decorators for cross-cutting concerns
- Configure policies explicitly via dataclasses
- Stack decorators in correct order
- Specify `retry_on` exceptions explicitly
- Use `observability_context` for tracing

**DO NOT:**

- Implement manual retry loops
- Implement manual rate limiting
- Use bare try/except for error handling
- Skip validation on user input
- Create custom implementations without Protocol compliance
- Retry on all exceptions (be specific)
