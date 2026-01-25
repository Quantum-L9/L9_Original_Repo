#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Module: Packet Validator
Purpose: Validate PacketEnvelope structure and fields
================================================================================

Summary:
    Validates incoming packets for required fields, data types, and business
    rules. Part of the reasoning pipeline Stage 1 (Ingestion & Validation).
    Ensures all packets meet L9 protocol requirements before processing.

Extended Metadata:
    See __footer_meta__ at module footer. Runtime trace in __l9_trace__.

================================================================================
# HEADER META - Module Identity (Static)
# component_id: SEC-DTB-001
# layer: security
# domain: validation
# governance_level: high
# created_at: 2026-01-02T03:35:00Z
================================================================================
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Packet Validator",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-23T15:07:20Z",
    "updated_at": "2026-01-24T13:02:52Z",
    "layer": "operations",
    "domain": "domain_tensor_bridge",
    "module_name": "packet_validator",
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

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

from core.schemas import PacketEnvelope, PacketKind

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of packet validation."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PacketValidator:
    """
    Validates PacketEnvelope structures.

    Validation rules:
    - Required fields present (source_id, kind, payload)
    - Field types correct
    - Payload structure matches expected format
    - Security constraints met
    """

    REQUIRED_FIELDS = ["source_id", "kind", "payload"]
    MAX_PAYLOAD_SIZE = 1024 * 1024  # 1MB

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode

    def validate_packet(self, packet: PacketEnvelope) -> ValidationResult:
        """
        Validate packet structure and fields.

        Args:
            packet: Packet to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Check required fields
        for field_name in self.REQUIRED_FIELDS:
            if not hasattr(packet, field_name):
                errors.append(f"Missing required field: {field_name}")
            elif getattr(packet, field_name) is None:
                if self.strict_mode:
                    errors.append(f"Field is None: {field_name}")
                else:
                    warnings.append(f"Field is None: {field_name}")

        # Validate source_id
        if hasattr(packet, "source_id") and packet.source_id:
            if not self._validate_source_id(packet.source_id):
                errors.append(f"Invalid source_id format: {packet.source_id}")

        # Validate kind
        if hasattr(packet, "kind") and packet.kind:
            if not self._validate_kind(packet.kind):
                errors.append(f"Invalid packet kind: {packet.kind}")

        # Validate payload
        if hasattr(packet, "payload") and packet.payload:
            payload_validation = self._validate_payload(packet.payload)
            errors.extend(payload_validation["errors"])
            warnings.extend(payload_validation["warnings"])

        # Log validation result
        if errors:
            logger.warning(
                "packet_validation_failed",
                error_count=len(errors),
                errors=errors[:3],  # Log first 3
            )
        else:
            logger.debug("packet_validation_passed")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata={"strict_mode": self.strict_mode},
        )

    def _validate_source_id(self, source_id: str) -> bool:
        """Validate source_id format."""
        if not isinstance(source_id, str):
            return False
        if len(source_id) < 1 or len(source_id) > 256:
            return False
        # Allow alphanumeric, underscore, hyphen, dot
        allowed = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-."
        )
        return all(c in allowed for c in source_id)

    def _validate_kind(self, kind: Any) -> bool:
        """Validate packet kind."""
        if isinstance(kind, PacketKind):
            return True
        if isinstance(kind, str):
            valid_kinds = [k.value for k in PacketKind]
            return kind in valid_kinds
        return False

    def _validate_payload(self, payload: Any) -> Dict[str, List[str]]:
        """Validate payload structure and size."""
        errors = []
        warnings = []

        if not isinstance(payload, dict):
            errors.append(f"Payload must be dict, got {type(payload).__name__}")
            return {"errors": errors, "warnings": warnings}

        # Check size (estimate)
        import json

        try:
            payload_str = json.dumps(payload)
            if len(payload_str) > self.MAX_PAYLOAD_SIZE:
                errors.append(
                    f"Payload exceeds max size: {len(payload_str)} > {self.MAX_PAYLOAD_SIZE}"
                )
        except (TypeError, ValueError):
            warnings.append("Could not serialize payload for size check")

        return {"errors": errors, "warnings": warnings}


# ============================================================================
# FOOTER META - Extended Metadata (Static)
# ============================================================================

__footer_meta__ = {
    "component_id": "SEC-DTB-001",
    "component_name": "Packet Validator",
    "module_version": "1.0.0",
    "created_at": "2026-01-02T03:35:00Z",
    "created_by": "L9_Codegen_Engine",
    "layer": "security",
    "domain": "validation",
    "type": "validator",
    "status": "active",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Validate PacketEnvelope structure and fields",
    "summary": "Validates incoming packets for required fields, data types, and business rules as part of reasoning pipeline Stage 1.",
    "dependencies": ["structlog", "l9.core.schemas"],
}

__all__ = [
    "PacketValidator",
    "ValidationResult",
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
    "component_id": "DOM-OPER-015",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas"],
    "tags": [
        "dataclass",
        "debugging",
        "domain-tensor-bridge",
        "logging",
        "operations",
        "serialization",
        "tracing",
        "validation",
    ],
    "keywords": ["packet", "validate", "validation", "validator"],
    "business_value": "Provides packet validator components including ValidationResult, PacketValidator",
    "last_modified": "2026-01-24T13:02:52Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
