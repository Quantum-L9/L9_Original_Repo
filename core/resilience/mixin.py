"""
L9 Core - Resilience Mixin
==========================

Mixin providing standard retry + circuit breaker + DLQ behavior.
Components inherit this and call with_resilience() to wrap operations.

Usage:
    from core.resilience.mixin import ResilienceMixin

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

Version: 1.0.0
ADR: readme/adr/0014-resilience-mixin-pattern.md
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Resilience Mixin",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-20T16:00:00Z",
    "updated_at": "2026-01-20T16:00:00Z",
    "layer": "foundation",
    "domain": "resilience",
    "module_name": "mixin",
    "type": "mixin",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from core.observability.circuit_breaker import CircuitBreaker
    from memory.dead_letter import DeadLetterQueue
    from memory.substrate_dag_wrapper import RetryPolicy

from core.observability.circuit_breaker import CircuitOpenError

logger = structlog.get_logger(__name__)


class ResilienceMixin:
    """
    Mixin providing standard retry + circuit breaker + DLQ behavior.

    Components inherit this mixin and call with_resilience() to wrap
    critical async operations with:
    - Circuit breaker check (fast-fail when open)
    - Retry with exponential backoff
    - Dead letter queue on exhaustion

    Required attributes (set in subclass __init__):
        _circuit_breaker: Optional[CircuitBreaker]
        _dlq: Optional[DeadLetterQueue]
        _retry_policy: Optional[RetryPolicy]

    Example:
        class MyService(ResilienceMixin):
            def __init__(self, cb=None, dlq=None, retry_policy=None):
                self._circuit_breaker = cb
                self._dlq = dlq
                self._retry_policy = retry_policy or RetryPolicy()

            async def do_work(self, data):
                return await self.with_resilience(
                    operation=lambda: self._actual_work(data),
                    envelope={"data": data},
                    operation_name="do_work"
                )
    """

    # Type hints for required attributes (set by subclass)
    _circuit_breaker: CircuitBreaker | None
    _dlq: DeadLetterQueue | None
    _retry_policy: RetryPolicy | None

    @must_stay_async("callers use await")
    async def with_resilience(
        self,
        operation: Callable[[], Awaitable[Any]],
        envelope: dict | Any,
        operation_name: str,
    ) -> Any:
        """
        Wrap an async operation with retry + circuit breaker + DLQ.

        Flow:
        1. Check circuit breaker state → fast-fail if open (DLQ the envelope)
        2. Execute operation with retry loop
        3. On success → record with circuit breaker
        4. On transient failure → retry with exponential backoff
        5. On exhaustion → DLQ the envelope and raise

        Args:
            operation: Async callable to execute (called on each attempt)
            envelope: Data to enqueue to DLQ on failure (dict or model with model_dump())
            operation_name: Name for logging and metrics

        Returns:
            Result of operation if successful

        Raises:
            CircuitOpenError: If circuit breaker is open
            Exception: Original exception if all retries exhausted (after DLQ enqueue)
        """
        # Ensure envelope is a dict for DLQ
        if hasattr(envelope, "model_dump"):
            envelope_dict = envelope.model_dump(mode="json")
        elif isinstance(envelope, dict):
            envelope_dict = envelope
        else:
            envelope_dict = {"data": str(envelope)}

        # Circuit breaker check
        if self._circuit_breaker and self._circuit_breaker.is_open():
            logger.warning(
                "Circuit breaker OPEN, rejecting request",
                operation=operation_name,
                state=self._circuit_breaker.get_state(),
            )
            # DLQ the envelope so it's not lost
            if self._dlq:
                await self._dlq.enqueue(
                    envelope_dict,
                    error="Circuit breaker open",
                    attempts=0,
                )
            raise CircuitOpenError(
                f"{operation_name}: Circuit breaker open — service degraded",
                circuit_name=getattr(
                    getattr(self._circuit_breaker, "config", None), "name", "default"
                ),
            )

        # Get retry policy (use default if not set)
        from memory.substrate_dag_wrapper import RetryPolicy

        policy = self._retry_policy or RetryPolicy()

        # Retry loop
        last_error: Exception | None = None
        max_attempts = policy.max_retries + 1

        for attempt in range(max_attempts):
            try:
                result = await operation()

                # Success — record with circuit breaker
                if self._circuit_breaker:
                    self._circuit_breaker.record_success()

                logger.debug(
                    "Operation succeeded",
                    operation=operation_name,
                    attempt=attempt + 1,
                )
                return result

            except Exception as e:
                last_error = e

                # Record failure with circuit breaker
                if self._circuit_breaker:
                    self._circuit_breaker.record_failure(str(e))

                # Check if we should retry
                if attempt < policy.max_retries:
                    delay = policy.get_delay(attempt)
                    logger.warning(
                        "Operation failed, retrying",
                        operation=operation_name,
                        attempt=attempt + 1,
                        max_retries=policy.max_retries,
                        delay_seconds=round(delay, 2),
                        error=str(e)[:200],
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Operation failed, retries exhausted",
                        operation=operation_name,
                        attempts=attempt + 1,
                        error=str(e),
                    )

        # All retries exhausted — dead letter
        if self._dlq and last_error:
            await self._dlq.enqueue(
                envelope_dict,
                error=last_error,
                attempts=max_attempts,
            )

        # Re-raise the last error
        if last_error:
            raise last_error

        # Should never reach here, but satisfy type checker
        raise RuntimeError(f"{operation_name}: Unexpected retry loop exit")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-092",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.observability.circuit_breaker",
        "memory.dead_letter",
        "memory.substrate_dag_wrapper",
    ],
    "tags": [
        "async",
        "circuit-breaker",
        "dip",
        "dlq",
        "foundation",
        "mixin",
        "resilience",
        "retry",
    ],
    "keywords": [
        "circuit_breaker",
        "dlq",
        "mixin",
        "resilience",
        "retry",
        "with_resilience",
    ],
    "business_value": "Mixin providing standard retry + CB + DLQ, reducing boilerplate from ~40 to ~5 lines per component",
    "last_modified": "2026-01-20T16:00:00Z",
    "modified_by": "GMP-091",
    "change_summary": "Initial creation per ADR-0014",
}
# ============================================================================
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
