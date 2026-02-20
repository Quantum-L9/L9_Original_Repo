"""
Invariant tests for L9SessionHooks (ADR-0092).

Tests:
  1. on_task_start() returns context dict with retrieval hits
  2. on_task_start() returns empty context when retrieval kernel absent
  3. on_tool_call() does not raise when working memory absent
  4. on_task_end() does not raise when bridge absent
  5. on_task_end() calls bridge.submit() when bridge present
  6. on_task_end() propagates principal_id to bridge
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# =============================================================================
# Fake Dependencies
# =============================================================================


class FakeRetrievalKernel:
    """Fake retrieval kernel."""

    async def retrieve(
        self,
        agent_id: str,
        query: str = "",
        thread_id: str | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        from memory.retrieval_kernel import RetrievalHit

        return [
            RetrievalHit(
                content="test hit",
                source_tier="working_memory",
                score=1.0,
                metadata={},
            )
        ]


class FakeWorkingMemory:
    """Fake working memory service."""

    async def update(
        self,
        repo_id: str,
        branch: str,
        *,
        principal_id: str | None = None,
        **kwargs: Any,
    ) -> Any:
        return MagicMock()


class FakeBridge:
    """Fake DomainBridgeGateway."""

    def __init__(self) -> None:
        self.submitted: list[dict[str, Any]] = []

    async def submit(
        self,
        packet: Any,
        *,
        principal_id: str,
        ingress_origin: str,
    ) -> Any:
        self.submitted.append(
            {
                "packet": packet,
                "principal_id": principal_id,
                "ingress_origin": ingress_origin,
            }
        )
        return MagicMock(status="ok")


# =============================================================================
# Tests
# =============================================================================


class TestL9SessionHooks:
    """Invariant tests for L9SessionHooks."""

    @pytest.fixture
    def hooks(self):
        from runtime.session_hooks import L9SessionHooks

        return L9SessionHooks(
            retrieval_kernel=FakeRetrievalKernel(),
            working_memory=FakeWorkingMemory(),
            bridge=FakeBridge(),
        )

    @pytest.fixture
    def bare_hooks(self):
        from runtime.session_hooks import L9SessionHooks

        return L9SessionHooks()

    @pytest.mark.asyncio
    async def test_on_task_start_returns_context(self, hooks: Any) -> None:
        """on_task_start() returns context dict with retrieval_hits."""
        ctx = await hooks.on_task_start(
            agent_id="test-agent",
            task_id="task-123",
            task_payload={"message": "find the DAG spec"},
        )
        assert isinstance(ctx, dict)
        assert "retrieval_hits" in ctx
        assert len(ctx["retrieval_hits"]) == 1

    @pytest.mark.asyncio
    async def test_on_task_start_empty_without_kernel(self, bare_hooks: Any) -> None:
        """on_task_start() returns empty context when no retrieval kernel."""
        ctx = await bare_hooks.on_task_start(
            agent_id="test-agent",
            task_id="task-123",
            task_payload={},
        )
        assert isinstance(ctx, dict)
        assert ctx.get("retrieval_hits", []) == []

    @pytest.mark.asyncio
    async def test_on_tool_call_no_raise_without_wm(self, bare_hooks: Any) -> None:
        """on_tool_call() does not raise when working memory absent."""
        # Should not raise
        await bare_hooks.on_tool_call(
            agent_id="test-agent",
            tool_id="test-tool",
            tool_result={"result": "ok", "success": True},
        )

    @pytest.mark.asyncio
    async def test_on_task_end_no_raise_without_bridge(self, bare_hooks: Any) -> None:
        """on_task_end() does not raise when bridge absent."""
        await bare_hooks.on_task_end(
            agent_id="test-agent",
            task_id="task-123",
            result={"status": "completed"},
        )

    @pytest.mark.asyncio
    async def test_on_task_end_calls_bridge(self, hooks: Any) -> None:
        """on_task_end() calls bridge.submit() when bridge present."""
        await hooks.on_task_end(
            agent_id="test-agent",
            task_id="task-123",
            result={"status": "completed", "result": "done"},
        )
        assert len(hooks._bridge.submitted) == 1
        submitted = hooks._bridge.submitted[0]
        assert submitted["ingress_origin"] == "session_hooks"

    @pytest.mark.asyncio
    async def test_on_task_end_propagates_principal(self, hooks: Any) -> None:
        """on_task_end() propagates principal_id to bridge."""
        await hooks.on_task_end(
            agent_id="test-agent",
            task_id="task-123",
            result={"status": "completed"},
            principal_id="user:test-user",
        )
        submitted = hooks._bridge.submitted[0]
        assert submitted["principal_id"] == "user:test-user"
