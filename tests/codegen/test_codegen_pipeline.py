"""
CodeGenAgent Pipeline Integration Tests
========================================

Tests the complete code generation pipeline:
1. MetaLoader -> Load YAML spec
2. SchemaValidator -> Validate against Module-Spec-v2.4
3. MetaToIRCompiler -> Transform to IR
4. IRToPythonCompiler -> Generate Python code
5. FileEmitter -> Write files (dry run)

Version: 1.0.0
"""

from __future__ import annotations

# Path setup must come before any project imports
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from typing import Any, Dict

import pytest

from agents.codegenagent.file_emitter import FileEmitter
from ir_engine.compile_meta_to_ir import MetaToIRCompiler, ModuleIR
from ir_engine.ir_to_python import IRToPythonCompiler
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
from ir_engine.schema_validator import SchemaValidator, validate_schema

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def valid_spec() -> dict[str, Any]:
    """Create a valid Module-Spec-v2.4 specification."""
    return {
        "schema_version": "2.4",
        "metadata": {
            "module_id": "slack_adapter",
            "name": "Slack Adapter",
            "tier": "2",
            "description": "Handles Slack webhook events and message routing",
            "system": "L9",
            "language": "python",
            "runtime": "python>=3.11",
        },
        "ownership": {
            "team": "integrations",
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
            "exposes_webhook": True,
            "exposes_tool": False,
            "callable_from": ["external"],
        },
        "dependencies": {
            "allowed_tiers": [0, 1, 2],
            "outbound_calls": [
                {
                    "module": "memory.service",
                    "interface": "http",
                    "endpoint": "/memory/ingest",
                },
                {
                    "module": "aios.runtime",
                    "interface": "http",
                    "endpoint": "/chat",
                },
            ],
        },
        "packet_contract": {
            "emits": [
                "slack_adapter.in",
                "slack_adapter.out",
                "slack_adapter.error",
            ],
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
        "observability": {
            "logs": {"enabled": True, "level": "info"},
            "metrics": {
                "enabled": True,
                "counters": [
                    "slack_adapter_requests_total",
                    "slack_adapter_errors_total",
                ],
                "histograms": ["slack_adapter_latency_seconds"],
            },
            "traces": {"enabled": True},
        },
        "runtime_touchpoints": {
            "touches_db": True,
            "touches_tools": False,
            "touches_external_network": True,
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
                    "description": "Valid Slack event processed",
                    "test": "test_valid_slack_event",
                },
                {
                    "id": "AP-2",
                    "description": "Signature verified",
                    "test": "test_signature_valid",
                },
                {
                    "id": "AP-3",
                    "description": "Packet stored correctly",
                    "test": "test_packet_stored",
                },
            ],
            "negative": [
                {
                    "id": "AN-1",
                    "description": "Invalid signature rejected",
                    "test": "test_invalid_signature_rejected",
                },
                {
                    "id": "AN-2",
                    "description": "Malformed event rejected",
                    "test": "test_malformed_event_rejected",
                },
            ],
        },
        "global_invariants_ack": {
            "emits_packet_on_ingress": True,
            "tool_calls_traceable": True,
            "unknown_tool_id_hard_fail": True,
            "malformed_packet_blocked": True,
            "missing_env_fails_boot": True,
        },
        "spec_confidence": {
            "level": "high",
            "basis": ["Existing code present", "Tested in production"],
        },
        "repo": {
            "root_path": "/Users/ib-mac/Projects/L9",
            "allowed_new_files": [
                "api/slack_adapter_adapter.py",
                "api/routes/slack_adapter.py",
                "memory/slack_adapter_ingest.py",
                "tests/test_slack_adapter_adapter.py",
                "tests/test_slack_adapter_smoke.py",
            ],
            "allowed_modified_files": ["api/server.py"],
        },
        "interfaces": {
            "inbound": [
                {
                    "name": "slack_webhook",
                    "method": "POST",
                    "route": "/slack/events",
                    "headers": ["X-Slack-Signature", "X-Slack-Request-Timestamp"],
                    "payload_type": "JSON",
                    "auth": "hmac-sha256",
                },
            ],
            "outbound": [
                {
                    "name": "aios_chat",
                    "endpoint": "/chat",
                    "method": "POST",
                    "timeout_seconds": 30,
                    "retry": False,
                },
            ],
        },
        "environment": {
            "required": [
                {"name": "SLACK_SIGNING_SECRET", "description": "Slack signing secret"},
                {"name": "SLACK_BOT_TOKEN", "description": "Slack bot OAuth token"},
            ],
            "optional": [
                {
                    "name": "AIOS_BASE_URL",
                    "description": "AIOS endpoint",
                    "default": "http://localhost:8000",
                },
            ],
        },
        "orchestration": {
            "validation": ["Verify signature", "Check timestamp freshness"],
            "context_reads": [
                {
                    "method": "substrate_service.search_packets",
                    "filter": "thread_uuid",
                    "purpose": "History",
                },
            ],
            "aios_calls": [
                {"endpoint": "/chat", "input": "message", "output": "response"}
            ],
            "side_effects": [
                {
                    "action": "Store packet",
                    "service": "substrate_service.write_packet",
                    "packet_type": "slack_adapter.in",
                },
            ],
        },
        "boot_impact": {
            "level": "none",
            "reason": "No boot dependencies, late initialization acceptable",
        },
        "standards": {
            "identity": {"canonical_identifier": "tool_id"},
            "logging": {"library": "structlog", "forbidden": ["logging", "print"]},
            "http_client": {"library": "httpx", "forbidden": ["aiohttp", "requests"]},
        },
        "goals": [
            "Handle Slack webhook events with minimal latency",
            "Store all events as packets for audit trail",
        ],
        "non_goals": [
            "No new database tables",
            "No new migrations",
            "No parallel memory/logging/config systems",
        ],
        "notes_for_perplexity": [
            "Use REPO_CONTEXT_PACK imports exactly",
            "Use PacketEnvelopeIn for all packets",
        ],
    }


