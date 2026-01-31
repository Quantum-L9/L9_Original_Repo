"""
L9 Core Tools - Registry Adapter (ExecutorToolRegistry)
========================================================

HYBRID TOOL SYSTEM ARCHITECTURE (Neo4j + Postgres)
--------------------------------------------------

This module implements the primary tool dispatch mechanism for L9.
Tools are registered and executed through ExecutorToolRegistry,
which integrates with Neo4j for governance and Postgres for data.

ARCHITECTURE OVERVIEW
~~~~~~~~~~~~~~~~~~~~~

Neo4j Graph Database (Optional - Observability Layer):
    - Tool metadata (scope, risk_level, requires_igor_approval)
    - Tool dependency graph (DEPENDS_ON, USES relationships)
    - Blast radius queries ("What breaks if OpenAI down?")
    - Governance audit trails (tool history, approval logs)

Postgres (Required - Data Layer):
    - Memory substrate (packets, embeddings, agent history)
    - User data, sessions, authentication
    - Task queue (QueuedTask models)

ExecutorToolRegistry (This Module):
    - Tool dispatch via dispatch_tool_call()
    - Governance enforcement (policy checks via engine)
    - Tool validation (Pydantic input schemas)
    - Rate limiting (if registry supports)
    - Error handling + logging

GRACEFUL DEGRADATION
~~~~~~~~~~~~~~~~~~~~

If Neo4j unavailable:
    - Tools still execute (via ExecutorToolRegistry + Postgres)
    - No graph queries (blast radius, dependencies)
    - No Neo4j-based governance audits
    - WARNING logged at startup + app.state.tool_graph_healthy = False

If Postgres unavailable:
    - System fails (required - memory + tasks + users)
    - No graceful degradation possible

GOVERNANCE MODEL
~~~~~~~~~~~~~~~~

High-Risk Tools (requires Igor approval):
    - GMPRUN - Execute GMP in Cursor
    - GITCOMMIT - Commit code to repository
    - MACAGENTEXECTASK - Execute shell command via Mac Agent

Approval Flow:
    1. L calls tool -> ExecutorToolRegistry.dispatch_tool_call()
    2. Governance engine checks: is_tool_approved(L, tool_id)?
    3. If high-risk + not approved -> return error (pending approval)
    4. If approved or low-risk -> execute via executor function
    5. Audit trail logged to memory substrate

LEGACY ORCHESTRATOR
~~~~~~~~~~~~~~~~~~~

ActionToolOrchestrator (orchestrators/action_tool/):
    Status: DEPRECATED v1.x -> v2.0
    Replacement: ExecutorToolRegistry (this module)
    Migration: See api/tools/router.py refactor
    Removal: Scheduled for Phase 3 cleanup

ACCESS PATTERN
~~~~~~~~~~~~~~

    # From FastAPI endpoints:
    registry = request.app.state.tool_registry
    result = await registry.dispatch_tool_call(
        tool_id="memory_search",
        arguments={"query": "L's capabilities", "limit": 10},
        context={"principal_id": "user123", "agent_id": "L"}
    )

Version: 2.1.0 (Governance Integration + Architecture Docs)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Registry Adapter (ExecutorToolRegistry)",
    "module_version": "2.1.0 (Governance Integration + Architecture Docs)",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "tool_registry",
    "module_name": "registry_adapter",
    "type": "adapter",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "OpenAI API", "Perplexity API", "Redis"],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [
            "api.server",
            "api.tools.router",
            "core.agents.bootstrap.phase_5_bind_tools",
            "core.tools.__init__",
            "orchestrators.action_tool.orchestrator",
            "orchestrators.action_tool.validator",
            "tests.integration.test_tool_observability_integration",
            "tests.unit.test_guarded_execution",
            "tests.unit.test_registry_adapter_sanitization",
        ],
    },
}
# ============================================================================

import asyncio
import time
from typing import TYPE_CHECKING, Any, Protocol
from uuid import uuid4

import structlog

from core.agents.schemas import ToolBinding, ToolCallResult

# GMP-124: Tool registry caching layer
from core.tools.registry_cache import CacheConfig, ToolRegistryCache

# GMP-45: Tool argument sanitization gate
from core.tools.sanitizer import ToolInputSanitizationError, ToolInputSanitizer

# NOTE: DEFAULT_L_CAPABILITIES is DEPRECATED - we now auto-discover from ToolDefinition.agent_id
# NOTE: log_tool_invocation imported lazily in guarded_execute to avoid
# test path shadowing issue (tests/memory shadows memory module)

if TYPE_CHECKING:
    from core.governance.engine import GovernanceEngineService

from core.decorators import must_stay_async

# GMP-104: Tool risk classification loaded from config/policies/high_risk_tools.yaml
from core.governance.tool_risk_policy import get_high_risk_tools, get_side_effect_tools

logger = structlog.get_logger(__name__)

# GMP-45: Stateless sanitizer instance (safe to reuse)
_TOOL_INPUT_SANITIZER = ToolInputSanitizer()

# =============================================================================
# Auto-Discovery: Tool → Agent Mapping (GMP-44)
# =============================================================================
# Instead of maintaining a manual allowlist (DEFAULT_L_CAPABILITIES), we now
# auto-discover which tools belong to which agent from ToolDefinition.agent_id.
# This dict is populated by register_l_tools() at startup.
_TOOL_AGENT_IDS: dict[str, str] = {}


def _tool_belongs_to_agent(tool_name: str, agent_id: str) -> bool:
    """
    Check if a tool belongs to an agent via auto-discovery.

    Args:
        tool_name: Name of the tool
        agent_id: Agent identifier (e.g., "L", "l-cto")

    Returns:
        True if tool's ToolDefinition.agent_id matches (or tool is unknown)
    """
    # Normalize agent aliases
    l_aliases = ("L", "l-cto", "l9-standard-v1")

    registered_agent = _TOOL_AGENT_IDS.get(tool_name)
    if registered_agent is None:
        # Tool not in registry - allow (it may be a system tool)
        return True

    # Check if both agent_id and registered_agent are L aliases
    if agent_id in l_aliases and registered_agent in l_aliases:
        return True

    # Exact match
    return registered_agent == agent_id


# =============================================================================
# Tool Executor Protocol
# =============================================================================


class ToolExecutor(Protocol):
    """Protocol for tool executors."""

    @must_stay_async("callers use await")
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with arguments."""
        ...


# =============================================================================
# Risk Levels
# =============================================================================


