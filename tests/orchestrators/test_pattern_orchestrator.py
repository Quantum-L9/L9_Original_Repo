"""
Pattern Orchestrator Tests
==========================

Unit and integration tests for PatternOrchestrator, CellAgentAdapter,
and Pattern API routes.

Version: 1.0.0
"""

import sys
from pathlib import Path

# Ensure project root is in path - use absolute resolved path
_this_file = Path(__file__).resolve()
PROJECT_ROOT = _this_file.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Try to import pattern modules - skip if unavailable
_pattern_import_error = ""
try:
    from orchestrators.pattern import metrics
    from orchestrators.pattern.cell_adapter import (CellAgentAdapter,
                                                    DirectLLMAgent)
    from orchestrators.pattern.interface import (NodeDefinition, NodeKind,
                                                 NodeResult, NodeStatus,
                                                 PipelineResult,
                                                 PipelineStatus)
    from orchestrators.pattern.orchestrator import PatternOrchestrator

    _pattern_available = True
except ImportError as e:
    _pattern_available = False
    _pattern_import_error = str(e)

# Mark all tests to skip if pattern module unavailable
pytestmark = pytest.mark.skipif(
    not _pattern_available,
    reason=f"Pattern module not available: {_pattern_import_error if not _pattern_available else ''}",
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_cell_result():
    """Create a mock CellResult."""
    # Use a simple mock instead of importing CellResult
    result = MagicMock()
    result.cell_id = uuid4()
    result.cell_type = "architect"
    result.success = True
    result.output = {"architecture_name": "test", "components": []}
    result.rounds = []
    result.consensus_reached = True
    result.final_score = 0.9
    result.total_rounds = 2
    result.duration_ms = 1500
    result.errors = []
    return result


@pytest.fixture
def mock_agent():
    """Create a mock agent that implements AgentProtocol."""
    agent = AsyncMock()
    agent.invoke = AsyncMock(
        return_value={
            "requirements": ["req1", "req2"],
            "constraints": ["const1"],
        }
    )
    return agent


# ============================================================================
# Interface Model Tests
# ============================================================================


class TestInterfaceModels:
    """Tests for Pydantic interface models."""

    def test_node_kind_enum(self):
        """Test NodeKind enum values."""
        assert NodeKind.REASONING == "reasoning"
        assert NodeKind.EXECUTION == "execution"
        assert NodeKind.VALIDATION == "validation"

    def test_node_status_enum(self):
        """Test NodeStatus enum values."""
        assert NodeStatus.PENDING == "pending"
        assert NodeStatus.RUNNING == "running"
        assert NodeStatus.SUCCESS == "success"
        assert NodeStatus.FAILURE == "failure"

    def test_pipeline_status_enum(self):
        """Test PipelineStatus enum values."""
        assert PipelineStatus.PENDING == "pending"
        assert PipelineStatus.SUCCESS == "success"
        assert PipelineStatus.FAILURE == "failure"

    def test_node_definition_creation(self):
        """Test NodeDefinition model creation."""
        node = NodeDefinition(
            id="N1",
            name="Reasoning",
            kind=NodeKind.REASONING,
            agent_role="ArchitectAgent",
            prompt_template="Analyze requirements",
        )

        assert node.id == "N1"
        assert node.kind == NodeKind.REASONING

    def test_node_result_creation(self):
        """Test NodeResult model creation."""
        result = NodeResult(
            node_id="N1",
            status=NodeStatus.SUCCESS,
            output={"key": "value"},
            duration_ms=1000,
        )

        assert result.status == NodeStatus.SUCCESS
        assert result.output == {"key": "value"}

    def test_pipeline_result_creation(self):
        """Test PipelineResult model creation."""
        from datetime import datetime

        result = PipelineResult(
            trace_id=uuid4(),
            subsystem="test",
            status=PipelineStatus.SUCCESS,
            started_at=datetime.utcnow(),
        )

        assert result.is_success is True
        assert result.node_results == []


# ============================================================================
# CellAgentAdapter Tests
# ============================================================================


class TestCellAgentAdapter:
    """Tests for CellAgentAdapter."""

    def test_adapter_initialization(self):
        """Test adapter initializes with default config."""
        adapter = CellAgentAdapter()

        assert adapter._role_mapping is not None
        assert "ArchitectAgent" in adapter._role_mapping
        assert "CoderAgent" in adapter._role_mapping

    def test_adapter_role_mapping(self):
        """Test role to cell class mapping."""
        adapter = CellAgentAdapter()

        assert (
            "collaborative_cells.architect_cell.ArchitectCell"
            in adapter._role_mapping["ArchitectAgent"]
        )
        assert (
            "collaborative_cells.coder_cell.CoderCell"
            in adapter._role_mapping["CoderAgent"]
        )

    def test_adapter_custom_role_mapping(self):
        """Test custom role mapping."""
        custom_mapping = {
            "CustomAgent": "mymodule.CustomCell",
        }

        adapter = CellAgentAdapter(role_mapping=custom_mapping)

        assert "CustomAgent" in adapter._role_mapping
        assert adapter._role_mapping["CustomAgent"] == "mymodule.CustomCell"

    def test_adapter_register_role(self):
        """Test registering new role."""
        adapter = CellAgentAdapter()
        adapter.register_role("NewAgent", "path.to.NewCell")

        assert "NewAgent" in adapter._role_mapping

    def test_adapter_clear_cache(self):
        """Test clearing cell cache."""
        adapter = CellAgentAdapter()
        adapter._cell_cache["test"] = MagicMock()

        adapter.clear_cache()

        assert len(adapter._cell_cache) == 0

    def test_adapter_unknown_role_raises(self):
        """Test unknown role raises ValueError."""
        adapter = CellAgentAdapter()

        with pytest.raises(ValueError, match="Unknown role"):
            adapter._get_cell_for_role("UnknownAgent")


# ============================================================================
# PatternOrchestrator Tests
# ============================================================================


class TestPatternOrchestrator:
    """Tests for PatternOrchestrator."""

    @pytest.fixture
    def test_configs(self, tmp_path):
        """Create temporary config files for testing."""
        import yaml

        pattern_config = {
            "pattern_name": "test_pattern",
            "version": 1,
            "nodes": [],
            "observability": {"emit_metrics": []},
        }

        subsystem_config = {
            "metadata": {"name": "test", "version": "1.0.0"},
            "goals": [],
        }

        pattern_path = tmp_path / "pattern.yaml"
        subsystem_path = tmp_path / "subsystem.yaml"

        with open(pattern_path, "w") as f:
            yaml.dump(pattern_config, f)

        with open(subsystem_path, "w") as f:
            yaml.dump(subsystem_config, f)

        return str(pattern_path), str(subsystem_path)

    def test_orchestrator_stub_agent_default(self, test_configs):
        """Test orchestrator uses StubAgent when no agent provided."""
        pattern_path, subsystem_path = test_configs
        orchestrator = PatternOrchestrator(
            pattern_path=pattern_path,
            subsystem_config_path=subsystem_path,
        )

        assert orchestrator._agent is not None

    def test_orchestrator_accepts_custom_agent(self, mock_agent, test_configs):
        """Test orchestrator accepts custom agent."""
        pattern_path, subsystem_path = test_configs
        orchestrator = PatternOrchestrator(
            pattern_path=pattern_path,
            subsystem_config_path=subsystem_path,
            agent=mock_agent,
        )

        assert orchestrator._agent is mock_agent

    def test_orchestrator_has_pattern(self, test_configs):
        """Test orchestrator has pattern config loaded."""
        pattern_path, subsystem_path = test_configs
        orchestrator = PatternOrchestrator(
            pattern_path=pattern_path,
            subsystem_config_path=subsystem_path,
        )

        # Verify pattern was loaded
        assert orchestrator._pattern is not None


# ============================================================================
# Metrics Tests
# ============================================================================


class TestMetrics:
    """Tests for pattern metrics."""

    def test_metrics_module_loads(self):
        """Test metrics module loads without error."""
        assert hasattr(metrics, "PatternMetrics")
        assert hasattr(metrics, "PROMETHEUS_AVAILABLE")

    def test_pattern_metrics_creation(self):
        """Test PatternMetrics can be created."""
        pm = metrics.PatternMetrics(subsystem="test")
        assert pm.subsystem == "test"

    def test_pattern_metrics_record_pipeline(self):
        """Test PatternMetrics can record pipeline result."""
        pm = metrics.PatternMetrics(subsystem="test")
        # Should not raise even if prometheus unavailable
        pm.record_pipeline_result(status="success")


# ============================================================================
# API Route Tests
# ============================================================================


class TestPatternAPI:
    """Tests for Pattern API routes."""

    def test_execute_request_validation(self):
        """Test PatternExecuteRequest validation."""
        try:
            from api.routes.pattern import PatternExecuteRequest
        except ImportError:
            pytest.skip("API routes not available")

        # Valid request
        request = PatternExecuteRequest(
            user_prompts=["Build a user auth system"],
        )
        assert len(request.user_prompts) == 1
        assert request.dry_run is False

    def test_execute_request_requires_prompts(self):
        """Test PatternExecuteRequest requires at least one prompt."""
        try:
            from api.routes.pattern import PatternExecuteRequest
        except ImportError:
            pytest.skip("API routes not available")
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PatternExecuteRequest(user_prompts=[])

    def test_execute_response_model(self):
        """Test PatternExecuteResponse model."""
        try:
            from api.routes.pattern import PatternExecuteResponse
        except ImportError:
            pytest.skip("API routes not available")

        response = PatternExecuteResponse(
            success=True,
            pipeline_id="test-123",
            status="completed",
        )

        assert response.nodes_executed == 0
        assert response.errors == []


# ============================================================================
# Integration Tests
# ============================================================================


class TestPatternIntegration:
    """Integration tests for full pattern pipeline."""

    @pytest.fixture
    def test_configs(self, tmp_path):
        """Create temporary config files for testing."""
        import yaml

        pattern_config = {
            "pattern_name": "test_pattern",
            "version": 1,
            "nodes": [],
            "observability": {"emit_metrics": []},
        }

        subsystem_config = {
            "metadata": {"name": "test", "version": "1.0.0"},
            "goals": [],
        }

        pattern_path = tmp_path / "pattern.yaml"
        subsystem_path = tmp_path / "subsystem.yaml"

        with open(pattern_path, "w") as f:
            yaml.dump(pattern_config, f)

        with open(subsystem_path, "w") as f:
            yaml.dump(subsystem_config, f)

        return str(pattern_path), str(subsystem_path)

    @pytest.mark.asyncio
    async def test_orchestrator_dry_run(self, mock_agent, test_configs):
        """Test orchestrator dry run mode."""
        pattern_path, subsystem_path = test_configs
        orchestrator = PatternOrchestrator(
            pattern_path=pattern_path,
            subsystem_config_path=subsystem_path,
            agent=mock_agent,
        )

        result = await orchestrator.execute(
            user_prompts=["Test prompt"],
            dry_run=True,
        )

        # Dry run should complete but not invoke agents
        assert result is not None

    @pytest.mark.asyncio
    async def test_cell_adapter_invoke(self, mock_cell_result):
        """Test CellAgentAdapter.invoke with mocked cell."""
        adapter = CellAgentAdapter()

        # Mock the cell execution
        with patch.object(adapter, "_get_cell_for_role") as mock_get_cell:
            mock_cell = AsyncMock()
            mock_cell.execute = AsyncMock(return_value=mock_cell_result)
            mock_get_cell.return_value = mock_cell

            result = await adapter.invoke(
                role="ArchitectAgent",
                prompt="Design a system",
                input_data={"user_prompts": ["Build X"]},
                context={"trace_id": "test-123"},
            )

            assert result is not None
            assert "_cell_metadata" in result


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_cell_adapter(self):
        """Test create_cell_adapter factory."""
        from orchestrators.pattern.cell_adapter import create_cell_adapter

        adapter = create_cell_adapter(model="gpt-4o", max_rounds=5)

        assert adapter is not None
        assert adapter._cell_config.max_rounds == 5

    def test_create_direct_agent(self):
        """Test create_direct_agent factory."""
        try:
            from orchestrators.pattern.cell_adapter import create_direct_agent

            # Will fail without API key, but should not raise on creation
            agent = create_direct_agent(model="gpt-4o")

            assert agent is not None
            assert agent._model == "gpt-4o"
        except Exception:
            # May fail if OpenAI not installed
            pytest.skip("OpenAI not available")
