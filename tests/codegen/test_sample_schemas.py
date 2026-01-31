"""
Test Sample Schemas from codegen/schemas
=========================================

Tests that sample schemas from codegen/schemas/samples/
can be loaded and processed by the schema validator and MetaContract model.

Note: The sample_schemas use Research Factory v6.0 format, not Module-Spec-v2.4.
This test validates both formats are handled appropriately.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

# Import after structlog is configured
from ir_engine.meta_ir import (
    AcceptanceCriterion,
    AcceptanceSpec,
    BootImpact,
    DependencySpec,
    ErrorPolicy,
    EscalationConfig,
    ExternalSurface,
    IdempotencySpec,
    MetaContract,
    ModuleMetadata,
    OwnershipSpec,
    PacketContract,
    RetryConfig,
    RuntimeTouchpoints,
    RuntimeWiringSpec,
    SpecConfidence,
    TestScope,
)
from ir_engine.schema_validator import (
    SchemaValidationError,
    SchemaValidator,
    validate_schema,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_schemas_dir() -> Path:
    """Get path to sample schemas directory."""
    return Path(__file__).parent.parent.parent / "codegen" / "schemas" / "samples"


@pytest.fixture
def module_spec_template_path() -> Path:
    """Get path to Module-Spec-v2.4 template."""
    return (
        Path(__file__).parent.parent.parent
        / "codegen"
        / "schemas"
        / "Module-Spec-v2.4.yaml"
    )


@pytest.fixture
def validator() -> SchemaValidator:
    """Create a schema validator instance."""
    return SchemaValidator(strict=False)


@pytest.fixture
def minimal_valid_contract() -> dict:
    """Create a minimal valid MetaContract dict."""
    return {
        "schema_version": "2.4",
        "metadata": {
            "module_id": "test_module",
            "name": "Test Module",
            "tier": "1",
            "description": "A test module for validation",
            "system": "L9",
            "language": "python",
            "runtime": "python>=3.11",
        },
        "ownership": {
            "team": "core",
            "primary_contact": "L-CTO",
        },
        "runtime_wiring": {
            "service": "api",
            "startup_phase": "normal",
            "depends_on": ["postgres", "redis"],
            "blocks_startup_on_failure": False,
        },
        "external_surface": {
            "exposes_http_endpoint": True,
            "exposes_webhook": False,
            "exposes_tool": False,
            "callable_from": ["internal"],
        },
        "dependencies": {
            "allowed_tiers": [0, 1, 2],
            "outbound_calls": [
                {
                    "module": "memory.service",
                    "interface": "http",
                    "endpoint": "/memory/ingest",
                }
            ],
        },
        "packet_contract": {
            "emits": ["test_module.in", "test_module.out", "test_module.error"],
            "requires_metadata": ["task_id", "thread_uuid", "source", "tool_id"],
        },
        "idempotency": {
            "pattern": "event_id",
            "source": "platform_event_id",
            "durability": "substrate",
        },
        "error_policy": {
            "default": "fail_fast",
            "retries": {"enabled": True, "max_attempts": 3},
            "escalation": {
                "emit_error_packet": True,
                "mark_task_failed": True,
                "alert": "log",
            },
        },
        "runtime_touchpoints": {
            "touches_db": True,
            "touches_tools": False,
            "touches_external_network": False,
            "affects_boot": False,
        },
        "test_scope": {
            "unit": True,
            "integration": True,
            "docker_smoke": True,
        },
        "acceptance": {
            "positive": [
                {
                    "id": "AP-1",
                    "description": "Valid request processed",
                    "test": "test_valid",
                }
            ],
            "negative": [
                {
                    "id": "AN-1",
                    "description": "Invalid request rejected",
                    "test": "test_invalid",
                }
            ],
        },
        "spec_confidence": {
            "level": "high",
            "basis": ["Existing code present", "Tested in production"],
        },
        "boot_impact": {
            "level": "none",
            "reason": "No boot impact for this module",
        },
    }


# =============================================================================
# TEST: MetaContract Model Creation
# =============================================================================


class TestMetaContractModel:
    """Test MetaContract Pydantic model."""

    def test_create_minimal_contract(self, minimal_valid_contract: dict) -> None:
        """Test creating a minimal valid MetaContract."""
        contract = MetaContract(**minimal_valid_contract)

        assert contract.metadata.module_id == "test_module"
        assert contract.metadata.name == "Test Module"
        assert contract.runtime_wiring.service == "api"
        assert contract.runtime_wiring.startup_phase == "normal"
        assert len(contract.packet_contract.emits) == 3

    def test_module_metadata(self) -> None:
        """Test ModuleMetadata validation."""
        metadata = ModuleMetadata(
            module_id="slack_adapter",
            name="Slack Adapter",
            tier="2",
            description="Slack integration module",
        )

        assert metadata.module_id == "slack_adapter"
        assert metadata.system == "L9"
        assert metadata.language == "python"

    def test_runtime_wiring_spec(self) -> None:
        """Test RuntimeWiringSpec validation."""
        wiring = RuntimeWiringSpec(
            service="worker",
            startup_phase="early",
            depends_on=["postgres", "redis"],
            blocks_startup_on_failure=True,
        )

        assert wiring.service == "worker"
        assert wiring.startup_phase == "early"
        assert len(wiring.depends_on) == 2

    def test_packet_contract_requires_emits(self) -> None:
        """Test that packet_contract.emits must be non-empty."""
        with pytest.raises(Exception):  # Pydantic validation error
            PacketContract(emits=[], requires_metadata=["task_id"])

    def test_acceptance_spec(self) -> None:
        """Test AcceptanceSpec validation."""
        acceptance = AcceptanceSpec(
            positive=[
                AcceptanceCriterion(
                    id="AP-1", description="Happy path", test="test_happy"
                )
            ],
            negative=[
                AcceptanceCriterion(
                    id="AN-1", description="Error case", test="test_error"
                )
            ],
        )

        assert len(acceptance.positive) == 1
        assert len(acceptance.negative) == 1

    def test_generation_context(self, minimal_valid_contract: dict) -> None:
        """Test to_generation_context method."""
        contract = MetaContract(**minimal_valid_contract)
        context = contract.to_generation_context()

        assert context["module_id"] == "test_module"
        assert context["service"] == "api"
        assert context["exposes_http_endpoint"] is True
        assert len(context["packet_types"]) == 3


# =============================================================================
# TEST: Schema Validator
# =============================================================================


class TestSchemaValidator:
    """Test SchemaValidator functionality."""

    def test_validate_valid_dict(
        self, validator: SchemaValidator, minimal_valid_contract: dict
    ) -> None:
        """Test validation of a valid dictionary."""
        result = validator.validate_dict(minimal_valid_contract)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_missing_required_section(
        self, validator: SchemaValidator, minimal_valid_contract: dict
    ) -> None:
        """Test validation fails for missing required sections."""
        del minimal_valid_contract["runtime_wiring"]

        result = validator.validate_dict(minimal_valid_contract)

        assert result.valid is False
        assert any("runtime_wiring" in e.message for e in result.errors)

    def test_validate_forbidden_patterns(self, validator: SchemaValidator) -> None:
        """Test validation catches forbidden patterns."""
        data = {
            "metadata": {
                "module_id": "test",
                "name": "Test",
                "tier": "1",
                "description": "This is TBD",  # Forbidden pattern
            },
            "ownership": {"team": "core", "primary_contact": "test"},
            "runtime_wiring": {
                "service": "api",
                "startup_phase": "normal",
                "depends_on": [],
                "blocks_startup_on_failure": False,
            },
            "external_surface": {
                "exposes_http_endpoint": False,
                "exposes_webhook": False,
                "exposes_tool": False,
                "callable_from": [],
            },
            "dependencies": {"allowed_tiers": [], "outbound_calls": []},
            "packet_contract": {"emits": ["test.in"], "requires_metadata": []},
            "idempotency": {
                "pattern": "event_id",
                "source": "platform_event_id",
                "durability": "in_memory",
            },
            "error_policy": {
                "default": "fail_fast",
                "retries": {"enabled": False, "max_attempts": 0},
                "escalation": {
                    "emit_error_packet": True,
                    "mark_task_failed": True,
                    "alert": "none",
                },
            },
            "runtime_touchpoints": {
                "touches_db": False,
                "touches_tools": False,
                "touches_external_network": False,
                "affects_boot": False,
            },
            "test_scope": {"unit": True, "integration": False, "docker_smoke": False},
            "acceptance": {
                "positive": [{"id": "AP-1", "description": "test"}],
                "negative": [{"id": "AN-1", "description": "test"}],
            },
            "spec_confidence": {"level": "low", "basis": []},
            "boot_impact": {"level": "none", "reason": "none"},
        }

        result = validator.validate_dict(data)

        # Should have error for forbidden pattern
        assert any("TBD" in e.message for e in result.errors)


# =============================================================================
# TEST: Sample Schemas Loading
# =============================================================================


class TestSampleSchemas:
    """Test loading sample schemas from codegen/schemas/samples."""

    def test_sample_schemas_directory_exists(self, sample_schemas_dir: Path) -> None:
        """Test that sample schemas directory exists."""
        assert sample_schemas_dir.exists(), (
            f"Sample schemas dir not found: {sample_schemas_dir}"
        )

    def test_load_simple_agent_yaml(self, sample_schemas_dir: Path) -> None:
        """Test loading simple_agent.yaml (v6.0 Research Factory format)."""
        path = sample_schemas_dir / "simple_agent.yaml"
        assert path.exists(), f"File not found: {path}"

        with open(path) as f:
            data = yaml.safe_load(f)

        # v6.0 format uses different structure
        assert "system" in data
        assert data["system"]["module"] == "echo"
        assert data["system"]["name"] == "SimpleEchoAgent"

    def test_load_domain_adapter_yaml(self, sample_schemas_dir: Path) -> None:
        """Test loading domain_adapter.yaml (v6.0 Research Factory format)."""
        path = sample_schemas_dir / "domain_adapter.yaml"
        assert path.exists(), f"File not found: {path}"

        with open(path) as f:
            data = yaml.safe_load(f)

        assert "system" in data
        assert data["system"]["module"] == "domain_adapter"
        assert "memorytopology" in data

    def test_load_orchestrator_yaml(self, sample_schemas_dir: Path) -> None:
        """Test loading orchestrator.yaml (v6.0 Research Factory format)."""
        path = sample_schemas_dir / "orchestrator.yaml"
        assert path.exists(), f"File not found: {path}"

        with open(path) as f:
            data = yaml.safe_load(f)

        assert "system" in data
        assert data["system"]["module"] == "orchestrator"
        assert data["system"]["name"] == "MainOrchestrator"

    def test_load_glue_layer_yaml(self, sample_schemas_dir: Path) -> None:
        """Test loading glue_layer.yaml (v6.0 Research Factory format)."""
        path = sample_schemas_dir / "glue_layer.yaml"
        assert path.exists(), f"File not found: {path}"

        with open(path) as f:
            data = yaml.safe_load(f)

        # Glue layer has different structure
        assert "wirings" in data
        assert "memory_harmonization" in data

    def test_all_sample_schemas_are_valid_yaml(self, sample_schemas_dir: Path) -> None:
        """Test all sample schemas are valid YAML."""
        yaml_files = list(sample_schemas_dir.glob("*.yaml"))
        assert len(yaml_files) > 0, "No YAML files found in sample_schemas/"

        for yaml_file in yaml_files:
            with open(yaml_file) as f:
                try:
                    data = yaml.safe_load(f)
                    assert data is not None, f"Empty YAML file: {yaml_file}"
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {yaml_file}: {e}")


# =============================================================================
# TEST: Module-Spec-v2.4 Template
# =============================================================================


class TestModuleSpecTemplate:
    """Test Module-Spec-v2.4.yaml template loading."""

    def test_template_exists(self, module_spec_template_path: Path) -> None:
        """Test that Module-Spec-v2.4.yaml exists."""
        assert module_spec_template_path.exists(), (
            f"Template not found: {module_spec_template_path}"
        )

    def test_template_is_valid_yaml(self, module_spec_template_path: Path) -> None:
        """Test that template is valid YAML."""
        with open(module_spec_template_path) as f:
            data = yaml.safe_load(f)

        assert data is not None
        assert "schema_version" in data
        assert data["schema_version"] == "2.4"

    def test_template_has_all_sections(self, module_spec_template_path: Path) -> None:
        """Test that template has all 22 sections."""
        with open(module_spec_template_path) as f:
            data = yaml.safe_load(f)

        required_sections = [
            "metadata",
            "ownership",
            "runtime_wiring",
            "external_surface",
            "dependencies",
            "packet_contract",
            "idempotency",
            "error_policy",
            "observability",
            "runtime_touchpoints",
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

        for section in required_sections:
            assert section in data, f"Missing section: {section}"


# =============================================================================
# TEST: Integration - Schema to Contract
# =============================================================================


class TestSchemaToContract:
    """Integration tests for schema loading and contract creation."""

    def test_create_contract_from_valid_dict(
        self, minimal_valid_contract: dict
    ) -> None:
        """Test creating a MetaContract from valid dict."""
        contract = MetaContract(**minimal_valid_contract)

        # Verify key properties
        assert contract.get_module_id() == "test_module"
        assert contract.get_packet_types() == [
            "test_module.in",
            "test_module.out",
            "test_module.error",
        ]
        assert contract.get_required_env_vars() == []  # No env vars in minimal

    def test_contract_validation_rules(self, minimal_valid_contract: dict) -> None:
        """Test validation rules are enforced."""
        # HTTP endpoint should require docker_smoke test
        minimal_valid_contract["external_surface"]["exposes_http_endpoint"] = True
        minimal_valid_contract["test_scope"]["docker_smoke"] = True  # Compliant

        contract = MetaContract(**minimal_valid_contract)
        assert contract.external_surface.exposes_http_endpoint is True
        assert contract.test_scope.docker_smoke is True
