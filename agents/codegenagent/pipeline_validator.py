"""
CodeGenAgent Pipeline Validator
===============================

Validates that meta.yaml contains all required fields before generation.
Supports configurable validation rules and schema-based checking.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Pipeline Validator",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-15T23:26:08Z",
    "updated_at": "2026-01-15T23:33:19Z",
    "layer": "intelligence",
    "domain": "data_models",
    "module_name": "pipeline_validator",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================


DEFAULT_REQUIRED_FIELDS = [
    "name",
    "description",
]

RECOMMENDED_FIELDS = [
    "inputs",
    "outputs",
    "responsibilities",
    "version",
]

WIRING_FIELDS = [
    "wiring",
    "dependencies",
]

# Field type validators
FIELD_TYPES = {
    "name": str,
    "description": str,
    "version": str,
    "inputs": (list, str),
    "outputs": (list, str),
    "responsibilities": list,
    "wiring": dict,
    "dependencies": list,
    "required_tests": (list, str, int),
}


# =============================================================================
# DATA CLASSES
# =============================================================================


class ValidationLevel(str, Enum):
    """Validation issue severity."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue."""

    level: ValidationLevel
    field: str
    message: str
    expected: str | None = None
    actual: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the ValidationIssue, including its severity level, affected field, message, and expected versus actual values."""
        return {
            "level": self.level.value,
            "field": self.field,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass
class ValidationResult:
    """Result of meta validation."""

    valid: bool
    meta_name: str

    # Issues
    missing_fields: list[str] = field(default_factory=list)
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    info: list[ValidationIssue] = field(default_factory=list)

    # Metadata
    fields_checked: int = 0
    validation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def total_issues(self) -> int:
        """
        Calculates the total number of validation issues (errors, warnings, info) in the ValidationResult.

        Args:
            None

        Returns:
            int: Total count of validation issues including errors, warnings, and informational messages.
        """
        return len(self.errors) + len(self.warnings) + len(self.info)

    @property
    def is_error_free(self) -> bool:
        """
        Checks if the validation results contain no errors, indicating the meta.yaml is error-free.

        Args: None

        Returns:
            bool: True if there are no validation errors, False otherwise.
        """
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the ValidationResult, including validation status, meta information, missing fields, errors, and warnings."""
        return {
            "valid": self.valid,
            "meta_name": self.meta_name,
            "missing_fields": self.missing_fields,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "info": [i.to_dict() for i in self.info],
            "fields_checked": self.fields_checked,
            "validation_timestamp": self.validation_timestamp.isoformat(),
            "total_issues": self.total_issues,
        }

    def to_summary(self) -> str:
        """Generate summary string."""
        status = "✅ VALID" if self.valid else "❌ INVALID"
        return (
            f"{status} | {self.meta_name} | "
            f"Errors: {len(self.errors)} | "
            f"Warnings: {len(self.warnings)} | "
            f"Missing: {len(self.missing_fields)}"
        )


# =============================================================================
# EXCEPTIONS
# =============================================================================


class PipelineValidatorError(Exception):
    """Exception raised during validation."""

    pass


class SchemaError(PipelineValidatorError):
    """Exception raised for schema violations."""

    pass


# =============================================================================
# PIPELINE VALIDATOR
# =============================================================================


