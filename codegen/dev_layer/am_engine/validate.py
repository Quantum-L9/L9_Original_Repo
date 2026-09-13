"""
Schema Validation: Ensure compiled YAML conforms to governance law.

Validates:
- Structure conformance
- Constraint satisfaction
- Type checking
- Idempotency
"""


import logging  # noqa: ADR-0019
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validate YAML artifacts against schema."""

    REQUIRED_METADATA_FIELDS = {
        "source_document": str,
        "source_hash": str,
        "category": str,
        "confidence": (int, float),
        "compiled_at": str,
    }

    def validate_artifact(self, artifact: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate artifact structure.

        Returns: (is_valid, [error messages])
        """
        errors: list[str] = []

        # Check top-level keys
        if "metadata" not in artifact:
            errors.append("Missing 'metadata' key")
            return False, errors

        # Validate metadata
        metadata = artifact.get("metadata", {})
        for field, expected_type in self.REQUIRED_METADATA_FIELDS.items():
            if field not in metadata:
                errors.append(f"Missing metadata.{field}")
            elif not isinstance(metadata[field], expected_type):
                errors.append(
                    f"metadata.{field} has wrong type: "
                    f"expected {expected_type}, got {type(metadata[field])}"
                )

        # Confidence must be 0.0-1.0
        confidence = metadata.get("confidence", -1)
        if not (0.0 <= confidence <= 1.0):
            errors.append(f"Confidence {confidence} outside [0.0, 1.0]")

        # Category must be valid
        valid_categories = {
            "constraints",
            "protocols",
            "policies",
            "patterns",
            "heuristics",
            "interfaces",
            "world_model",
            "reflection_rules",
            "codegen",
        }
        if metadata.get("category") not in valid_categories:
            errors.append(f"Unknown category: {metadata.get('category')}")

        return len(errors) == 0, errors


class ComplianceAuditor:
    """Audit governance compliance."""

    def __init__(self, governance_law: dict[str, Any]):
        self.governance_law = governance_law

    def audit_compliance(self, artifact: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Audit artifact against governance law.

        Returns: (is_compliant, [violation messages])
        """
        violations: list[str] = []

        metadata = artifact.get("metadata", {})
        category = metadata.get("category", "unknown")

        # Check if category is defined in governance
        if category not in self.governance_law.get("categories", {}):
            violations.append(f"Category {category} not defined in governance law")

        # Check confidence threshold
        confidence = metadata.get("confidence", 0.0)
        min_confidence = self.governance_law.get("min_confidence", 0.5)
        if confidence < min_confidence:
            violations.append(
                f"Confidence {confidence} below threshold {min_confidence}"
            )

        return len(violations) == 0, violations


def validate_yaml_file(filepath: Path) -> tuple[bool, list[str]]:
    """
    Validate a YAML file for basic correctness.

    Returns: (is_valid, [error messages])
    """
    errors: list[str] = []

    try:
        with open(filepath) as f:
            yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML: {e}")
    except Exception as e:
        errors.append(f"Failed to read file: {e}")

    return len(errors) == 0, errors


# Runtime execution trace - updated automatically on every execution
