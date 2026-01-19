"""
L9 Memory - Packet Validator
Version: 2.0.0

Centralized validation for PacketEnvelopeIn before it hits the DAG.
This is where we enforce business-level constraints above Pydantic's typing.

v2.0.0: Expanded to cover all packet types used in codebase. Uses warn mode
for unknown types instead of hard rejection to avoid breaking new integrations.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Packet Validator",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-14T13:21:36Z",
    "layer": "learning",
    "domain": "error_handling",
    "module_name": "packet_validator",
    "type": "exception",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "memory.ingestion",
            "memory.substrate_service",
            "memory.validators.__init__",
            "tests.memory.test_ingestion_pipeline_audit",
            "tests.memory.test_packet_validation_v2",
        ],
    },
}
# ============================================================================

import structlog
from datetime import datetime
from typing import Any, Iterable, Optional

from pydantic import ValidationError

from core.schemas import (
    PacketEnvelopeIn,
    VALID_DERIVE_TYPES,
)
from memory.audit_utils import detect_injection_markers, detect_pii_types

logger = structlog.get_logger(__name__)


# Core packet types (strictly enforced)
CORE_PACKET_TYPES: set[str] = {
    "event",
    "memory_write",
    "reasoning_trace",
    "tool_call",
    "tool_result",
    "message",
}

# Extended packet types (domain-specific, also valid)
EXTENDED_PACKET_TYPES: set[str] = {
    # Insights & knowledge
    "insight",
    "decision",
    "audit",
    # Agent persistence
    "checkpoint_created",
    "checkpoint_restored",
    "checkpoints_pruned",
    # Slack integration
    "slack.in",
    "slack.out",
    "slack.command",
    "slack.command.out",
    "slack.l_agent.out",
    # Testing
    "smoke_test",
    "test",
}

# Combined set for validation
ALLOWED_PACKET_TYPES: set[str] = CORE_PACKET_TYPES | EXTENDED_PACKET_TYPES


class PacketValidationError(Exception):
    """Raised when a packet fails custom validation with structured error details."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        error_code: Optional[str] = None,
    ):
        """
        Initialize validation error with structured details.

        Args:
            message: Human-readable error message
            field: Dotted path to the invalid field (e.g., 'confidence.score')
            value: The invalid value that caused the error
            error_code: Machine-readable error code for programmatic handling
        """
        self.field = field
        self.value = value
        self.error_code = error_code
        super().__init__(message)


