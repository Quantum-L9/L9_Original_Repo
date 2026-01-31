"""
L9 IR Engine - Schema Validator
================================

Validates MetaContract schemas against Module-Spec-v2.4.0 constraints.

Enforces:
- No "if applicable" allowed
- runtime_wiring is REQUIRED
- packet_contract.emits must be non-empty
- global_invariants_ack all true
- All 22 sections present (required ones)
- No inferred dependencies
- No undeclared packet emission
- No implicit boot behavior
- No silent failure

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Schema Validator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "error_handling",
    "module_name": "schema_validator",
    "type": "exception",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "Redis"],
        "memory_layers": [],
        "imported_by": ["ir_engine.__init__", "runtime.construct_enhancer"],
    },
}
# ============================================================================

from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import ValidationError

from ir_engine.meta_ir import (
    MetaContract,
    MetaContractValidationError,
    MetaContractValidationResult,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# FORBIDDEN PATTERNS
# =============================================================================

FORBIDDEN_PATTERNS = [
    "if applicable",
    "when needed",
    "as required",
    "optional",
    "maybe",
    "possibly",
    "TBD",
    "TODO",
    "FIXME",
]


# =============================================================================
# REQUIRED SECTIONS
# =============================================================================

REQUIRED_SECTIONS = [
    "metadata",
    "ownership",
    "runtime_wiring",
    "external_surface",
    "dependencies",
    "packet_contract",
    "idempotency",
    "error_policy",
    "runtime_touchpoints",
    "test_scope",
    "acceptance",
    "spec_confidence",
    "boot_impact",
]


# =============================================================================
# SCHEMA VALIDATOR
# =============================================================================


class SchemaValidationError(Exception):
    """Raised when schema validation fails."""

    def __init__(self, message: str, errors: list[MetaContractValidationError]):
        """
        Validates schema specifications against Module-Spec-v2.4.0 constraints to ensure compliance.

        Args:
            message: Error message describing validation failure.
            errors: List of MetaContractValidationError instances detailing specific issues.
        """
        super().__init__(message)
        self.errors = errors


class SchemaValidator:
    """
    Validates YAML specs against Module-Spec-v2.4.0 constraints.

    Enforces strict rules:
    - No inference allowed
    - All required sections present
    - No forbidden patterns
    - Runtime wiring is complete
    - Global invariants acknowledged
    """

    def __init__(self, strict: bool = True):
        """
        Initialize the validator.

        Args:
            strict: If True, treat warnings as errors
        """
        self.strict = strict
        logger.info("schema_validator_initialized", strict=strict)

    def validate_yaml(self, yaml_path: str) -> MetaContractValidationResult:
        """
        Validate a YAML file against Module-Spec-v2.4.0.

        Args:
            yaml_path: Path to YAML file

        Returns:
            Validation result with errors and warnings
        """
        result = MetaContractValidationResult()
        path = Path(yaml_path)

        if not path.exists():
            result.add_error("file", f"File not found: {yaml_path}")
            return result

        try:
            with open(path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            result.add_error("yaml", f"YAML parse error: {e}")
            return result

        if raw is None:
            result.add_error("yaml", "Empty YAML file")
            return result

        return self.validate_dict(raw)

    def validate_dict(self, data: dict[str, Any]) -> MetaContractValidationResult:
        """
        Validate a dictionary against Module-Spec-v2.4.0.

        Args:
            data: Parsed YAML data

        Returns:
            Validation result
        """
        result = MetaContractValidationResult()

        # Step 1: Check required sections
        self._check_required_sections(data, result)

        # Step 2: Check for forbidden patterns in string values
        self._check_forbidden_patterns(data, result)

        # Step 3: Try to parse as MetaContract
        contract = self._parse_as_contract(data, result)

        if contract:
            # Step 4: Additional validation rules
            self._validate_runtime_wiring(contract, result)
            self._validate_packet_contract(contract, result)
            self._validate_test_scope_rules(contract, result)
            self._validate_dependencies(contract, result)

        logger.info(
            "schema_validation_complete",
            valid=result.valid,
            error_count=len(result.errors),
            warning_count=len(result.warnings),
        )

        return result

    def validate_and_parse(self, yaml_path: str) -> MetaContract:
        """
        Validate and parse a YAML file to MetaContract.

        Args:
            yaml_path: Path to YAML file

        Returns:
            Parsed MetaContract

        Raises:
            SchemaValidationError: If validation fails
        """
        result = self.validate_yaml(yaml_path)

        if not result.valid:
            raise SchemaValidationError(
                f"Schema validation failed with {len(result.errors)} errors",
                result.errors,
            )

        if self.strict and result.warnings:
            raise SchemaValidationError(
                f"Schema validation has {len(result.warnings)} warnings (strict mode)",
                result.warnings,
            )

        with open(yaml_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        return MetaContract(**raw)

    # =========================================================================
    # PRIVATE VALIDATION METHODS
    # =========================================================================

    def _check_required_sections(
        self, data: dict[str, Any], result: MetaContractValidationResult
    ) -> None:
        """Check that all required sections are present."""
        for section in REQUIRED_SECTIONS:
            if section not in data:
                result.add_error(section, f"Required section '{section}' is missing")

    def _check_forbidden_patterns(
        self, data: dict[str, Any], result: MetaContractValidationResult, path: str = ""
    ) -> None:
        """Recursively check for forbidden patterns in string values."""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                self._check_forbidden_patterns(value, result, current_path)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                self._check_forbidden_patterns(item, result, current_path)
        elif isinstance(data, str):
            data_lower = data.lower()
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.lower() in data_lower:
                    result.add_error(
                        path,
                        f"Forbidden pattern '{pattern}' found in value: {data[:50]}...",
                    )

    def _parse_as_contract(
        self, data: dict[str, Any], result: MetaContractValidationResult
    ) -> MetaContract | None:
        """Try to parse data as MetaContract."""
        try:
            return MetaContract(**data)
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                result.add_error(field, error["msg"])
            return None

    def _validate_runtime_wiring(
        self, contract: MetaContract, result: MetaContractValidationResult
    ) -> None:
        """Validate runtime wiring completeness."""
        wiring = contract.runtime_wiring

        # Check service is valid
        valid_services = ["api", "worker", "scheduler", "memory"]
        if wiring.service not in valid_services:
            result.add_error(
                "runtime_wiring.service",
                f"Invalid service '{wiring.service}', must be one of {valid_services}",
            )

        # Check startup_phase is valid
        valid_phases = ["early", "normal", "late"]
        if wiring.startup_phase not in valid_phases:
            result.add_error(
                "runtime_wiring.startup_phase",
                f"Invalid startup_phase '{wiring.startup_phase}', must be one of {valid_phases}",
            )

        # Check depends_on references are resolvable
        valid_deps = ["postgres", "redis", "memory.service", "neo4j", "api.server"]
        for dep in wiring.depends_on:
            if dep not in valid_deps and not dep.endswith(".service"):
                result.add_warning(
                    "runtime_wiring.depends_on",
                    f"Dependency '{dep}' may not be resolvable",
                )

    def _validate_packet_contract(
        self, contract: MetaContract, result: MetaContractValidationResult
    ) -> None:
        """Validate packet contract."""
        packets = contract.packet_contract

        # Emits must not be empty
        if not packets.emits:
            result.add_error(
                "packet_contract.emits",
                "packet_contract.emits must have at least one packet type",
            )

        # Check packet naming convention
        module_id = contract.metadata.module_id
        for packet_type in packets.emits:
            if not packet_type.startswith(module_id):
                result.add_warning(
                    "packet_contract.emits",
                    f"Packet type '{packet_type}' should start with module_id '{module_id}'",
                )

        # Required metadata must include standard fields
        required_fields = ["task_id", "thread_uuid", "source"]
        for field in required_fields:
            if field not in packets.requires_metadata:
                result.add_warning(
                    "packet_contract.requires_metadata",
                    f"Standard metadata field '{field}' not included",
                )

    def _validate_test_scope_rules(
        self, contract: MetaContract, result: MetaContractValidationResult
    ) -> None:
        """
        Validate test scope rules from Module-Spec-v2.4:
        - If external_surface.exposes_http_endpoint == true → docker_smoke: true
        - If runtime_wiring.service != api → integration: true
        - If startup_phase == early → boot-failure test REQUIRED
        """
        # Rule 1: HTTP endpoint requires docker smoke test
        if contract.external_surface.exposes_http_endpoint:
            if not contract.test_scope.docker_smoke:
                result.add_warning(
                    "test_scope.docker_smoke",
                    "Module exposes HTTP endpoint but docker_smoke is false",
                )

        # Rule 2: Non-API service requires integration tests
        if contract.runtime_wiring.service != "api":
            if not contract.test_scope.integration:
                result.add_warning(
                    "test_scope.integration",
                    "Module runs in non-API service but integration tests not required",
                )

        # Rule 3: Early startup requires boot-failure test
        if contract.runtime_wiring.startup_phase == "early":
            if contract.boot_impact.level != "hard":
                result.add_warning(
                    "boot_impact.level",
                    "Module has early startup_phase but boot_impact is not 'hard'",
                )

    def _validate_dependencies(
        self, contract: MetaContract, result: MetaContractValidationResult
    ) -> None:
        """Validate dependencies are properly declared."""
        deps = contract.dependencies

        # All outbound calls must have endpoint
        for call in deps.outbound_calls:
            if not call.endpoint:
                result.add_error(
                    "dependencies.outbound_calls",
                    f"Outbound call to '{call.module}' missing endpoint",
                )

            # Check interface type
            valid_interfaces = ["http", "tool"]
            if call.interface not in valid_interfaces:
                result.add_error(
                    "dependencies.outbound_calls",
                    f"Invalid interface '{call.interface}' for call to '{call.module}'",
                )


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================


def validate_schema(
    yaml_path: str, strict: bool = True
) -> MetaContractValidationResult:
    """
    Validate a YAML schema file.

    Args:
        yaml_path: Path to YAML file
        strict: Treat warnings as errors

    Returns:
        Validation result
    """
    validator = SchemaValidator(strict=strict)
    return validator.validate_yaml(yaml_path)


def validate_and_parse(yaml_path: str, strict: bool = True) -> MetaContract:
    """
    Validate and parse a YAML schema file.

    Args:
        yaml_path: Path to YAML file
        strict: Treat warnings as errors

    Returns:
        Parsed MetaContract

    Raises:
        SchemaValidationError: If validation fails
    """
    validator = SchemaValidator(strict=strict)
    return validator.validate_and_parse(yaml_path)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "IR_-INTE-002",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "config",
        "error-handling",
        "exception",
        "filesystem",
        "intelligence",
        "logging",
        "messaging",
        "scheduling",
        "testing",
    ],
    "keywords": [
        "module",
        "parse",
        "required",
        "schema",
        "validate",
        "validation",
        "validator",
        "yaml",
    ],
    "business_value": "Provides schema validator components including SchemaValidationError, SchemaValidator",
    "last_modified": "2026-01-07T13:35:57Z",
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
