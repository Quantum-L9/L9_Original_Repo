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
    See __footer_meta__ at module footer. Runtime trace in __l9_trace__.

================================================================================
# HEADER META - Module Identity (Static)
# component_id: INT-DTB-003
# layer: intelligence
# domain: context_enrichment
# governance_level: high
# created_at: 2026-01-02T03:35:00Z
================================================================================
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Context Enricher",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-02T04:42:10Z",
    "updated_at": "2026-01-02T15:16:47Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "context_enricher",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API"],
        "memory_layers": ["episodic_memory", "semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from typing import Any

import structlog
from l9.core.schemas import PacketEnvelope

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


__footer_meta__ = {
    "component_id": "INT-DTB-003",
    "component_name": "Context Enricher",
    "module_version": "1.0.0",
    "created_at": "2026-01-02T03:35:00Z",
    "created_by": "L9_Codegen_Engine",
    "layer": "intelligence",
    "domain": "context_enrichment",
    "type": "enricher",
    "status": "active",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Query world model and enrich packet context",
    "summary": "Enriches incoming packets with context from world model, memory layers, and domain knowledge.",
    "dependencies": ["structlog", "httpx", "l9.core.schemas"],
}

__all__ = ["ContextEnricher", "EnrichedContext", "__footer_meta__", "__l9_trace__"]

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
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-059",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "code-generation",
        "dataclass",
        "event-driven",
        "foundation",
        "http-client",
        "logging",
        "tracing",
    ],
    "keywords": ["enrich", "enriched", "enricher"],
    "business_value": "Provides context enricher components including EnrichedContext, ContextEnricher",
    "last_modified": "2026-01-02T15:16:47Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
