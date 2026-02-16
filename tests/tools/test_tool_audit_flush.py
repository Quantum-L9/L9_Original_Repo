"""
L9 Tool Audit — Flush Resilience & Ordering Tests
===================================================

Regression tests for Bug 2: flush() lost audit entries on DB failure.

Root cause: Race condition between buffer copy-clear and log_execution()
interleaving. On DB failure, entries added during the write window were
lost or reordered when extend() prepended the failed batch.

Reference: L9 Bug Postmortem — 5 Root Causes (2026-02-12)

Author: L9 Engineering
Created: 2026-02-12
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

# ============================================================================
__dora_meta__ = {
    "component_name": "Tool Audit Flush Tests",
    "module_version": "1.0.0",
    "created_by": "L9 Engineering",
    "created_at": "2026-02-12T03:41:00Z",
    "updated_at": "2026-02-12T03:41:00Z",
    "layer": "testing",
    "domain": "tool_registry",
    "module_name": "test_tool_audit_flush",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL"],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================


def _make_entry(tool_name: str):
    """Create a minimal ToolAuditEntry for testing."""
    from core.tools.tool_audit import ToolAuditEntry

    return ToolAuditEntry(
        tool_name=tool_name,
        agent_id="test-agent",
        input_data={"key": "value"},
        output_data={"result": "ok"},
        duration_ms=10.0,
    )


def _make_mock_substrate(*, fail_db: bool = False) -> MagicMock:
    """Build a mock MemorySubstrateService with optional DB failure."""
    substrate = MagicMock()

    pool = MagicMock()
    conn = AsyncMock()

    if fail_db:
        conn.executemany = AsyncMock(side_effect=RuntimeError("DB write failed"))
    else:
        conn.executemany = AsyncMock(return_value=None)

    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    substrate.postgres_pool = pool
    return substrate


# ---------------------------------------------------------------------------
# Bug 2 regression: flush failure must preserve entries + ordering
# ---------------------------------------------------------------------------


class TestFlushFailurePreservesEntries:
    """On DB failure, all entries must be retained and ordering preserved."""

    @pytest.mark.asyncio
    async def test_flush_failure_retains_all_entries(self):
        """After a failed flush, all entries remain in the local buffer."""
        from core.tools.tool_audit import ToolAuditService

        substrate = _make_mock_substrate(fail_db=True)
        service = ToolAuditService(substrate, buffer_size=100)

        entry_1 = _make_entry("tool_alpha")
        entry_2 = _make_entry("tool_beta")
        await service.log_execution(entry_1)
        await service.log_execution(entry_2)

        assert len(service.local_buffer) == 2

        await service.flush()

        assert len(service.local_buffer) == 2, (
            f"Expected 2 entries after failed flush, got {len(service.local_buffer)}"
        )

    @pytest.mark.asyncio
    async def test_flush_failure_preserves_ordering(self):
        """Failed entries must be prepended BEFORE any new entries added during failure."""
        from core.tools.tool_audit import ToolAuditService

        substrate = _make_mock_substrate(fail_db=True)
        service = ToolAuditService(substrate, buffer_size=100)

        entry_1 = _make_entry("first")
        entry_2 = _make_entry("second")
        await service.log_execution(entry_1)
        await service.log_execution(entry_2)

        await service.flush()

        entry_3 = _make_entry("third")
        await service.log_execution(entry_3)

        names = [e.tool_name for e in service.local_buffer]
        assert names == ["first", "second", "third"], (
            f"Ordering violated: {names}. "
            "Failed entries must be prepended before new arrivals."
        )

    @pytest.mark.asyncio
    async def test_successful_flush_clears_buffer(self):
        """A successful flush must leave the buffer empty."""
        from core.tools.tool_audit import ToolAuditService

        substrate = _make_mock_substrate(fail_db=False)
        service = ToolAuditService(substrate, buffer_size=100)

        await service.log_execution(_make_entry("tool_a"))
        await service.log_execution(_make_entry("tool_b"))

        await service.flush()

        assert len(service.local_buffer) == 0, (
            "Buffer must be empty after successful flush"
        )

    @pytest.mark.asyncio
    async def test_empty_buffer_flush_is_noop(self):
        """Flushing an empty buffer must not raise or produce DB calls."""
        from core.tools.tool_audit import ToolAuditService

        substrate = _make_mock_substrate(fail_db=False)
        service = ToolAuditService(substrate, buffer_size=100)

        await service.flush()

        substrate.postgres_pool.acquire.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrent_flush_and_log_no_entry_loss(self):
        """Concurrent flush() and log_execution() must not lose entries."""
        from core.tools.tool_audit import ToolAuditService

        substrate = _make_mock_substrate(fail_db=False)
        service = ToolAuditService(substrate, buffer_size=1000)

        for i in range(10):
            await service.log_execution(_make_entry(f"pre_{i}"))

        async def writer():
            for i in range(10):
                await service.log_execution(_make_entry(f"concurrent_{i}"))
                await asyncio.sleep(0)

        await asyncio.gather(service.flush(), writer())

        db_calls = substrate.postgres_pool.acquire.return_value.__aenter__.return_value.executemany
        total_flushed = (
            sum(len(call.args[1]) for call in db_calls.call_args_list)
            if db_calls.call_args_list
            else 0
        )
        total_buffered = len(service.local_buffer)

        assert total_flushed + total_buffered == 20, (
            f"Entry loss detected: flushed={total_flushed}, "
            f"buffered={total_buffered}, expected total=20"
        )