class RiskLevel:
    """Risk levels for tools."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


SIDE_EFFECT_TOOLS = get_side_effect_tools()
HIGH_RISK_TOOLS = get_high_risk_tools()


# =============================================================================
# Executor Tool Registry
# =============================================================================


class ExecutorToolRegistry:
    """
    Tool registry adapter for AgentExecutorService.

    Wraps the existing tool registry and provides:
    - ToolBinding conversion for agent context
    - Tool dispatch with result wrapping
    - Governance engine integration for policy-based access
    - Rate limiting checks

    Attributes:
        base_registry: The underlying tool registry
        governance_engine: Optional governance engine for policy evaluation
    """

    def __init__(
        self,
        base_registry: Any | None = None,
        governance_enabled: bool = True,
        governance_engine: GovernanceEngineService | None = None,
        cache_config: CacheConfig | None = None,
    ):
        """
        Initialize the adapter.

        Args:
            base_registry: Existing ToolRegistry (auto-creates if None)
            governance_enabled: Whether to enforce governance (legacy flag)
            governance_engine: GovernanceEngineService for policy evaluation
            cache_config: Optional cache configuration (creates default if None)
        """
        # Get or create base registry
        if base_registry is None:
            try:
                from core.tools.base_registry import get_tool_registry
            except ImportError as exc:
                raise RuntimeError(
                    "Tool registry import failed; tool dispatch blocked"
                ) from exc
            self._registry = get_tool_registry()
        else:
            self._registry = base_registry

        if self._registry is None:
            raise RuntimeError("Tool registry unavailable; tool dispatch blocked")

        self._governance_enabled = governance_enabled
        self._governance_engine = governance_engine
        self._approved_overrides: dict[
            str, set[str]
        ] = {}  # agent_id -> approved tool IDs

        # GMP-124: Initialize tool metadata cache
        self._cache = ToolRegistryCache(cache_config or CacheConfig())

        logger.info(
            "ExecutorToolRegistry initialized: governance=%s, engine=%s, tools=%d, cache=%s",
            governance_enabled,
            "attached" if governance_engine else "none",
            len(self._registry.list_all()) if self._registry else 0,
            "enabled",
        )

    def set_governance_engine(self, engine: GovernanceEngineService) -> None:
        """Attach a governance engine for policy evaluation."""
        self._governance_engine = engine
        logger.info("Governance engine attached to tool registry")

    # =========================================================================
    # ToolRegistryProtocol Implementation
    # =========================================================================

    def get_approved_tools(
        self,
        agent_id: str,
        principal_id: str,
    ) -> list[ToolBinding]:
        """
        Get list of tools approved for an agent.

        Converts ToolMetadata to ToolBinding format expected by AgentInstance.
        Uses governance engine for policy-based filtering if available,
        falls back to hardcoded rules otherwise.

        Args:
            agent_id: Agent identifier
            principal_id: Principal requesting tools

        Returns:
            List of approved ToolBinding objects
        """
        if self._registry is None:
            raise RuntimeError("Tool registry unavailable; tool dispatch blocked")

        bindings: list[ToolBinding] = []

        for tool_meta in self._registry.list_enabled():
            # GMP-44: Auto-discover tool capabilities from ToolDefinition.agent_id
            # instead of manual DEFAULT_L_CAPABILITIES allowlist.
            if not _tool_belongs_to_agent(tool_meta.id, agent_id):
                logger.debug(
                    "Tool %s denied for agent %s by auto-discovery (agent_id mismatch)",
                    tool_meta.id,
                    agent_id,
                )
                continue

            # Use governance engine if available
            if self._governance_engine:
                allowed = self._governance_engine.is_allowed(
                    subject=agent_id,
                    action="tool.execute",
                    resource=tool_meta.id,
                    context={"principal_id": principal_id},
                )
                if not allowed:
                    logger.debug(
                        "Tool %s denied for agent %s by governance policy",
                        tool_meta.id,
                        agent_id,
                    )
                    continue
            elif self._governance_enabled:
                # Fallback to hardcoded rules
                if tool_meta.id in SIDE_EFFECT_TOOLS and not self._is_approved(
                    agent_id, tool_meta.id
                ):
                    logger.debug(
                        "Tool %s denied for agent %s (side-effect, not approved)",
                        tool_meta.id,
                        agent_id,
                    )
                    continue

                if tool_meta.id in HIGH_RISK_TOOLS:
                    logger.debug(
                        "Tool %s denied for agent %s (high-risk)",
                        tool_meta.id,
                        agent_id,
                    )
                    continue

            # Convert to ToolBinding (tool_id is canonical identity)
            # Use registry's schema method if available
            if hasattr(self._registry, "get_tool_schema"):
                schema = self._registry.get_tool_schema(tool_meta.id)
            else:
                schema = self._get_tool_schema(tool_meta.id)

            binding = ToolBinding(
                tool_id=tool_meta.id,
                display_name=tool_meta.name,  # UI/logs only
                description=tool_meta.description,
                input_schema=schema,
                enabled=True,
            )
            bindings.append(binding)

        logger.debug(
            "Approved %d tools for agent %s",
            len(bindings),
            agent_id,
        )

        return bindings

    async def get_relevant_tools(
        self,
        agent_id: str,
        principal_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[ToolBinding]:
        """
        Get tools relevant to query (semantic filtered + governance approved).

        GMP-78: Semantic Tool Retrieval

        Combines:
        1. Semantic search to find top_k relevant tools via embeddings
        2. Governance filter to ensure agent has permission

        Args:
            agent_id: Agent identifier
            principal_id: Principal requesting tools
            query: User query or task description for semantic matching
            top_k: Maximum number of tools to return

        Returns:
            List of ToolBinding objects for relevant + approved tools
        """
        if self._registry is None:
            raise RuntimeError("Tool registry unavailable; tool dispatch blocked")

        # Step 1: Get semantically relevant tools via embeddings
        relevant_tool_names: set[str] = set()
        try:
            from core.tools.tool_embeddings import find_relevant_tools

            results = await find_relevant_tools(
                query=query,
                top_k=top_k * 2,  # Fetch more to account for governance filtering
            )
            relevant_tool_names = {r.tool_name for r in results}

            logger.debug(
                "Semantic search found %d relevant tools for query",
                len(relevant_tool_names),
                query=query[:50],
            )
        except Exception as e:
            raise RuntimeError(
                f"Semantic tool retrieval unavailable; tool binding blocked: {e}"
            ) from e

        if not relevant_tool_names:
            # No semantic results - return empty list (fail-closed, no fallback to all tools)
            logger.debug("No semantic matches found; returning empty tool list")
            return []

        # Step 2: Filter by governance (intersection of relevant + approved)
        bindings: list[ToolBinding] = []

        for tool_meta in self._registry.list_enabled():
            # Skip if not semantically relevant
            if tool_meta.id not in relevant_tool_names:
                continue

            # GMP-44: Auto-discover tool capabilities
            if not _tool_belongs_to_agent(tool_meta.id, agent_id):
                continue

            # Governance engine check
            if self._governance_engine:
                allowed = self._governance_engine.is_allowed(
                    subject=agent_id,
                    action="tool.execute",
                    resource=tool_meta.id,
                    context={"principal_id": principal_id},
                )
                if not allowed:
                    continue
            elif self._governance_enabled:
                if tool_meta.id in SIDE_EFFECT_TOOLS and not self._is_approved(
                    agent_id, tool_meta.id
                ):
                    continue
                if tool_meta.id in HIGH_RISK_TOOLS:
                    continue

            # Convert to ToolBinding
            if hasattr(self._registry, "get_tool_schema"):
                schema = self._registry.get_tool_schema(tool_meta.id)
            else:
                schema = self._get_tool_schema(tool_meta.id)

            binding = ToolBinding(
                tool_id=tool_meta.id,
                display_name=tool_meta.name,
                description=tool_meta.description,
                input_schema=schema,
                enabled=True,
            )
            bindings.append(binding)

        # Cap at top_k
        bindings = bindings[:top_k]

        logger.info(
            "agent.registry.tools.shortlisted",
            agent_id=agent_id,
            query=query[:50],
            semantic_matches=len(relevant_tool_names),
            approved_matches=len(bindings),
            tools=[b.tool_id for b in bindings],
        )

        return bindings

    async def dispatch_tool_call(
        self,
        tool_id: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> ToolCallResult:
        """
        Dispatch a tool call and return result.

        Uses tool_id as the sole identity for lookup and dispatch.
        Governance is checked via engine if available.
        All tool calls are logged to memory substrate for audit.

        Args:
            tool_id: Canonical tool identity
            arguments: Arguments for tool
            context: Execution context

        Returns:
            ToolCallResult with success/failure, result, and tool_id
        """
        call_id = uuid4()
        start_time = time.monotonic()
        agent_id = context.get("agent_id", "unknown")
        task_id = context.get("task_id")

        # Import lazily to avoid test path shadowing issue
        # (tests/memory shadows memory module in pytest)
        try:
            import importlib

            tool_audit_module = importlib.import_module("memory.tool_audit")
            log_tool_invocation = tool_audit_module.log_tool_invocation
        except Exception:

            @must_stay_async("callers use await")
            async def log_tool_invocation(**kwargs):  # type: ignore[no-redef]
                """
                Performs asynchronous logging of tool invocation events within the Neo4j and Postgres hybrid registry system.

                Args:
                    **kwargs: Dictionary containing invocation details such as tool ID, user info, and context.

                Returns:
                    None, as the function primarily logs invocation data without returning a value.

                Raises:
                    Exception: If logging fails or required invocation data is missing.
                """
                return

        try:
            # Get tool from registry using tool_id
            if self._registry is None:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                await log_tool_invocation(
                    call_id=call_id,
                    tool_id=tool_id,
                    agent_id=agent_id,
                    task_id=task_id,
                    status="failure",
                    duration_ms=duration_ms,
                    error="Tool registry not available",
                )
                return ToolCallResult(
                    call_id=call_id,
                    tool_id=tool_id,
                    success=False,
                    error="Tool registry not available",
                )

            # GMP-124: Check cache first, then fall back to registry
            tool_meta = self._cache.get(tool_id)
            if tool_meta is None:
                # Cache miss - fetch from registry
                tool_meta = self._registry.get(tool_id)
                if tool_meta is not None:
                    # Cache the result for future lookups
                    self._cache.set(tool_id, tool_meta)

            if tool_meta is None:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                await log_tool_invocation(
                    call_id=call_id,
                    tool_id=tool_id,
                    agent_id=agent_id,
                    task_id=task_id,
                    status="failure",
                    duration_ms=duration_ms,
                    error=f"Tool not found: {tool_id}",
                )
                return ToolCallResult(
                    call_id=call_id,
                    tool_id=tool_id,
                    success=False,
                    error=f"Tool not found: {tool_id}",
                )

            # Check if tool is enabled
            if not tool_meta.enabled:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                await log_tool_invocation(
                    call_id=call_id,
                    tool_id=tool_id,
                    agent_id=agent_id,
                    task_id=task_id,
                    status="failure",
                    duration_ms=duration_ms,
                    error=f"Tool is disabled: {tool_id}",
                )
                return ToolCallResult(
                    call_id=call_id,
                    tool_id=tool_id,
                    success=False,
                    error=f"Tool is disabled: {tool_id}",
                )

            # Governance check - use engine if available, else fallback
            if self._governance_engine:
                # Use policy-based governance
                allowed = self._governance_engine.is_allowed(
                    subject=agent_id,
                    action="tool.execute",
                    resource=tool_id,
                    context=context,
                )
                if not allowed:
                    duration_ms = int((time.monotonic() - start_time) * 1000)
                    await log_tool_invocation(
                        call_id=call_id,
                        tool_id=tool_id,
                        agent_id=agent_id,
                        task_id=task_id,
                        status="denied",
                        duration_ms=duration_ms,
                        error=f"Tool {tool_id} denied by governance policy",
                    )
                    return ToolCallResult(
                        call_id=call_id,
                        tool_id=tool_id,
                        success=False,
                        error=f"Tool {tool_id} denied by governance policy",
                    )
            elif self._governance_enabled:
                # Fallback to hardcoded rules
                if tool_id in SIDE_EFFECT_TOOLS and not self._is_approved(
                    agent_id, tool_id
                ):
                    duration_ms = int((time.monotonic() - start_time) * 1000)
                    await log_tool_invocation(
                        call_id=call_id,
                        tool_id=tool_id,
                        agent_id=agent_id,
                        task_id=task_id,
                        status="denied",
                        duration_ms=duration_ms,
                        error=f"Tool {tool_id} requires governance approval",
                    )
                    return ToolCallResult(
                        call_id=call_id,
                        tool_id=tool_id,
                        success=False,
                        error=f"Tool {tool_id} requires governance approval",
                    )

            # Use registry's execute_tool if available (handles timeout)
            if hasattr(self._registry, "execute_tool"):
                # Inject agent_id and task_id into arguments for tools that need them
                arguments_with_context = {
                    **arguments,
                    "agent_id": agent_id,
                    "task_id": task_id,
                }

                # GMP-45: deterministic sanitization gate (schema + resource limits)
                tool_schema: dict[str, Any]
                if hasattr(self._registry, "get_tool_schema"):
                    tool_schema = self._registry.get_tool_schema(tool_id)
                else:
                    tool_schema = self._get_tool_schema(tool_id)

                try:
                    sanitized_arguments = _TOOL_INPUT_SANITIZER.sanitize(
                        tool_id=tool_id,
                        arguments=arguments_with_context,
                        schema=tool_schema,
                    )
                except ToolInputSanitizationError as sanitize_err:
                    duration_ms = int((time.monotonic() - start_time) * 1000)
                    await log_tool_invocation(
                        call_id=call_id,
                        tool_id=tool_id,
                        agent_id=agent_id,
                        task_id=task_id,
                        status="denied",
                        duration_ms=duration_ms,
                        error=str(sanitize_err),
                        arguments=arguments_with_context,
                    )
                    return ToolCallResult(
                        call_id=call_id,
                        tool_id=tool_id,
                        success=False,
                        error=str(sanitize_err),
                    )

                logger.info(
                    "Executing tool via registry: %s with arguments: %s",
                    tool_id,
                    sanitized_arguments,
                )
                result = await self._registry.execute_tool(tool_id, sanitized_arguments)
                duration_ms = int((time.monotonic() - start_time) * 1000)

                if result["success"]:
                    await log_tool_invocation(
                        call_id=call_id,
                        tool_id=tool_id,
                        agent_id=agent_id,
                        task_id=task_id,
                        status="success",
                        duration_ms=duration_ms,
                        arguments=sanitized_arguments,
                    )
                    return ToolCallResult(
                        call_id=call_id,
                        tool_id=tool_id,
                        success=True,
                        result=result["result"],
                        duration_ms=result["duration_ms"],
                    )
                await log_tool_invocation(
                    call_id=call_id,
                    tool_id=tool_id,
                    agent_id=agent_id,
                    task_id=task_id,
                    status="failure",
                    duration_ms=duration_ms,
                    error=result["error"],
                    arguments=sanitized_arguments,
                )
                return ToolCallResult(
                    call_id=call_id,
                    tool_id=tool_id,
                    success=False,
                    error=result["error"],
                    duration_ms=result.get("duration_ms", 0),
                )

            # Fallback: direct execution (legacy path)
            executor = self._registry.get_executor(tool_id)
            if executor is None:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                await log_tool_invocation(
                    call_id=call_id,
                    tool_id=tool_id,
                    agent_id=agent_id,
                    task_id=task_id,
                    status="failure",
                    duration_ms=duration_ms,
                    error=f"No executor registered for tool: {tool_id}",
                )
                return ToolCallResult(
                    call_id=call_id,
                    tool_id=tool_id,
                    success=False,
                    error=f"No executor registered for tool: {tool_id}",
                )

            # Inject agent_id and task_id for legacy path too
            arguments_with_context = {
                **arguments,
                "agent_id": agent_id,
                "task_id": task_id,
            }

            # GMP-45: deterministic sanitization gate for legacy path
            tool_schema: dict[str, Any]
            if hasattr(self._registry, "get_tool_schema"):
                tool_schema = self._registry.get_tool_schema(tool_id)
            else:
                tool_schema = self._get_tool_schema(tool_id)

            try:
                sanitized_arguments = _TOOL_INPUT_SANITIZER.sanitize(
                    tool_id=tool_id,
                    arguments=arguments_with_context,
                    schema=tool_schema,
                )
            except ToolInputSanitizationError as sanitize_err:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                await log_tool_invocation(
                    call_id=call_id,
                    tool_id=tool_id,
                    agent_id=agent_id,
                    task_id=task_id,
                    status="denied",
                    duration_ms=duration_ms,
                    error=str(sanitize_err),
                    arguments=arguments_with_context,
                )
                return ToolCallResult(
                    call_id=call_id,
                    tool_id=tool_id,
                    success=False,
                    error=str(sanitize_err),
                )

            logger.info(
                "Executing tool: %s with arguments: %s",
                tool_id,
                sanitized_arguments,
            )

            # Handle both sync and async executors
            if hasattr(executor, "execute"):
                if asyncio.iscoroutinefunction(executor.execute):
                    result = await executor.execute(**sanitized_arguments)
                else:
                    result = executor.execute(**sanitized_arguments)
            elif callable(executor):
                if asyncio.iscoroutinefunction(executor):
                    result = await executor(**sanitized_arguments)
                else:
                    result = executor(**sanitized_arguments)
            else:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                await log_tool_invocation(
                    call_id=call_id,
                    tool_id=tool_id,
                    agent_id=agent_id,
                    task_id=task_id,
                    status="failure",
                    duration_ms=duration_ms,
                    error=f"Tool executor is not callable: {tool_id}",
                )
                return ToolCallResult(
                    call_id=call_id,
                    tool_id=tool_id,
                    success=False,
                    error=f"Tool executor is not callable: {tool_id}",
                )

            # Calculate duration
            duration_ms = int((time.monotonic() - start_time) * 1000)

            logger.info(
                "Tool %s completed in %dms",
                tool_id,
                duration_ms,
            )

            # Log successful execution
            await log_tool_invocation(
                call_id=call_id,
                tool_id=tool_id,
                agent_id=agent_id,
                task_id=task_id,
                status="success",
                duration_ms=duration_ms,
                arguments=sanitized_arguments,
            )

            return ToolCallResult(
                call_id=call_id,
                tool_id=tool_id,
                success=True,
                result=result,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.exception("Tool execution failed: %s", str(e))

            # Log failed execution
            await log_tool_invocation(
                call_id=call_id,
                tool_id=tool_id,
                agent_id=agent_id,
                task_id=task_id,
                status="failure",
                duration_ms=duration_ms,
                error=str(e),
                arguments=arguments,
            )

            return ToolCallResult(
                call_id=call_id,
                tool_id=tool_id,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def guarded_execute(
        self,
        agent: Any,
        tool_id: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
        principal_id: str | None = None,
    ) -> ToolCallResult:
        """
        Execute a tool call with kernel enforcement.

        This wraps dispatch_tool_call with additional kernel-aware guards:
        1. Verify agent has active kernels (GATE 1)
        2. Verify kernels are loaded (GATE 2)
        3. Check behavioral/safety kernel constraints (GATE 3-4)
        5. Check governance policies allow the tool (GATE 5)
        6. Check tool approval if required (GATE 6)
        7. Execute tool via dispatch_tool_call
        8. Emit ToolAuditEntry with kernel metadata (GATE 7)

        Args:
            agent: The kernel-aware agent (must have kernel_state attribute)
            tool_id: Tool identifier
            arguments: Tool call arguments
            context: Optional execution context
            principal_id: Optional principal ID for audit trail

        Returns:
            ToolCallResult with success/failure, result, and tool_id

        Raises:
            RuntimeError: If kernels not active (hard failure)
        """
        start_time = time.time()
        call_id = uuid4()

        # Build context if not provided
        if context is None:
            context = {}

        agent_id = getattr(agent, "agent_id", context.get("agent_id", "unknown"))
        context["agent_id"] = agent_id
        principal_id = principal_id or context.get("principal_id", "unknown")

        # Extract kernel metadata for audit trail
        kernel_hashes = getattr(agent, "_kernel_hashes", {})
        kernel_version = getattr(agent, "_kernel_version", "unknown")

        # GATE 1: Verify kernel activation
        kernel_state = getattr(agent, "kernel_state", None)
        kernel_active = False
        if isinstance(kernel_state, str):
            kernel_active = kernel_state == "ACTIVE"
        elif hasattr(kernel_state, "initialized"):
            kernel_active = bool(kernel_state.initialized)

        if not kernel_active:
            logger.error(
                "guarded_execute.kernel_not_active",
                agent_id=agent_id,
                kernel_state=kernel_state,
                tool_id=tool_id,
            )
            return ToolCallResult(
                call_id=call_id,
                tool_id=tool_id,
                success=False,
                error=f"Kernel set not active (state={kernel_state}). Execution denied.",
            )

        # GATE 2: Verify agent has kernels loaded
        kernels = getattr(agent, "kernels", {})
        if not kernels or len(kernels) == 0:
            logger.error(
                "guarded_execute.no_kernels",
                agent_id=agent_id,
                tool_id=tool_id,
            )
            return ToolCallResult(
                call_id=call_id,
                tool_id=tool_id,
                success=False,
                error="No kernels loaded. Execution denied.",
            )

        # GATE 3: Check behavioral constraints from kernels (if available)
        behavioral = getattr(agent, "_behavioral", {})
        prohibited_tools = behavioral.get("prohibited_tools", [])
        if tool_id in prohibited_tools:
            logger.warning(
                "guarded_execute.tool_prohibited_by_kernel",
                agent_id=agent_id,
                tool_id=tool_id,
            )
            return ToolCallResult(
                call_id=call_id,
                tool_id=tool_id,
                success=False,
                error=f"Tool {tool_id} prohibited by behavioral kernel.",
            )

        # GATE 4: Check safety constraints from kernels (if available)
        safety = getattr(agent, "_safety", {})
        prohibited_actions = safety.get("prohibited_actions", [])
        for action in prohibited_actions:
            if action.lower() in tool_id.lower():
                logger.warning(
                    "guarded_execute.action_prohibited_by_safety_kernel",
                    agent_id=agent_id,
                    tool_id=tool_id,
                    prohibited_action=action,
                )
                return ToolCallResult(
                    call_id=call_id,
                    tool_id=tool_id,
                    success=False,
                    error=f"Tool {tool_id} matches prohibited action '{action}' in safety kernel.",
                )

        # GATE 5: Check governance engine policies (if attached)
        if self._governance_engine is not None:
            try:
                from core.governance.schemas import EvaluationRequest

                eval_request = EvaluationRequest(
                    subject=agent_id,
                    action="tool.execute",
                    resource=tool_id,
                    context={
                        "kernel_state": kernel_state,
                        "kernel_count": len(kernels),
                        "principal_id": principal_id,
                        **context,
                    },
                )
                eval_result = await self._governance_engine.evaluate(eval_request)

                if not eval_result.allowed:
                    logger.warning(
                        "guarded_execute.governance_denied",
                        agent_id=agent_id,
                        tool_id=tool_id,
                        policy_id=eval_result.policy_id,
                        reason=eval_result.reason,
                    )
                    return ToolCallResult(
                        call_id=call_id,
                        tool_id=tool_id,
                        success=False,
                        error=f"Governance denied: {eval_result.reason}",
                    )

                logger.debug(
                    "guarded_execute.governance_allowed",
                    agent_id=agent_id,
                    tool_id=tool_id,
                    policy_id=eval_result.policy_id,
                )
            except Exception as gov_err:
                logger.error(
                    "guarded_execute.governance_check_error",
                    agent_id=agent_id,
                    tool_id=tool_id,
                    error=str(gov_err),
                )
                return ToolCallResult(
                    call_id=call_id,
                    tool_id=tool_id,
                    success=False,
                    error=f"Governance check failed: {gov_err}",
                )

        # GATE 6: Check tool approval for high-risk tools
        try:
            from core.governance.approvals import ApprovalManager

            # GMP-104: Uses module-level HIGH_RISK_TOOLS from tool_risk_policy (line 213)

            if tool_id in HIGH_RISK_TOOLS:
                # Import substrate service if available
                substrate = getattr(self, "_substrate_service", None)
                if substrate is None:
                    # Try to get from context
                    substrate = context.get("substrate_service")

                if substrate:
                    approval_manager = ApprovalManager(substrate)
                    is_approved = await approval_manager.is_approved(str(call_id))

                    if not is_approved:
                        logger.warning(
                            "guarded_execute.approval_required",
                            agent_id=agent_id,
                            tool_id=tool_id,
                            call_id=str(call_id),
                        )
                        return ToolCallResult(
                            call_id=call_id,
                            tool_id=tool_id,
                            success=False,
                            error=f"Tool {tool_id} requires approval. Request ID: {call_id}",
                        )
        except ImportError as approval_import_error:
            return ToolCallResult(
                call_id=call_id,
                tool_id=tool_id,
                success=False,
                error=f"Approval enforcement unavailable: {approval_import_error}",
            )
        except Exception as approval_err:
            logger.warning(
                "guarded_execute.approval_check_error",
                agent_id=agent_id,
                tool_id=tool_id,
                error=str(approval_err),
            )

        # Log guarded execution start
        logger.info(
            "guarded_execute.start",
            agent_id=agent_id,
            tool_id=tool_id,
            kernel_state=kernel_state,
            kernel_count=len(kernels),
        )

        # Execute tool via dispatch_tool_call
        result = await self.dispatch_tool_call(
            tool_id=tool_id,
            arguments=arguments,
            context=context,
        )

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # GATE 7: Emit ToolAuditEntry with kernel metadata
        try:
            # Import lazily to avoid test path shadowing issue
            # (tests/memory shadows memory module in pytest)
            import importlib

            tool_audit_module = importlib.import_module("memory.tool_audit")
            log_tool_invocation = tool_audit_module.log_tool_invocation
            tool_audit_entry_class = tool_audit_module.ToolAuditEntry

            _audit_entry = tool_audit_entry_class(
                tool_name=tool_id,
                agent_id=agent_id,
                input_data={
                    "arguments": arguments,
                    "principal_id": principal_id,
                    "kernel_version": kernel_version,
                    "kernel_hash": (
                        next(iter(kernel_hashes.values()), "unknown")
                        if kernel_hashes
                        else "unknown"
                    ),
                    "kernel_count": len(kernels),
                },
                output_data={
                    "success": result.success,
                    "result": str(result.result)[:500] if result.result else None,
                    "error": result.error,
                },
                duration_ms=float(duration_ms),
                error=result.error,
                request_id=str(call_id),
            )

            # Log to audit trail (best-effort)
            await log_tool_invocation(
                tool_id=tool_id,
                agent_id=agent_id,
                success=result.success,
                duration_ms=duration_ms,
                error=result.error,
            )

            logger.debug(
                "guarded_execute.audit_emitted",
                agent_id=agent_id,
                tool_id=tool_id,
                request_id=str(call_id),
            )
        except Exception as audit_err:
            # Audit emission is best-effort - don't fail execution
            logger.warning(
                "guarded_execute.audit_error",
                agent_id=agent_id,
                tool_id=tool_id,
                error=str(audit_err),
            )

        # Log guarded execution result
        logger.info(
            "guarded_execute.complete",
            agent_id=agent_id,
            tool_id=tool_id,
            success=result.success,
            duration_ms=duration_ms,
        )

        return result

    # =========================================================================
    # Governance
    # =========================================================================

    def approve_tool(self, agent_id: str, tool_id: str) -> None:
        """
        Explicitly approve a tool for an agent.

        Used to grant access to side-effect tools.

        Args:
            agent_id: Agent identifier
            tool_id: Tool to approve
        """
        if agent_id not in self._approved_overrides:
            self._approved_overrides[agent_id] = set()
        self._approved_overrides[agent_id].add(tool_id)

        logger.info("Approved tool %s for agent %s", tool_id, agent_id)

    def revoke_tool(self, agent_id: str, tool_id: str) -> None:
        """
        Revoke approval for a tool.

        Args:
            agent_id: Agent identifier
            tool_id: Tool to revoke
        """
        if agent_id in self._approved_overrides:
            self._approved_overrides[agent_id].discard(tool_id)

        logger.info("Revoked tool %s for agent %s", tool_id, agent_id)

    def _is_approved(self, agent_id: str, tool_id: str) -> bool:
        """Check if a tool is explicitly approved for an agent."""
        return (
            agent_id in self._approved_overrides
            and tool_id in self._approved_overrides[agent_id]
        )

    # =========================================================================
    # Schema Helpers
    # =========================================================================

    def _get_tool_schema(self, tool_id: str) -> dict[str, Any]:
        """
        Get JSON Schema for a tool's parameters.

        Returns a basic schema based on tool type.
        L-CTO tools have comprehensive schemas; research tools have basic schemas.
        """
        # L-CTO tool schemas (comprehensive - for function calling)
        l_tool_schemas = {
            "memory_search": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "segment": {
                        "type": "string",
                        "description": "Memory segment: 'all', 'governance', 'project', 'session'",
                        "default": "all",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return (1-100)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
            "memory_write": {
                "type": "object",
                "properties": {
                    "packet": {
                        "type": "object",
                        "description": "Packet data to write",
                    },
                    "segment": {
                        "type": "string",
                        "description": "Target memory segment",
                    },
                },
                "required": ["packet", "segment"],
            },
            # Memory Substrate Direct Access (GMP-31 Batch 1)
            "memory_get_packet": {
                "type": "object",
                "properties": {
                    "packet_id": {
                        "type": "string",
                        "description": "UUID of packet to retrieve",
                    },
                },
                "required": ["packet_id"],
            },
            "memory_query_packets": {
                "type": "object",
                "properties": {
                    "filters": {"type": "object", "description": "Filter criteria"},
                    "limit": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 50,
                    },
                },
                "required": ["filters"],
            },
            "memory_search_by_thread": {
                "type": "object",
                "properties": {
                    "thread_id": {
                        "type": "string",
                        "description": "Thread/conversation ID",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 50,
                    },
                },
                "required": ["thread_id"],
            },
            "memory_search_by_type": {
                "type": "object",
                "properties": {
                    "packet_type": {
                        "type": "string",
                        "description": "Packet kind (REASONING, TOOL_CALL, etc.)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 50,
                    },
                },
                "required": ["packet_type"],
            },
            "memory_get_events": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "Optional event type filter",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 50,
                    },
                },
                "required": [],
            },
            "memory_get_reasoning_traces": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Optional task ID filter",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max traces",
                        "default": 20,
                    },
                },
                "required": [],
            },
            "memory_get_facts": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Subject to query facts about",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max facts",
                        "default": 20,
                    },
                },
                "required": ["subject"],
            },
            "memory_write_insight": {
                "type": "object",
                "properties": {
                    "insight": {
                        "type": "string",
                        "description": "Insight text to store",
                    },
                    "category": {
                        "type": "string",
                        "description": "Category (governance, project, session)",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence 0-1",
                        "default": 0.8,
                    },
                },
                "required": ["insight", "category"],
            },
            "memory_embed_text": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to embed"},
                },
                "required": ["text"],
            },
            # Memory Client API (GMP-31 Batch 2)
            "memory_hybrid_search": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 10,
                    },
                    "filters": {"type": "object", "description": "Optional filters"},
                },
                "required": ["query"],
            },
            "memory_fetch_lineage": {
                "type": "object",
                "properties": {
                    "packet_id": {"type": "string", "description": "Packet UUID"},
                    "direction": {
                        "type": "string",
                        "description": "ancestors or descendants",
                        "default": "ancestors",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Max traversal depth",
                        "default": 5,
                    },
                },
                "required": ["packet_id"],
            },
            "memory_fetch_thread": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string", "description": "Thread ID"},
                    "limit": {
                        "type": "integer",
                        "description": "Max packets",
                        "default": 100,
                    },
                },
                "required": ["thread_id"],
            },
            "memory_fetch_facts_api": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Subject filter"},
                    "predicate": {"type": "string", "description": "Predicate filter"},
                    "limit": {
                        "type": "integer",
                        "description": "Max facts",
                        "default": 50,
                    },
                },
                "required": [],
            },
            "memory_fetch_insights": {
                "type": "object",
                "properties": {
                    "packet_id": {
                        "type": "string",
                        "description": "Source packet filter",
                    },
                    "insight_type": {
                        "type": "string",
                        "description": "Insight type filter",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max insights",
                        "default": 50,
                    },
                },
                "required": [],
            },
            "memory_gc_stats": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "gmp_run": {
                "type": "object",
                "properties": {
                    "gmp_id": {
                        "type": "string",
                        "description": "GMP identifier (e.g., 'GMP-L-CTO-P0-TOOLS')",
                    },
                    "params": {
                        "type": "object",
                        "description": "GMP execution parameters",
                        "default": {},
                    },
                },
                "required": ["gmp_id"],
            },
            "git_commit": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Commit message",
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to commit (empty = all staged)",
                        "default": [],
                    },
                },
                "required": ["message"],
            },
            "mac_agent_exec_task": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (5-300)",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
            "mcp_list_servers": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "mcp_list_tools": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "MCP server identifier: 'github', 'notion', 'filesystem', 'memory', 'l9-memory'",
                    },
                },
                "required": ["server_id"],
            },
            "mcp_call_tool": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "MCP server identifier: 'github', 'notion', 'filesystem', etc.",
                    },
                    "tool_name": {
                        "type": "string",
                        "description": "Tool name (e.g., 'create_issue', 'search', 'read_file')",
                    },
                    "arguments": {
                        "type": "object",
                        "description": "Tool arguments",
                        "default": {},
                    },
                },
                "required": ["server_id", "tool_name"],
            },
            "mcp_discover_and_register": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "world_model_query": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "description": "Query type: 'get_entity', 'list_entities', 'state_version'",
                    },
                    "params": {
                        "type": "object",
                        "description": "Query parameters",
                        "default": {},
                    },
                },
                "required": ["query_type"],
            },
            "kernel_read": {
                "type": "object",
                "properties": {
                    "kernel_name": {
                        "type": "string",
                        "description": "Kernel identifier: 'identity', 'safety', 'execution', etc.",
                    },
                    "property": {
                        "type": "string",
                        "description": "Property to read from kernel",
                    },
                },
                "required": ["kernel_name", "property"],
            },
            "long_plan_execute": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "string",
                        "description": "Plan identifier",
                    },
                    "params": {
                        "type": "object",
                        "description": "Execution parameters",
                        "default": {},
                    },
                },
                "required": ["plan_id"],
            },
            "long_plan_simulate": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "string",
                        "description": "Plan identifier",
                    },
                    "params": {
                        "type": "object",
                        "description": "Simulation parameters",
                        "default": {},
                    },
                },
                "required": ["plan_id"],
            },
            "neo4j_query": {
                "type": "object",
                "properties": {
                    "cypher": {
                        "type": "string",
                        "description": "Cypher query to run against Neo4j graph",
                    },
                    "params": {
                        "type": "object",
                        "description": "Query parameters",
                        "default": {},
                    },
                },
                "required": ["cypher"],
            },
            "redis_get": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Redis key to retrieve",
                    },
                },
                "required": ["key"],
            },
            "redis_set": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Redis key",
                    },
                    "value": {
                        "type": "string",
                        "description": "Value to store",
                    },
                    "ttl_seconds": {
                        "type": "integer",
                        "description": "Optional TTL in seconds",
                    },
                },
                "required": ["key", "value"],
            },
            "redis_keys": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Key pattern (e.g., 'agent:*')",
                        "default": "*",
                    },
                },
                "required": [],
            },
            # Redis State Management (GMP-31 Batch 3)
            "redis_delete": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key to delete"}
                },
                "required": ["key"],
            },
            "redis_enqueue_task": {
                "type": "object",
                "properties": {
                    "queue_name": {"type": "string", "description": "Queue name"},
                    "task_data": {"type": "object", "description": "Task payload"},
                    "priority": {
                        "type": "integer",
                        "description": "Priority",
                        "default": 0,
                    },
                },
                "required": ["queue_name", "task_data"],
            },
            "redis_dequeue_task": {
                "type": "object",
                "properties": {
                    "queue_name": {"type": "string", "description": "Queue name"}
                },
                "required": ["queue_name"],
            },
            "redis_queue_size": {
                "type": "object",
                "properties": {
                    "queue_name": {"type": "string", "description": "Queue name"}
                },
                "required": ["queue_name"],
            },
            "redis_get_task_context": {
                "type": "object",
                "properties": {"task_id": {"type": "string", "description": "Task ID"}},
                "required": ["task_id"],
            },
            "redis_set_task_context": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "context": {"type": "object", "description": "Context data"},
                    "ttl_seconds": {
                        "type": "integer",
                        "description": "TTL",
                        "default": 3600,
                    },
                },
                "required": ["task_id", "context"],
            },
            # Tool Graph Introspection (GMP-31 Batch 4)
            "tools_list_all": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "tools_list_enabled": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "tools_get_metadata": {
                "type": "object",
                "properties": {"tool_id": {"type": "string", "description": "Tool ID"}},
                "required": ["tool_id"],
            },
            "tools_get_schema": {
                "type": "object",
                "properties": {"tool_id": {"type": "string", "description": "Tool ID"}},
                "required": ["tool_id"],
            },
            "tools_get_by_type": {
                "type": "object",
                "properties": {
                    "tool_type": {"type": "string", "description": "Tool type"}
                },
                "required": ["tool_type"],
            },
            "tools_get_for_role": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "description": "Role identifier"}
                },
                "required": ["role"],
            },
            # World Model Operations (GMP-31 Batch 5)
            "world_model_get_entity": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": "Entity ID"}
                },
                "required": ["entity_id"],
            },
            "world_model_list_entities": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Entity type filter",
                    },
                    "min_confidence": {
                        "type": "number",
                        "description": "Min confidence",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max entities",
                        "default": 50,
                    },
                },
                "required": [],
            },
            "world_model_snapshot": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Snapshot description",
                    }
                },
                "required": [],
            },
            "world_model_list_snapshots": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max snapshots",
                        "default": 20,
                    }
                },
                "required": [],
            },
            "world_model_send_insights": {
                "type": "object",
                "properties": {
                    "insights": {"type": "array", "description": "List of insights"}
                },
                "required": ["insights"],
            },
            "world_model_get_state_version": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "symbolic_compute": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Symbolic mathematical expression",
                    },
                    "variables": {
                        "type": "object",
                        "description": "Variable substitutions",
                        "default": {},
                    },
                },
                "required": ["expression"],
            },
            "symbolic_codegen": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Symbolic expression to compile",
                    },
                    "language": {
                        "type": "string",
                        "description": "Target language: 'python', 'c', 'fortran'",
                        "default": "python",
                    },
                },
                "required": ["expression"],
            },
            "symbolic_optimize": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Symbolic expression to optimize",
                    },
                },
                "required": ["expression"],
            },
            "simulation": {
                "type": "object",
                "properties": {
                    "graph_data": {
                        "type": "object",
                        "description": "IR graph data from IRGenerator.to_dict()",
                    },
                    "scenario_params": {
                        "type": "object",
                        "description": "Scenario configuration",
                        "default": {},
                    },
                    "mode": {
                        "type": "string",
                        "description": "Simulation mode: 'fast', 'standard', 'thorough'",
                        "default": "standard",
                    },
                },
                "required": ["graph_data"],
            },
        }

        # Research tool schemas (basic)
        research_schemas = {
            "perplexity_search": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                },
                "required": ["query"],
            },
            "http_request": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to request",
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                        "default": "GET",
                    },
                    "body": {
                        "type": "object",
                        "description": "Request body (for POST/PUT)",
                    },
                },
                "required": ["url"],
            },
            "mock_search": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                },
                "required": ["query"],
            },
        }

        # Merge schemas (L tools take precedence)
        all_schemas = {**research_schemas, **l_tool_schemas}

        return all_schemas.get(tool_id, {"type": "object", "properties": {}})

    # =========================================================================
    # Registry Passthrough
    # =========================================================================

    def register_tool(
        self,
        tool_id: str,
        name: str,
        description: str,
        executor: Any,
        tool_type: str = "custom",
        **kwargs,
    ) -> None:
        """
        Register a new tool.

        Args:
            tool_id: Unique tool identifier
            name: Human-readable name
            description: Tool description
            executor: Callable or object with execute method
            tool_type: Tool type category
            **kwargs: Additional metadata
        """
        if self._registry is None:
            logger.error("Cannot register tool: no base registry")
            return

        try:
            from core.tools.base_registry import ToolMetadata, ToolType

            # Try to get tool type enum, default to MOCK if unknown
            try:
                tt = ToolType(tool_type)
            except ValueError:
                tt = ToolType.MOCK

            metadata = ToolMetadata(
                id=tool_id,
                name=name,
                description=description,
                tool_type=tt,
                **kwargs,
            )
            self._registry.register(metadata, executor)

            # GMP-124: Invalidate cache entry for this tool
            self._cache.invalidate(tool_id)
            logger.debug("tool_cache.invalidated_on_register", tool_id=tool_id)

        except ImportError:
            logger.error("Cannot register tool: tool_registry not available")

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools."""
        if self._registry is None:
            return []

        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "enabled": t.enabled,
                "type": t.tool_type,
            }
            for t in self._registry.list_all()
        ]

    def get_cache_metrics(self) -> dict[str, Any]:
        """
        Get tool registry cache metrics.

        Returns:
            Dict with cache hit/miss rates, size, evictions, etc.
        """
        return self._cache.get_metrics().to_dict()

    def invalidate_cache(self, tool_id: str | None = None) -> int:
        """
        Invalidate cache entries.

        Args:
            tool_id: Specific tool to invalidate (None = all)

        Returns:
            Number of entries invalidated
        """
        if tool_id is not None:
            return 1 if self._cache.invalidate(tool_id) else 0
        return self._cache.invalidate_all()