class PipelineValidator:
    """
    Meta Specification Validator.

    Validates that meta.yaml contains all required fields
    with correct types before code generation.
    """

    def __init__(
        self,
        required_fields: list[str] | None = None,
        strict_mode: bool = False,
        custom_validators: dict[str, callable] | None = None,
    ):
        """
        Initialize the Pipeline Validator.

        Args:
            required_fields: List of required field names
            strict_mode: Treat warnings as errors
            custom_validators: Dict of field name to validator function
        """
        self.required_fields = required_fields or DEFAULT_REQUIRED_FIELDS.copy()
        self.strict_mode = strict_mode
        self._custom_validators = custom_validators or {}

        logger.info(
            "pipeline_validator_initialized",
            required_fields=self.required_fields,
            strict_mode=strict_mode,
            custom_validators=list(self._custom_validators.keys()),
        )

    def validate_meta(self, meta: dict[str, Any]) -> ValidationResult:
        """
        Validate a meta specification.

        Args:
            meta: Meta specification dictionary

        Returns:
            ValidationResult with all findings
        """
        meta_name = meta.get("name") or meta.get("filename", "unknown")

        result = ValidationResult(
            valid=True,
            meta_name=meta_name,
        )

        logger.info("validation_started", meta_name=meta_name)

        # Run all validation checks
        self.check_required_fields(meta, result)
        self.validate_structure(meta, result)
        self.validate_types(meta, result)
        self.validate_wiring(meta, result)
        self._run_custom_validators(meta, result)

        # Count fields checked
        result.fields_checked = len(meta.keys())

        # Determine validity
        if result.errors or result.missing_fields:
            result.valid = False

        if self.strict_mode and result.warnings:
            result.valid = False

        logger.info(
            "validation_complete",
            meta_name=meta_name,
            valid=result.valid,
            errors=len(result.errors),
            warnings=len(result.warnings),
            missing=len(result.missing_fields),
        )

        return result

    def check_required_fields(
        self,
        meta: dict[str, Any],
        result: ValidationResult,
    ) -> None:
        """
        Check for required fields.

        Args:
            meta: Meta specification
            result: ValidationResult to update
        """
        for field_name in self.required_fields:
            if field_name not in meta:
                result.missing_fields.append(field_name)
                result.errors.append(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        field=field_name,
                        message=f"Required field '{field_name}' is missing",
                    )
                )
            elif meta[field_name] is None:
                result.errors.append(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        field=field_name,
                        message=f"Required field '{field_name}' is null",
                    )
                )
            elif isinstance(meta[field_name], str) and not meta[field_name].strip():
                result.errors.append(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        field=field_name,
                        message=f"Required field '{field_name}' is empty",
                    )
                )

    def validate_structure(
        self,
        meta: dict[str, Any],
        result: ValidationResult,
    ) -> None:
        """
        Validate overall structure of meta.

        Args:
            meta: Meta specification
            result: ValidationResult to update
        """
        # Check for recommended fields
        for field_name in RECOMMENDED_FIELDS:
            if field_name not in meta:
                result.warnings.append(
                    ValidationIssue(
                        level=ValidationLevel.WARNING,
                        field=field_name,
                        message=f"Recommended field '{field_name}' is missing",
                    )
                )

        # Check for unknown fields (info only)
        known_fields = set(FIELD_TYPES.keys()) | set(self.required_fields)
        for field_name in meta:
            if field_name not in known_fields and not field_name.startswith("_"):
                result.info.append(
                    ValidationIssue(
                        level=ValidationLevel.INFO,
                        field=field_name,
                        message=f"Unknown field '{field_name}' (will be ignored)",
                    )
                )

    def validate_types(
        self,
        meta: dict[str, Any],
        result: ValidationResult,
    ) -> None:
        """
        Validate field types.

        Args:
            meta: Meta specification
            result: ValidationResult to update
        """
        for field_name, expected_type in FIELD_TYPES.items():
            if field_name not in meta:
                continue

            value = meta[field_name]
            if value is None:
                continue

            # Handle tuple of types (any of)
            if isinstance(expected_type, tuple):
                if not isinstance(value, expected_type):
                    result.errors.append(
                        ValidationIssue(
                            level=ValidationLevel.ERROR,
                            field=field_name,
                            message=f"Field '{field_name}' has wrong type",
                            expected=str(expected_type),
                            actual=type(value).__name__,
                        )
                    )
            else:
                if not isinstance(value, expected_type):
                    result.errors.append(
                        ValidationIssue(
                            level=ValidationLevel.ERROR,
                            field=field_name,
                            message=f"Field '{field_name}' has wrong type",
                            expected=expected_type.__name__,
                            actual=type(value).__name__,
                        )
                    )

    def validate_wiring(
        self,
        meta: dict[str, Any],
        result: ValidationResult,
    ) -> None:
        """
        Validate wiring configuration.

        Args:
            meta: Meta specification
            result: ValidationResult to update
        """
        wiring = meta.get("wiring")
        if not wiring:
            result.info.append(
                ValidationIssue(
                    level=ValidationLevel.INFO,
                    field="wiring",
                    message="No wiring configuration (standalone module)",
                )
            )
            return

        if not isinstance(wiring, dict):
            result.errors.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    field="wiring",
                    message="Wiring must be a dictionary",
                    expected="dict",
                    actual=type(wiring).__name__,
                )
            )
            return

        # Validate wiring structure
        valid_wiring_keys = {
            "source",
            "output",
            "styles",
            "checks",
            "required_fields",
            "reads",
            "writes",
            "triggers",
            "consumers",
            "dependencies",
        }

        for key in wiring:
            if key not in valid_wiring_keys:
                result.info.append(
                    ValidationIssue(
                        level=ValidationLevel.INFO,
                        field=f"wiring.{key}",
                        message=f"Unknown wiring key '{key}'",
                    )
                )

    def _run_custom_validators(
        self,
        meta: dict[str, Any],
        result: ValidationResult,
    ) -> None:
        """Run any custom validators."""
        for field_name, validator in self._custom_validators.items():
            if field_name not in meta:
                continue

            try:
                is_valid, message = validator(meta[field_name])
                if not is_valid:
                    result.errors.append(
                        ValidationIssue(
                            level=ValidationLevel.ERROR,
                            field=field_name,
                            message=message,
                        )
                    )
            except Exception as e:
                result.warnings.append(
                    ValidationIssue(
                        level=ValidationLevel.WARNING,
                        field=field_name,
                        message=f"Custom validator failed: {e}",
                    )
                )

    def add_required_field(self, field_name: str) -> None:
        """Add a required field to validation."""
        if field_name not in self.required_fields:
            self.required_fields.append(field_name)

    def add_custom_validator(
        self,
        field_name: str,
        validator: callable,
    ) -> None:
        """
        Add a custom validator function.

        Args:
            field_name: Field to validate
            validator: Function(value) -> (bool, message)
        """
        self._custom_validators[field_name] = validator

    def validate_batch(
        self,
        metas: list[dict[str, Any]],
    ) -> list[ValidationResult]:
        """
        Validate multiple meta specifications.

        Args:
            metas: List of meta specifications

        Returns:
            List of ValidationResults
        """
        results = []
        for meta in metas:
            results.append(self.validate_meta(meta))

        passed = sum(1 for r in results if r.valid)
        logger.info(
            "batch_validation_complete",
            total=len(metas),
            passed=passed,
            failed=len(metas) - passed,
        )

        return results


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def validate_meta(meta: dict[str, Any]) -> ValidationResult:
    """
    Validate a meta specification.

    Args:
        meta: Meta specification dictionary

    Returns:
        ValidationResult
    """
    validator = PipelineValidator()
    return validator.validate_meta(meta)


def is_valid_meta(meta: dict[str, Any]) -> bool:
    """
    Quick check if meta is valid.

    Args:
        meta: Meta specification dictionary

    Returns:
        True if valid, False otherwise
    """
    validator = PipelineValidator()
    result = validator.validate_meta(meta)
    return result.valid


def get_missing_fields(
    meta: dict[str, Any],
    required: list[str] | None = None,
) -> list[str]:
    """
    Get list of missing required fields.

    Args:
        meta: Meta specification
        required: Optional custom required fields list

    Returns:
        List of missing field names
    """
    fields = required or DEFAULT_REQUIRED_FIELDS
    return [f for f in fields if f not in meta or meta[f] is None]


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-007",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "batch-processing",
        "data-models",
        "dataclass",
        "filesystem",
        "intelligence",
        "logging",
        "messaging",
        "testing",
        "validation",
    ],
    "keywords": [
        "batch",
        "check",
        "custom",
        "field",
        "fields",
        "free",
        "issue",
        "issues",
    ],
    "business_value": "Provides pipeline validator components including ValidationLevel, ValidationIssue, ValidationResult",
    "last_modified": "2026-01-15T23:33:19Z",
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
