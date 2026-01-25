"""
L9 Spec Normalizer v2.0.0
=========================

Transforms raw Module-Spec inputs (YAML, JSON, dict) into normalized,
validated NormalizedSpec objects for deterministic code generation.

**Features**:
- Parses YAML, JSON, and dict inputs
- Validates against Module-Spec v2.6 schema
- Normalizes field names and types
- Fills defaults for optional fields
- Generates unique module IDs
- Detects spec version and architecture patterns
- Returns fully typed NormalizedSpec dataclass

**Design Pattern**: Substrate service (reusable across codegen tools)
**Integration**: Imported by ModuleCompilerV2, SpecValidator, SpecOptimizer
**Version**: 2.0.0 (L9-Aligned)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Spec Normalizer V2",
    "module_version": "2.0.0",
    "created_by": "CodeGenAgent",
    "created_at": "2026-01-25T22:54:40Z",
    "updated_at": "2026-01-25T22:54:40Z",
    "layer": "intelligence",
    "domain": "codegen",
    "module_name": "spec_normalizer_v2",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "core.codegen.compiler.module_compiler_v2",
            "core.codegen.gatekeeper.spec_validator",
            "core.codegen.gatekeeper.spec_optimizer",
        ],
    },
}
# ============================================================================

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union
from uuid import uuid4

import structlog
import yaml
from pydantic import BaseModel, Field, validator

logger = structlog.get_logger(__name__)


# =============================================================================
# EXCEPTIONS
# =============================================================================


class SpecParseError(Exception):
    """Raised when spec parsing fails (invalid YAML/JSON syntax)"""

    pass


class SpecValidationError(Exception):
    """Raised when spec validation fails (missing required fields, invalid types)"""

    pass


# =============================================================================
# DATA MODELS (Pydantic - for validation)
# =============================================================================


class MetadataModel(BaseModel):
    """Validated metadata section"""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10, max_length=2048)
    version: str = Field(default="1.0.0")
    domain: Optional[str] = Field(default="general")
    role: Optional[str] = Field(default="General Agent")


class GovernanceModel(BaseModel):
    """Validated governance section"""

    tier: int = Field(default=2, ge=1, le=4)
    escalation_path: str = Field(default="Igor")
    requires_approval: bool = Field(default=False)
    risk_level: str = Field(default="low")


class SystemModel(BaseModel):
    """Validated system section"""

    role: Optional[str] = Field(default="General Agent")
    capabilities: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class IntegrationModel(BaseModel):
    """Validated integration section"""

    depends_on: list[str] = Field(default_factory=list)
    provides: list[str] = Field(default_factory=list)
    memory_access: bool = Field(default=False)
    tool_registry: bool = Field(default=False)


class DependencyContractModel(BaseModel):
    """Validated dependency contract section"""

    external_services: list[dict[str, Any]] = Field(default_factory=list)
    kernel_requirements: list[str] = Field(default_factory=list)
    memory_substrates: list[str] = Field(default_factory=list)


class ModuleSpecModel(BaseModel):
    """Full validated Module-Spec v2.6"""

    spec_version: str = Field(default="2.6")
    metadata: MetadataModel
    governance: GovernanceModel = Field(default_factory=GovernanceModel)
    system: SystemModel = Field(default_factory=SystemModel)
    integration: IntegrationModel = Field(default_factory=IntegrationModel)
    dependency_contract: DependencyContractModel = Field(
        default_factory=DependencyContractModel
    )


# =============================================================================
# NORMALIZED SPEC (Output dataclass - immutable after creation)
# =============================================================================


@dataclass(frozen=True)
class NormalizedSpec:
    """
    Frozen, immutable normalized spec.
    All fields are guaranteed valid and present.
    """

    # Metadata
    spec_version: str = "2.6"
    module_id: str = field(default_factory=lambda: f"module_{uuid4().hex[:8]}")
    module_name: str = ""
    module_description: str = ""
    module_version: str = "1.0.0"
    module_domain: str = "general"
    module_role: str = "General Agent"

    # Governance
    tier: int = 2
    escalation_path: str = "Igor"
    requires_approval: bool = False
    risk_level: str = "low"

    # System
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    constraints: tuple[str, ...] = field(default_factory=tuple)

    # Integration
    depends_on: tuple[str, ...] = field(default_factory=tuple)
    provides: tuple[str, ...] = field(default_factory=tuple)
    memory_access: bool = False
    tool_registry: bool = False

    # Dependencies
    external_services: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    kernel_requirements: tuple[str, ...] = field(default_factory=tuple)
    memory_substrates: tuple[str, ...] = field(default_factory=tuple)

    # Metadata
    normalized_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    normalized_from: str = "unknown"  # 'yaml', 'json', 'dict'

    def to_dict(self) -> dict[str, Any]:
        """Convert to mutable dict for template rendering"""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict(), indent=2, default=str)


# =============================================================================
# SPEC NORMALIZER SERVICE
# =============================================================================


class SpecNormalizer:
    """
    Stateless spec normalization service.

    Transforms raw inputs (YAML, JSON, dict) into validated NormalizedSpec objects.
    Reusable across multiple codegen tools (compiler, validator, optimizer).
    """

    def __init__(self):
        self.logger = logger

    async def normalize_from_file(self, file_path: Union[str, Path]) -> NormalizedSpec:
        """
        Load and normalize spec from file.

        Args:
            file_path: Path to YAML or JSON spec file

        Returns:
            Normalized spec

        Raises:
            SpecParseError: If file cannot be parsed
            SpecValidationError: If spec is invalid
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise SpecParseError(f"Spec file not found: {file_path}")

        try:
            content = file_path.read_text()
        except Exception as e:
            raise SpecParseError(f"Cannot read spec file: {e}")

        # Detect format
        if file_path.suffix == ".yaml" or file_path.suffix == ".yml":
            return await self.normalize_from_yaml(content)
        elif file_path.suffix == ".json":
            return await self.normalize_from_json(content)
        else:
            raise SpecParseError(f"Unsupported file format: {file_path.suffix}")

    async def normalize_from_yaml(self, yaml_content: str) -> NormalizedSpec:
        """
        Parse and normalize from YAML string.

        Args:
            yaml_content: YAML spec content

        Returns:
            Normalized spec

        Raises:
            SpecParseError: If YAML is invalid
            SpecValidationError: If spec is invalid
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise SpecParseError(f"Invalid YAML: {e}")

        if not isinstance(data, dict):
            raise SpecParseError("YAML must parse to a dictionary")

        return await self.normalize_from_dict(data, source="yaml")

    async def normalize_from_json(self, json_content: str) -> NormalizedSpec:
        """
        Parse and normalize from JSON string.

        Args:
            json_content: JSON spec content

        Returns:
            Normalized spec

        Raises:
            SpecParseError: If JSON is invalid
            SpecValidationError: If spec is invalid
        """
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            raise SpecParseError(f"Invalid JSON: {e}")

        if not isinstance(data, dict):
            raise SpecParseError("JSON must parse to an object")

        return await self.normalize_from_dict(data, source="json")

    async def normalize_from_dict(self, data: dict, source: str = "dict") -> NormalizedSpec:
        """
        Parse and normalize from dictionary (main normalization logic).

        Args:
            data: Raw spec dictionary
            source: Source format ('yaml', 'json', 'dict')

        Returns:
            Normalized spec

        Raises:
            SpecValidationError: If spec is invalid
        """
        self.logger.info("Normalizing spec", source=source)

        try:
            # Validate structure with Pydantic
            validated = ModuleSpecModel(**data)

            # Extract and normalize
            module_id = self._generate_module_id(
                validated.metadata.name, data.get("metadata", {}).get("module_id")
            )
            module_name = self._normalize_name(validated.metadata.name)

            # Build normalized spec
            normalized = NormalizedSpec(
                spec_version=validated.spec_version,
                module_id=module_id,
                module_name=module_name,
                module_description=validated.metadata.description,
                module_version=validated.metadata.version,
                module_domain=validated.metadata.domain or "general",
                module_role=validated.metadata.role or "General Agent",
                # Governance
                tier=validated.governance.tier,
                escalation_path=validated.governance.escalation_path,
                requires_approval=validated.governance.requires_approval,
                risk_level=validated.governance.risk_level,
                # System
                capabilities=tuple(validated.system.capabilities),
                constraints=tuple(validated.system.constraints),
                # Integration
                depends_on=tuple(validated.integration.depends_on),
                provides=tuple(validated.integration.provides),
                memory_access=validated.integration.memory_access,
                tool_registry=validated.integration.tool_registry,
                # Dependencies
                external_services=tuple(validated.dependency_contract.external_services),
                kernel_requirements=tuple(validated.dependency_contract.kernel_requirements),
                memory_substrates=tuple(validated.dependency_contract.memory_substrates),
                normalized_from=source,
            )

            self.logger.info(
                "Spec normalized successfully",
                module_id=module_id,
                source=source,
                tier=normalized.tier,
            )

            return normalized

        except Exception as e:
            self.logger.error("Spec validation failed", error=str(e), exc_info=True)
            raise SpecValidationError(f"Invalid spec: {e}")

    def _generate_module_id(self, name: str, override: Optional[str] = None) -> str:
        """
        Generate deterministic module ID from name.

        Args:
            name: Module name
            override: Optional explicit module ID

        Returns:
            Module ID (e.g., 'my_awesome_agent')
        """
        if override:
            return override

        # Normalize: lowercase, replace spaces with underscores
        module_id = re.sub(r"[^a-z0-9_]", "_", name.lower())
        # Remove consecutive underscores
        module_id = re.sub(r"_+", "_", module_id)
        # Trim underscores
        module_id = module_id.strip("_")

        return module_id or f"module_{uuid4().hex[:8]}"

    def _normalize_name(self, name: str) -> str:
        """
        Normalize display name (title case, trim).

        Args:
            name: Raw name

        Returns:
            Normalized name
        """
        return " ".join(word.capitalize() for word in name.split())


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-CODEGEN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["pydantic>=2.0.0", "pyyaml>=6.0.0", "structlog>=23.1.0"],
    "tags": [
        "async",
        "api",
        "codegen",
        "data-models",
        "foundation",
        "parsing",
        "validation",
    ],
    "keywords": ["normalize", "parse", "spec", "validate", "yaml", "json"],
    "business_value": "Deterministic spec parsing and normalization service for L9 code generation",
    "last_modified": "2026-01-25T22:54:40Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with Option B modular design",
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
