"""
L9 Core - Resilience Utilities
==============================

Retry logic, backoff strategies, and fault tolerance utilities.
Includes Protocol + Mixin for DIP-based resilience.

Version: 1.1.0
"""


from core.resilience.mixin import ResilienceMixin
from core.resilience.protocols import ResilientService
from core.resilience.retry import AsyncRetryConfig, RetryExhaustedError, async_retry

__all__ = [
    "AsyncRetryConfig",
    "ResilienceMixin",
    "ResilientService",
    "RetryExhaustedError",
    # Retry utilities
    "async_retry",
]
# Runtime execution trace - updated automatically on every execution
