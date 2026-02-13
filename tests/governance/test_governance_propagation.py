"""
L9 Governance — Context Propagation & Boundary Tests
=====================================================

Validates that governance context (ContextVar-based) propagates correctly
across async boundaries and fails explicitly when missing.

Root cause from Slack incident (2026-02-12): L-CTO tool-invoked memory
write failed because governance context did not propagate into the
AgentExecutorService tool execution boundary.

Author: L9 Engineering
Created: 2026-02-12
"""

from __future__ import annotations

import asyncio
from contextvars import copy_context

import pytest

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Governance Propagation Tests",
    "module_version": "1.0.0",
    "created_by": "L9 Engineering",
    "created_at": "2026-02-12T03:41:00Z",
    "updated_at": "2026-02-12T03:41:00Z",
    "layer": "testing",
    "domain": "governance",
    "module_name": "test_governance_propagation",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================


def _skip_if_no_governance():
    """Skip test if governance_gate module is not available."""
    try:
        from memory.governance_gate import governance_context

        return governance_context
    except ImportError:
        pytest.skip("governance_gate not available")


class TestGovernanceContextPropagation:
    """Governance ContextVar must propagate across async task boundaries."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_context_survives_asyncio_create_task(self):
        """ContextVar set before create_task must be readable inside the task."""
        gov_ctx = _skip_if_no_governance()
        from memory.governance_gate import MemoryGovernanceContext

        ctx = MemoryGovernanceContext(
            caller_id="test-agent",
            role="platform_admin",
            project_id="test-project",
            allowed_scopes=["memory", "developer"],
        )

        token = gov_ctx.set(ctx)
        captured = []

        async def inner_task():
            captured.append(gov_ctx.get(None))

        try:
            task = asyncio.create_task(inner_task())
            await task
        finally:
            gov_ctx.reset(token)

        assert captured[0] is not None, (
            "Governance context must propagate into asyncio.create_task(). "
            "If this fails, tool-invoked memory writes will lack governance."
        )
        assert captured[0].caller_id == "test-agent"

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_context_lost_in_thread_pool(self):
        """ContextVar does NOT propagate into run_in_executor (thread pool).
        This documents the known limitation."""
        gov_ctx = _skip_if_no_governance()
        from memory.governance_gate import MemoryGovernanceContext

        ctx = MemoryGovernanceContext(
            caller_id="test-agent",
            role="platform_admin",
            project_id="test-project",
            allowed_scopes=["memory"],
            scope="memory",
        )

        token = gov_ctx.set(ctx)
        captured = []

        def sync_worker():
            captured.append(gov_ctx.get(None))

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, sync_worker)
        finally:
            gov_ctx.reset(token)

        assert captured[0] is None, (
            "ContextVar unexpectedly propagated into thread pool. "
            "If now supported, update governance docs and remove workarounds."
        )

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_context_propagates_via_copy_context(self):
        """Using copy_context().run() DOES propagate ContextVar into threads."""
        gov_ctx = _skip_if_no_governance()
        from memory.governance_gate import MemoryGovernanceContext

        ctx = MemoryGovernanceContext(
            caller_id="test-agent",
            role="platform_admin",
            project_id="test-project",
            allowed_scopes=["memory"],
            scope="memory",
        )

        token = gov_ctx.set(ctx)
        captured = []

        def sync_worker():
            captured.append(gov_ctx.get(None))

        try:
            ctx_copy = copy_context()
            ctx_copy.run(sync_worker)
        finally:
            gov_ctx.reset(token)

        assert captured[0] is not None, (
            "copy_context().run() must propagate governance ContextVar"
        )

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_memory_write_without_governance_raises(self):
        """Memory write with no governance context must raise RuntimeError."""
        gov_ctx = _skip_if_no_governance()
        from memory.governance_gate import build_governance_context

        token = gov_ctx.set(None)

        try:
            with pytest.raises((RuntimeError, ValueError)):
                build_governance_context()
        finally:
            gov_ctx.reset(token)

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_governance_rejects_empty_caller_id(self):
        """MemoryGovernanceContext must reject empty caller_id at construction."""
        try:
            from memory.governance_gate import MemoryGovernanceContext
        except ImportError:
            pytest.skip("governance_gate not available")

        with pytest.raises((RuntimeError, ValueError)):
            MemoryGovernanceContext(
                caller_id="",
                role="platform_admin",
                project_id="test-project",
                allowed_scopes=["memory"],
            )