# =============================================================================
# Factory Function
# =============================================================================


def create_executor_tool_registry(
    governance_enabled: bool = True,
    base_registry: Any | None = None,
    governance_engine: GovernanceEngineService | None = None,
    cache_config: CacheConfig | None = None,
) -> ExecutorToolRegistry:
    """
    Factory function to create an ExecutorToolRegistry.

    Args:
        governance_enabled: Whether to enforce governance (legacy)
        base_registry: Optional base registry to wrap
        governance_engine: Optional GovernanceEngineService for policy evaluation
        cache_config: Optional cache configuration

    Returns:
        Configured ExecutorToolRegistry
    """
    return ExecutorToolRegistry(
        base_registry=base_registry,
        governance_enabled=governance_enabled,
        governance_engine=governance_engine,
        cache_config=cache_config,
    )


def get_tool_registry_adapter() -> ExecutorToolRegistry:
    """
    Get a default ExecutorToolRegistry instance.

    Used as a FastAPI dependency.
    """
    return create_executor_tool_registry(governance_enabled=True)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "HIGH_RISK_TOOLS",
    "SIDE_EFFECT_TOOLS",
    "CacheConfig",
    "ExecutorToolRegistry",
    "RiskLevel",
    "ToolRegistryCache",
    "create_executor_tool_registry",
    "register_l_tools",
]


