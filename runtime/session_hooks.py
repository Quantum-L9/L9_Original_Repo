"""
L9 Session Hooks — Agent Lifecycle Hooks
========================================
L9-native replacement for CursorSessionHooks.

Lifecycle hooks injected into AgentExecutorService:
  - on_task_start: hydrate context from working memory + retrieval kernel
  - on_tool_call: update working memory cache with tool results
  - on_task_end: optionally promote high-value results to long-term memory

All substrate writes go through DomainBridgeGateway (ADR-0092).
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Session Hooks",
    "module_version": "1.0.0",
    "created_by": "Manus Agent",
    "created_at": "2026-02-19T12:00:00Z",
    "updated_at": "2026-02-19T12:00:00Z",
    "layer": "core",
    "domain": "runtime",
    "module_name": "runtime.session_hooks",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis", "PostgreSQL", "Neo4j"],
        "memory_layers": ["working_memory", "semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from typing import Any, Protocol, runtime_checkable

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Backend Protocols (ADR-0026)
# =============================================================================


@runtime_checkable
class WorkingMemoryProvider(Protocol):
    """Protocol for working memory context building."""

    async def build_world_model_context(
        self,
        agent_id: str,
        thread_id: str | None = None,
    ) -> dict[str, Any]: ...

    async def semantic_recall_for_intent(
        self,
        query: str,
        agent_id: str,
    ) -> list[Any]: ...


@runtime_checkable
class RetrievalProvider(Protocol):
    """Protocol for the retrieval kernel."""

    async def retrieve(
        self,
        *,
        agent_id: str,
        thread_id: str | None,
        query: str,
        top_k: int = 5,
    ) -> list[Any]: ...


@runtime_checkable
class WorkingMemoryCacheProvider(Protocol):
    """Protocol for working memory cache updates (Redis)."""

    async def update(
        self,
        repo_id: str,
        branch: str,
        **kwargs: Any,
    ) -> Any: ...


@runtime_checkable
class BridgeGatewayProvider(Protocol):
    """Protocol for the Domain Bridge Gateway (ADR-0092)."""

    async def submit(
        self,
        packet: Any,
        *,
        principal_id: str,
        ingress_origin: str,
    ) -> Any: ...


# =============================================================================
# L9 Session Hooks
# =============================================================================


class L9SessionHooks:
    """
    Agent lifecycle hooks for the L9 runtime.

    Injected into ``AgentExecutorService`` to provide:
    - Pre-execution context hydration
    - Mid-execution working memory updates
    - Post-execution long-term memory promotion

    All long-term writes route through ``DomainBridgeGateway`` (ADR-0092).

    Usage::

        hooks = L9SessionHooks(
            working_memory=wm_adapter,
            retrieval=retrieval_kernel,
            cache=wmc_service,
            bridge=domain_bridge,
        )
        # Injected into executor:
        executor.set_session_hooks(hooks)
    """

    __slots__ = (
        "_bridge",
        "_cache",
        "_retrieval",
        "_working_memory",
    )

    def __init__(
        self,
        *,
        working_memory: WorkingMemoryProvider | None = None,
        retrieval: RetrievalProvider | None = None,
        cache: WorkingMemoryCacheProvider | None = None,
        bridge: BridgeGatewayProvider | None = None,
    ) -> None:
        """
        Initialise session hooks with optional dependencies.

        Args:
            working_memory: WorkingMemoryAdapter for context building.
            retrieval: L9RetrievalKernel for multi-tier retrieval.
            cache: WorkingMemoryService for Redis cache updates.
            bridge: DomainBridgeGateway for long-term memory writes.
        """
        self._working_memory = working_memory
        self._retrieval = retrieval
        self._cache = cache
        self._bridge = bridge
        logger.info(
            "session_hooks.init",
            has_working_memory=working_memory is not None,
            has_retrieval=retrieval is not None,
            has_cache=cache is not None,
            has_bridge=bridge is not None,
        )

    @must_stay_async("callers use await")
    async def on_task_start(
        self,
        *,
        agent_id: str,
        task_id: str,
        task_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Called before agent execution begins.

        Hydrates context from working memory and the retrieval kernel.

        Args:
            agent_id: The agent about to execute.
            task_id: The task being executed.
            task_payload: Raw task payload.

        Returns:
            Enriched context dict with ``world_model_context`` and
            ``retrieval_hits`` keys.
        """
        context: dict[str, Any] = {}

        # ── World model context ─────────────────────────────────────────
        if self._working_memory is not None:
            try:
                wm_context = await self._working_memory.build_world_model_context(
                    agent_id=agent_id,
                    thread_id=task_payload.get("thread_id"),
                )
                context["world_model_context"] = wm_context
            except Exception as exc:
                logger.warning(
                    "session_hooks.on_task_start.wm_error",
                    agent_id=agent_id,
                    task_id=task_id,
                    error=str(exc),
                )

        # ── Retrieval kernel ────────────────────────────────────────────
        if self._retrieval is not None:
            try:
                query = task_payload.get("message", "") or task_payload.get("query", "")
                if query:
                    hits = await self._retrieval.retrieve(
                        agent_id=agent_id,
                        thread_id=task_payload.get("thread_id"),
                        query=query,
                        top_k=5,
                    )
                    context["retrieval_hits"] = [
                        h.model_dump() if hasattr(h, "model_dump") else h for h in hits
                    ]
            except Exception as exc:
                logger.warning(
                    "session_hooks.on_task_start.retrieval_error",
                    agent_id=agent_id,
                    task_id=task_id,
                    error=str(exc),
                )

        logger.info(
            "session_hooks.on_task_start",
            agent_id=agent_id,
            task_id=task_id,
            context_keys=list(context.keys()),
        )

        return context

    @must_stay_async("callers use await")
    async def on_tool_call(
        self,
        *,
        agent_id: str,
        tool_id: str,
        tool_result: dict[str, Any],
    ) -> None:
        """
        Called after each tool call completes.

        Updates the working memory cache (Redis) with tool results.
        Redis is exempt from Domain Bridge per ADR-0092 Rule 6.

        Args:
            agent_id: The agent that invoked the tool.
            tool_id: The tool that was called.
            tool_result: The result returned by the tool.
        """
        if self._cache is None:
            return

        try:
            await self._cache.update(
                repo_id=agent_id,
                branch="main",
                tool_id=tool_id,
                tool_result=_summarize_result(tool_result),
            )
            logger.debug(
                "session_hooks.on_tool_call",
                agent_id=agent_id,
                tool_id=tool_id,
            )
        except Exception as exc:
            logger.warning(
                "session_hooks.on_tool_call.cache_error",
                agent_id=agent_id,
                tool_id=tool_id,
                error=str(exc),
            )

    @must_stay_async("callers use await")
    async def on_task_end(
        self,
        *,
        agent_id: str,
        task_id: str,
        result: dict[str, Any],
        principal_id: str | None = None,
    ) -> None:
        """
        Called after agent execution completes.

        Optionally promotes high-value results to long-term memory
        via DomainBridgeGateway (ADR-0092).

        Args:
            agent_id: The agent that completed.
            task_id: The task that completed.
            result: The execution result.
            principal_id: Namespaced caller identity (fail-closed).
        """
        logger.info(
            "session_hooks.on_task_end",
            agent_id=agent_id,
            task_id=task_id,
            status=result.get("status", "unknown"),
            has_principal_id=bool(principal_id and str(principal_id).strip()),
        )

        if self._bridge is None or not _should_promote(result):
            return

        cleaned = principal_id.strip() if isinstance(principal_id, str) else ""
        if not cleaned:
            raise ValueError("principal_id is required (fail-closed)")

        try:
            await self._promote_to_long_term(
                agent_id=agent_id,
                task_id=task_id,
                content=result,
                principal_id=cleaned,
            )
        except Exception as exc:
            logger.warning(
                "session_hooks.on_task_end.promotion_error",
                agent_id=agent_id,
                task_id=task_id,
                error=str(exc),
            )

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    async def _promote_to_long_term(
        self,
        *,
        agent_id: str,
        task_id: str,
        content: dict[str, Any],
        principal_id: str,
    ) -> None:
        """
        Promote task result to long-term memory via Domain Bridge.

        Builds a PacketEnvelope and submits through the gateway.
        """
        if self._bridge is None:
            return

        from core.schemas import PacketEnvelope, PacketMetadata

        packet = PacketEnvelope(
            packet_type="agent_task_result",
            payload={
                "task_id": task_id,
                "agent_id": agent_id,
                "result_summary": _summarize_result(content),
            },
            metadata=PacketMetadata(
                agent=agent_id,
                domain="l9",
            ).model_copy(
                update={
                    "source_system": "l9_session_hooks",
                    "promotion_reason": "high_value_result",
                }
            ),
        )

        await self._bridge.submit(
            packet,
            principal_id=principal_id,
            ingress_origin="session_hooks",
        )

        logger.info(
            "session_hooks.promoted_to_long_term",
            agent_id=agent_id,
            task_id=task_id,
            packet_id=str(packet.packet_id),
        )


# =============================================================================
# Module-level helpers
# =============================================================================


def _summarize_result(data: dict[str, Any], max_len: int = 500) -> dict[str, Any]:
    """Shrink a result dict for storage (no full payloads)."""
    summary: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            summary[key] = value[:max_len]
        elif isinstance(value, (int, float, bool)):
            summary[key] = value
        elif isinstance(value, (list, dict)):
            summary[key] = f"<{type(value).__name__} len={len(value)}>"
        else:
            summary[key] = str(type(value).__name__)
    return summary


def _should_promote(result: dict[str, Any]) -> bool:
    """Determine if a task result is worth promoting to long-term memory."""
    status = result.get("status", "")
    if status in ("success", "completed"):
        return True
    confidence = result.get("confidence", 0.0)
    return isinstance(confidence, (int, float)) and confidence >= 0.8


# =============================================================================
# Sorted public API
# =============================================================================

__all__ = [
    "BridgeGatewayProvider",
    "L9SessionHooks",
    "RetrievalProvider",
    "WorkingMemoryCacheProvider",
    "WorkingMemoryProvider",
]
