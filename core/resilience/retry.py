"""
L9 Core - Async Retry Utility
=============================

Reusable async retry logic with exponential backoff and jitter.

Usage:
    from core.resilience.retry import async_retry, AsyncRetryConfig

    # With default config (3 retries, 0.5s base backoff)
    result = await async_retry(my_async_func, operation="fetch_data")

    # With custom config
    config = AsyncRetryConfig(max_retries=5, base_backoff=1.0, jitter=0.2)
    result = await async_retry(my_async_func, config=config, operation="api_call")

    # With specific exceptions to retry
    result = await async_retry(
        my_async_func,
        retry_on=(httpx.TimeoutException, httpx.ConnectError),
        operation="http_request"
    )

Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import random
import structlog
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple, Type, TypeVar

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, message: str, last_error: Optional[Exception] = None, attempts: int = 0):
        super().__init__(message)
        self.last_error = last_error
        self.attempts = attempts


@dataclass
class AsyncRetryConfig:
    """Configuration for async retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        base_backoff: Base delay in seconds before first retry (default: 0.5)
        max_backoff: Maximum delay cap in seconds (default: 30.0)
        jitter: Random jitter factor (0.0-1.0) to add to delay (default: 0.1)
        exponential_base: Base for exponential backoff calculation (default: 2)
    """

    max_retries: int = 3
    base_backoff: float = 0.5
    max_backoff: float = 30.0
    jitter: float = 0.1
    exponential_base: int = 2

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number (1-indexed).

        Uses exponential backoff: base_backoff * (exponential_base ^ (attempt - 1))
        Plus random jitter to avoid thundering herd.
        """
        delay = self.base_backoff * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_backoff)
        jitter_amount = random.random() * self.jitter * delay
        return delay + jitter_amount


# Default configuration
DEFAULT_RETRY_CONFIG = AsyncRetryConfig()


async def async_retry(
    coro_func: Callable[[], Any],
    *,
    config: Optional[AsyncRetryConfig] = None,
    operation: str = "operation",
    retry_on: Optional[Tuple[Type[Exception], ...]] = None,
) -> T:
    """
    Execute async function with retry logic and exponential backoff.

    Args:
        coro_func: Async function to execute (called on each attempt)
        config: Retry configuration (uses DEFAULT_RETRY_CONFIG if None)
        operation: Name of operation for logging
        retry_on: Tuple of exception types to retry on (retries all exceptions if None)

    Returns:
        Result from successful coro_func() call

    Raises:
        RetryExhaustedError: If all retries exhausted, wrapping the last error

    Example:
        async def fetch():
            return await httpx_client.get(url)

        result = await async_retry(fetch, operation="fetch_url")
    """
    cfg = config or DEFAULT_RETRY_CONFIG
    last_error: Optional[Exception] = None

    for attempt in range(1, cfg.max_retries + 1):
        try:
            return await coro_func()
        except Exception as exc:
            last_error = exc

            # Check if we should retry this exception type
            if retry_on is not None and not isinstance(exc, retry_on):
                raise

            # Don't retry if this was the last attempt
            if attempt == cfg.max_retries:
                break

            delay = cfg.calculate_delay(attempt)
            logger.warning(
                "Operation failed, retrying",
                operation=operation,
                attempt=attempt,
                max_retries=cfg.max_retries,
                error=str(exc),
                error_type=type(exc).__name__,
                delay_seconds=round(delay, 3),
            )
            await asyncio.sleep(delay)

    # All retries exhausted
    error_msg = f"{operation} failed after {cfg.max_retries} retries: {last_error}"
    logger.error(
        "Retry exhausted",
        operation=operation,
        attempts=cfg.max_retries,
        last_error=str(last_error),
    )
    raise RetryExhaustedError(error_msg, last_error=last_error, attempts=cfg.max_retries) from last_error