# =============================================================================
# L-CTO Tool Registration
# =============================================================================


def _get_l_tool_schema_for_registry(tool_name: str):
    """
    Get ToolSchema object for an L-CTO tool.

    Returns a ToolSchema compatible with the base registry.
    Uses the same schema definitions as _get_tool_schema().
    """
    from core.tools.base_registry import ToolSchema

    # L-CTO tool schemas (same as _get_tool_schema but returns ToolSchema)
    schemas = {
        "memory_search": ToolSchema(
            type="object",
            properties={
                "query": {
                    "type": "string",
                    "description": "Natural language search query",
                },
                "segment": {
                    "type": "string",
                    "description": "Memory segment: 'all', 'governance', 'project', 'session'",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (1-100)",
                },
            },
            required=["query"],
        ),
        "memory_write": ToolSchema(
            type="object",
            properties={
                "packet": {"type": "object", "description": "Packet data to write"},
                "segment": {"type": "string", "description": "Target memory segment"},
            },
            required=["packet", "segment"],
        ),
        # Memory Substrate Direct Access (GMP-31 Batch 1)
        "memory_get_packet": ToolSchema(
            type="object",
            properties={
                "packet_id": {"type": "string", "description": "UUID of packet"}
            },
            required=["packet_id"],
        ),
        "memory_query_packets": ToolSchema(
            type="object",
            properties={
                "filters": {"type": "object", "description": "Filter criteria"},
                "limit": {"type": "integer", "description": "Max results"},
            },
            required=["filters"],
        ),
        "memory_search_by_thread": ToolSchema(
            type="object",
            properties={
                "thread_id": {"type": "string", "description": "Thread ID"},
                "limit": {"type": "integer", "description": "Max results"},
            },
            required=["thread_id"],
        ),
        "memory_search_by_type": ToolSchema(
            type="object",
            properties={
                "packet_type": {"type": "string", "description": "Packet kind"},
                "limit": {"type": "integer", "description": "Max results"},
            },
            required=["packet_type"],
        ),
        "memory_get_events": ToolSchema(
            type="object",
            properties={
                "event_type": {"type": "string", "description": "Event type filter"},
                "limit": {"type": "integer", "description": "Max results"},
            },
            required=[],
        ),
        "memory_get_reasoning_traces": ToolSchema(
            type="object",
            properties={
                "task_id": {"type": "string", "description": "Task ID filter"},
                "limit": {"type": "integer", "description": "Max traces"},
            },
            required=[],
        ),
        "memory_get_facts": ToolSchema(
            type="object",
            properties={
                "subject": {"type": "string", "description": "Subject to query"},
                "limit": {"type": "integer", "description": "Max facts"},
            },
            required=["subject"],
        ),
        "memory_write_insight": ToolSchema(
            type="object",
            properties={
                "insight": {"type": "string", "description": "Insight text"},
                "category": {"type": "string", "description": "Category"},
                "confidence": {"type": "number", "description": "Confidence 0-1"},
            },
            required=["insight", "category"],
        ),
        "memory_embed_text": ToolSchema(
            type="object",
            properties={"text": {"type": "string", "description": "Text to embed"}},
            required=["text"],
        ),
        # Memory Client API (GMP-31 Batch 2)
        "memory_hybrid_search": ToolSchema(
            type="object",
            properties={
                "query": {"type": "string", "description": "Search query"},
                "top_k": {"type": "integer", "description": "Max results"},
                "filters": {"type": "object", "description": "Optional filters"},
            },
            required=["query"],
        ),
        "memory_fetch_lineage": ToolSchema(
            type="object",
            properties={
                "packet_id": {"type": "string", "description": "Packet UUID"},
                "direction": {
                    "type": "string",
                    "description": "ancestors or descendants",
                },
                "max_depth": {"type": "integer", "description": "Max depth"},
            },
            required=["packet_id"],
        ),
        "memory_fetch_thread": ToolSchema(
            type="object",
            properties={
                "thread_id": {"type": "string", "description": "Thread ID"},
                "limit": {"type": "integer", "description": "Max packets"},
            },
            required=["thread_id"],
        ),
        "memory_fetch_facts_api": ToolSchema(
            type="object",
            properties={
                "subject": {"type": "string", "description": "Subject filter"},
                "predicate": {"type": "string", "description": "Predicate filter"},
                "limit": {"type": "integer", "description": "Max facts"},
            },
            required=[],
        ),
        "memory_fetch_insights": ToolSchema(
            type="object",
            properties={
                "packet_id": {"type": "string", "description": "Source packet"},
                "insight_type": {"type": "string", "description": "Type filter"},
                "limit": {"type": "integer", "description": "Max insights"},
            },
            required=[],
        ),
        "memory_gc_stats": ToolSchema(
            type="object",
            properties={},
            required=[],
        ),
        "gmp_run": ToolSchema(
            type="object",
            properties={
                "gmp_id": {"type": "string", "description": "GMP identifier"},
                "params": {"type": "object", "description": "GMP execution parameters"},
            },
            required=["gmp_id"],
        ),
        "git_commit": ToolSchema(
            type="object",
            properties={
                "message": {"type": "string", "description": "Commit message"},
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files to commit",
                },
            },
            required=["message"],
        ),
        "mac_agent_exec_task": ToolSchema(
            type="object",
            properties={
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (5-300)",
                },
            },
            required=["command"],
        ),
        "mcp_list_servers": ToolSchema(
            type="object",
            properties={},
            required=[],
        ),
        "mcp_list_tools": ToolSchema(
            type="object",
            properties={
                "server_id": {
                    "type": "string",
                    "description": "MCP server: 'github', 'notion', 'filesystem', etc.",
                },
            },
            required=["server_id"],
        ),
        "mcp_call_tool": ToolSchema(
            type="object",
            properties={
                "server_id": {
                    "type": "string",
                    "description": "MCP server: 'github', 'notion', 'filesystem', etc.",
                },
                "tool_name": {
                    "type": "string",
                    "description": "Tool name (e.g., 'create_issue', 'search')",
                },
                "arguments": {"type": "object", "description": "Tool arguments"},
            },
            required=["server_id", "tool_name"],
        ),
        "mcp_discover_and_register": ToolSchema(
            type="object",
            properties={},
            required=[],
        ),
        "world_model_query": ToolSchema(
            type="object",
            properties={
                "query_type": {"type": "string", "description": "Query type"},
                "params": {"type": "object", "description": "Query parameters"},
            },
            required=["query_type"],
        ),
        "kernel_read": ToolSchema(
            type="object",
            properties={
                "kernel_name": {"type": "string", "description": "Kernel identifier"},
                "property": {"type": "string", "description": "Property to read"},
            },
            required=["kernel_name", "property"],
        ),
        "long_plan_execute": ToolSchema(
            type="object",
            properties={
                "plan_id": {"type": "string", "description": "Plan identifier"},
                "params": {"type": "object", "description": "Execution parameters"},
            },
            required=["plan_id"],
        ),
        "long_plan_simulate": ToolSchema(
            type="object",
            properties={
                "plan_id": {"type": "string", "description": "Plan identifier"},
                "params": {"type": "object", "description": "Simulation parameters"},
            },
            required=["plan_id"],
        ),
        "neo4j_query": ToolSchema(
            type="object",
            properties={
                "cypher": {
                    "type": "string",
                    "description": "Cypher query to run against Neo4j",
                },
                "params": {"type": "object", "description": "Query parameters"},
            },
            required=["cypher"],
        ),
        "redis_get": ToolSchema(
            type="object",
            properties={
                "key": {"type": "string", "description": "Redis key to retrieve"},
            },
            required=["key"],
        ),
        "redis_set": ToolSchema(
            type="object",
            properties={
                "key": {"type": "string", "description": "Redis key"},
                "value": {"type": "string", "description": "Value to store"},
                "ttl_seconds": {
                    "type": "integer",
                    "description": "Optional TTL in seconds",
                },
            },
            required=["key", "value"],
        ),
        "redis_keys": ToolSchema(
            type="object",
            properties={
                "pattern": {
                    "type": "string",
                    "description": "Key pattern (e.g., 'agent:*')",
                },
            },
            required=[],
        ),
        # Redis State Management (GMP-31 Batch 3)
        "redis_delete": ToolSchema(
            type="object",
            properties={"key": {"type": "string", "description": "Key to delete"}},
            required=["key"],
        ),
        "redis_enqueue_task": ToolSchema(
            type="object",
            properties={
                "queue_name": {"type": "string", "description": "Queue name"},
                "task_data": {"type": "object", "description": "Task payload"},
                "priority": {"type": "integer", "description": "Priority"},
            },
            required=["queue_name", "task_data"],
        ),
        "redis_dequeue_task": ToolSchema(
            type="object",
            properties={"queue_name": {"type": "string", "description": "Queue name"}},
            required=["queue_name"],
        ),
        "redis_queue_size": ToolSchema(
            type="object",
            properties={"queue_name": {"type": "string", "description": "Queue name"}},
            required=["queue_name"],
        ),
        "redis_get_task_context": ToolSchema(
            type="object",
            properties={"task_id": {"type": "string", "description": "Task ID"}},
            required=["task_id"],
        ),
        "redis_set_task_context": ToolSchema(
            type="object",
            properties={
                "task_id": {"type": "string", "description": "Task ID"},
                "context": {"type": "object", "description": "Context data"},
                "ttl_seconds": {"type": "integer", "description": "TTL"},
            },
            required=["task_id", "context"],
        ),
        # Tool Graph Introspection (GMP-31 Batch 4)
        "tools_list_all": ToolSchema(type="object", properties={}, required=[]),
        "tools_list_enabled": ToolSchema(type="object", properties={}, required=[]),
        "tools_get_metadata": ToolSchema(
            type="object",
            properties={"tool_id": {"type": "string", "description": "Tool ID"}},
            required=["tool_id"],
        ),
        "tools_get_schema": ToolSchema(
            type="object",
            properties={"tool_id": {"type": "string", "description": "Tool ID"}},
            required=["tool_id"],
        ),
        "tools_get_by_type": ToolSchema(
            type="object",
            properties={"tool_type": {"type": "string", "description": "Tool type"}},
            required=["tool_type"],
        ),
        "tools_get_for_role": ToolSchema(
            type="object",
            properties={"role": {"type": "string", "description": "Role"}},
            required=["role"],
        ),
        # World Model Operations (GMP-31 Batch 5)
        "world_model_get_entity": ToolSchema(
            type="object",
            properties={"entity_id": {"type": "string", "description": "Entity ID"}},
            required=["entity_id"],
        ),
        "world_model_list_entities": ToolSchema(
            type="object",
            properties={
                "entity_type": {"type": "string", "description": "Type filter"},
                "min_confidence": {"type": "number", "description": "Min confidence"},
                "limit": {"type": "integer", "description": "Max entities"},
            },
            required=[],
        ),
        "world_model_snapshot": ToolSchema(
            type="object",
            properties={
                "description": {"type": "string", "description": "Description"}
            },
            required=[],
        ),
        "world_model_list_snapshots": ToolSchema(
            type="object",
            properties={"limit": {"type": "integer", "description": "Max snapshots"}},
            required=[],
        ),
        "world_model_send_insights": ToolSchema(
            type="object",
            properties={"insights": {"type": "array", "description": "Insights list"}},
            required=["insights"],
        ),
        "world_model_get_state_version": ToolSchema(
            type="object",
            properties={},
            required=[],
        ),
        "symbolic_compute": ToolSchema(
            type="object",
            properties={
                "expression": {
                    "type": "string",
                    "description": "Symbolic mathematical expression",
                },
                "variables": {
                    "type": "object",
                    "description": "Variable substitutions",
                },
            },
            required=["expression"],
        ),
        "symbolic_codegen": ToolSchema(
            type="object",
            properties={
                "expression": {
                    "type": "string",
                    "description": "Symbolic expression to compile",
                },
                "language": {
                    "type": "string",
                    "description": "Target language: 'python', 'c', 'fortran'",
                },
            },
            required=["expression"],
        ),
        "symbolic_optimize": ToolSchema(
            type="object",
            properties={
                "expression": {
                    "type": "string",
                    "description": "Symbolic expression to optimize",
                },
            },
            required=["expression"],
        ),
        "simulation": ToolSchema(
            type="object",
            properties={
                "graph_data": {"type": "object", "description": "IR graph data"},
                "scenario_params": {
                    "type": "object",
                    "description": "Scenario configuration",
                },
                "mode": {"type": "string", "description": "Simulation mode"},
            },
            required=["graph_data"],
        ),
        # MCP Server Control (GMP-32 Batch 6)
        "mcp_start_server": ToolSchema(
            type="object",
            properties={
                "server_id": {
                    "type": "string",
                    "description": "MCP server ID to start",
                },
            },
            required=["server_id"],
        ),
        "mcp_stop_server": ToolSchema(
            type="object",
            properties={
                "server_id": {"type": "string", "description": "MCP server ID to stop"},
            },
            required=["server_id"],
        ),
        "mcp_stop_all_servers": ToolSchema(
            type="object",
            properties={},
            required=[],
        ),
        # Rate Limiting (GMP-32 Batch 7)
        "redis_get_rate_limit": ToolSchema(
            type="object",
            properties={
                "key": {"type": "string", "description": "Rate limit key"},
            },
            required=["key"],
        ),
        "redis_set_rate_limit": ToolSchema(
            type="object",
            properties={
                "key": {"type": "string", "description": "Rate limit key"},
                "count": {"type": "integer", "description": "Count value to set"},
                "ttl_seconds": {"type": "integer", "description": "TTL in seconds"},
            },
            required=["key", "count"],
        ),
        "redis_increment_rate_limit": ToolSchema(
            type="object",
            properties={
                "key": {"type": "string", "description": "Rate limit key"},
                "amount": {"type": "integer", "description": "Amount to increment"},
            },
            required=["key"],
        ),
        "redis_decrement_rate_limit": ToolSchema(
            type="object",
            properties={
                "key": {"type": "string", "description": "Rate limit key"},
                "amount": {"type": "integer", "description": "Amount to decrement"},
            },
            required=["key"],
        ),
        # Memory Advanced (GMP-32 Batch 8)
        "memory_get_checkpoint": ToolSchema(
            type="object",
            properties={
                "agent_id": {"type": "string", "description": "Agent ID"},
            },
            required=[],
        ),
        "memory_trigger_world_model_update": ToolSchema(
            type="object",
            properties={
                "insights": {"type": "array", "description": "List of insight dicts"},
            },
            required=["insights"],
        ),
        "memory_health_check": ToolSchema(
            type="object",
            properties={},
            required=[],
        ),
        # Tool Graph Analysis (GMP-32 Batch 9)
        "tools_get_api_dependents": ToolSchema(
            type="object",
            properties={
                "api_name": {
                    "type": "string",
                    "description": "API name (e.g., GitHub, OpenAI)",
                },
            },
            required=["api_name"],
        ),
        "tools_get_dependencies": ToolSchema(
            type="object",
            properties={
                "tool_name": {"type": "string", "description": "Tool name"},
            },
            required=["tool_name"],
        ),
        "tools_get_blast_radius": ToolSchema(
            type="object",
            properties={
                "api_name": {"type": "string", "description": "API name"},
            },
            required=["api_name"],
        ),
        "tools_detect_circular_deps": ToolSchema(
            type="object",
            properties={},
            required=[],
        ),
        "tools_get_catalog": ToolSchema(
            type="object",
            properties={},
            required=[],
        ),
        # World Model Advanced (GMP-32 Batch 10)
        "world_model_restore": ToolSchema(
            type="object",
            properties={
                "snapshot_id": {
                    "type": "string",
                    "description": "Snapshot ID to restore",
                },
            },
            required=["snapshot_id"],
        ),
        "world_model_list_updates": ToolSchema(
            type="object",
            properties={
                "limit": {"type": "integer", "description": "Max updates to return"},
            },
            required=[],
        ),
        # Research Agent Tools (GMP: wire_research_lcto_integration)
        "research_agent_synthesize": ToolSchema(
            type="object",
            properties={
                "topic": {
                    "type": "string",
                    "description": "Research topic to synthesize (required)",
                },
                "context": {
                    "type": "object",
                    "description": "Optional additional context as key-value pairs",
                },
            },
            required=["topic"],
        ),
        "research_agent_discover": ToolSchema(
            type="object",
            properties={
                "topic": {
                    "type": "string",
                    "description": "Research topic (required)",
                },
                "domain": {
                    "type": "string",
                    "description": "Research domain (default: general)",
                },
                "stages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Stages to run: landscape, deep_dive, comparative, gaps, hypotheses",
                },
            },
            required=["topic"],
        ),
        "research_agent_generate_spec": ToolSchema(
            type="object",
            properties={
                "topic": {
                    "type": "string",
                    "description": "Module topic (required)",
                },
                "description": {
                    "type": "string",
                    "description": "Module description",
                },
                "run_synthesis_first": {
                    "type": "boolean",
                    "description": "Run synthesis before spec generation (default: true)",
                },
            },
            required=["topic"],
        ),
        # Reflection Agent Tools (GMP: wire_reflection_agent_yaml)
        "reflection_agent_reflect": ToolSchema(
            type="object",
            properties={
                "history": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Execution history to reflect on (required)",
                },
                "focus": {
                    "type": "string",
                    "description": "Focus area: general, failures, patterns (default: general)",
                },
                "goals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Goals to evaluate against",
                },
            },
            required=["history"],
        ),
        "reflection_agent_analyze_failure": ToolSchema(
            type="object",
            properties={
                "failure_context": {
                    "type": "object",
                    "description": "Context of the failure (required)",
                },
                "error": {
                    "type": "string",
                    "description": "Error message (required)",
                },
                "stack_trace": {
                    "type": "string",
                    "description": "Optional stack trace",
                },
            },
            required=["failure_context", "error"],
        ),
        "reflection_agent_compare_approaches": ToolSchema(
            type="object",
            properties={
                "approach_a": {
                    "type": "object",
                    "description": "First approach to compare (required)",
                },
                "approach_b": {
                    "type": "object",
                    "description": "Second approach to compare (required)",
                },
                "criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Comparison criteria (required)",
                },
            },
            required=["approach_a", "approach_b", "criteria"],
        ),
        "reflection_agent_extract_patterns": ToolSchema(
            type="object",
            properties={
                "examples": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Examples to analyze (required, min 2)",
                },
            },
            required=["examples"],
        ),
        "reflection_agent_generate_improvements": ToolSchema(
            type="object",
            properties={
                "current_performance": {
                    "type": "object",
                    "description": "Current performance metrics (required)",
                },
                "goals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Improvement goals (required)",
                },
            },
            required=["current_performance", "goals"],
        ),
    }

    return schemas.get(tool_name)


