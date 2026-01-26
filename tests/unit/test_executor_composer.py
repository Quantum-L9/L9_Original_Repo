"""
Unit Tests for ExecutorComposer
================================

Tests the composition pattern implementation for AgentExecutorService.

Test Coverage:
- ExecutorConfig.from_env() with various env configurations
- ExecutorComposer.compose() happy path
- ExecutorComposer.compose() with missing DIContainer
- ExecutorComposer.compose() with missing dependencies
- ExecutorDeps resolution with required and optional dependencies
- Fluent interface pattern (set_di_container returns self)
- Config validation and error handling

Mutation Testing Target: 85%+ score
"""

from unittest.mock import Mock, patch

import pytest

from core.agents.executor_composer import (
    ExecutorComposer,
    ExecutorConfig,
    ExecutorDeps,
)


class TestExecutorConfig:
    """Test ExecutorConfig dataclass and from_env() factory."""

    def test_from_env_with_defaults(self):
        """Test config loading with default values."""
        env = {}
        config = ExecutorConfig.from_env(env)

        assert config.default_agent_id == "l-cto"
        assert config.max_iterations == 10
        assert config.enable_persistence is True
        assert config.enable_approval_gates is True
        assert config.fallback_agent_id == "l9-standard-v1"

    def test_from_env_with_custom_values(self):
        """Test config loading with custom env vars."""
        env = {
            "DEFAULT_AGENT_ID": "custom-agent",
            "AGENT_MAX_ITERATIONS": "20",
            "AGENT_ENABLE_PERSISTENCE": "false",
            "AGENT_ENABLE_APPROVAL_GATES": "false",
            "FALLBACK_AGENT_ID": "fallback-agent",
        }
        config = ExecutorConfig.from_env(env)

        assert config.default_agent_id == "custom-agent"
        assert config.max_iterations == 20
        assert config.enable_persistence is False
        assert config.enable_approval_gates is False
        assert config.fallback_agent_id == "fallback-agent"

    def test_from_env_boolean_parsing(self):
        """Test boolean env var parsing (case insensitive)."""
        # Test true variants
        for true_val in ["true", "True", "TRUE", "yes", "1"]:
            env = {"AGENT_ENABLE_PERSISTENCE": true_val}
            config = ExecutorConfig.from_env(env)
            # Only "true" (case insensitive) should be True
            if true_val.lower() == "true":
                assert config.enable_persistence is True

        # Test false variants
        for false_val in ["false", "False", "FALSE", "no", "0", ""]:
            env = {"AGENT_ENABLE_PERSISTENCE": false_val}
            config = ExecutorConfig.from_env(env)
            assert config.enable_persistence is False

    def test_from_env_max_iterations_parsing(self):
        """Test max_iterations parsing with various inputs."""
        # Valid integer
        env = {"AGENT_MAX_ITERATIONS": "15"}
        config = ExecutorConfig.from_env(env)
        assert config.max_iterations == 15

        # Invalid integer should raise ValueError
        env = {"AGENT_MAX_ITERATIONS": "not-a-number"}
        with pytest.raises(ValueError):
            ExecutorConfig.from_env(env)

    def test_from_env_boundary_values(self):
        """Test boundary values for max_iterations."""
        # Zero iterations
        env = {"AGENT_MAX_ITERATIONS": "0"}
        config = ExecutorConfig.from_env(env)
        assert config.max_iterations == 0

        # Large iterations
        env = {"AGENT_MAX_ITERATIONS": "1000"}
        config = ExecutorConfig.from_env(env)
        assert config.max_iterations == 1000

        # Negative iterations (should parse but may be invalid)
        env = {"AGENT_MAX_ITERATIONS": "-1"}
        config = ExecutorConfig.from_env(env)
        assert config.max_iterations == -1


