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
            # ADR-0094: Tool access filtering moved to agent kernels / governance.
            # All tools in the registry are available; governance engine below
            # handles per-agent policy checks.

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
            # ADR-0094: schemas served from base registry (populated by bridge)
            schema = self._registry.get_tool_schema(tool_meta.id)

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

    @must_stay_async("callers use await")
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

            # ADR-0094: Tool access filtering moved to agent kernels / governance.

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
            # ADR-0094: schemas served from base registry (populated by bridge)
            schema = self._registry.get_tool_schema(tool_meta.id)

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

    @must_stay_async("callers use await")
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
                # ADR-0094: schemas served from base registry (populated by bridge)
                tool_schema = self._registry.get_tool_schema(tool_id)

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
            # ADR-0094: schemas served from base registry (populated by bridge)
            tool_schema = self._registry.get_tool_schema(tool_id)

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

    @must_stay_async("callers use await")
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

        Security Model (Fail-Closed):
        - principal_id is MANDATORY (no default, no fallback)
        - Raises ValueError if principal_id is None or empty
        - This is defense-in-depth (kernel already checks, but enforce here too)

        Args:
            agent: The kernel-aware agent (must have kernel_state attribute)
            tool_id: Tool identifier
            arguments: Tool call arguments
            context: Optional execution context
            principal_id: Principal authorizing this execution (REQUIRED)

        Returns:
            ToolCallResult with success/failure, result, and tool_id

        Raises:
            ValueError: If principal_id is missing or empty (fail-closed)
            RuntimeError: If kernels not active (hard failure)
            PermissionError: If governance denies execution
        """
        start_time = time.time()
        call_id = uuid4()

        # Build context if not provided
        if context is None:
            context = {}

        agent_id = getattr(agent, "agent_id", context.get("agent_id", "unknown"))
        context["agent_id"] = agent_id
        # Defense-in-depth: reject None, empty, and whitespace-only principals
        if (
            principal_id is None
            or not isinstance(principal_id, str)
            or not principal_id.strip()
        ):
            raise ValueError(
                "principal_id is required for guarded tool execution. "
                f"Tool: {tool_id}"
            )
        principal_id = principal_id.strip()

        # Extract kernel metadata for audit trail
        kernel_hashes = getattr(agent, "_kernel_hashes", {})
        kernel_version = getattr(agent, "_kernel_version", "unknown")

        # GATE 1: Verify kernel activation
        kernel_state = getattr(agent, "kernel_state", None)
        kernel_active = False
        if isinstance(kernel_state, str):
            kernel_active = kernel_state == "ACTIVE"
        elif hasattr(kernel_state, "initialized") and kernel_state is not None:
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
                if substrate is None:  # nosemgrep: l9-singleton-requires-lock
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
    # Schema Helpers — ADR-0094: Schemas now in config/tool_schemas.py
    # _get_tool_schema() removed; base_registry.get_tool_schema() is canonical.
    # =========================================================================
    # =========================================================================
    # Registry Passthrough
    # =========================================================================

    @must_stay_async("callers use await")
    async def register_tool(
        self,
        tool_id: str,
        name: str,
        description: str,
        executor: Any,
        tool_type: str = "custom",
        **kwargs,
    ) -> None:
        """
        Register a new tool (async).

        GMP-79: Made async to support deterministic cache invalidation.
        When tools are registered, all multi-turn tool caches are cleared
        so subsequent turns discover the updated tool set.

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

            # GMP-79: Invalidate all multi-turn tool caches
            # Use runtime import to avoid circular dependency
            import importlib

            module = importlib.import_module("core.tools.dynamic_discovery")
            await module.invalidate_all_tool_caches()

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
# ADR-0094 Step 2: Bridge for Runtime Auto-Registered Tools
# =============================================================================


def sync_runtime_tools_to_primary() -> int:
    """
    Bridge that syncs runtime auto-registered tool executors into the primary
    base registry pipeline.

    This is the ONLY sanctioned access point for ``tool_executor_registry``
    outside of ``runtime/tool_registry.py`` itself.  All feature code must
    use the base registry (``get_tool_registry()``) or
    ``ExecutorToolRegistry`` after this bridge runs.

    Called once during ``api/server.py`` lifespan, **after** runtime tool
    discovery (``discover_tools``, ``register_extension_tool_executors``).

    ADR-0094: Enhanced to load OpenAI function-calling schemas from
    ``config.tool_schemas`` so that ``base_registry.get_tool_schema()``
    returns real schemas for all tools.

    Returns:
        Number of runtime tools synced into the base registry.
    """
    from config.tool_schemas import TOOL_SCHEMAS
    from core.tools.base_registry import (
        ToolMetadata,
        ToolSchema,
        ToolType,
        get_tool_registry,
    )
    from runtime.tool_registry import tool_executor_registry

    base = get_tool_registry()
    synced = 0

    for tool_id in tool_executor_registry.list_ids():
        # Skip tools already present in the base registry.
        if base.get_tool(tool_id):
            continue

        executor = tool_executor_registry.get(tool_id)
        if executor is None:
            continue

        # Pull metadata attached by the @register_tool decorator
        meta_dict: dict = getattr(executor, "_tool_metadata", {})
        category = meta_dict.get("category", "")
        description = meta_dict.get("description", "")

        # Look up OpenAI function-calling schema from canonical data module
        schema_dict = TOOL_SCHEMAS.get(tool_id)
        input_schema: ToolSchema | None = None
        if schema_dict:
            input_schema = ToolSchema(
                type=schema_dict.get("type", "object"),
                properties=schema_dict.get("properties", {}),
                required=schema_dict.get("required", []),
            )

        metadata = ToolMetadata(
            id=tool_id,
            name=tool_id,
            description=description or f"Auto-registered tool: {tool_id}",
            tool_type=ToolType.CUSTOM,
            allowed_roles=["l-cto", "researcher", "agent"],
            rate_limit=60,
            timeout_seconds=30,
            enabled=True,
            tags=[category] if category else [],
            input_schema=input_schema,
        )
        base.register(metadata, executor)
        synced += 1

    if synced:
        logger.info(
            "sync_runtime_tools_to_primary.done",
            synced=synced,
            total_base=len(base.list_all()),
        )
    return synced


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
    "sync_runtime_tools_to_primary",
]


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