async def register_l_tools() -> int:
    """
    Register all L-CTO tools in the tool registry with governance metadata.

    Called once at server startup.
    Each tool gets:
      - Execution function from runtime.l_tools
      - Governance metadata (scope, risk_level, requires_approval)
      - Input schema for validation and LLM function calling
      - Registration in base registry for dispatch

    Returns:
        Number of tools registered

    Raises:
        Exception: If registration fails
    """
    from core.tools.base_registry import ToolMetadata, ToolType, get_tool_registry
    from core.tools.tool_graph import ToolDefinition, ToolGraph
    from runtime.l_tools import TOOL_EXECUTORS

    # Get base registry for executor registration
    base_registry = get_tool_registry()

    logger.info("Registering L-CTO tools...")

    # Define all L-CTO tools with metadata
    tools_to_register = [
        ToolDefinition(
            name="memory_search",
            description="Search L's memory substrate using semantic search",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_write",
            description="Write to L's memory substrate",
            category="memory",
            scope="internal",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # Memory Substrate Direct Access (GMP-31 Batch 1)
        ToolDefinition(
            name="memory_get_packet",
            description="Get a specific packet by ID from memory substrate",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_query_packets",
            description="Query packets with complex filters",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_search_by_thread",
            description="Search packets by conversation thread ID",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_search_by_type",
            description="Search packets by type (REASONING, TOOL_CALL, etc.)",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_get_events",
            description="Get memory audit events (tool calls, decisions)",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_get_reasoning_traces",
            description="Get L's reasoning traces from memory",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_get_facts",
            description="Get knowledge facts by subject from memory graph",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_write_insight",
            description="Write an insight to memory substrate",
            category="memory",
            scope="internal",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_embed_text",
            description="Generate embedding vector for text",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # Memory Client API (GMP-31 Batch 2)
        ToolDefinition(
            name="memory_hybrid_search",
            description="Hybrid search combining semantic + keyword matching",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_fetch_lineage",
            description="Fetch packet lineage (ancestors or descendants)",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_fetch_thread",
            description="Fetch all packets in a conversation thread",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_fetch_facts_api",
            description="Fetch knowledge facts from memory API",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_fetch_insights",
            description="Fetch insights from memory",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_gc_stats",
            description="Get garbage collection statistics from memory",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="gmp_run",
            description="Execute a GMP (Governance Management Process)",
            category="governance",
            scope="requires_igor_approval",
            risk_level="high",
            requires_igor_approval=True,
            requires_confirmation=True,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="git_commit",
            description="Commit code changes to git repository",
            category="vcs",
            scope="requires_igor_approval",
            risk_level="high",
            requires_igor_approval=True,
            requires_confirmation=True,
            is_destructive=True,
            agent_id="L",
        ),
        ToolDefinition(
            name="mac_agent_exec_task",
            description="Execute command via Mac agent",
            category="execution",
            scope="requires_igor_approval",
            risk_level="high",
            requires_igor_approval=True,
            requires_confirmation=True,
            is_destructive=True,
            agent_id="L",
        ),
        ToolDefinition(
            name="mcp_list_servers",
            description="List all configured MCP servers and their status",
            category="integration",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="mcp_list_tools",
            description="List available tools from an MCP server (dynamic discovery)",
            category="integration",
            scope="external",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="mcp_call_tool",
            description="Call any tool on any MCP server (GitHub, Notion, Filesystem, etc.)",
            category="integration",
            scope="external",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="mcp_discover_and_register",
            description="Auto-discover all MCP tools and register them in Neo4j graph",
            category="integration",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="world_model_query",
            description="Query the world model",
            category="world_model",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="kernel_read",
            description="Read a property from a kernel",
            category="kernel",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="long_plan_execute",
            description="Execute a long plan through LangGraph DAG",
            category="orchestration",
            scope="internal",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=True,
            is_destructive=True,
            agent_id="L",
        ),
        ToolDefinition(
            name="long_plan_simulate",
            description="Simulate a long plan without executing (dry run)",
            category="orchestration",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # Neo4j Graph Database tools
        ToolDefinition(
            name="neo4j_query",
            description="Run Cypher queries against Neo4j graph (tool deps, events, knowledge)",
            category="knowledge",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # Redis Cache tools
        ToolDefinition(
            name="redis_get",
            description="Get value from Redis cache",
            category="cache",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="redis_set",
            description="Set value in Redis cache with optional TTL",
            category="cache",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=True,
            agent_id="L",
        ),
        ToolDefinition(
            name="redis_keys",
            description="List Redis keys matching a pattern",
            category="cache",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # Redis State Management (GMP-31 Batch 3)
        ToolDefinition(
            name="redis_delete",
            description="Delete a key from Redis",
            category="cache",
            scope="internal",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=True,
            agent_id="L",
        ),
        ToolDefinition(
            name="redis_enqueue_task",
            description="Enqueue a task to Redis queue",
            category="cache",
            scope="internal",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="redis_dequeue_task",
            description="Dequeue task from Redis queue",
            category="cache",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="redis_queue_size",
            description="Get size of a Redis task queue",
            category="cache",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="redis_get_task_context",
            description="Get cached task context from Redis",
            category="cache",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="redis_set_task_context",
            description="Set task context in Redis cache",
            category="cache",
            scope="internal",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # Tool Graph Introspection (GMP-31 Batch 4)
        ToolDefinition(
            name="tools_list_all",
            description="List all registered tools",
            category="introspection",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="tools_list_enabled",
            description="List only enabled tools",
            category="introspection",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="tools_get_metadata",
            description="Get detailed metadata for a tool",
            category="introspection",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="tools_get_schema",
            description="Get OpenAI function schema for a tool",
            category="introspection",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="tools_get_by_type",
            description="Get all tools of a specific type",
            category="introspection",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="tools_get_for_role",
            description="Get all tools available for a role",
            category="introspection",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # World Model Operations (GMP-31 Batch 5)
        ToolDefinition(
            name="world_model_get_entity",
            description="Get entity from world model by ID",
            category="knowledge",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="world_model_list_entities",
            description="List entities from world model",
            category="knowledge",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="world_model_snapshot",
            description="Create snapshot of world model state",
            category="knowledge",
            scope="internal",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="world_model_list_snapshots",
            description="List recent world model snapshots",
            category="knowledge",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="world_model_send_insights",
            description="Send insights for world model update",
            category="knowledge",
            scope="internal",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="world_model_get_state_version",
            description="Get current world model state version",
            category="knowledge",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # Symbolic computation tools (Quantum AI Factory) - always available via lazy loading
        ToolDefinition(
            name="symbolic_compute",
            description="Evaluate symbolic mathematical expressions numerically",
            category="computation",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="symbolic_codegen",
            description="Generate compilable C/Fortran/Python code from symbolic expressions",
            category="computation",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="symbolic_optimize",
            description="Optimize and simplify symbolic expressions using CSE",
            category="computation",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # Simulation tools (IR graph evaluation)
        ToolDefinition(
            name="simulation",
            description="Execute IR graph simulation for agent reasoning traces",
            category="simulation",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # MCP Server Control (GMP-32 Batch 6)
        ToolDefinition(
            name="mcp_start_server",
            description="Start an MCP server process",
            category="mcp",
            scope="internal",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="mcp_stop_server",
            description="Stop an MCP server process",
            category="mcp",
            scope="internal",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="mcp_stop_all_servers",
            description="Stop all running MCP server processes",
            category="mcp",
            scope="internal",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # Rate Limiting (GMP-32 Batch 7)
        ToolDefinition(
            name="redis_get_rate_limit",
            description="Get current rate limit count for a key",
            category="redis",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="redis_set_rate_limit",
            description="Set rate limit count with TTL",
            category="redis",
            scope="internal",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="redis_increment_rate_limit",
            description="Increment rate limit counter",
            category="redis",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="redis_decrement_rate_limit",
            description="Decrement rate limit counter",
            category="redis",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # Memory Advanced (GMP-32 Batch 8)
        ToolDefinition(
            name="memory_get_checkpoint",
            description="Get the latest checkpoint state for an agent",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_trigger_world_model_update",
            description="Trigger world model update from insights",
            category="memory",
            scope="internal",
            risk_level="medium",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="memory_health_check",
            description="Check health of all memory substrate components",
            category="memory",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # Tool Graph Analysis (GMP-32 Batch 9)
        ToolDefinition(
            name="tools_get_api_dependents",
            description="Get all tools that depend on an API",
            category="tools",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="tools_get_dependencies",
            description="Get all dependencies of a tool",
            category="tools",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="tools_get_blast_radius",
            description="Calculate full blast radius if an API goes down",
            category="tools",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="tools_detect_circular_deps",
            description="Detect circular dependencies in the tool graph",
            category="tools",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        ToolDefinition(
            name="tools_get_catalog",
            description="Get L's complete tool catalog with metadata",
            category="tools",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
        # World Model Advanced (GMP-32 Batch 10)
        ToolDefinition(
            name="world_model_restore",
            description="Restore world model from a snapshot",
            category="world_model",
            scope="internal",
            risk_level="high",
            requires_igor_approval=True,
            requires_confirmation=True,
            is_destructive=True,
            agent_id="L",
        ),
        ToolDefinition(
            name="world_model_list_updates",
            description="List recent world model updates",
            category="world_model",
            scope="internal",
            risk_level="low",
            requires_igor_approval=False,
            requires_confirmation=False,
            is_destructive=False,
            agent_id="L",
        ),
    ]

    # GMP-44: Populate auto-discovery mapping before registration
    global _TOOL_AGENT_IDS
    for tool_def in tools_to_register:
        _TOOL_AGENT_IDS[tool_def.name] = tool_def.agent_id
    logger.info(f"Auto-discovery: populated {len(_TOOL_AGENT_IDS)} tool→agent mappings")

    # Register each tool in BOTH Neo4j AND base registry
    registered_count = 0
    for tool_def in tools_to_register:
        try:
            # 1. Register in Neo4j (for graph queries and governance metadata)
            success = await ToolGraph.register_tool(tool_def)
            if success:
                logger.debug(f"Neo4j: registered {tool_def.name}")
            else:
                logger.debug(f"Neo4j: skipped {tool_def.name} (unavailable)")

            # 2. Register in base registry (for dispatch execution)
            executor_func = TOOL_EXECUTORS.get(tool_def.name)
            if executor_func:
                # Get input schema for LLM function calling
                tool_schema = _get_l_tool_schema_for_registry(tool_def.name)

                metadata = ToolMetadata(
                    id=tool_def.name,
                    name=tool_def.name,
                    description=tool_def.description,
                    tool_type=ToolType.CUSTOM,
                    allowed_roles=["l-cto", "researcher", "agent"],
                    rate_limit=60,
                    timeout_seconds=(
                        120
                        if tool_def.name in ["gmp_run", "mac_agent_exec_task"]
                        else 30
                    ),
                    enabled=True,
                    requires_api_key=False,
                    input_schema=tool_schema,  # LLM function calling schema
                )
                base_registry.register(metadata, executor_func)
                logger.info(
                    f"✓ Registered tool: {tool_def.name} (risk={tool_def.risk_level}, schema={'yes' if tool_schema else 'no'})"
                )
            else:
                logger.warning(f"No executor found for tool: {tool_def.name}")

            registered_count += 1
        except Exception as e:
            logger.error(f"✗ Failed to register {tool_def.name}: {e}")
            raise

    high_risk_count = sum(1 for t in tools_to_register if t.requires_igor_approval)
    logger.info(
        f"✓✓ L-CTO tools registered: {registered_count} total, "
        f"{high_risk_count} high-risk requiring approval, "
        f"executors wired to base registry"
    )

    return registered_count


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-021",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.agents.schemas",
        "core.decorators",
        "core.governance.approvals",
        "core.governance.engine",
        "core.governance.schemas",
    ],
    "tags": [
        "adapter",
        "api",
        "async",
        "audit-tool",
        "authorization",
        "batch-processing",
        "cache",
        "caching",
        "debugging",
        "event-driven",
    ],
    "keywords": [
        "(executortoolregistry)",
        "adapter",
        "agent",
        "approval",
        "approve",
        "approved",
        "architecture",
        "audit",
    ],
    "business_value": "This module implements the primary tool dispatch mechanism for L9. Tools are registered and executed through ExecutorToolRegistry, which integrates with Neo4j for governance and Postgres for data. ARC",
    "last_modified": "2026-01-17T23:47:56Z",
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