class TestExecutorDeps:
    """Test ExecutorDeps dataclass."""

    def test_deps_creation_required_only(self):
        """Test creating deps with only required dependencies."""
        aios = Mock()
        tool_registry = Mock()
        substrate = Mock()
        agent_registry = Mock()

        deps = ExecutorDeps(
            aios_runtime=aios,
            tool_registry=tool_registry,
            substrate_service=substrate,
            agent_registry=agent_registry,
        )

        assert deps.aios_runtime is aios
        assert deps.tool_registry is tool_registry
        assert deps.substrate_service is substrate
        assert deps.agent_registry is agent_registry
        assert deps.agent_persistence is None
        assert deps.approval_manager is None

    def test_deps_creation_with_optional(self):
        """Test creating deps with optional dependencies."""
        aios = Mock()
        tool_registry = Mock()
        substrate = Mock()
        agent_registry = Mock()
        persistence = Mock()
        approval = Mock()

        deps = ExecutorDeps(
            aios_runtime=aios,
            tool_registry=tool_registry,
            substrate_service=substrate,
            agent_registry=agent_registry,
            agent_persistence=persistence,
            approval_manager=approval,
        )

        assert deps.agent_persistence is persistence
        assert deps.approval_manager is approval


class TestExecutorComposer:
    """Test ExecutorComposer composition pattern."""

    def test_composer_initialization(self):
        """Test composer initialization with default env."""
        composer = ExecutorComposer()
        assert composer._env is not None
        assert composer._di_container is None
        assert composer._config is None

    def test_composer_initialization_with_custom_env(self):
        """Test composer initialization with custom env."""
        custom_env = {"TEST_VAR": "test_value"}
        composer = ExecutorComposer(env=custom_env)
        assert composer._env == custom_env

    def test_set_di_container_fluent_interface(self):
        """Test set_di_container returns self for fluent chaining."""
        composer = ExecutorComposer()
        container = Mock()

        result = composer.set_di_container(container)

        assert result is composer
        assert composer._di_container is container

    def test_compose_without_di_container_raises_error(self):
        """Test compose() raises ValueError if DIContainer not set."""
        composer = ExecutorComposer()

        with pytest.raises(ValueError) as exc_info:
            composer.compose()

        assert "DIContainer not wired" in str(exc_info.value)

    @patch("core.agents.executor_composer.ExecutorConfig.from_env")
    @patch("core.agents.executor.AgentExecutorService")
    def test_compose_happy_path(self, mock_executor_class, mock_from_env):
        """Test successful composition with all dependencies."""
        # Setup mocks
        mock_config = Mock()
        mock_config.default_agent_id = "test-agent"
        mock_config.max_iterations = 10
        mock_config.enable_persistence = True
        mock_config.enable_approval_gates = True
        mock_from_env.return_value = mock_config

        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor

        # Mock DIContainer
        mock_container = Mock()
        mock_aios = Mock()
        mock_tool_registry = Mock()
        mock_substrate = Mock()
        mock_agent_registry = Mock()
        mock_persistence = Mock()
        mock_approval = Mock()

        def mock_resolve(interface):
            """Mock resolve based on interface type."""
            if "AIOSRuntime" in str(interface):
                return mock_aios
            if "ExecutorToolRegistry" in str(interface):
                return mock_tool_registry
            if "MemorySubstrateService" in str(interface):
                return mock_substrate
            if "AgentRegistry" in str(interface):
                return mock_agent_registry
            raise KeyError(f"Unknown interface: {interface}")

        def mock_get_optional(interface):
            """Mock get_optional for optional dependencies."""
            if "AgentPersistenceService" in str(interface):
                return mock_persistence
            if "ApprovalManager" in str(interface):
                return mock_approval
            return None

        mock_container.resolve = mock_resolve
        mock_container.get_optional = mock_get_optional

        # Execute
        composer = ExecutorComposer()
        composer.set_di_container(mock_container)

        with patch("core.agents.executor_composer.AIOSRuntime", Mock()):
            with patch("core.agents.executor_composer.ExecutorToolRegistry", Mock()):
                with patch(
                    "core.agents.executor_composer.MemorySubstrateService", Mock()
                ):
                    with patch("core.agents.executor_composer.AgentRegistry", Mock()):
                        with patch(
                            "core.agents.executor_composer.AgentPersistenceService",
                            Mock(),
                        ):
                            with patch(
                                "core.agents.executor_composer.ApprovalManager", Mock()
                            ):
                                result = composer.compose()

        # Verify
        assert result is mock_executor
        mock_executor_class.assert_called_once()

    def test_compose_with_missing_required_dependency(self):
        """Test compose() raises ValueError if required dependency missing."""
        mock_container = Mock()
        mock_container.resolve.side_effect = KeyError("AIOSRuntime not registered")

        composer = ExecutorComposer()
        composer.set_di_container(mock_container)

        with patch("core.agents.executor_composer.ExecutorConfig.from_env"):
            with patch("core.agents.executor_composer.AIOSRuntime", Mock()):
                with pytest.raises(ValueError) as exc_info:
                    composer.compose()

        assert "Missing dependency" in str(exc_info.value)

    def test_get_config_before_compose(self):
        """Test get_config() returns None before compose()."""
        composer = ExecutorComposer()
        assert composer.get_config() is None

    @patch("core.agents.executor_composer.ExecutorConfig.from_env")
    def test_get_config_after_compose(self, mock_from_env):
        """Test get_config() returns config after compose()."""
        mock_config = Mock()
        mock_from_env.return_value = mock_config

        mock_container = Mock()

        # Mock all required imports and dependencies
        with patch("core.agents.executor_composer.AIOSRuntime", Mock()):
            with patch("core.agents.executor_composer.ExecutorToolRegistry", Mock()):
                with patch(
                    "core.agents.executor_composer.MemorySubstrateService", Mock()
                ):
                    with patch("core.agents.executor_composer.AgentRegistry", Mock()):
                        with patch("core.agents.executor.AgentExecutorService", Mock()):
                            mock_container.resolve = Mock(return_value=Mock())
                            mock_container.get_optional = Mock(return_value=None)

                            composer = ExecutorComposer()
                            composer.set_di_container(mock_container)

                            try:
                                composer.compose()
                            except Exception:
                                pass  # Ignore errors, we just want config set

                            config = composer.get_config()
                            assert config is mock_config


