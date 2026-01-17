"""
L9 Substrate DAG Orchestrator Wrapper
Version: 2.0.0

Production-grade orchestrator around SubstrateDAG with:
- Retry with exponential backoff
- Circuit breaker integration
- Dead letter queue for failed packets

GMP-88: Core Resilience for SubstrateDagOrchestrator
"""

from __future__ import annotations

import asyncio
import random
import structlog
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from memory.substrate_dag import SubstrateDAG
from core.schemas import PacketEnvelope, PacketEnvelopeIn, PacketWriteResult

if TYPE_CHECKING:
    from core.observability.circuit_breaker import CircuitBreaker
    from memory.dead_letter import DeadLetterQueue

logger = structlog.get_logger(__name__)


# =============================================================================
# Retry Policy
# =============================================================================


@dataclass
class RetryPolicy:
    """Retry configuration for DAG ingestion."""

    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_max: float = 30.0
    jitter: float = 0.1  # ±10% randomization

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay with exponential backoff + jitter.

        Args:
            attempt: Zero-based attempt number

        Returns:
            Delay in seconds
        """
        delay = min(self.backoff_base * (2**attempt), self.backoff_max)
        jitter_range = delay * self.jitter
        return delay + random.uniform(-jitter_range, jitter_range)


# =============================================================================
# Orchestrator Class
# =============================================================================


class SubstrateDagOrchestrator:
    """
    Orchestrator for SubstrateDAG packet ingestion.

    Provides a production-grade interface for external integrations (Cursor, etc.)
    to ingest packets through the full DAG pipeline with:
    - Retry with exponential backoff on transient failures
    - Circuit breaker for cascade failure prevention
    - Dead letter queue for failed packets (no data loss)
    """

    def __init__(
        self,
        dag: Optional[SubstrateDAG] = None,
        circuit_breaker: Optional["CircuitBreaker"] = None,
        dead_letter_queue: Optional["DeadLetterQueue"] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        """
        Initialize DAG orchestrator with resilience features.

        Args:
            dag: SubstrateDAG instance (required)
            circuit_breaker: CircuitBreaker for failure isolation
            dead_letter_queue: DLQ for failed packets
            retry_policy: Retry configuration (defaults to 3 retries)
        """
        if dag is None:
            raise ValueError("SubstrateDAG instance required")

        self._dag = dag
        self._circuit_breaker = circuit_breaker
        self._dlq = dead_letter_queue
        self._retry_policy = retry_policy or RetryPolicy()

        logger.info(
            "SubstrateDagOrchestrator initialized",
            has_circuit_breaker=circuit_breaker is not None,
            has_dlq=dead_letter_queue is not None,
            max_retries=self._retry_policy.max_retries,
        )

    async def ingest_packet(
        self,
        envelope: PacketEnvelopeIn | PacketEnvelope,
        idempotency_key: Optional[str] = None,
    ) -> PacketWriteResult:
        """
        Ingest packet with retry, circuit breaker, and dead letter handling.

        Flow:
        1. Convert envelope if needed
        2. Check circuit breaker state
        3. Retry with exponential backoff on transient failures
        4. Dead letter on permanent failure or retry exhaustion

        Args:
            envelope: Packet to ingest
            idempotency_key: Optional key for deduplication (future use)

        Returns:
            PacketWriteResult with status
        """
        # Convert to full envelope
        if isinstance(envelope, PacketEnvelopeIn):
            full_envelope = envelope.to_envelope()
        else:
            full_envelope = envelope

        envelope_dict = full_envelope.model_dump(mode="json")
        packet_id = full_envelope.packet_id

        logger.info("Ingesting packet via DAG orchestrator", packet_id=packet_id)

        # Circuit breaker check
        if self._circuit_breaker and self._circuit_breaker.is_open():
            logger.warning(
                "Circuit breaker OPEN, rejecting request",
                packet_id=packet_id,
                state=self._circuit_breaker.get_state(),
            )
            # Still DLQ the packet so it's not lost
            if self._dlq:
                await self._dlq.enqueue(
                    envelope_dict,
                    error="Circuit breaker open",
                    attempts=0,
                )
            return PacketWriteResult(
                packet_id=packet_id,
                status="rejected",
                written_tables=[],
                error_message="Circuit breaker open — service degraded",
            )

        # Retry loop
        last_error: Optional[Exception] = None
        for attempt in range(self._retry_policy.max_retries + 1):
            try:
                result = await self._dag.run(full_envelope)

                # Success — record with circuit breaker
                if self._circuit_breaker:
                    self._circuit_breaker.record_success()

                logger.info(
                    "Packet ingested successfully",
                    packet_id=packet_id,
                    status=result.status,
                    attempt=attempt + 1,
                )
                return result

            except Exception as e:
                last_error = e

                # Record failure with circuit breaker
                if self._circuit_breaker:
                    self._circuit_breaker.record_failure(str(e))

                # Check if retryable
                if attempt < self._retry_policy.max_retries:
                    delay = self._retry_policy.get_delay(attempt)
                    logger.warning(
                        "DAG execution failed, retrying",
                        packet_id=packet_id,
                        attempt=attempt + 1,
                        max_retries=self._retry_policy.max_retries,
                        delay_seconds=round(delay, 2),
                        error=str(e)[:200],
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "DAG execution failed, retries exhausted",
                        packet_id=packet_id,
                        attempts=attempt + 1,
                        error=str(e),
                    )

        # All retries exhausted — dead letter
        if self._dlq:
            await self._dlq.enqueue(
                envelope_dict,
                error=last_error or "Unknown error",
                attempts=self._retry_policy.max_retries + 1,
            )

        return PacketWriteResult(
            packet_id=packet_id,
            status="error",
            written_tables=[],
            error_message=f"Retries exhausted: {last_error}",
        )
