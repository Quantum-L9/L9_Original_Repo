"""
L9 Core - Resilience Utilities
==============================

Retry logic, backoff strategies, and fault tolerance utilities.
Includes Protocol + Mixin for DIP-based resilience (ADR-0014).

Version: 1.1.0
"""

from core.resilience.mixin import ResilienceMixin
from core.resilience.protocols import ResilientService
from core.resilience.retry import AsyncRetryConfig, RetryExhaustedError, async_retry

__all__ = [
    "AsyncRetryConfig",
    "ResilienceMixin",
    # DIP Protocol + Mixin (ADR-0014)
    "ResilientService",
    "RetryExhaustedError",
    # Retry utilities
    "async_retry",
]
