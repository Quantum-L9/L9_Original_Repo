"""
L9 Core - Resilience Utilities
==============================

Retry logic, backoff strategies, and fault tolerance utilities.
Includes Protocol + Mixin for DIP-based resilience (ADR-0014).

Version: 1.1.0
"""

from core.resilience.retry import (
    async_retry,
    AsyncRetryConfig,
    RetryExhaustedError,
)
from core.resilience.protocols import ResilientService
from core.resilience.mixin import ResilienceMixin

__all__ = [
    # Retry utilities
    "async_retry",
    "AsyncRetryConfig",
    "RetryExhaustedError",
    # DIP Protocol + Mixin (ADR-0014)
    "ResilientService",
    "ResilienceMixin",
]
