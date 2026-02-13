#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Module: Packet Router
Purpose: Route PacketEnvelopes to appropriate handlers based on type and domain
================================================================================

Summary:
    Routes incoming packets to the correct handler based on packet type,
    source domain, and routing rules. Supports dynamic handler registration
    and fallback routing for unknown packet types.

Extended Metadata:
    See __footer_meta__ at module footer. Runtime trace in __l9_trace__.

================================================================================
# HEADER META - Module Identity (Static)
# component_id: OPS-DTB-003
# layer: operations
# domain: packet_routing
# governance_level: high
# created_at: 2026-01-02T03:35:00Z
================================================================================
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Packet Router",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-02T04:39:40Z",
    "updated_at": "2026-01-02T15:16:47Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "packet_router",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import structlog

from l9.core.schemas import PacketEnvelope, PacketKind

logger = structlog.get_logger(__name__)


@dataclass
class RoutingResult:
    """Result of packet routing decision."""

    handler_name: str
    handler: Optional[Callable]
    route_confidence: float
    fallback_used: bool


class PacketRouter:
    """
    Routes packets to appropriate handlers.

    Features:
    - Type-based routing (PacketKind)
    - Domain-based routing (source_id prefix)
    - Priority routing for critical packets
    - Fallback handlers for unknown types
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._domain_handlers: Dict[str, Callable] = {}
        self._fallback_handler: Optional[Callable] = None

    def register_handler(
        self,
        packet_kind: PacketKind,
        handler: Callable,
    ) -> None:
        """Register handler for packet type."""
        self._handlers[packet_kind.value] = handler
        logger.info("handler_registered", kind=packet_kind.value)

    def register_domain_handler(
        self,
        domain: str,
        handler: Callable,
    ) -> None:
        """Register handler for domain."""
        self._domain_handlers[domain] = handler
        logger.info("domain_handler_registered", domain=domain)

    def set_fallback_handler(self, handler: Callable) -> None:
        """Set fallback handler for unknown packets."""
        self._fallback_handler = handler
        logger.info("fallback_handler_set")

    async def route_packet(self, packet: PacketEnvelope) -> str:
        """
        Determine routing for packet.

        Args:
            packet: Packet to route

        Returns:
            Handler name for this packet
        """
        packet_kind = getattr(packet, "kind", None)
        source_id = getattr(packet, "source_id", "")

        logger.info(
            "routing_packet",
            kind=packet_kind.value if packet_kind else "unknown",
            source=source_id,
        )

        # Try type-based routing first
        if packet_kind and packet_kind.value in self._handlers:
            return packet_kind.value

        # Try domain-based routing
        domain = self._extract_domain(source_id)
        if domain in self._domain_handlers:
            return f"domain:{domain}"

        # Fallback
        if self._fallback_handler:
            return "fallback"

        return "default"

    def get_handler_for_type(self, packet_type: str) -> Optional[Callable]:
        """
        Get handler for packet type.

        Args:
            packet_type: Packet type or handler name

        Returns:
            Handler callable or None
        """
        if packet_type.startswith("domain:"):
            domain = packet_type.split(":", 1)[1]
            return self._domain_handlers.get(domain)

        if packet_type == "fallback":
            return self._fallback_handler

        return self._handlers.get(packet_type)

    async def validate(self, packet: PacketEnvelope) -> "ValidationResult":
        """Validate packet structure."""
        from .packet_validator import ValidationResult

        errors = []

        if not hasattr(packet, "source_id") or not packet.source_id:
            errors.append("Missing source_id")

        if not hasattr(packet, "kind"):
            errors.append("Missing kind")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    async def route(self, packet: PacketEnvelope) -> Dict[str, Any]:
        """Route packet and return routing info."""
        handler_name = await self.route_packet(packet)
        handler = self.get_handler_for_type(handler_name)

        return {
            "handler_name": handler_name,
            "handler_found": handler is not None,
            "routed": True,
        }

    def _extract_domain(self, source_id: str) -> str:
        """Extract domain from source_id."""
        if not source_id:
            return "unknown"

        # Domain is typically the first part before underscore or hyphen
        for sep in ["_", "-", "."]:
            if sep in source_id:
                return source_id.split(sep)[0]

        return source_id


# ============================================================================
# FOOTER META - Extended Metadata (Static)
# ============================================================================

__footer_meta__ = {
    "component_id": "OPS-DTB-003",
    "component_name": "Packet Router",
    "module_version": "1.0.0",
    "created_at": "2026-01-02T03:35:00Z",
    "created_by": "L9_Codegen_Engine",
    "layer": "operations",
    "domain": "packet_routing",
    "type": "router",
    "status": "active",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Route PacketEnvelopes to appropriate handlers",
    "summary": "Routes incoming packets to the correct handler based on packet type, source domain, and routing rules.",
    "dependencies": ["structlog", "l9.core.schemas"],
}

__all__ = [
    "PacketRouter",
    "RoutingResult",
    "__footer_meta__",
    "__l9_trace__",
]

# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
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

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-048",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "code-generation",
        "dataclass",
        "foundation",
        "logging",
        "routing",
        "tracing",
    ],
    "keywords": [
        "domain",
        "fallback",
        "handler",
        "packet",
        "register",
        "route",
        "router",
        "routing",
    ],
    "business_value": "Provides packet router components including RoutingResult, PacketRouter",
    "last_modified": "2026-01-02T15:16:47Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
