"""
L9 Research Factory - Schema Validator
=======================================

Validates parsed schemas against Research Factory rules.

Validation Rules:
- All required keys present
- Version constraint >= 6.0.0
- File size <= 50KB
- No circular dependencies
- Valid import paths
- PascalCase agent names
- Valid governance modes
- Valid status values

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Schema Validator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-06T16:58:23Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "schema_validator",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "Redis", "S3"],
        "memory_layers": ["episodic_memory", "semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import structlog
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from services.research_factory.schema_parser import AgentSchema, parse_schema

logger = structlog.get_logger(__name__)


# =============================================================================
# Validation Result Models
# =============================================================================


@dataclass
class ValidationError:
    """Single validation error."""

    code: str
    message: str
    path: Optional[str] = None
    severity: str = "error"  # error, warning, info

    def __str__(self) -> str:
        loc = f" at {self.path}" if self.path else ""
        return f"[{self.severity.upper()}] {self.code}{loc}: {self.message}"


@dataclass
class ValidationResult:
    """Result of schema validation."""

    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    schema: Optional[AgentSchema] = None

    def add_error(self, code: str, message: str, path: Optional[str] = None) -> None:
        """Add an error to the result."""
        self.errors.append(ValidationError(code, message, path, "error"))
        self.valid = False

    def add_warning(self, code: str, message: str, path: Optional[str] = None) -> None:
        """Add a warning to the result."""
        self.warnings.append(ValidationError(code, message, path, "warning"))

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "valid": self.valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [
                {"code": e.code, "message": e.message, "path": e.path}
                for e in self.errors
            ],
            "warnings": [
                {"code": w.code, "message": w.message, "path": w.path}
                for w in self.warnings
            ],
        }


# =============================================================================
# Validation Constants
# =============================================================================

MIN_VERSION = (6, 0, 0)
MAX_FILE_SIZE_BYTES = 50 * 1024  # 50KB

REQUIRED_SECTIONS = {
    "system",
    "integration",
    "governance",
    "memorytopology",
    "communicationstack",
    "reasoningengine",
    "collaborationnetwork",
    "learningsystem",
    "worldmodelintegration",
    "cursorinstructions",
    "deployment",
    "metadata",
}

VALID_GOVERNANCE_MODES = {"hybrid", "autonomous", "supervised"}
VALID_STATUSES = {"draft", "review", "production", "deprecated"}
VALID_STORAGE_TYPES = {
    "redis",
    "redis_cluster",
    "postgres",
    "postgresql",
    "postgres + pgvector",
    "neo4j",
    "neo4j_auradb",
    "hypergraphdb",
    "s3",
    "s3_durable_archive",
    "s3_durable_archive + glacier",
}

PASCAL_CASE_PATTERN = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
PATH_PATTERN = re.compile(r"^[a-zA-Z0-9_/.-]+$")


# =============================================================================
# Validator Class
# =============================================================================


class SchemaValidator:
    """
    Validates Research Factory agent schemas.

    Usage:
        validator = SchemaValidator()
        result = validator.validate(schema)
        if not result.valid:
            for error in result.errors:
                logger.error(error)
    """

    def __init__(
        self,
        min_version: tuple[int, int, int] = MIN_VERSION,
        max_file_size: int = MAX_FILE_SIZE_BYTES,
        strict: bool = False,
    ):
        """
        Initialize validator.

        Args:
            min_version: Minimum schema version required
            max_file_size: Maximum file size in bytes
            strict: If True, treat warnings as errors
        """
        self.min_version = min_version
        self.max_file_size = max_file_size
        self.strict = strict

    def validate(self, schema: AgentSchema) -> ValidationResult:
        """
        Validate an AgentSchema instance.

        Args:
            schema: Parsed schema to validate

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(valid=True, schema=schema)

        # Run all validation checks
        self._validate_version(schema, result)
        self._validate_system_block(schema, result)
        self._validate_integration_block(schema, result)
        self._validate_governance_block(schema, result)
        self._validate_memory_topology(schema, result)
        self._validate_cursor_instructions(schema, result)
        self._validate_deployment_block(schema, result)
        self._validate_metadata_block(schema, result)

        # In strict mode, warnings become errors
        if self.strict and result.warnings:
            for warning in result.warnings:
                result.add_error(warning.code, warning.message, warning.path)

        return result

    def validate_file(self, filepath: str | Path) -> ValidationResult:
        """
        Validate a schema file.

        Args:
            filepath: Path to YAML schema file

        Returns:
            ValidationResult
        """
        path = Path(filepath)
        result = ValidationResult(valid=True)

        # Check file exists
        if not path.exists():
            result.add_error("FILE_NOT_FOUND", f"Schema file not found: {path}")
            return result

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.max_file_size:
            result.add_error(
                "FILE_TOO_LARGE",
                f"Schema file exceeds {self.max_file_size // 1024}KB limit: {file_size // 1024}KB",
                str(path),
            )
            return result

        # Parse and validate
        try:
            schema = parse_schema(path)
            return self.validate(schema)
        except Exception as e:
            result.add_error("PARSE_ERROR", str(e), str(path))
            return result

    def validate_yaml(self, yaml_content: str) -> ValidationResult:
        """
        Validate a YAML string.

        Args:
            yaml_content: YAML content as string

        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)

        # Check size
        if len(yaml_content.encode("utf-8")) > self.max_file_size:
            result.add_error(
                "CONTENT_TOO_LARGE",
                f"Schema content exceeds {self.max_file_size // 1024}KB limit",
            )
            return result

        # Parse and validate
        try:
            schema = parse_schema(yaml_content)
            return self.validate(schema)
        except Exception as e:
            result.add_error("PARSE_ERROR", str(e))
            return result

    # =========================================================================
    # Individual Validation Methods
    # =========================================================================

    def _validate_version(self, schema: AgentSchema, result: ValidationResult) -> None:
        """Validate schema version meets minimum requirement."""
        version_str = schema.metadata.version
        try:
            parts = version_str.split(".")
            version = tuple(int(p) for p in parts[:3])  # noqa: ADR-0086 - validated input

            if version < self.min_version:
                result.add_error(
                    "VERSION_TOO_LOW",
                    f"Schema version {version_str} is below minimum {'.'.join(map(str, self.min_version))}",
                    "metadata.version",
                )
        except (ValueError, IndexError):
            result.add_error(
                "INVALID_VERSION",
                f"Invalid version format: {version_str}. Expected: X.Y.Z",
                "metadata.version",
            )

    def _validate_system_block(
        self, schema: AgentSchema, result: ValidationResult
    ) -> None:
        """Validate system block."""
        system = schema.system

        # Check name is PascalCase
        if not PASCAL_CASE_PATTERN.match(system.name):
            result.add_error(
                "INVALID_NAME_FORMAT",
                f"Agent name must be PascalCase: {system.name}",
                "system.name",
            )

        # Check rootpath is valid
        if not PATH_PATTERN.match(system.rootpath):
            result.add_error(
                "INVALID_PATH",
                f"Invalid rootpath format: {system.rootpath}",
                "system.rootpath",
            )

        # Check role is not empty
        if not system.role or len(system.role.strip()) < 10:
            result.add_warning(
                "SHORT_ROLE",
                "Agent role should be at least 10 characters",
                "system.role",
            )

    def _validate_integration_block(
        self, schema: AgentSchema, result: ValidationResult
    ) -> None:
        """Validate integration block."""
        integration = schema.integration

        # Check for valid paths in connectto
        for i, path in enumerate(integration.connectto):
            if not PATH_PATTERN.match(path):
                result.add_error(
                    "INVALID_IMPORT_PATH",
                    f"Invalid import path: {path}",
                    f"integration.connectto[{i}]",
                )

        # Warn if no connections
        if not integration.connectto:
            result.add_warning(
                "NO_CONNECTIONS",
                "Agent has no connections defined",
                "integration.connectto",
            )

    def _validate_governance_block(
        self, schema: AgentSchema, result: ValidationResult
    ) -> None:
        """Validate governance block."""
        governance = schema.governance

        # Mode is already validated by Pydantic, but double-check
        if governance.mode not in VALID_GOVERNANCE_MODES:
            result.add_error(
                "INVALID_GOVERNANCE_MODE",
                f"Invalid governance mode: {governance.mode}",
                "governance.mode",
            )

        # Warn if no anchors in non-autonomous mode
        if governance.mode != "autonomous" and not governance.anchors:
            result.add_warning(
                "NO_GOVERNANCE_ANCHORS",
                "Non-autonomous agents should have governance anchors",
                "governance.anchors",
            )

        # Warn if no escalation policy
        if not governance.escalationpolicy:
            result.add_warning(
                "NO_ESCALATION_POLICY",
                "Consider defining an escalation policy",
                "governance.escalationpolicy",
            )

    def _validate_memory_topology(
        self, schema: AgentSchema, result: ValidationResult
    ) -> None:
        """Validate memory topology block."""
        memory = schema.memorytopology

        # Check that at least one memory layer is defined
        layers = [
            memory.workingmemory,
            memory.episodicmemory,
            memory.semanticmemory,
            memory.causalmemory,
            memory.longtermpersistence,
        ]

        if not any(layers):
            result.add_warning(
                "NO_MEMORY_LAYERS",
                "No memory layers defined. Consider adding at least workingmemory.",
                "memorytopology",
            )

        # Validate storage types
        for layer_name, layer in [
            ("workingmemory", memory.workingmemory),
            ("episodicmemory", memory.episodicmemory),
            ("semanticmemory", memory.semanticmemory),
            ("causalmemory", memory.causalmemory),
            ("longtermpersistence", memory.longtermpersistence),
        ]:
            if layer and layer.storagetype:
                storage = layer.storagetype.lower()
                # Check if any valid storage type is in the string
                if not any(valid in storage for valid in VALID_STORAGE_TYPES):
                    result.add_warning(
                        "UNKNOWN_STORAGE_TYPE",
                        f"Unknown storage type: {layer.storagetype}",
                        f"memorytopology.{layer_name}.storagetype",
                    )

    def _validate_cursor_instructions(
        self, schema: AgentSchema, result: ValidationResult
    ) -> None:
        """Validate cursor instructions block."""
        instructions = schema.cursorinstructions

        # Check paths in createifmissing
        for i, path in enumerate(instructions.createifmissing):
            if not PATH_PATTERN.match(path):
                result.add_error(
                    "INVALID_PATH",
                    f"Invalid directory path: {path}",
                    f"cursorinstructions.createifmissing[{i}]",
                )

        # Check files to generate
        for i, filename in enumerate(instructions.generatefiles):
            if not filename.endswith(".py") and not filename.endswith(".md"):
                result.add_warning(
                    "UNUSUAL_FILE_EXTENSION",
                    f"File has unusual extension: {filename}",
                    f"cursorinstructions.generatefiles[{i}]",
                )

        # Warn if no files to generate
        if not instructions.generatefiles:
            result.add_warning(
                "NO_FILES_TO_GENERATE",
                "No files specified for generation",
                "cursorinstructions.generatefiles",
            )

    def _validate_deployment_block(
        self, schema: AgentSchema, result: ValidationResult
    ) -> None:
        """Validate deployment block."""
        deployment = schema.deployment

        # Check endpoints have valid format
        for i, endpoint in enumerate(deployment.endpoints):
            if not endpoint.startswith("/"):
                result.add_error(
                    "INVALID_ENDPOINT",
                    f"Endpoint must start with /: {endpoint}",
                    f"deployment.endpoints[{i}]",
                )

        # Warn if no endpoints
        if not deployment.endpoints:
            result.add_warning(
                "NO_ENDPOINTS",
                "No API endpoints defined",
                "deployment.endpoints",
            )

        # Check replicas
        if deployment.replicas < 1:
            result.add_error(
                "INVALID_REPLICAS",
                f"Replicas must be at least 1: {deployment.replicas}",
                "deployment.replicas",
            )

    def _validate_metadata_block(
        self, schema: AgentSchema, result: ValidationResult
    ) -> None:
        """Validate metadata block."""
        metadata = schema.metadata

        # Status is already validated by Pydantic

        # Warn if no owner
        if not metadata.owner:
            result.add_warning(
                "NO_OWNER",
                "Consider specifying a schema owner",
                "metadata.owner",
            )

        # Warn if no tags
        if not metadata.tags:
            result.add_warning(
                "NO_TAGS",
                "Consider adding classification tags",
                "metadata.tags",
            )


# =============================================================================
# Convenience Functions
# =============================================================================


def validate_schema(schema: AgentSchema, strict: bool = False) -> ValidationResult:
    """
    Validate an AgentSchema instance.

    Args:
        schema: Parsed schema to validate
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult
    """
    validator = SchemaValidator(strict=strict)
    return validator.validate(schema)


def validate_schema_file(
    filepath: str | Path, strict: bool = False
) -> ValidationResult:
    """
    Validate a schema file.

    Args:
        filepath: Path to YAML schema file
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult
    """
    validator = SchemaValidator(strict=strict)
    return validator.validate_file(filepath)


def validate_schema_yaml(yaml_content: str, strict: bool = False) -> ValidationResult:
    """
    Validate YAML content.

    Args:
        yaml_content: YAML content as string
        strict: If True, treat warnings as errors

    Returns:
        ValidationResult
    """
    validator = SchemaValidator(strict=strict)
    return validator.validate_yaml(yaml_content)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Classes
    "SchemaValidator",
    "ValidationResult",
    "ValidationError",
    # Functions
    "validate_schema",
    "validate_schema_file",
    "validate_schema_yaml",
    # Constants
    "MIN_VERSION",
    "MAX_FILE_SIZE_BYTES",
    "REQUIRED_SECTIONS",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "code-generation",
        "dataclass",
        "filesystem",
        "foundation",
        "linting",
        "logging",
        "messaging",
        "validation",
    ],
    "keywords": [
        "agent",
        "count",
        "factory",
        "governance",
        "research",
        "rules",
        "schema",
        "valid",
    ],
    "business_value": "Provides schema validator components including ValidationError, ValidationResult, SchemaValidator",
    "last_modified": "2026-01-06T16:58:23Z",
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
