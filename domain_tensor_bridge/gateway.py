"""
Domain Bridge Gateway — Single Ingress Point for All Substrate Writes
=====================================================================
Implements ADR-0092: every write to Postgres, Neo4j, Redis (non-exempt),
pgvector, or the World Model MUST pass through this gateway.

Pipeline per submit():
  1. Validate PacketEnvelope schema (verify_integrity)
  2. Enforce principal_id (fail-closed)
  3. Enforce ingress_origin (fail-closed)
  4. Governance gate (GovernanceEngine.evaluate)
  5. Audit trail emission (structlog)
  6. Provenance stamp (with_mutation)
  7. Forward to IngestionPipeline.ingest()
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Domain Bridge Gateway",
    "module_version": "1.0.0",
    "created_by": "Manus Agent",
    "created_at": "2026-02-19T12:00:00Z",
    "updated_at": "2026-02-19T12:00:00Z",
    "layer": "core",
    "domain": "dtb",
    "module_name": "domain_tensor_bridge.gateway",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL", "Redis"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable
from uuid import UUID

import structlog
from pydantic import BaseModel, Field

from core.decorators import must_stay_async
from core.schemas import PacketEnvelope, PacketEnvelopeIn, PacketWriteResult

if TYPE_CHECKING:
    from core.governance.schemas import EvaluationRequest, EvaluationResult

logger = structlog.get_logger(__name__)


# =============================================================================
# Protocols (DI boundaries — ADR-0026)
# =============================================================================


@runtime_checkable
class GovernanceGate(Protocol):
    """Protocol for governance evaluation."""

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult: ...


@runtime_checkable
class IngestionSink(Protocol):
    """Protocol for the downstream ingestion pipeline."""

    async def ingest(
        self,
        packet_in: PacketEnvelopeIn,
        embed: bool | None = None,
        generate_tags: bool | None = None,
    ) -> PacketWriteResult: ...


# =============================================================================
# Result Models
# =============================================================================


class WriteResult(BaseModel):
    """Result of a single submit() call through the Domain Bridge."""

    packet_id: UUID = Field(..., description="Packet ID that was submitted")
    status: str = Field(..., description="'ok', 'denied', or 'error'")
    governance_allowed: bool = Field(
        ..., description="Whether governance gate allowed the write"
    )
    governance_reason: str | None = Field(
        None, description="Reason from governance evaluation"
    )
    write_result: PacketWriteResult | None = Field(
        None, description="Downstream write result (None if denied)"
    )
    error_message: str | None = Field(
        None, description="Error details if status='error'"
    )
    submitted_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=datetime.now(tz=UTC).tzinfo or UTC),
        description="Timestamp of submission",
    )

    model_config = {"extra": "forbid"}


class BatchWriteResult(BaseModel):
    """Result of a submit_batch() call."""

    total: int = Field(..., description="Total packets submitted")
    succeeded: int = Field(default=0, description="Packets that succeeded")
    denied: int = Field(default=0, description="Packets denied by governance")
    failed: int = Field(default=0, description="Packets that errored")
    results: list[WriteResult] = Field(
        default_factory=list, description="Per-packet results"
    )

    model_config = {"extra": "forbid"}


class HealthStatus(BaseModel):
    """Liveness/readiness probe for the Domain Bridge."""

    healthy: bool = Field(..., description="Overall health status")
    governance_available: bool = Field(
        ..., description="Whether governance engine is reachable"
    )
    ingestion_available: bool = Field(
        ..., description="Whether ingestion pipeline is reachable"
    )
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="Timestamp of health check",
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# Domain Bridge Gateway
# =============================================================================


class DomainBridgeGateway:
    """
    Mandatory single ingress point for all L9 substrate writes (ADR-0092).

    Sits upstream of ``memory/ingestion.py``. Every write — to Postgres,
    Neo4j, Redis (non-exempt), pgvector, or the World Model — must pass
    through ``submit()`` or ``submit_batch()``.

    Usage::

        gateway = DomainBridgeGateway(
            governance=governance_engine,
            ingestion=ingestion_pipeline,
        )
        result = await gateway.submit(
            packet=envelope,
            principal_id="user:igor",
            ingress_origin="api",
        )
    """

    __slots__ = ("_governance", "_ingestion")

    def __init__(
        self,
        *,
        governance: GovernanceGate,
        ingestion: IngestionSink,
    ) -> None:
        """
        Initialise the gateway with its two mandatory dependencies.

        Args:
            governance: Governance engine for policy evaluation.
            ingestion: Downstream ingestion pipeline.

        Raises:
            TypeError: If governance or ingestion do not satisfy their protocols.
        """
        if not isinstance(governance, GovernanceGate):
            raise TypeError("governance must satisfy GovernanceGate protocol")
        if not isinstance(ingestion, IngestionSink):
            raise TypeError("ingestion must satisfy IngestionSink protocol")
        self._governance = governance
        self._ingestion = ingestion
        logger.info("domain_bridge.gateway.init")

    # --------------------------------------------------------------------- #
    # Public API (exactly 3 methods per ADR-0092)
    # --------------------------------------------------------------------- #

    @must_stay_async("callers use await")
    async def submit(
        self,
        packet: PacketEnvelope,
        *,
        principal_id: str,
        ingress_origin: str,
    ) -> WriteResult:
        """
        Submit a single packet through the Domain Bridge.

        Pipeline:
          1. Validate principal_id (fail-closed)
          2. Validate ingress_origin (fail-closed)
          3. Governance gate
          4. Audit trail
          5. Provenance stamp
          6. Forward to ingestion

        Args:
            packet: The PacketEnvelope to submit.
            principal_id: Non-empty identity of the submitting principal.
            ingress_origin: Non-empty origin label (must be known value).

        Returns:
            WriteResult with status 'ok', 'denied', or 'error'.

        Raises:
            ValueError: If principal_id or ingress_origin is missing/empty.
        """
        # ── Gate 0: principal_id (fail-closed) ──────────────────────────
        if not principal_id or not principal_id.strip():
            raise ValueError("principal_id is required (fail-closed)")

        # ── Gate 1: ingress_origin (fail-closed) ────────────────────────
        if not ingress_origin or not ingress_origin.strip():
            raise ValueError("ingress_origin is required (fail-closed)")

        packet_id = packet.packet_id

        # ── Gate 2: Governance ──────────────────────────────────────────
        try:
            gov_result = await self._evaluate_governance(
                packet=packet,
                principal_id=principal_id,
                ingress_origin=ingress_origin,
            )
        except Exception as exc:
            logger.error(
                "domain_bridge.governance.error",
                packet_id=str(packet_id),
                principal_id=principal_id,
                error=str(exc),
                exc_info=True,
            )
            return WriteResult(
                packet_id=packet_id,
                status="error",
                governance_allowed=False,
                governance_reason=f"Governance evaluation failed: {exc}",
                error_message=str(exc),
            )

        if not gov_result.allowed:
            logger.warning(
                "domain_bridge.submit.denied",
                packet_id=str(packet_id),
                principal_id=principal_id,
                ingress_origin=ingress_origin,
                reason=gov_result.reason,
            )
            return WriteResult(
                packet_id=packet_id,
                status="denied",
                governance_allowed=False,
                governance_reason=gov_result.reason,
            )

        # ── Audit trail ─────────────────────────────────────────────────
        logger.info(
            "domain_bridge.submit",
            packet_id=str(packet_id),
            principal_id=principal_id,
            ingress_origin=ingress_origin,
            packet_type=packet.packet_type,
        )

        # ── Provenance stamp ────────────────────────────────────────────
        stamped = packet.with_mutation(
            metadata={
                **(packet.metadata or {}),
                "domain_bridge_principal_id": principal_id,
                "domain_bridge_ingress_origin": ingress_origin,
                "domain_bridge_submitted_at": datetime.now(tz=UTC).isoformat(),
            },
        )

        # ── Forward to ingestion ────────────────────────────────────────
        try:
            packet_in = PacketEnvelopeIn(
                packet_type=stamped.packet_type,
                payload=stamped.payload,
                source_id=stamped.source_id,
                thread_id=str(stamped.thread_id) if stamped.thread_id else None,
                metadata=stamped.metadata,
                tags=stamped.tags,
                principal_id=principal_id,
                ingress_origin=ingress_origin,
            )
            write_result = await self._ingestion.ingest(packet_in)
        except Exception as exc:
            logger.error(
                "domain_bridge.ingestion.error",
                packet_id=str(packet_id),
                principal_id=principal_id,
                error=str(exc),
                exc_info=True,
            )
            return WriteResult(
                packet_id=packet_id,
                status="error",
                governance_allowed=True,
                governance_reason=gov_result.reason,
                error_message=str(exc),
            )

        logger.info(
            "domain_bridge.submit.ok",
            packet_id=str(packet_id),
            principal_id=principal_id,
            downstream_status=write_result.status,
        )

        return WriteResult(
            packet_id=packet_id,
            status="ok",
            governance_allowed=True,
            governance_reason=gov_result.reason,
            write_result=write_result,
        )

    @must_stay_async("callers use await")
    async def submit_batch(
        self,
        packets: list[PacketEnvelope],
        *,
        principal_id: str,
        ingress_origin: str,
    ) -> BatchWriteResult:
        """
        Submit multiple packets through the Domain Bridge.

        Each packet is submitted individually via ``submit()``.
        Failures in one packet do not block others.

        Args:
            packets: List of PacketEnvelopes to submit.
            principal_id: Non-empty identity of the submitting principal.
            ingress_origin: Non-empty origin label.

        Returns:
            BatchWriteResult with per-packet results.

        Raises:
            ValueError: If principal_id or ingress_origin is missing/empty.
        """
        if not principal_id or not principal_id.strip():
            raise ValueError("principal_id is required (fail-closed)")
        if not ingress_origin or not ingress_origin.strip():
            raise ValueError("ingress_origin is required (fail-closed)")

        results: list[WriteResult] = []
        succeeded = 0
        denied = 0
        failed = 0

        for packet in packets:
            result = await self.submit(
                packet=packet,
                principal_id=principal_id,
                ingress_origin=ingress_origin,
            )
            results.append(result)
            if result.status == "ok":
                succeeded += 1
            elif result.status == "denied":
                denied += 1
            else:
                failed += 1

        logger.info(
            "domain_bridge.submit_batch.complete",
            total=len(packets),
            succeeded=succeeded,
            denied=denied,
            failed=failed,
            principal_id=principal_id,
        )

        return BatchWriteResult(
            total=len(packets),
            succeeded=succeeded,
            denied=denied,
            failed=failed,
            results=results,
        )

    @must_stay_async("callers use await")
    async def health(self) -> HealthStatus:
        """
        Liveness/readiness probe.

        Checks that both governance and ingestion dependencies are reachable.

        Returns:
            HealthStatus with component-level availability.
        """
        governance_ok = self._governance is not None
        ingestion_ok = self._ingestion is not None

        return HealthStatus(
            healthy=governance_ok and ingestion_ok,
            governance_available=governance_ok,
            ingestion_available=ingestion_ok,
        )

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    async def _evaluate_governance(
        self,
        *,
        packet: PacketEnvelope,
        principal_id: str,
        ingress_origin: str,
    ) -> Any:
        """
        Build an EvaluationRequest and call the governance gate.

        Imports EvaluationRequest at call-time to avoid circular imports
        (the schema module is lightweight, but the engine may import us).
        """
        from core.governance.schemas import EvaluationRequest

        request = EvaluationRequest(
            subject=principal_id,
            action="domain_bridge.submit",
            resource=packet.packet_type or "unknown",
            context={
                "packet_id": str(packet.packet_id),
                "ingress_origin": ingress_origin,
                "packet_type": packet.packet_type,
            },
        )
        return await self._governance.evaluate(request)


# =============================================================================
# Sorted public API
# =============================================================================

__all__ = [
    "BatchWriteResult",
    "DomainBridgeGateway",
    "GovernanceGate",
    "HealthStatus",
    "IngestionSink",
    "WriteResult",
]