@pytest.fixture
def contract(valid_spec: dict[str, Any]) -> MetaContract:
    """Create a MetaContract from valid spec."""
    return MetaContract(**valid_spec)


@pytest.fixture
def ir_compiler() -> MetaToIRCompiler:
    """Create IR compiler instance."""
    return MetaToIRCompiler()


@pytest.fixture
def py_compiler() -> IRToPythonCompiler:
    """Create Python compiler instance."""
    return IRToPythonCompiler()


@pytest.fixture
def file_emitter() -> FileEmitter:
    """Create file emitter in dry-run mode."""
    return FileEmitter(dry_run=True)


# =============================================================================
# TEST: MetaContract Creation
# =============================================================================


class TestMetaContractCreation:
    """Test MetaContract creation from spec."""

    def test_create_from_valid_spec(self, valid_spec: dict[str, Any]) -> None:
        """Test creating MetaContract from valid spec."""
        contract = MetaContract(**valid_spec)

        assert contract.metadata.module_id == "slack_adapter"
        assert contract.metadata.name == "Slack Adapter"
        assert contract.metadata.tier == "2"

    def test_get_module_id(self, contract: MetaContract) -> None:
        """Test get_module_id helper."""
        assert contract.get_module_id() == "slack_adapter"

    def test_get_packet_types(self, contract: MetaContract) -> None:
        """Test get_packet_types helper."""
        packets = contract.get_packet_types()

        assert len(packets) == 3
        assert "slack_adapter.in" in packets
        assert "slack_adapter.out" in packets
        assert "slack_adapter.error" in packets

    def test_get_required_env_vars(self, contract: MetaContract) -> None:
        """Test get_required_env_vars helper."""
        env_vars = contract.get_required_env_vars()

        assert len(env_vars) == 2
        assert "SLACK_SIGNING_SECRET" in env_vars
        assert "SLACK_BOT_TOKEN" in env_vars

    def test_to_generation_context(self, contract: MetaContract) -> None:
        """Test to_generation_context helper."""
        context = contract.to_generation_context()

        assert context["module_id"] == "slack_adapter"
        assert context["service"] == "api"
        assert context["exposes_http_endpoint"] is True
        assert context["exposes_webhook"] is True
        assert len(context["packet_types"]) == 3


