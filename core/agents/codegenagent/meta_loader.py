"""
CodeGenAgent Meta Loader
========================

Loads YAML meta specifications for code generation.
Part of the Quantum AI Factory architecture.

Supports two schema formats:
1. Module-Spec-v2.4.0 (22-section operational/enterprise grade)
2. Research Factory v6.0 (agent/adapter schemas)

Version: 2.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Meta Loader",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-25T14:49:28Z",
    "layer": "operations",
    "domain": "error_handling",
    "module_name": "meta_loader",
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
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import ValidationError

from ir_engine.meta_ir import MetaContract, MetaContractValidationResult
from ir_engine.schema_validator import SchemaValidator

logger = structlog.get_logger(__name__)


class MetaLoaderError(Exception):
    """Exception raised when meta loading fails."""

    pass


class MetaLoader:
    """
    Loads and validates YAML meta specifications.

    Used by CodeGenAgent to parse spec files before code generation.
    Supports both Module-Spec-v2.4 and Research Factory v6.0 formats.
    """

    def __init__(
        self,
        specs_dir: str | None = None,
        strict_validation: bool = False,
    ):
        """
        Initialize the meta loader.

        Args:
            specs_dir: Directory containing YAML specs (default: core/agents/codegenagent/)
            strict_validation: If True, treat validation warnings as errors
        """
        if specs_dir is None:
            # Default to the codegenagent directory
            specs_dir = str(Path(__file__).parent)
        self.specs_dir = Path(specs_dir)
        self.strict_validation = strict_validation
        self._validator = SchemaValidator(strict=strict_validation)
        logger.info(
            "meta_loader_initialized",
            specs_dir=str(self.specs_dir),
            strict_validation=strict_validation,
        )

    def load_meta(self, path: str) -> dict[str, Any]:
        """
        Load a YAML meta specification as raw dict.

        Args:
            path: Path to YAML file (absolute or relative to specs_dir)

        Returns:
            Parsed YAML as dictionary

        Raises:
            MetaLoaderError: If loading fails
        """
        try:
            # Resolve path
            file_path = Path(path) if os.path.isabs(path) else self.specs_dir / path

            if not file_path.exists():
                raise MetaLoaderError(f"Spec file not found: {file_path}")

            with open(file_path, encoding="utf-8") as f:
                meta = yaml.safe_load(f)

            logger.info(
                "meta_loaded",
                path=str(file_path),
                keys=list(meta.keys()) if meta else [],
                schema_version=meta.get("schema_version", "unknown") if meta else None,
            )

            return meta or {}

        except yaml.YAMLError as e:
            logger.error("meta_yaml_error", path=path, error=str(e))
            raise MetaLoaderError(f"YAML parse error: {e}") from e
        except Exception as e:
            logger.error("meta_load_error", path=path, error=str(e))
            raise MetaLoaderError(f"Failed to load meta: {e}") from e

    def load_as_contract(self, path: str) -> MetaContract:
        """
        Load a YAML meta specification as a validated MetaContract.

        Only works with Module-Spec-v2.4 format. For Research Factory v6.0
        schemas, use load_meta() instead.

        Args:
            path: Path to YAML file

        Returns:
            Validated MetaContract instance

        Raises:
            MetaLoaderError: If loading or validation fails
        """
        raw = self.load_meta(path)

        try:
            contract = MetaContract(**raw)
            logger.info(
                "meta_contract_loaded",
                module_id=contract.metadata.module_id,
                schema_version=contract.schema_version,
            )
            return contract
        except ValidationError as e:
            errors = [
                f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
                for err in e.errors()
            ]
            logger.error("meta_contract_validation_failed", path=path, errors=errors)
            raise MetaLoaderError(
                f"Contract validation failed: {'; '.join(errors)}"
            ) from e

    def validate_meta(self, path: str) -> MetaContractValidationResult:
        """
        Validate a meta specification against Module-Spec-v2.4.

        Args:
            path: Path to YAML file

        Returns:
            Validation result with errors and warnings
        """
        file_path = path if os.path.isabs(path) else str(self.specs_dir / path)

        return self._validator.validate_yaml(file_path)

    def load_all_specs(self, pattern: str = "*.yaml") -> list[dict[str, Any]]:
        """
        Load all YAML specs matching a pattern.

        Args:
            pattern: Glob pattern for spec files

        Returns:
            List of parsed YAML specifications
        """
        specs = []
        for path in self.specs_dir.glob(pattern):
            try:
                spec = self.load_meta(str(path))
                spec["_source_file"] = str(path)
                specs.append(spec)
            except MetaLoaderError as e:
                logger.warning("spec_load_skipped", path=str(path), error=str(e))

        logger.info("all_specs_loaded", count=len(specs))
        return specs

    def load_all_contracts(self, pattern: str = "*.yaml") -> list[MetaContract]:
        """
        Load all YAML specs as MetaContract instances.

        Only loads specs that are valid Module-Spec-v2.4 format.

        Args:
            pattern: Glob pattern for spec files

        Returns:
            List of validated MetaContract instances
        """
        contracts = []
        for path in self.specs_dir.glob(pattern):
            try:
                contract = self.load_as_contract(str(path))
                contracts.append(contract)
            except MetaLoaderError as e:
                logger.debug("contract_load_skipped", path=str(path), error=str(e))

        logger.info("all_contracts_loaded", count=len(contracts))
        return contracts

    def detect_schema_format(self, meta: dict[str, Any]) -> str:
        """
        Detect the schema format of a loaded meta specification.

        Args:
            meta: Parsed meta specification

        Returns:
            One of: "module-spec-v2.4", "research-factory-v6", "unknown"
        """
        # Module-Spec-v2.4 has schema_version and specific sections
        if meta.get("schema_version") == "2.4":
            return "module-spec-v2.4"

        # Research Factory v6.0 has 'system' with 'module' and 'rootpath'
        if "system" in meta and isinstance(meta["system"], dict):
            if "module" in meta["system"] and "rootpath" in meta["system"]:
                return "research-factory-v6"

        # Glue layer format
        if "wirings" in meta and "memory_harmonization" in meta:
            return "glue-layer-v6"

        return "unknown"

    def legacy_validate_meta(self, meta: dict[str, Any]) -> bool:
        """
        Legacy validation: check for minimal required fields.

        Args:
            meta: Parsed meta specification

        Returns:
            True if valid, False otherwise
        """
        # Check based on detected format
        schema_format = self.detect_schema_format(meta)

        if schema_format == "module-spec-v2.4":
            required = ["metadata", "runtime_wiring", "packet_contract"]
        elif schema_format == "research-factory-v6":
            required = ["system", "integration", "governance"]
        else:
            required = ["name", "description"]

        for field in required:
            if field not in meta:
                logger.warning("meta_validation_failed", missing_field=field)
                return False

        return True

    def get_code_sections(self, meta: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extract code sections from a meta specification.

        Args:
            meta: Parsed meta specification

        Returns:
            List of code section dictionaries
        """
        sections = []

        # Check for 'code' key
        if "code" in meta:
            code = meta["code"]
            if isinstance(code, list):
                sections.extend(code)
            elif isinstance(code, dict):
                sections.append(code)
            elif isinstance(code, str):
                sections.append({"content": code})

        # Check for 'code_blocks' key
        if "code_blocks" in meta:
            sections.extend(meta["code_blocks"])

        return sections

    def get_generation_targets(self, meta: dict[str, Any]) -> list[str]:
        """
        Extract file generation targets from a meta specification.

        Works with both Module-Spec-v2.4 and Research Factory v6.0 formats.

        Args:
            meta: Parsed meta specification

        Returns:
            List of file paths to generate
        """
        targets = []

        schema_format = self.detect_schema_format(meta)

        if schema_format == "module-spec-v2.4":
            if "repo" in meta:
                targets.extend(meta["repo"].get("allowed_new_files", []))
        elif schema_format == "research-factory-v6":
            if "cursorinstructions" in meta:
                targets.extend(meta["cursorinstructions"].get("generatefiles", []))

        return targets


# Convenience functions for loading meta files


def load_meta(path: str) -> dict[str, Any]:
    """
    Load a YAML meta specification.

    Args:
        path: Path to YAML file

    Returns:
        Parsed YAML as dictionary
    """
    loader = MetaLoader()
    return loader.load_meta(path)


def load_as_contract(path: str) -> MetaContract:
    """
    Load a YAML meta specification as MetaContract.

    Args:
        path: Path to YAML file

    Returns:
        Validated MetaContract instance
    """
    loader = MetaLoader()
    return loader.load_as_contract(path)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "config",
        "debugging",
        "error-handling",
        "exception",
        "filesystem",
        "loader",
        "logging",
        "operations",
        "validation",
    ],
    "keywords": [
        "agent",
        "all",
        "contract",
        "contracts",
        "detect",
        "factory",
        "format",
        "generation",
    ],
    "business_value": "Provides meta loader components including MetaLoaderError, MetaLoader",
    "last_modified": "2026-01-25T14:49:28Z",
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
