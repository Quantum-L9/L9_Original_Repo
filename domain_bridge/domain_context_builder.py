#!/usr/bin/env python3
"""
================================================================================
Module: Domain Context Builder
Purpose: Build domain-specific context for reasoning
================================================================================

Summary:
    Constructs domain-specific context structures from packets and enrichment
    data. Tailors context format to each domain's requirements.

Extended Metadata:

================================================================================
# HEADER META - Module Identity (Static)
# component_id: OPS-DTB-006
# layer: operations
# domain: context_building
# governance_level: medium
# created_at: 2026-01-02T03:35:00Z
================================================================================
"""


from dataclasses import dataclass, field
from typing import Any

import structlog

from core.schemas import PacketEnvelope

logger = structlog.get_logger(__name__)


@dataclass
class DomainContext:
    """Domain-specific context structure."""

    domain: str
    entity_data: dict[str, Any] = field(default_factory=dict)
    domain_rules: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)


class DomainContextBuilder:
    """Builds domain-specific context."""

    DOMAIN_CONFIGS = {
        "plastos": {"requires_compliance": True, "risk_threshold": 0.7},
        "mortgageos": {"requires_compliance": True, "risk_threshold": 0.6},
        "default": {"requires_compliance": False, "risk_threshold": 0.5},
    }

    def build_domain_context(
        self, packet: PacketEnvelope, domain: str
    ) -> DomainContext:
        """Build context for specific domain."""
        logger.debug("building_domain_context", domain=domain)

        config = self.DOMAIN_CONFIGS.get(domain, self.DOMAIN_CONFIGS["default"])

        return DomainContext(
            domain=domain,
            entity_data=packet.payload,
            domain_rules=config,
            constraints={"max_confidence": 1.0, "min_confidence": 0.1},
        )



__all__ = ["DomainContext", "DomainContextBuilder"]