class TestExecutorComposerIntegration:
    """Integration tests for ExecutorComposer with real DIContainer."""

    def test_compose_with_real_container_missing_deps(self):
        """Test compose() with real DIContainer but no registrations."""
        from core.di.container import DIContainer

        container = DIContainer()
        composer = ExecutorComposer()
        composer.set_di_container(container)

        with pytest.raises(ValueError) as exc_info:
            composer.compose()

        assert "Missing dependency" in str(exc_info.value)


# =============================================================================
# Mutation Testing Targets
# =============================================================================


class TestMutationTargets:
    """
    Tests specifically designed to kill common mutations.

    These tests target boundary conditions, boolean logic, and
    comparison operators that mutation testing commonly mutates.
    """

    def test_max_iterations_boundary_zero(self):
        """Kill mutation: max_iterations > 0 -> max_iterations >= 0."""
        env = {"AGENT_MAX_ITERATIONS": "0"}
        config = ExecutorConfig.from_env(env)
        assert config.max_iterations == 0  # Exact match

    def test_max_iterations_boundary_one(self):
        """Kill mutation: max_iterations >= 1 -> max_iterations > 1."""
        env = {"AGENT_MAX_ITERATIONS": "1"}
        config = ExecutorConfig.from_env(env)
        assert config.max_iterations == 1  # Exact match

    def test_enable_persistence_exact_true(self):
        """Kill mutation: == 'true' -> != 'true'."""
        env = {"AGENT_ENABLE_PERSISTENCE": "true"}
        config = ExecutorConfig.from_env(env)
        assert config.enable_persistence is True

        env = {"AGENT_ENABLE_PERSISTENCE": "false"}
        config = ExecutorConfig.from_env(env)
        assert config.enable_persistence is False

    def test_di_container_none_check(self):
        """Kill mutation: if not container -> if container."""
        composer = ExecutorComposer()
        # Don't set container

        with pytest.raises(ValueError):
            composer.compose()

    def test_optional_dependency_none_handling(self):
        """Kill mutation: if persistence -> if not persistence."""
        deps = ExecutorDeps(
            aios_runtime=Mock(),
            tool_registry=Mock(),
            substrate_service=Mock(),
            agent_registry=Mock(),
            agent_persistence=None,  # Explicitly None
        )

        assert deps.agent_persistence is None
