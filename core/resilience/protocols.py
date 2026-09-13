"""
L9 Core - Resilience Protocols
==============================

Protocol definitions for resilient services.
Enables DIP: components depend on protocol, not concrete implementations.

Usage:
    from core.resilience.protocols import ResilientService

    class MyService(ResilientService, ResilienceMixin):
        ...

Version: 1.0.0
ADR: readme/adr/0014-resilience-mixin-pattern.md
"""

from __future__ import annotations


from typing import Protocol

from core.observability.circuit_breaker import CircuitBreaker
from memory.dead_letter import DeadLetterQueue
from memory.substrate_dag_wrapper import RetryPolicy


class ResilientService(Protocol):
    """
    Protocol for services that support resilience patterns.

    Components implementing this protocol have:
    - Circuit breaker for cascade failure prevention
    - Dead letter queue for failed operations
    - Retry policy for transient failures

    Usage:
        class MyService(ResilientService):
            def __init__(self, circuit_breaker=None, dlq=None, retry_policy=None):
                self._circuit_breaker = circuit_breaker
                self._dlq = dlq
                self._retry_policy = retry_policy or RetryPolicy()
    """

    _circuit_breaker: CircuitBreaker | None
    _dlq: DeadLetterQueue | None
    _retry_policy: RetryPolicy | None


# Runtime execution trace - updated automatically on every execution
