#!/usr/bin/env python3
"""
================================================================================
Module: Context Enricher
Purpose: Query world model and enrich packet context
================================================================================

Summary:
    Enriches incoming packets with context from world model, memory layers,
    and domain knowledge. Part of reasoning pipeline Stage 2.

Extended Metadata:

================================================================================
# HEADER META - Module Identity (Static)
# component_id: INT-DTB-003
# layer: intelligence
# domain: context_enrichment
# governance_level: high
# created_at: 2026-01-02T03:35:00Z
================================================================================
"""


from dataclasses import dataclass, field
from typing import Any

import structlog

from core.schemas import PacketEnvelope

logger = structlog.get_logger(__name__)


@dataclass
class EnrichedContext:
    """Enriched context for reasoning."""

    original_payload: dict[str, Any]
    world_model_data: dict[str, Any] = field(default_factory=dict)
    episodic_context: list[dict[str, Any]] = field(default_factory=list)
    semantic_entities: list[dict[str, Any]] = field(default_factory=list)
    causal_factors: list[dict[str, Any]] = field(default_factory=list)


class ContextEnricher:
    """Enriches context for reasoning."""

    def __init__(
        self,
        world_model_bridge: Any | None = None,
        memory_bridge: Any | None = None,
    ):
        self.world_model = world_model_bridge
        self.memory = memory_bridge

    async def enrich_context(self, packet: PacketEnvelope) -> EnrichedContext:
        """Enrich packet with contextual data."""
        logger.info("enriching_context", packet_id=getattr(packet, "id", ""))

        context = EnrichedContext(original_payload=packet.payload)

        # Query world model
        if self.world_model:
            entity_id = packet.payload.get("entity_id", "")
            if entity_id:
                context.causal_factors = await self.world_model.query_causal_factors(
                    entity_id
                )

        # Query episodic memory
        if self.memory:
            events = await self.memory.query_episodic_memory(
                {"entity_id": packet.payload.get("entity_id")}
            )
            context.episodic_context = [
                {"event_id": e.event_id, "type": e.event_type} for e in events
            ]

        logger.info(
            "context_enriched",
            causal_count=len(context.causal_factors),
            episodic_count=len(context.episodic_context),
        )

        return context



__all__ = ["ContextEnricher", "EnrichedContext"]
