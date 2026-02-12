"""
Unit Tests – Tool Audit Trail & Cost Tracking
===============================================

Tests for core/tools/tool_audit.py.

Covers:
- ToolAuditEntry: auto-generated timestamp and request_id
- ToolCostEstimator: cost calculation per tool
- ToolAuditService: buffered logging, flush, auto-flush lifecycle
- execute_tool_with_audit(): success + failure paths with feedback

Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.tools.tool_audit import (
    ToolAuditEntry,
    ToolAuditService,
    ToolCostEstimator,
    execute_tool_with_audit,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_substrate() -> MagicMock:
    """Mock MemorySubstrateService with postgres_pool."""
    substrate = MagicMock()
    substrate.postgres_pool = None  # No real Postgres by default
    return substrate


@pytest.fixture()
def audit_service(mock_substrate: MagicMock) -> ToolAuditService:
    """Create ToolAuditService with small buffer for testing."""
    return ToolAuditService(substrate_service=mock_substrate, buffer_size=3)


@pytest.fixture()
def mock_executor() -> MagicMock:
    """Mock tool executor that returns a dict."""
    executor = MagicMock()
    executor.call = AsyncMock(return_value={"result": "success", "data": [1, 2, 3]})
    return executor


# ---------------------------------------------------------------------------
# ToolAuditEntry
# ---------------------------------------------------------------------------


class TestToolAuditEntry:
    """Tests for audit entry auto-initialization."""

    def test_auto_generates_timestamp(self) -> None:
        entry = ToolAuditEntry(
            tool_name="memory_search",
            agent_id="agent-1",
            input_data={"query": "test"},
            output_data={"hits": []},
            duration_ms=42.5,
        )
        assert entry.timestamp is not None
        # Must be valid ISO format
        datetime.fromisoformat(entry.timestamp)

    def test_auto_generates_request_id(self) -> None:
        entry = ToolAuditEntry(
            tool_name="redis_get",
            agent_id="agent-2",
            input_data={},
            output_data={},
            duration_ms=1.0,
        )
        assert entry.request_id is not None
        assert len(entry.request_id) > 0

    def test_preserves_explicit_values(self) -> None:
        entry = ToolAuditEntry(
            tool_name="git_commit",
            agent_id="agent-3",
            input_data={},
            output_data={},
            duration_ms=100.0,
            timestamp="2026-01-01T00:00:00+00:00",
            request_id="explicit-id-123",
        )
        assert entry.timestamp == "2026-01-01T00:00:00+00:00"
        assert entry.request_id == "explicit-id-123"

    def test_default_cost_and_tokens(self) -> None:
        entry = ToolAuditEntry(
            tool_name="test",
            agent_id="a",
            input_data={},
            output_data={},
            duration_ms=0.0,
        )
        assert entry.tokens_used == 0
        assert entry.cost_usd == 0.0
        assert entry.error is None


# ---------------------------------------------------------------------------
# ToolCostEstimator
# ---------------------------------------------------------------------------


class TestToolCostEstimator:
    """Tests for tool cost estimation."""

    def test_known_tool_has_base_cost(self) -> None:
        estimator = ToolCostEstimator()
        cost = estimator.estimate("memory_search", {"query": "test"}, {"hits": []})
        assert cost > 0.0
        # memory_search base is 0.0005, token cost is additive
        assert cost >= 0.0005

    def test_unknown_tool_uses_default(self) -> None:
        estimator = ToolCostEstimator()
        cost = estimator.estimate("totally_unknown_tool_xyz", {}, {})
        # Default base cost is 0.001
        assert cost >= 0.001

    def test_larger_payload_costs_more(self) -> None:
        estimator = ToolCostEstimator()
        small = estimator.estimate("memory_write", {"data": "x"}, {"id": "1"})
        large = estimator.estimate(
            "memory_write",
            {"data": "x" * 1000},
            {"id": "1", "extra": list(range(100))},
        )
        assert large > small


# ---------------------------------------------------------------------------
# ToolAuditService – Buffered Logging
# ---------------------------------------------------------------------------


class TestToolAuditServiceBuffer:
    """Tests for buffered audit logging."""

    @pytest.mark.asyncio()
    async def test_log_execution_buffers(
        self, audit_service: ToolAuditService
    ) -> None:
        entry = ToolAuditEntry(
            tool_name="t", agent_id="a", input_data={}, output_data={}, duration_ms=1.0
        )
        await audit_service.log_execution(entry)
        assert len(audit_service.local_buffer) == 1

    @pytest.mark.asyncio()
    async def test_auto_flush_on_buffer_full(
        self, audit_service: ToolAuditService
    ) -> None:
        """Buffer flushes when buffer_size (3) is reached."""
        for i in range(3):
            entry = ToolAuditEntry(
                tool_name=f"t{i}",
                agent_id="a",
                input_data={},
                output_data={},
                duration_ms=1.0,
            )
            await audit_service.log_execution(entry)
        # Buffer should be cleared after flush
        assert len(audit_service.local_buffer) == 0

    @pytest.mark.asyncio()
    async def test_flush_empty_buffer_is_noop(
        self, audit_service: ToolAuditService
    ) -> None:
        assert len(audit_service.local_buffer) == 0
        await audit_service.flush()  # Must not raise
        assert len(audit_service.local_buffer) == 0

    @pytest.mark.asyncio()
    async def test_flush_retries_on_failure(
        self, audit_service: ToolAuditService, mock_substrate: MagicMock
    ) -> None:
        """If Postgres flush fails, entries are put back in the buffer."""
        # Set up a pool that raises
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.executemany = AsyncMock(side_effect=RuntimeError("DB down"))
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock()
        mock_substrate.postgres_pool = mock_pool

        entry = ToolAuditEntry(
            tool_name="t", agent_id="a", input_data={}, output_data={}, duration_ms=1.0
        )
        audit_service.local_buffer.append(entry)
        await audit_service.flush()
        # Entries should be returned to buffer on failure
        assert len(audit_service.local_buffer) >= 1


# ---------------------------------------------------------------------------
# ToolAuditService – Lifecycle
# ---------------------------------------------------------------------------


class TestToolAuditServiceLifecycle:
    """Tests for start/stop lifecycle."""

    @pytest.mark.asyncio()
    async def test_start_creates_flush_task(
        self, audit_service: ToolAuditService
    ) -> None:
        await audit_service.start()
        assert audit_service._flush_task is not None
        assert not audit_service._flush_task.done()
        await audit_service.stop()

    @pytest.mark.asyncio()
    async def test_stop_cancels_task_and_flushes(
        self, audit_service: ToolAuditService
    ) -> None:
        await audit_service.start()
        entry = ToolAuditEntry(
            tool_name="t", agent_id="a", input_data={}, output_data={}, duration_ms=1.0
        )
        audit_service.local_buffer.append(entry)
        await audit_service.stop()
        assert audit_service._flush_task.cancelled() or audit_service._flush_task.done()
        # Buffer should be flushed on stop
        assert len(audit_service.local_buffer) == 0


# ---------------------------------------------------------------------------
# execute_tool_with_audit – Success Path
# ---------------------------------------------------------------------------


class TestExecuteToolWithAuditSuccess:
    """Tests for audit-wrapped tool execution on success."""

    @pytest.mark.asyncio()
    async def test_returns_tool_output(
        self,
        audit_service: ToolAuditService,
        mock_executor: MagicMock,
        mock_substrate: MagicMock,
    ) -> None:
        with patch(
            "core.tools.tool_audit.get_tool_feedback_service",
            return_value=MagicMock(record_outcome=AsyncMock()),
        ):
            result = await execute_tool_with_audit(
                tool_name="memory_search",
                agent_id="agent-1",
                input_data={"query": "test"},
                executor=mock_executor,
                audit_service=audit_service,
                substrate_service=mock_substrate,
            )
        assert result == {"result": "success", "data": [1, 2, 3]}

    @pytest.mark.asyncio()
    async def test_logs_audit_entry_on_success(
        self,
        audit_service: ToolAuditService,
        mock_executor: MagicMock,
        mock_substrate: MagicMock,
    ) -> None:
        with patch(
            "core.tools.tool_audit.get_tool_feedback_service",
            return_value=MagicMock(record_outcome=AsyncMock()),
        ):
            await execute_tool_with_audit(
                tool_name="redis_get",
                agent_id="agent-2",
                input_data={"key": "k"},
                executor=mock_executor,
                audit_service=audit_service,
                substrate_service=mock_substrate,
            )
        assert len(audit_service.local_buffer) == 1
        entry = audit_service.local_buffer[0]
        assert entry.tool_name == "redis_get"
        assert entry.error is None
        assert entry.duration_ms > 0


# ---------------------------------------------------------------------------
# execute_tool_with_audit – Failure Path
# ---------------------------------------------------------------------------


class TestExecuteToolWithAuditFailure:
    """Tests for audit-wrapped tool execution on failure."""

    @pytest.mark.asyncio()
    async def test_raises_and_logs_error(
        self,
        audit_service: ToolAuditService,
        mock_substrate: MagicMock,
    ) -> None:
        failing_executor = MagicMock()
        failing_executor.call = AsyncMock(side_effect=RuntimeError("Tool exploded"))

        with (
            patch(
                "core.tools.tool_audit.get_tool_feedback_service",
                return_value=MagicMock(record_outcome=AsyncMock()),
            ),
            pytest.raises(RuntimeError, match="Tool exploded"),
        ):
            await execute_tool_with_audit(
                tool_name="bad_tool",
                agent_id="agent-3",
                input_data={},
                executor=failing_executor,
                audit_service=audit_service,
                substrate_service=mock_substrate,
            )
        assert len(audit_service.local_buffer) == 1
        entry = audit_service.local_buffer[0]
        assert entry.tool_name == "bad_tool"
        assert entry.error == "Tool exploded"
        assert entry.duration_ms > 0