# =============================================================================
# TEST: Schema Validation
# =============================================================================


class TestSchemaValidation:
    """Test schema validation."""

    def test_valid_spec_passes(self, valid_spec: dict[str, Any]) -> None:
        """Test that valid spec passes validation."""
        validator = SchemaValidator(strict=False)
        result = validator.validate_dict(valid_spec)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_metadata_fails(self, valid_spec: dict[str, Any]) -> None:
        """Test that missing metadata fails validation."""
        del valid_spec["metadata"]

        validator = SchemaValidator(strict=False)
        result = validator.validate_dict(valid_spec)

        assert result.valid is False
        assert any("metadata" in e.field for e in result.errors)

    def test_missing_runtime_wiring_fails(self, valid_spec: dict[str, Any]) -> None:
        """Test that missing runtime_wiring fails validation."""
        del valid_spec["runtime_wiring"]

        validator = SchemaValidator(strict=False)
        result = validator.validate_dict(valid_spec)

        assert result.valid is False
        assert any("runtime_wiring" in e.message for e in result.errors)


# =============================================================================
# TEST: IR Compilation
# =============================================================================


class TestIRCompilation:
    """Test MetaContract to IR compilation."""

    def test_compile_to_ir(
        self,
        contract: MetaContract,
        ir_compiler: MetaToIRCompiler,
    ) -> None:
        """Test compiling MetaContract to IR."""
        ir = ir_compiler.compile(contract)

        assert ir.module_id == "slack_adapter"
        assert ir.module_name == "Slack Adapter"
        assert ir.tier == "2"

    def test_ir_has_targets(
        self,
        contract: MetaContract,
        ir_compiler: MetaToIRCompiler,
    ) -> None:
        """Test IR has generation targets."""
        ir = ir_compiler.compile(contract)

        assert len(ir.targets) > 0

        # Check for expected file types
        target_paths = [t.path for t in ir.targets]
        assert any("adapter.py" in p for p in target_paths)
        assert any("routes" in p for p in target_paths)

    def test_ir_has_dependencies(
        self,
        contract: MetaContract,
        ir_compiler: MetaToIRCompiler,
    ) -> None:
        """Test IR has dependency edges."""
        ir = ir_compiler.compile(contract)

        assert len(ir.dependencies) == 2

        dep_modules = [d.target_module for d in ir.dependencies]
        assert "memory.service" in dep_modules
        assert "aios.runtime" in dep_modules

    def test_ir_has_packets(
        self,
        contract: MetaContract,
        ir_compiler: MetaToIRCompiler,
    ) -> None:
        """Test IR has packet specs."""
        ir = ir_compiler.compile(contract)

        assert len(ir.packets) == 3

        packet_types = [p.packet_type for p in ir.packets]
        assert "slack_adapter.in" in packet_types

    def test_ir_has_tests(
        self,
        contract: MetaContract,
        ir_compiler: MetaToIRCompiler,
    ) -> None:
        """Test IR has test specs."""
        ir = ir_compiler.compile(contract)

        assert len(ir.tests) == 5  # 3 positive + 2 negative

        # Check positive tests
        positive_tests = [t for t in ir.tests if t.is_positive]
        assert len(positive_tests) == 3

        # Check negative tests
        negative_tests = [t for t in ir.tests if not t.is_positive]
        assert len(negative_tests) == 2

    def test_ir_has_wiring(
        self,
        contract: MetaContract,
        ir_compiler: MetaToIRCompiler,
    ) -> None:
        """Test IR has wiring spec."""
        ir = ir_compiler.compile(contract)

        assert ir.wiring is not None
        assert ir.wiring.service == "api"
        assert ir.wiring.startup_phase == "normal"
        assert ir.wiring.router_include == "slack_adapter_router"


# =============================================================================
# TEST: Python Code Generation
# =============================================================================


