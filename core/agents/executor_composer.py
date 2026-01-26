"""
L9 Core Agents - Executor Composer
===================================

Composition pattern for AgentExecutorService following Dependency Inversion Principle.

Separates concerns:
  - Composition (env reading, dependency wiring) → ExecutorComposer
  - Execution (agent lifecycle, planning, tool execution) → AgentExecutorService

Follows frontier AI lab pattern (dependency injection + composition root).

Key responsibilities:
- Read environment configuration
- Resolve dependencies from DIContainer
- Validate configuration
- Return fully-wired AgentExecutorService

This module does NOT:
- Execute agent tasks (AgentExecutorService does that)
- Define agent personalities (AIOS does that)
- Approve or deny tool usage (Governance Engine does that)

Version: 1.0.0
GMP: refactor-phase0-plan1
"""

from __future__ import annotations

# ============================================================================
# DORA HEADER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_meta__ = {
    "component_id": "COR-FOUN-002",
    "component_name": "ExecutorComposer",
    "module_version": "1.0.0",
    "created_at": "2026-01-21T00:00:00Z",
    "created_by": "L9_Refactoring_Phase0",
    "layer": "foundation",
    "domain": "agent_composition",
    "type": "composer",
    "status": "active",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "purpose": "Composition root for AgentExecutorService with DI pattern",
    "dependencies": [
        "core.agents.executor",
        "core.di.container",
        "memory.substrate_service",
        "core.tools.registry_adapter",
    ],
}
# ============================================================================

import os
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Configuration and Dependency Models
# =============================================================================


@dataclass
class ExecutorConfig:
    """
    Environment-driven configuration for AgentExecutorService.

    All environment variable reading is centralized here to maintain
    separation of concerns and testability.

    Attributes:
        default_agent_id: Default agent ID for tasks without explicit agent
        max_iterations: Maximum reasoning loop iterations
        enable_persistence: Enable agent state persistence
        enable_approval_gates: Enable governance approval gates
        fallback_agent_id: Fallback agent if default not found
    """

    default_agent_id: str
    max_iterations: int
    enable_persistence: bool
    enable_approval_gates: bool
    fallback_agent_id: str = "l9-standard-v1"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> ExecutorConfig:
        """
        Load configuration from environment variables.

        Args:
            env: Optional environment dict (defaults to os.environ for testing)

        Returns:
            ExecutorConfig instance with values from environment

        Example:
            >>> config = ExecutorConfig.from_env()
            >>> config.default_agent_id
            'l-cto'
        """
        env = env or os.environ

        return cls(
            default_agent_id=env.get("DEFAULT_AGENT_ID", "l-cto"),
            max_iterations=int(env.get("AGENT_MAX_ITERATIONS", "10")),
            enable_persistence=env.get("AGENT_ENABLE_PERSISTENCE", "true").lower()
            == "true",
            enable_approval_gates=env.get("AGENT_ENABLE_APPROVAL_GATES", "true").lower()
            == "true",
            fallback_agent_id=env.get("FALLBACK_AGENT_ID", "l9-standard-v1"),
        )


@dataclass
class ExecutorDeps:
    """
    Immutable dependency bundle for AgentExecutorService.

    All dependencies are resolved from DIContainer and bundled here
    to maintain explicit dependency contracts.

    Attributes:
        aios_runtime: AIOS runtime for agent reasoning
        tool_registry: Tool registry for tool dispatch
        substrate_service: Memory substrate for persistence
        agent_registry: Agent registry for configs
        agent_persistence: Optional agent persistence service
        approval_manager: Optional approval manager for governance
    """

    aios_runtime: Any
    tool_registry: Any
    substrate_service: Any
    agent_registry: Any
    agent_persistence: Any | None = None
    approval_manager: Any | None = None


# =============================================================================
# Executor Composer
# =============================================================================


