"""
L9 Memory - Checkpoint Validator
Version: 1.0.0

Cryptographic integrity validation for agent checkpoints.
Implements memory_spec_v3.0.yaml integrity requirements.

Responsibilities:
- Generate SHA-256 checksums for checkpoint state
- Validate checksum on restore (detect corruption)
- Schema version detection and validation
"""

from __future__ import annotations

import hashlib
import json
import structlog
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from enum import Enum

logger = structlog.get_logger(__name__)


class SchemaVersion(Enum):
    """Checkpoint schema versions for backward compatibility."""

    V1_0 = "1.0"  # Initial schema (no checksum)
    V1_1 = "1.1"  # Added checksum field
    V2_0 = "2.0"  # Future: encrypted storage

    @classmethod
    def current(cls) -> "SchemaVersion":
        """Return current schema version."""
        return cls.V1_1


class CheckpointValidator:
    """
    Cryptographic validator for checkpoint integrity.

    Uses SHA-256 to generate and validate checksums for checkpoint state.
    Supports schema versioning for backward compatibility.
    """

    CHECKSUM_FIELD = "_checksum"
    SCHEMA_VERSION_FIELD = "_schema_version"
    CHECKSUM_TIMESTAMP_FIELD = "_checksum_timestamp"

    def __init__(self):
        """Initialize checkpoint validator."""
        logger.info("CheckpointValidator initialized")

    def generate_checksum(self, state: Dict[str, Any]) -> str:
        """
        Generate SHA-256 checksum for checkpoint state.

        Args:
            state: Checkpoint state dict (without checksum fields)

        Returns:
            Hex-encoded SHA-256 checksum
        """
        # Remove any existing checksum fields before computing
        clean_state = self._strip_checksum_fields(state)

        # Serialize deterministically (sorted keys)
        serialized = json.dumps(clean_state, sort_keys=True, default=str)

        # Compute SHA-256
        checksum = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        logger.debug(
            "Checksum generated",
            checksum=checksum[:16] + "...",
            state_size=len(serialized),
        )

        return checksum

    def add_checksum_to_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add checksum and schema version to state dict.

        Args:
            state: Original checkpoint state

        Returns:
            State dict with checksum fields added
        """
        checksum = self.generate_checksum(state)

        # Create new dict with checksum fields
        validated_state = {
            **state,
            self.CHECKSUM_FIELD: checksum,
            self.SCHEMA_VERSION_FIELD: SchemaVersion.current().value,
            self.CHECKSUM_TIMESTAMP_FIELD: datetime.utcnow().isoformat(),
        }

        return validated_state

    def validate_checksum(
        self,
        state: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate checksum of a restored checkpoint state.

        Args:
            state: Checkpoint state dict (with checksum fields)

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, "reason") if invalid or no checksum
        """
        # Check if checksum exists
        stored_checksum = state.get(self.CHECKSUM_FIELD)
        if stored_checksum is None:
            # Legacy checkpoint without checksum (V1.0)
            schema_version = state.get(self.SCHEMA_VERSION_FIELD, "1.0")
            if schema_version == "1.0":
                logger.debug(
                    "Legacy checkpoint (V1.0) without checksum, skipping validation"
                )
                return True, None
            else:
                return False, "Missing checksum field"

        # Compute checksum of current state
        computed_checksum = self.generate_checksum(state)

        # Compare
        if computed_checksum == stored_checksum:
            logger.debug(
                "Checksum validation passed",
                checksum=stored_checksum[:16] + "...",
            )
            return True, None
        else:
            logger.warning(
                "Checksum validation FAILED - possible corruption",
                stored=stored_checksum[:16] + "...",
                computed=computed_checksum[:16] + "...",
            )
            return (
                False,
                f"Checksum mismatch: stored={stored_checksum[:16]}..., computed={computed_checksum[:16]}...",
            )

    def get_schema_version(self, state: Dict[str, Any]) -> SchemaVersion:
        """
        Detect schema version of checkpoint state.

        Args:
            state: Checkpoint state dict

        Returns:
            SchemaVersion enum value
        """
        version_str = state.get(self.SCHEMA_VERSION_FIELD, "1.0")

        try:
            return SchemaVersion(version_str)
        except ValueError:
            logger.warning(
                "Unknown schema version, defaulting to V1_0",
                version=version_str,
            )
            return SchemaVersion.V1_0

    def _strip_checksum_fields(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove checksum-related fields from state for computation.

        Args:
            state: State dict possibly containing checksum fields

        Returns:
            State dict without checksum fields
        """
        return {
            k: v
            for k, v in state.items()
            if k
            not in (
                self.CHECKSUM_FIELD,
                self.SCHEMA_VERSION_FIELD,
                self.CHECKSUM_TIMESTAMP_FIELD,
            )
        }

    def strip_metadata_for_restore(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove all internal metadata fields before returning to caller.

        Args:
            state: State dict with metadata

        Returns:
            Clean state dict for agent restoration
        """
        return {k: v for k, v in state.items() if not k.startswith("_")}


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "CheckpointValidator",
    "SchemaVersion",
]
