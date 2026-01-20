# ADR 0018: Async Retry Pattern

## Status
Accepted

## Pattern
External I/O wrapped with `async_retry()` using exponential backoff + jitter.

## Files
- `core/resilience/retry.py` - Implementation
- `services/research/tools/perplexity_client.py` - Usage example
- `memory/substrate_service.py` - Memory operations

## Import Block
```python
from core.resilience.retry import (
    async_retry,
    AsyncRetryConfig,
    RetryExhaustedError,
)
import httpx
```

## Minimal Implementation
```python
from dataclasses import dataclass
from typing import Callable, TypeVar, Any
import asyncio
import random
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")

@dataclass
class AsyncRetryConfig:
    """Configuration for async retry behavior."""
    max_retries: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True

class RetryExhaustedError(Exception):
    """Raised when all retries are exhausted."""
    pass

async def async_retry(
    operation: Callable[[], T],
    config: AsyncRetryConfig | None = None,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    operation_name: str = "operation",
) -> T:
    """
    Retry an async operation with exponential backoff.
    
    Args:
        operation: Async callable to retry
        config: Retry configuration
        retry_on: Exception types to retry on
        operation_name: Name for logging
    
    Returns:
        Result of successful operation
    
    Raises:
        RetryExhaustedError: If all retries fail
    """
    config = config or AsyncRetryConfig()
    last_exception: Exception | None = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await operation()
        except retry_on as e:
            last_exception = e
            
            if attempt == config.max_retries:
                break
            
            # Calculate delay with exponential backoff
            delay = min(
                config.base_delay_seconds * (config.exponential_base ** attempt),
                config.max_delay_seconds,
            )
            
            # Add jitter to prevent thundering herd
            if config.jitter:
                delay *= (0.5 + random.random())
            
            logger.warning(
                "retry.attempt_failed",
                operation=operation_name,
                attempt=attempt + 1,
                max_retries=config.max_retries,
                delay_seconds=delay,
                error=str(e),
            )
            
            await asyncio.sleep(delay)
    
    raise RetryExhaustedError(
        f"{operation_name} failed after {config.max_retries} retries: {last_exception}"
    )
```

## Usage Example
```python
import httpx
from core.resilience.retry import async_retry, AsyncRetryConfig

# Simple usage with defaults
async def fetch_data():
    result = await async_retry(
        operation=lambda: client.get("/api/data"),
        operation_name="fetch_data",
    )
    return result.json()

# Custom config for specific exceptions
async def call_external_api():
    config = AsyncRetryConfig(
        max_retries=5,
        base_delay_seconds=1.0,
        max_delay_seconds=60.0,
    )
    
    result = await async_retry(
        operation=lambda: external_client.post("/endpoint", json=payload),
        config=config,
        retry_on=(httpx.TimeoutException, httpx.ConnectError),
        operation_name="external_api_call",
    )
    return result

# With error handling
async def robust_operation():
    try:
        return await async_retry(
            operation=lambda: risky_call(),
            operation_name="risky_call",
        )
    except RetryExhaustedError as e:
        logger.error("operation_failed", error=str(e))
        raise
```

## Anti-Pattern Example
```python
# ❌ WRONG — No retry on external call
async def fetch_data():
    return await client.get("/api/data")  # Single attempt, no retry

# ❌ WRONG — Retry on ALL exceptions (including bugs)
await async_retry(
    operation=lambda: buggy_code(),
    retry_on=(Exception,),  # Will retry programming errors!
)

# ❌ WRONG — Manual retry loop (duplicates logic)
for i in range(3):
    try:
        result = await client.get("/api")
        break
    except Exception:
        await asyncio.sleep(i * 2)

# ✅ CORRECT — Specific exceptions, named operation
await async_retry(
    operation=lambda: client.get("/api"),
    retry_on=(httpx.TimeoutException, httpx.ConnectError),
    operation_name="api_fetch",
)
```

## Rules
1. ALL external I/O MUST use `async_retry`
2. Specify `retry_on` exceptions explicitly (not bare Exception)
3. Include `operation_name` for logging
4. Handle `RetryExhaustedError` at caller
5. Use default config unless specific needs

## AI Guidance
**DO:**
- Wrap external API calls with `async_retry`
- Specify which exceptions to retry
- Use meaningful `operation_name`
- Handle exhaustion at caller level

**DO NOT:**
- Remove retry "for simplicity"
- Retry on all exceptions (be specific)
- Implement manual retry loops
- Skip retry for "fast" operations