class TestPythonGeneration:
    """Test IR to Python code generation."""

    def test_generate_python_files(
        self,
        contract: MetaContract,
        ir_compiler: MetaToIRCompiler,
        py_compiler: IRToPythonCompiler,
    ) -> None:
        """Test generating Python files from IR."""
        ir = ir_compiler.compile(contract)
        files = py_compiler.compile(ir)

        assert len(files) > 0

    def test_generated_adapter_has_class(
        self,
        contract: MetaContract,
        ir_compiler: MetaToIRCompiler,
        py_compiler: IRToPythonCompiler,
    ) -> None:
        """Test generated adapter has expected class."""
        ir = ir_compiler.compile(contract)
        adapter_code = py_compiler.compile_single(ir, "adapter")

        assert "class SlackAdapterValidator:" in adapter_code
        assert "class SlackAdapterNormalizer:" in adapter_code
        assert "def validate_signature" in adapter_code

    def test_generated_route_has_endpoint(
        self,
        contract: MetaContract,
        ir_compiler: MetaToIRCompiler,
        py_compiler: IRToPythonCompiler,
    ) -> None:
        """Test generated route has expected endpoint."""
        ir = ir_compiler.compile(contract)
        route_code = py_compiler.compile_single(ir, "route")

        assert "router = APIRouter" in route_code
        assert '/slack_adapter"' in route_code or "slack_adapter" in route_code
        assert "async def" in route_code

    def test_generated_test_has_fixtures(
        self,
        contract: MetaContract,
        ir_compiler: MetaToIRCompiler,
        py_compiler: IRToPythonCompiler,
    ) -> None:
        """Test generated test has fixtures."""
        ir = ir_compiler.compile(contract)
        test_code = py_compiler.compile_single(ir, "test")

        assert "@pytest.fixture" in test_code
        assert "def validator" in test_code or "validator:" in test_code


# =============================================================================
# TEST: File Emission (Dry Run)
# =============================================================================


class TestFileEmission:
    """Test file emission in dry-run mode."""

    def test_emit_dry_run(
        self,
        contract: MetaContract,
        ir_compiler: MetaToIRCompiler,
        py_compiler: IRToPythonCompiler,
        file_emitter: FileEmitter,
    ) -> None:
        """Test emitting files in dry-run mode."""
        ir = ir_compiler.compile(contract)
        files = py_compiler.compile(ir)

        result = file_emitter.emit(files)

        # Should succeed (even though no actual files written)
        assert result.success
        # Should track what would be created
        assert result.file_count > 0

    def test_preview_emission(
        self,
        contract: MetaContract,
        ir_compiler: MetaToIRCompiler,
        py_compiler: IRToPythonCompiler,
        file_emitter: FileEmitter,
    ) -> None:
        """Test preview emission."""
        ir = ir_compiler.compile(contract)
        files = py_compiler.compile(ir)

        preview = file_emitter.preview(files)

        assert "new_files" in preview
        assert "modified_files" in preview
        assert len(preview["new_files"]) > 0


# =============================================================================
# TEST: Full Pipeline
# =============================================================================


class TestFullPipeline:
    """Test complete pipeline from spec to files."""

    def test_full_pipeline(
        self,
        valid_spec: dict[str, Any],
    ) -> None:
        """Test complete pipeline: spec -> contract -> IR -> Python -> files."""
        # Step 1: Validate spec
        validator = SchemaValidator(strict=False)
        validation = validator.validate_dict(valid_spec)
        assert validation.valid

        # Step 2: Create contract
        contract = MetaContract(**valid_spec)
        assert contract.metadata.module_id == "slack_adapter"

        # Step 3: Compile to IR
        ir_compiler = MetaToIRCompiler()
        ir = ir_compiler.compile(contract)
        assert ir.module_id == "slack_adapter"
        assert len(ir.targets) > 0

        # Step 4: Generate Python
        py_compiler = IRToPythonCompiler()
        files = py_compiler.compile(ir)
        assert len(files) > 0

        # Step 5: Emit files (dry run)
        emitter = FileEmitter(dry_run=True)
        result = emitter.emit_from_ir(ir, files)
        assert result.success

        # Verify outputs
        assert result.file_count > 0
        assert len(result.created_files) > 0
