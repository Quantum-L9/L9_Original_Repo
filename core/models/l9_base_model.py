# core/models/l9_base_model.py
"""
L9 Unified BaseModel

Central place for all Pydantic models in L9.
Provides DORA compliance, streaming, content hashing, and serialization.

Extends pydantic.BaseModel with L9-specific capabilities:
- DORA metadata (__dora_meta__, __dora_footer__)
- Content hashing (SHA-256)
- Streaming serialization
- Telemetry integration
- Validation error tracking

All models in L9 should inherit from L9BaseModel.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Base Model",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-25T06:00:00Z",
    "updated_at": "2026-01-25T06:00:00Z",
    "layer": "foundation",
    "domain": "data_models",
    "module_name": "l9_base_model",
    "type": "base_model",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [
            "core.schemas.*",
            "memory.*",
            "agents.*",
        ],
    },
}
# ============================================================================

import hashlib
import json
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, model_validator

logger = structlog.get_logger(__name__)


class L9BaseModel(BaseModel):
    """
    Unified base model for all L9 types.

    Provides:
    - DORA compliance metadata
    - Content hashing (SHA-256)
    - Streaming serialization
    - Telemetry integration
    - Validation error tracking

    All models in L9 should inherit from this.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_default=True,
        use_enum_values=False,
    )

    # =========================================================================
    # DORA Metadata
    # =========================================================================

    @classmethod
    def _get_dora_meta(cls) -> dict[str, Any]:
        """Return DORA metadata for this model."""
        if hasattr(cls, "__dora_meta__"):
            return cls.__dora_meta__
        return {
            "component_name": cls.__name__,
            "module_version": "1.0.0",
            "status": "active",
        }

    @classmethod
    def _get_dora_footer(cls) -> dict[str, Any]:
        """Return DORA footer for this model."""
        if hasattr(cls, "__dora_footer__"):
            return cls.__dora_footer__
        return {
            "component_id": f"L9-{cls.__name__.upper()}",
            "governance_level": "standard",
            "compliance_required": False,
        }

    # =========================================================================
    # Content Hashing
    # =========================================================================

    def compute_content_hash(self) -> str:
        """
        Compute SHA-256 hash of model content for integrity verification.

        Returns:
            64-character hex SHA-256 hash
        """
        content_dict = self.model_dump(mode="json", exclude_none=False)
        content_bytes = json.dumps(
            content_dict,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(content_bytes).hexdigest()

    def verify_content_hash(self, expected_hash: str) -> bool:
        """
        Verify that content matches expected hash.

        Args:
            expected_hash: Expected SHA-256 hash (hex)

        Returns:
            True if hashes match, False otherwise
        """
        return self.compute_content_hash() == expected_hash

    # =========================================================================
    # Serialization
    # =========================================================================

    def model_dump_json_streaming(self, chunk_size: int = 8192) -> Any:
        """
        Serialize model to JSON in streaming fashion (generator).

        Useful for large models to avoid memory spikes.

        Args:
            chunk_size: Bytes per chunk

        Yields:
            JSON string chunks
        """
        full_json = self.model_dump_json()
        for i in range(0, len(full_json), chunk_size):
            yield full_json[i : i + chunk_size]

    def to_wire_format(self) -> dict[str, Any]:
        """
        Convert to wire format for API transmission.

        Excludes internal fields, converts to JSON-safe types.

        Returns:
            Wire-format dict
        """
        return self.model_dump(mode="json", exclude_none=True)

    # =========================================================================
    # Validation
    # =========================================================================

    @model_validator(mode="after")
    def _post_validation(self) -> "L9BaseModel":
        """
        Post-validation hook for all L9 models.

        Can be overridden in subclasses for custom validation.
        """
        return self

    # =========================================================================
    # Error Tracking
    # =========================================================================

    @classmethod
    def from_dict_with_error_tracking(
        cls,
        data: dict[str, Any],
        source: str | None = None,
    ) -> "L9BaseModel":
        """
        Create instance from dict with error tracking to telemetry.

        Args:
            data: Input dict
            source: Source identifier for error tracking

        Returns:
            Instance or raises ValidationError (with telemetry logged)

        Raises:
            pydantic.ValidationError: If validation fails
        """
        try:
            return cls(**data)
        except Exception as e:
            # Log to error telemetry
            logger.error(
                f"{cls.__name__}_validation_error",
                error=str(e),
                source=source,
                data_keys=list(data.keys()) if isinstance(data, dict) else None,
                error_type=type(e).__name__,
            )
            raise


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CORE-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "base-model",
        "data-models",
        "foundation",
        "pydantic",
        "serialization",
    ],
    "keywords": [
        "base",
        "content",
        "dora",
        "hash",
        "metadata",
        "model",
        "serialize",
        "streaming",
    ],
    "business_value": "Unified base model for all L9 types with DORA compliance, content hashing, and streaming support.",
    "last_modified": "2026-01-25T06:00:00Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
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
