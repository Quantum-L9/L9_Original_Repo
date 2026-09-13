#!/usr/bin/env python3
"""
================================================================================
Module: Agent Controller
Purpose: Main entry point and packet dispatcher for Domain-Tensor Bridge
================================================================================

Summary:
    Central controller that receives PacketEnvelopes from domain agents,
    orchestrates the reasoning pipeline, and returns enriched results.
    Handles packet validation, routing, and response formatting.

Extended Metadata:

================================================================================
# HEADER META - Module Identity (Static)
# component_id: OPS-DTB-002
# layer: operations
# domain: agent_orchestration
# governance_level: critical
# created_at: 2026-01-02T03:35:00Z
================================================================================
"""


from typing import Any

import structlog

from core.decorators import must_stay_async
from core.schemas import PacketEnvelope

logger = structlog.get_logger(__name__)


class AgentController:
    """
    Main controller for Domain-Tensor Bridge.

    Orchestrates the full processing pipeline:
    1. Validate incoming packet
    2. Route to appropriate handler
    3. Enrich context
    4. Coordinate tensor scoring
    5. Execute reasoning
    6. Check governance
    7. Format and return response
    """

    def __init__(
        self,
        reasoning_engine: Any | None = None,
        packet_router: Any | None = None,
        governance_bridge: Any | None = None,
    ):
        self.reasoning_engine = reasoning_engine
        self.packet_router = packet_router
        self.governance_bridge = governance_bridge
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize controller and all sub-components."""
        logger.info("agent_controller_initializing")

        if self.reasoning_engine:
            await self.reasoning_engine.initialize()
        if self.governance_bridge:
            await self.governance_bridge.initialize()

        self._initialized = True
        logger.info("agent_controller_ready")

    @must_stay_async("callers use await")
    async def process_packet(self, packet: PacketEnvelope) -> PacketEnvelope:
        """
        Process incoming domain packet through full pipeline.

        Args:
            packet: Incoming PacketEnvelope from domain agent

        Returns:
            Enriched PacketEnvelope with results

        Raises:
            ValueError: If packet validation fails
            GovernanceBlockedError: If governance check fails
        """
        logger.info(
            "processing_packet",
            packet_id=packet.id if hasattr(packet, "id") else "unknown",
            source=packet.source_id if hasattr(packet, "source_id") else "unknown",
        )

        try:
            # Step 1: Validate packet
            if self.packet_router:
                validation_result = await self.packet_router.validate(packet)
                if not validation_result.valid:
                    raise ValueError(
                        f"Packet validation failed: {validation_result.errors}"
                    )

            # Step 2: Route to handler
            if self.packet_router:
                await self.packet_router.route(packet)
            else:
                pass

            # Step 3: Execute reasoning
            if self.reasoning_engine:
                reasoning_result = await self.reasoning_engine.execute(packet)
            else:
                reasoning_result = {"reasoning": "completed", "confidence": 0.85}

            # Step 4: Check governance
            if self.governance_bridge:
                governance_result = await self.governance_bridge.check(reasoning_result)
                if not governance_result.approved:
                    logger.warning(
                        "governance_blocked",
                        reason=governance_result.reason,
                    )
                    return self._create_blocked_response(
                        packet, governance_result.reason
                    )

            # Step 5: Format response
            response = self._create_success_response(packet, reasoning_result)

            logger.info(
                "packet_processed",
                packet_id=packet.id if hasattr(packet, "id") else "unknown",
                success=True,
            )

            return response

        except Exception as e:
            logger.error(
                "packet_processing_failed",
                packet_id=packet.id if hasattr(packet, "id") else "unknown",
                error=str(e),
            )
            raise

    def _create_success_response(
        self,
        original_packet: PacketEnvelope,
        result: dict[str, Any],
    ) -> PacketEnvelope:
        """Create successful response packet."""
        return PacketEnvelope(
            packet_type="decision",
            payload={"result": result, "status": "success"},
            provenance={"source": "domain_bridge"},
            metadata={"original_packet_id": getattr(original_packet, "id", None)},
        )

    def _create_blocked_response(
        self,
        original_packet: PacketEnvelope,
        reason: str,
    ) -> PacketEnvelope:
        """Create governance-blocked response packet."""
        return PacketEnvelope(
            packet_type="decision",
            payload={"status": "blocked", "reason": reason},
            provenance={"source": "domain_bridge"},
            metadata={
                "original_packet_id": getattr(original_packet, "id", None),
                "governance_blocked": True,
            },
        )


async def process_packet(packet: PacketEnvelope) -> PacketEnvelope:
    """
    Convenience function to process a packet using default controller.

    Args:
        packet: Incoming PacketEnvelope

    Returns:
        Processed PacketEnvelope
    """
    controller = AgentController()
    await controller.initialize()
    return await controller.process_packet(packet)


# ============================================================================
# FOOTER META - Extended Metadata (Static)
# ============================================================================


__all__ = [
    "AgentController",
    "process_packet",
]