class PacketValidator:
    """Static helpers for validating PacketEnvelopeIn instances."""

    @staticmethod
    def validate(packet_in: PacketEnvelopeIn, strict: bool = False) -> None:
        """
        Perform custom validation:
        - Pydantic structural validation
        - packet_type sanity check
        - TTL future check
        - Confidence range check
        - Provenance validation (derive_type, source_timestamp)

        Args:
            packet_in: PacketEnvelopeIn to validate
            strict: If True, reject unknown packet_types. If False (default), warn only.

        Note: This is a pure function with no I/O, safe to call from async contexts.
        """
        # Structural validation via Pydantic
        try:
            PacketEnvelopeIn.model_validate(packet_in.model_dump())
        except ValidationError as exc:
            raise PacketValidationError(
                f"Structural validation failed: {exc}",
                field="packet",
                value=None,
                error_code="STRUCTURAL_VALIDATION_FAILED",
            ) from exc

        # packet_type check
        if packet_in.packet_type not in ALLOWED_PACKET_TYPES:
            if strict:
                raise PacketValidationError(
                    f"packet_type '{packet_in.packet_type}' not in allowed types. "
                    f"Core: {sorted(CORE_PACKET_TYPES)}, Extended: {sorted(EXTENDED_PACKET_TYPES)}",
                    field="packet_type",
                    value=packet_in.packet_type,
                    error_code="INVALID_PACKET_TYPE",
                )
            else:
                # Warn but allow (future-proofs for new integrations)
                logger.warning(
                    "packet_type_unknown",
                    packet_type=packet_in.packet_type,
                    hint="Consider adding to EXTENDED_PACKET_TYPES in packet_validator.py",
                )

        # TTL must be in future (if provided)
        if packet_in.ttl and packet_in.ttl < datetime.utcnow():
            raise PacketValidationError(
                f"ttl must be in the future, got {packet_in.ttl}",
                field="ttl",
                value=packet_in.ttl,
                error_code="TTL_IN_PAST",
            )

        # Confidence score must be 0.0-1.0 (if provided)
        if packet_in.confidence:
            score = (
                packet_in.confidence.get("score")
                if isinstance(packet_in.confidence, dict)
                else getattr(packet_in.confidence, "score", None)
            )
            if score is not None and (score < 0.0 or score > 1.0):
                raise PacketValidationError(
                    f"confidence.score must be between 0.0 and 1.0, got {score}",
                    field="confidence.score",
                    value=score,
                    error_code="CONFIDENCE_OUT_OF_RANGE",
                )

        # Provenance validation (v2.0.0 fields)
        PacketValidator._validate_provenance(packet_in)

    @staticmethod
    def _validate_provenance(packet_in: PacketEnvelopeIn) -> None:
        """
        Validate provenance fields if present.

        Checks:
        - derive_type is one of: 'direct', 'inferred', 'synthesized'
        - source_timestamp is not in the future

        Args:
            packet_in: PacketEnvelopeIn to validate
        """
        if packet_in.provenance is None:
            return  # No provenance = valid (optional)

        provenance = packet_in.provenance

        # Handle both dict and object access patterns
        if isinstance(provenance, dict):
            derive_type = provenance.get("derive_type")
            source_timestamp = provenance.get("source_timestamp")
        else:
            derive_type = getattr(provenance, "derive_type", None)
            source_timestamp = getattr(provenance, "source_timestamp", None)

        # Validate derive_type if present
        if derive_type is not None:
            if derive_type not in VALID_DERIVE_TYPES:
                raise PacketValidationError(
                    f"derive_type must be one of {sorted(VALID_DERIVE_TYPES)}, got '{derive_type}'",
                    field="provenance.derive_type",
                    value=derive_type,
                    error_code="INVALID_DERIVE_TYPE",
                )

        # Validate source_timestamp if present (must not be in future)
        if source_timestamp is not None:
            # Handle string timestamps
            if isinstance(source_timestamp, str):
                try:
                    source_timestamp = datetime.fromisoformat(
                        source_timestamp.replace("Z", "+00:00")
                    )
                except ValueError:
                    raise PacketValidationError(
                        f"source_timestamp must be valid ISO format, got '{source_timestamp}'",
                        field="provenance.source_timestamp",
                        value=source_timestamp,
                        error_code="INVALID_SOURCE_TIMESTAMP_FORMAT",
                    )

            if source_timestamp > datetime.utcnow():
                raise PacketValidationError(
                    f"source_timestamp cannot be in the future, got {source_timestamp}",
                    field="provenance.source_timestamp",
                    value=source_timestamp,
                    error_code="FUTURE_SOURCE_TIMESTAMP",
                )

    @staticmethod
    def allowed_types() -> Iterable[str]:
        """Return all allowed packet types (core + extended)."""
        return sorted(ALLOWED_PACKET_TYPES)

    @staticmethod
    def core_types() -> Iterable[str]:
        """Return core packet types only."""
        return sorted(CORE_PACKET_TYPES)

    @staticmethod
    def extended_types() -> Iterable[str]:
        """Return extended packet types only."""
        return sorted(EXTENDED_PACKET_TYPES)

    @staticmethod
    def scan_security(packet_in: PacketEnvelopeIn) -> dict[str, list[str]]:
        """
        Scan packet payload for PII and injection markers.

        This is a non-blocking security scan that returns detected issues
        without raising exceptions. Use for audit logging and telemetry.

        Args:
            packet_in: Packet to scan

        Returns:
            Dict with keys:
                - pii_types: List of detected PII categories (email, ssn, phone, api_key)
                - injection_markers: List of detected prompt injection markers
        """
        pii_types = list(detect_pii_types(packet_in.payload))
        injection_markers = list(detect_injection_markers(packet_in.payload))
        return {
            "pii_types": pii_types,
            "injection_markers": injection_markers,
        }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "MEM-LEAR-059",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas", "memory.audit_utils"],
    "tags": [
        "api",
        "error-handling",
        "event-driven",
        "exception",
        "learning",
        "logging",
        "messaging",
        "rest-api",
        "testing",
        "tracing",
    ],
    "keywords": [
        "allowed",
        "core",
        "extended",
        "memory",
        "packet",
        "scan",
        "security",
        "types",
    ],
    "business_value": "This is where we enforce business-level constraints above Pydantic's typing. v2.0.0: Expanded to cover all packet types used in codebase. Uses warn mode for unknown types instead of hard rejection to ",
    "last_modified": "2026-01-14T13:21:36Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
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