class ExecutorComposer:
    """
    Composition root for AgentExecutorService.

    Implements the Composition Pattern (formerly called Factory Pattern in
    Phase 0 docs, renamed to avoid confusion with GoF Factory Pattern).

    Responsibilities:
      1. Read environment configuration
      2. Resolve dependencies from DIContainer
      3. Validate configuration
      4. Return fully-wired AgentExecutorService

    Pattern: Composition Root (Dependency Injection)

    Example:
        >>> from core.di.container import DIContainer
        >>> container = DIContainer()
        >>> # ... register services ...
        >>> composer = ExecutorComposer()
        >>> composer.set_di_container(container)
        >>> executor = composer.compose()
    """

    def __init__(self, env: dict[str, str] | None = None):
        """
        Initialize composer with optional env override.

        Args:
            env: Override environment dict (default: os.environ)
                 Useful for testing with custom env vars
        """
        self._env = env or os.environ
        self._di_container: Any | None = None
        self._config: ExecutorConfig | None = None

        logger.debug(
            "executor_composer.initialized",
            env_override=env is not None,
        )

    def set_di_container(self, container: Any) -> ExecutorComposer:
        """
        Wire DIContainer for dependency resolution.

        Args:
            container: Initialized DIContainer with services registered

        Returns:
            self (fluent interface)

        Example:
            >>> composer.set_di_container(container)
            >>> executor = composer.compose()
        """
        self._di_container = container

        logger.debug(
            "executor_composer.di_container_set",
            container_type=type(container).__name__,
        )

        return self

    def compose(self) -> Any:
        """
        Compose fully-wired AgentExecutorService.

        Flow:
          1. Load config from env
          2. Resolve deps from DIContainer
          3. Validate config + deps
          4. Create + return AgentExecutorService

        Returns:
            AgentExecutorService instance (ready to execute)

        Raises:
            ValueError: If config invalid or deps missing

        Example:
            >>> executor = composer.compose()
            >>> result = await executor.start_agent_task(task)
        """
        # Step 1: Load config from environment
        self._config = ExecutorConfig.from_env(self._env)

        logger.info(
            "executor_composer.config_loaded",
            default_agent_id=self._config.default_agent_id,
            max_iterations=self._config.max_iterations,
            persistence=self._config.enable_persistence,
            approval_gates=self._config.enable_approval_gates,
        )

        # Step 2: Validate DIContainer
        if not self._di_container:
            error_msg = (
                "DIContainer not wired. Call set_di_container() before compose()."
            )
            logger.error("executor_composer.composition_failed", reason=error_msg)
            raise ValueError(error_msg)

        # Step 3: Resolve dependencies
        try:
            deps = self._resolve_dependencies()
        except KeyError as e:
            logger.error(
                "executor_composer.dependency_resolution_failed",
                missing_dependency=str(e),
            )
            raise ValueError(f"Missing dependency: {e}") from e
        except Exception as e:
            logger.error(
                "executor_composer.dependency_resolution_error",
                error=str(e),
                exc_info=True,
            )
            raise ValueError(f"Dependency resolution failed: {e}") from e

        # Step 4: Import AgentExecutorService (late import to avoid circular deps)
        try:
            from core.agents.executor import AgentExecutorService
        except ImportError as e:
            logger.error(
                "executor_composer.import_failed",
                module="core.agents.executor",
                error=str(e),
            )
            raise ValueError(f"Failed to import AgentExecutorService: {e}") from e

        # Step 5: Create AgentExecutorService
        executor = AgentExecutorService(
            aios_runtime=deps.aios_runtime,
            tool_registry=deps.tool_registry,
            substrate_service=deps.substrate_service,
            agent_registry=deps.agent_registry,
            default_agent_id=self._config.default_agent_id,
            max_iterations=self._config.max_iterations,
            agent_persistence=deps.agent_persistence
            if self._config.enable_persistence
            else None,
        )

        # Step 6: Wire optional approval manager if enabled
        if self._config.enable_approval_gates and deps.approval_manager:
            # Note: AgentExecutorService doesn't have set_approval_manager yet
            # This will be wired in a future PR when approval_manager is integrated
            logger.debug(
                "executor_composer.approval_manager_available",
                enabled=True,
            )

        trace_id = str(uuid4())
        logger.info(
            "executor_composer.composition_complete",
            executor_type=type(executor).__name__,
            trace_id=trace_id,
            config=self._config.__dict__,
        )

        return executor

    def _resolve_dependencies(self) -> ExecutorDeps:
        """
        Resolve all dependencies from DIContainer.

        Returns:
            ExecutorDeps (immutable bundle)

        Raises:
            KeyError: If any required dependency not registered

        Note:
            Uses get_optional() for optional dependencies (persistence, approval)
            to avoid failing if they're not registered.
        """
        # Import protocol types for resolution
        # Note: Actual protocol locations may vary, adjust imports as needed
        try:
            from core.agents.registry import AgentRegistry
            from core.aios.runtime import AIOSRuntime
            from core.tools.registry_adapter import ExecutorToolRegistry
            from memory.substrate_service import MemorySubstrateService
        except ImportError as e:
            logger.error(
                "executor_composer.protocol_import_failed",
                error=str(e),
            )
            raise KeyError(f"Failed to import protocol types: {e}") from e

        # Resolve required dependencies
        try:
            aios_runtime = self._di_container.resolve(AIOSRuntime)
            tool_registry = self._di_container.resolve(ExecutorToolRegistry)
            substrate_service = self._di_container.resolve(MemorySubstrateService)
            agent_registry = self._di_container.resolve(AgentRegistry)
        except Exception as e:
            logger.error(
                "executor_composer.required_dependency_missing",
                error=str(e),
            )
            raise KeyError(f"Required dependency not registered: {e}") from e

        # Resolve optional dependencies
        agent_persistence = None
        approval_manager = None

        if hasattr(self._di_container, "get_optional"):
            try:
                from memory.agent_persistence import AgentPersistenceService

                agent_persistence = self._di_container.get_optional(
                    AgentPersistenceService
                )
            except Exception as e:
                logger.debug(
                    "executor_composer.optional_dependency_unavailable",
                    dependency="AgentPersistenceService",
                    reason=str(e),
                )

        if hasattr(self._di_container, "get_optional"):
            try:
                from core.governance.approvals import ApprovalManager

                approval_manager = self._di_container.get_optional(ApprovalManager)
            except Exception as e:
                logger.debug(
                    "executor_composer.optional_dependency_unavailable",
                    dependency="ApprovalManager",
                    reason=str(e),
                )

        logger.debug(
            "executor_composer.dependencies_resolved",
            required_count=4,
            optional_count=sum(
                [
                    agent_persistence is not None,
                    approval_manager is not None,
                ]
            ),
        )

        return ExecutorDeps(
            aios_runtime=aios_runtime,
            tool_registry=tool_registry,
            substrate_service=substrate_service,
            agent_registry=agent_registry,
            agent_persistence=agent_persistence,
            approval_manager=approval_manager,
        )

    def get_config(self) -> ExecutorConfig | None:
        """
        Return loaded config (for debugging/testing).

        Returns:
            ExecutorConfig if compose() has been called, None otherwise
        """
        return self._config


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "ExecutorComposer",
    "ExecutorConfig",
    "ExecutorDeps",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-054",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.agents.executor",
        "core.agents.registry",
        "core.aios.runtime",
        "core.governance.approvals",
        "core.tools.registry_adapter",
    ],
    "tags": [
        "agent-execution",
        "dataclass",
        "debugging",
        "executor",
        "foundation",
        "logging",
        "testing",
        "tracing",
    ],
    "keywords": [
        "agent",
        "agentexecutorservice",
        "compose",
        "composer",
        "composition",
        "configuration",
        "container",
        "dependency",
    ],
    "business_value": "Provides executor composer components including ExecutorConfig, ExecutorDeps, ExecutorComposer",
    "last_modified": "2026-01-24T13:02:52Z",
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
