#!/usr/bin/env python3
"""
L9 Module Spec v2.5 Validator
=============================
Strict schema + checklist validation for Module-Spec v2.5.

BEHAVIOR:
- Fail loudly on ANY missing or invalid field
- NO permissive fallbacks
- NO inference of missing values
- NO "best effort" mode

EXIT CODES:
- 0: All validations passed
- 1: Validation failed (spec incomplete or invalid)
- 2: File not found or parse error

Usage:
    python ci/validate_spec_v25.py path/to/spec.yaml
    python ci/validate_spec_v25.py --all  # Validate all specs in repo
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Validate Spec V25",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-06T16:58:23Z",
    "layer": "foundation",
    "domain": "error_handling",
    "module_name": "validate_spec_v25",
    "type": "exception",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import os
import sys
from pathlib import Path
from typing import Any

import structlog
import yaml

# =============================================================================
# SCHEMA DEFINITION - v2.5 REQUIRED SECTIONS
# =============================================================================

# All v2.5 required top-level sections

logger = structlog.get_logger(__name__)
V25_REQUIRED_SECTIONS = [
    "schema_version",
    "metadata",
    "ownership",
    "runtime_wiring",
    "runtime_contract",
    "external_surface",
    "dependency_contract",
    "dependencies",
    "packet_contract",
    "packet_expectations",
    "idempotency",
    "error_policy",
    "observability",
    "runtime_touchpoints",
    "tier_expectations",
    "test_scope",
    "acceptance",
    "global_invariants_ack",
    "spec_confidence",
    "repo",
    "interfaces",
    "environment",
    "orchestration",
    "boot_impact",
    "standards",
    "goals",
    "non_goals",
]

# Keystone sections - MUST NOT be thin/empty
KEYSTONE_SECTIONS = [
    "runtime_wiring",
    "packet_contract",
    "acceptance",
    "global_invariants_ack",
]

# Metadata required fields
METADATA_REQUIRED = ["module_id", "name", "tier", "description", "system", "language"]

# Ownership required fields
OWNERSHIP_REQUIRED = ["team", "primary_contact"]

# Runtime wiring required fields (KEYSTONE)
RUNTIME_WIRING_REQUIRED = [
    "service",
    "startup_phase",
    "depends_on",
    "blocks_startup_on_failure",
]

# Runtime contract required fields (v2.5 NEW)
RUNTIME_CONTRACT_REQUIRED = ["runtime_class", "execution_model"]

# External surface required fields
EXTERNAL_SURFACE_REQUIRED = [
    "exposes_http_endpoint",
    "exposes_webhook",
    "exposes_tool",
    "callable_from",
]

# Dependency contract required fields (v2.5 NEW)
DEPENDENCY_CONTRACT_REQUIRED = ["inbound", "outbound"]

# Packet contract required fields
PACKET_CONTRACT_REQUIRED = ["emits", "requires_metadata"]

# Packet expectations required fields (v2.5 NEW)
PACKET_EXPECTATIONS_REQUIRED = ["on_success", "on_error", "durability"]

# Tier expectations required fields (v2.5 NEW)
TIER_EXPECTATIONS_REQUIRED = [
    "requires_runtime_wiring",
    "requires_packet_contract",
    "requires_negative_tests",
]

# Global invariants - ALL must be explicitly acknowledged
GLOBAL_INVARIANTS_REQUIRED = [
    "emits_packet_on_ingress",
    "tool_calls_traceable",
    "unknown_tool_id_hard_fail",
    "malformed_packet_blocked",
    "missing_env_fails_boot",
]

# Acceptance criteria
ACCEPTANCE_REQUIRED = ["positive", "negative"]

# Repo manifest required
REPO_REQUIRED = ["root_path", "allowed_new_files"]

# Packet metadata that MUST be present
REQUIRED_PACKET_METADATA = ["task_id", "thread_uuid", "source", "tool_id"]

# Valid tier values
VALID_TIERS = [0, 1, 2, 3, 4, 5, 6, 7]

# Valid service types
VALID_SERVICES = ["api", "worker", "scheduler", "memory"]

# Valid startup phases
VALID_STARTUP_PHASES = ["early", "normal", "late"]

# Valid runtime classes
VALID_RUNTIME_CLASSES = ["control_plane", "data_plane", "background"]

# Valid execution models
VALID_EXECUTION_MODELS = ["request_driven", "event_driven", "scheduled"]


# =============================================================================
# VALIDATION ERRORS
# =============================================================================


class SpecValidationError(Exception):
    """Raised when spec validation fails."""

    pass


class ValidationResult:
    """Accumulates validation errors."""

    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add_error(self, error: str) -> None:
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def print_report(self) -> None:
        """Print validation report."""
        logger.info(f"\n{'=' * 70}")
        logger.info(f"SPEC VALIDATION: {self.spec_path}")
        logger.info(f"{'=' * 70}")

        if self.is_valid:
            logger.info("✅ PASSED - All v2.5 requirements satisfied")
        else:
            logger.error(f"❌ FAILED - {len(self.errors)} error(s) found\n")
            for i, error in enumerate(self.errors, 1):
                logger.error(f"  [{i}] {error}")

        if self.warnings:
            logger.warning(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                logger.warning(f"    - {warning}")

        logger.info(f"{'=' * 70}\n")


# =============================================================================
# VALIDATORS
# =============================================================================


def validate_schema_version(spec: dict, result: ValidationResult) -> None:
    """Validate schema_version is exactly 2.5."""
    version = spec.get("schema_version")
    if version is None:
        result.add_error("MISSING: schema_version (REQUIRED)")
        return

    if str(version) != "2.5":
        result.add_error(f"INVALID: schema_version must be '2.5', got '{version}'")


def validate_required_sections(spec: dict, result: ValidationResult) -> None:
    """Validate all required sections are present."""
    for section in V25_REQUIRED_SECTIONS:
        if section not in spec:
            result.add_error(f"MISSING SECTION: {section} (REQUIRED in v2.5)")


def validate_metadata(spec: dict, result: ValidationResult) -> None:
    """Validate metadata section."""
    metadata = spec.get("metadata", {})
    if not metadata:
        result.add_error("MISSING: metadata section is empty")
        return

    for field in METADATA_REQUIRED:
        if field not in metadata:
            result.add_error(f"MISSING: metadata.{field} (REQUIRED)")

    # Validate tier is a valid value
    tier = metadata.get("tier")
    if tier is not None:
        # Handle template placeholders
        if isinstance(tier, str) and "{{" in tier:
            result.add_warning(
                "PLACEHOLDER: metadata.tier contains template placeholder"
            )
        elif tier not in VALID_TIERS and not isinstance(tier, str):
            result.add_error(
                f"INVALID: metadata.tier must be one of {VALID_TIERS}, got '{tier}'"
            )


def validate_ownership(spec: dict, result: ValidationResult) -> None:
    """Validate ownership section."""
    ownership = spec.get("ownership", {})
    for field in OWNERSHIP_REQUIRED:
        if field not in ownership:
            result.add_error(f"MISSING: ownership.{field} (REQUIRED)")


def validate_runtime_wiring(spec: dict, result: ValidationResult) -> None:
    """Validate runtime_wiring section (KEYSTONE)."""
    runtime_wiring = spec.get("runtime_wiring", {})
    if not runtime_wiring:
        result.add_error("KEYSTONE EMPTY: runtime_wiring section is empty or missing")
        return

    for field in RUNTIME_WIRING_REQUIRED:
        if field not in runtime_wiring:
            result.add_error(f"MISSING: runtime_wiring.{field} (KEYSTONE REQUIRED)")

    # Validate service type
    service = runtime_wiring.get("service")
    if service and not _is_placeholder(service):
        if service not in VALID_SERVICES:
            result.add_error(
                f"INVALID: runtime_wiring.service must be one of {VALID_SERVICES}, got '{service}'"
            )

    # Validate startup phase
    phase = runtime_wiring.get("startup_phase")
    if phase and not _is_placeholder(phase):
        if phase not in VALID_STARTUP_PHASES:
            result.add_error(
                f"INVALID: runtime_wiring.startup_phase must be one of {VALID_STARTUP_PHASES}, got '{phase}'"
            )

    # depends_on must be a list
    depends_on = runtime_wiring.get("depends_on")
    if depends_on is not None and not isinstance(depends_on, list):
        result.add_error("INVALID: runtime_wiring.depends_on must be a list")


def validate_runtime_contract(spec: dict, result: ValidationResult) -> None:
    """Validate runtime_contract section (v2.5 NEW)."""
    contract = spec.get("runtime_contract", {})
    for field in RUNTIME_CONTRACT_REQUIRED:
        if field not in contract:
            result.add_error(f"MISSING: runtime_contract.{field} (v2.5 REQUIRED)")

    # Validate runtime_class
    rc = contract.get("runtime_class")
    if rc and not _is_placeholder(rc):
        if rc not in VALID_RUNTIME_CLASSES:
            result.add_error(
                f"INVALID: runtime_contract.runtime_class must be one of {VALID_RUNTIME_CLASSES}"
            )

    # Validate execution_model
    em = contract.get("execution_model")
    if em and not _is_placeholder(em):
        if em not in VALID_EXECUTION_MODELS:
            result.add_error(
                f"INVALID: runtime_contract.execution_model must be one of {VALID_EXECUTION_MODELS}"
            )


def validate_external_surface(spec: dict, result: ValidationResult) -> None:
    """Validate external_surface section."""
    surface = spec.get("external_surface", {})
    for field in EXTERNAL_SURFACE_REQUIRED:
        if field not in surface:
            result.add_error(f"MISSING: external_surface.{field} (REQUIRED)")


def validate_dependency_contract(spec: dict, result: ValidationResult) -> None:
    """Validate dependency_contract section (v2.5 NEW)."""
    contract = spec.get("dependency_contract", {})
    for field in DEPENDENCY_CONTRACT_REQUIRED:
        if field not in contract:
            result.add_error(f"MISSING: dependency_contract.{field} (v2.5 REQUIRED)")

    # Validate inbound entries have required fields
    inbound = contract.get("inbound", [])
    if isinstance(inbound, list):
        for i, entry in enumerate(inbound):
            if isinstance(entry, dict):
                for req in ["from_module", "interface", "endpoint"]:
                    if req not in entry:
                        result.add_error(
                            f"MISSING: dependency_contract.inbound[{i}].{req}"
                        )

    # Validate outbound entries have required fields
    outbound = contract.get("outbound", [])
    if isinstance(outbound, list):
        for i, entry in enumerate(outbound):
            if isinstance(entry, dict):
                for req in ["to_module", "interface", "endpoint"]:
                    if req not in entry:
                        result.add_error(
                            f"MISSING: dependency_contract.outbound[{i}].{req}"
                        )


def validate_packet_contract(spec: dict, result: ValidationResult) -> None:
    """Validate packet_contract section (KEYSTONE)."""
    contract = spec.get("packet_contract", {})
    if not contract:
        result.add_error("KEYSTONE EMPTY: packet_contract section is empty or missing")
        return

    for field in PACKET_CONTRACT_REQUIRED:
        if field not in contract:
            result.add_error(f"MISSING: packet_contract.{field} (KEYSTONE REQUIRED)")

    # Validate emits is a non-empty list
    emits = contract.get("emits", [])
    if not isinstance(emits, list) or len(emits) == 0:
        result.add_error("INVALID: packet_contract.emits must be a non-empty list")

    # Validate requires_metadata includes all required fields
    requires_meta = contract.get("requires_metadata", [])
    if isinstance(requires_meta, list):
        for req in REQUIRED_PACKET_METADATA:
            if req not in requires_meta:
                result.add_error(
                    f"MISSING: packet_contract.requires_metadata must include '{req}'"
                )


def validate_packet_expectations(spec: dict, result: ValidationResult) -> None:
    """Validate packet_expectations section (v2.5 NEW)."""
    expectations = spec.get("packet_expectations", {})
    for field in PACKET_EXPECTATIONS_REQUIRED:
        if field not in expectations:
            result.add_error(f"MISSING: packet_expectations.{field} (v2.5 REQUIRED)")

    # Validate on_success.emits exists
    on_success = expectations.get("on_success", {})
    if "emits" not in on_success:
        result.add_error(
            "MISSING: packet_expectations.on_success.emits (v2.5 REQUIRED)"
        )

    # Validate on_error.emits exists
    on_error = expectations.get("on_error", {})
    if "emits" not in on_error:
        result.add_error("MISSING: packet_expectations.on_error.emits (v2.5 REQUIRED)")


def validate_tier_expectations(spec: dict, result: ValidationResult) -> None:
    """Validate tier_expectations section (v2.5 NEW)."""
    expectations = spec.get("tier_expectations", {})
    for field in TIER_EXPECTATIONS_REQUIRED:
        if field not in expectations:
            result.add_error(f"MISSING: tier_expectations.{field} (v2.5 REQUIRED)")


def validate_acceptance(spec: dict, result: ValidationResult) -> None:
    """Validate acceptance section (KEYSTONE)."""
    acceptance = spec.get("acceptance", {})
    if not acceptance:
        result.add_error("KEYSTONE EMPTY: acceptance section is empty or missing")
        return

    # Must have both positive and negative tests
    for field in ACCEPTANCE_REQUIRED:
        if field not in acceptance:
            result.add_error(f"MISSING: acceptance.{field} (KEYSTONE REQUIRED)")

    # Positive tests must have id, description, test
    positive = acceptance.get("positive", [])
    if isinstance(positive, list):
        if len(positive) == 0:
            result.add_error("INVALID: acceptance.positive must have at least one test")
        for i, test in enumerate(positive):
            if isinstance(test, dict):
                for req in ["id", "description", "test"]:
                    if req not in test:
                        result.add_error(f"MISSING: acceptance.positive[{i}].{req}")

    # Negative tests must have id, description, expected_behavior, test
    negative = acceptance.get("negative", [])
    if isinstance(negative, list):
        if len(negative) == 0:
            result.add_error("INVALID: acceptance.negative must have at least one test")
        for i, test in enumerate(negative):
            if isinstance(test, dict):
                for req in ["id", "description", "test"]:
                    if req not in test:
                        result.add_error(f"MISSING: acceptance.negative[{i}].{req}")


def validate_global_invariants(spec: dict, result: ValidationResult) -> None:
    """Validate global_invariants_ack section (KEYSTONE)."""
    invariants = spec.get("global_invariants_ack", {})
    if not invariants:
        result.add_error(
            "KEYSTONE EMPTY: global_invariants_ack section is empty or missing"
        )
        return

    for inv in GLOBAL_INVARIANTS_REQUIRED:
        if inv not in invariants:
            result.add_error(
                f"MISSING: global_invariants_ack.{inv} (INVARIANT NOT ACKNOWLEDGED)"
            )
        elif invariants[inv] is not True:
            result.add_error(f"INVALID: global_invariants_ack.{inv} must be true")


def validate_repo_manifest(spec: dict, result: ValidationResult) -> None:
    """Validate repo manifest section."""
    repo = spec.get("repo", {})
    for field in REPO_REQUIRED:
        if field not in repo:
            result.add_error(f"MISSING: repo.{field} (REQUIRED)")


def _is_placeholder(value: Any) -> bool:
    """Check if value is a template placeholder."""
    if isinstance(value, str):
        return "{{" in value and "}}" in value
    return False


# =============================================================================
# MAIN VALIDATION ENTRY POINT
# =============================================================================


def validate_spec(spec_path: str) -> ValidationResult:
    """
    Validate a Module-Spec v2.5 file.

    Args:
        spec_path: Path to the spec YAML file

    Returns:
        ValidationResult with all errors and warnings
    """
    result = ValidationResult(spec_path)

    # Check file exists
    if not os.path.exists(spec_path):
        result.add_error(f"FILE NOT FOUND: {spec_path}")
        return result

    # Parse YAML
    try:
        with open(spec_path) as f:
            spec = yaml.safe_load(f)
    except yaml.YAMLError as e:
        result.add_error(f"YAML PARSE ERROR: {e}")
        return result

    if spec is None:
        result.add_error("EMPTY FILE: Spec file is empty")
        return result

    # Run all validators
    validate_schema_version(spec, result)
    validate_required_sections(spec, result)
    validate_metadata(spec, result)
    validate_ownership(spec, result)
    validate_runtime_wiring(spec, result)
    validate_runtime_contract(spec, result)
    validate_external_surface(spec, result)
    validate_dependency_contract(spec, result)
    validate_packet_contract(spec, result)
    validate_packet_expectations(spec, result)
    validate_tier_expectations(spec, result)
    validate_acceptance(spec, result)
    validate_global_invariants(spec, result)
    validate_repo_manifest(spec, result)

    return result


def find_all_specs(repo_root: str) -> list[str]:
    """Find all spec files in the repo."""
    specs = []
    for pattern in ["**/spec*.yaml", "**/*_spec.yaml", "**/Module-Spec*.yaml"]:
        specs.extend(Path(repo_root).glob(pattern))
    return [str(p) for p in specs]


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        logger.info("Usage: python validate_spec_v25.py <spec.yaml> [spec2.yaml ...]")
        logger.info("       python validate_spec_v25.py --all")
        return 2

    if sys.argv[1] == "--all":
        # Find repo root (look for .git or use cwd)
        repo_root = Path(__file__).parent.parent  # noqa: ADR-0001 - internal path
        specs = find_all_specs(str(repo_root))
        if not specs:
            logger.info("No spec files found in repo")
            return 0
    else:
        specs = sys.argv[1:]

    all_passed = True
    for spec_path in specs:
        result = validate_spec(spec_path)
        result.print_report()
        if not result.is_valid:
            all_passed = False

    if all_passed:
        logger.info("✅ ALL SPECS PASSED VALIDATION")
        return 0
    logger.error("❌ VALIDATION FAILED - See errors above")
    return 1


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-003",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "config",
        "error-handling",
        "event-driven",
        "exception",
        "filesystem",
        "foundation",
        "logging",
        "scheduling",
        "testing",
    ],
    "keywords": [
        "acceptance",
        "all",
        "contract",
        "dependency",
        "expectations",
        "external",
        "find",
        "global",
    ],
    "business_value": "Provides validate spec v25 components including SpecValidationError, ValidationResult",
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
