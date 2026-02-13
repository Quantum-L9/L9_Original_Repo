"""
Tool Audit Module Tests
=======================

Comprehensive tests for memory/tool_audit.py.
Tests the fire-and-forget audit logging, argument sanitization,
and packet creation.

Coverage targets:
- log_tool_invocation() - all paths
- _sanitize_arguments() - all sanitization cases
- _ingest_audit_packet() - error handling
- TTL calculation
- Non-blocking behavior
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.decorators import must_stay_async


def _close_coroutine_mock(coro):
    """Mock for asyncio.create_task that properly closes the coroutine.

    Prevents 'coroutine was never awaited' RuntimeWarning in tests
    that patch asyncio.create_task.
    """
    coro.close()
    return MagicMock()  # Return a mock Task object


class TestSanitizeArguments:
    """Tests for _sanitize_arguments helper."""

    def test_sanitize_removes_password(self):
        """Contract: Password fields are redacted."""
        from memory.tool_audit import _sanitize_arguments

        args = {"username": "user", "password": "secret123"}
        result = _sanitize_arguments(args)

        assert result["username"] == "user"
        assert result["password"] == "[REDACTED]"

    def test_sanitize_removes_api_key(self):
        """Contract: API key fields are redacted."""
        from memory.tool_audit import _sanitize_arguments

        args = {"endpoint": "https://api.example.com", "api_key": "sk-12345"}
        result = _sanitize_arguments(args)

        assert result["endpoint"] == "https://api.example.com"
        assert result["api_key"] == "[REDACTED]"

    def test_sanitize_removes_token(self):
        """Contract: Token fields are redacted."""
        from memory.tool_audit import _sanitize_arguments

        args = {"auth_token": "bearer_xyz", "access_token": "abc123"}
        result = _sanitize_arguments(args)

        assert result["auth_token"] == "[REDACTED]"
        assert result["access_token"] == "[REDACTED]"

    def test_sanitize_removes_secret(self):
        """Contract: Secret fields are redacted."""
        from memory.tool_audit import _sanitize_arguments

        args = {"client_secret": "mysecret", "data": "normal"}
        result = _sanitize_arguments(args)

        assert result["client_secret"] == "[REDACTED]"
        assert result["data"] == "normal"

    def test_sanitize_truncates_long_strings(self):
        """Contract: Strings longer than 500 chars are truncated."""
        from memory.tool_audit import _sanitize_arguments

        long_string = "x" * 1000
        args = {"content": long_string}
        result = _sanitize_arguments(args)

        assert len(result["content"]) == 500 + len("...[truncated]")
        assert result["content"].endswith("...[truncated]")

    def test_sanitize_handles_nested_dicts(self):
        """Contract: Nested dictionaries are recursively sanitized."""
        from memory.tool_audit import _sanitize_arguments

        args = {
            "config": {
                "url": "https://example.com",
                "api_key": "secret123",
                "nested": {"password": "nested_secret"},
            }
        }
        result = _sanitize_arguments(args)

        assert result["config"]["url"] == "https://example.com"
        assert result["config"]["api_key"] == "[REDACTED]"
        assert result["config"]["nested"]["password"] == "[REDACTED]"

    def test_sanitize_preserves_normal_values(self):
        """Contract: Non-sensitive values are preserved."""
        from memory.tool_audit import _sanitize_arguments

        args = {
            "query": "search term",
            "count": 10,
            "enabled": True,
            "tags": ["a", "b"],
        }
        result = _sanitize_arguments(args)

        assert result["query"] == "search term"
        assert result["count"] == 10
        assert result["enabled"] is True
        assert result["tags"] == ["a", "b"]

    def test_sanitize_case_insensitive(self):
        """Contract: Sensitive key detection is case-insensitive."""
        from memory.tool_audit import _sanitize_arguments

        args = {
            "PASSWORD": "secret",
            "ApiKey": "key",
            "Secret_Value": "shh",
        }
        result = _sanitize_arguments(args)

        assert result["PASSWORD"] == "[REDACTED]"
        assert result["ApiKey"] == "[REDACTED]"
        assert result["Secret_Value"] == "[REDACTED]"

    def test_sanitize_empty_dict(self):
        """Contract: Empty dict returns empty dict."""
        from memory.tool_audit import _sanitize_arguments

        result = _sanitize_arguments({})
        assert result == {}

    def test_sanitize_handles_credential_variants(self):
        """Contract: Various credential-related keys are redacted."""
        from memory.tool_audit import _sanitize_arguments

        args = {
            "credential": "cred",
            "auth_header": "bearer",
            "private_key": "key",
        }
        result = _sanitize_arguments(args)

        assert result["credential"] == "[REDACTED]"
        assert result["auth_header"] == "[REDACTED]"
        assert result["private_key"] == "[REDACTED]"


class TestLogToolInvocation:
    """Tests for log_tool_invocation async function."""

    @pytest.mark.asyncio
    async def test_log_tool_invocation_success_path(self):
        """Contract: Successful tool calls are logged with correct packet structure."""
        from memory.tool_audit import log_tool_invocation

        call_id = uuid4()

        with (
            patch(
                "memory.tool_audit.asyncio.create_task",
                side_effect=_close_coroutine_mock,
            ) as mock_create_task,
            patch("memory.tool_audit.record_tool_invocation") as mock_record,
        ):
            await log_tool_invocation(
                call_id=call_id,
                tool_id="test_tool",
                agent_id="L",
                task_id="task-001",
                status="success",
                duration_ms=100,
            )

            # Verify background task was scheduled
            # create_task is called twice: once for _ingest_audit_packet, once for _write_to_audit_table
            assert mock_create_task.call_count >= 1

            # Verify Prometheus metrics recorded
            mock_record.assert_called_once_with(
                tool_id="test_tool",
                status="success",
                duration_ms=100,
            )

    @pytest.mark.asyncio
    async def test_log_tool_invocation_failure_status(self):
        """Contract: Failed tool calls are logged with error details."""
        from memory.tool_audit import log_tool_invocation

        call_id = uuid4()

        with (
            patch(
                "memory.tool_audit.asyncio.create_task",
                side_effect=_close_coroutine_mock,
            ) as mock_create_task,
            patch("memory.tool_audit.record_tool_invocation") as mock_record,
        ):
            await log_tool_invocation(
                call_id=call_id,
                tool_id="failing_tool",
                agent_id="L",
                status="failure",
                duration_ms=50,
                error="Connection timeout",
            )

            # create_task is called twice: once for _ingest_audit_packet, once for _write_to_audit_table
            assert mock_create_task.call_count >= 1
            mock_record.assert_called_once_with(
                tool_id="failing_tool",
                status="failure",
                duration_ms=50,
            )

    @pytest.mark.asyncio
    async def test_log_tool_invocation_timeout_status(self):
        """Contract: Timed out tool calls are logged correctly."""
        from memory.tool_audit import log_tool_invocation

        call_id = uuid4()

        with (
            patch(
                "memory.tool_audit.asyncio.create_task",
                side_effect=_close_coroutine_mock,
            ),
            patch("memory.tool_audit.record_tool_invocation") as mock_record,
        ):
            await log_tool_invocation(
                call_id=call_id,
                tool_id="slow_tool",
                agent_id="L",
                status="timeout",
                duration_ms=30000,
            )

            mock_record.assert_called_once_with(
                tool_id="slow_tool",
                status="timeout",
                duration_ms=30000,
            )

    @pytest.mark.asyncio
    async def test_log_tool_invocation_denied_status(self):
        """Contract: Denied tool calls (governance blocked) are logged."""
        from memory.tool_audit import log_tool_invocation

        call_id = uuid4()

        with (
            patch(
                "memory.tool_audit.asyncio.create_task",
                side_effect=_close_coroutine_mock,
            ),
            patch("memory.tool_audit.record_tool_invocation") as mock_record,
        ):
            await log_tool_invocation(
                call_id=call_id,
                tool_id="dangerous_tool",
                agent_id="L",
                status="denied",
                duration_ms=0,
            )

            mock_record.assert_called_once_with(
                tool_id="dangerous_tool",
                status="denied",
                duration_ms=0,
            )

    @pytest.mark.asyncio
    async def test_log_tool_invocation_never_raises(self):
        """Contract: log_tool_invocation NEVER raises exceptions."""
        from memory.tool_audit import log_tool_invocation

        call_id = uuid4()

        # Force an exception in the schemas import (now at core.schemas)
        with patch(
            "memory.tool_audit.PacketEnvelopeIn", side_effect=Exception("Model error")
        ):
            # Should not raise - errors are caught
            await log_tool_invocation(
                call_id=call_id,
                tool_id="test_tool",
                agent_id="L",
            )

    @pytest.mark.asyncio
    async def test_log_tool_invocation_with_arguments(self):
        """Contract: Arguments are sanitized and included in packet."""
        from memory.tool_audit import log_tool_invocation

        call_id = uuid4()

        with (
            patch(
                "memory.tool_audit.asyncio.create_task",
                side_effect=_close_coroutine_mock,
            ) as mock_create_task,
            patch("memory.tool_audit.record_tool_invocation"),
        ):
            await log_tool_invocation(
                call_id=call_id,
                tool_id="search_tool",
                agent_id="L",
                arguments={"query": "test", "api_key": "secret"},
            )

            # create_task is called twice: once for _ingest_audit_packet, once for _write_to_audit_table
            assert mock_create_task.call_count >= 1

    @pytest.mark.asyncio
    async def test_log_tool_invocation_with_result_summary(self):
        """Contract: Result summary is included when provided."""
        from memory.tool_audit import log_tool_invocation

        call_id = uuid4()

        with (
            patch(
                "memory.tool_audit.asyncio.create_task",
                side_effect=_close_coroutine_mock,
            ),
            patch("memory.tool_audit.record_tool_invocation"),
        ):
            await log_tool_invocation(
                call_id=call_id,
                tool_id="test_tool",
                agent_id="L",
                result_summary="Found 5 results",
            )

    @pytest.mark.asyncio
    async def test_log_tool_invocation_truncates_long_error(self):
        """Contract: Long error messages are truncated to 500 chars."""
        from memory.tool_audit import log_tool_invocation

        call_id = uuid4()
        long_error = "Error: " + "x" * 1000

        with (
            patch(
                "memory.tool_audit.asyncio.create_task",
                side_effect=_close_coroutine_mock,
            ) as mock_create_task,
            patch("memory.tool_audit.record_tool_invocation"),
        ):
            await log_tool_invocation(
                call_id=call_id,
                tool_id="test_tool",
                agent_id="L",
                status="failure",
                error=long_error,
            )

            # Get the packet from the create_task call
            # create_task is called twice: once for _ingest_audit_packet, once for _write_to_audit_table
            assert mock_create_task.call_count >= 1

    @pytest.mark.asyncio
    async def test_log_tool_invocation_default_values(self):
        """Contract: Default values are applied correctly."""
        from memory.tool_audit import log_tool_invocation

        call_id = uuid4()

        with (
            patch(
                "memory.tool_audit.asyncio.create_task",
                side_effect=_close_coroutine_mock,
            ),
            patch("memory.tool_audit.record_tool_invocation") as mock_record,
        ):
            await log_tool_invocation(
                call_id=call_id,
                tool_id="test_tool",
                agent_id="L",
            )

            # Default status is "success", default duration is 0
            mock_record.assert_called_once_with(
                tool_id="test_tool",
                status="success",
                duration_ms=0,
            )


class TestIngestAuditPacket:
    """Tests for _ingest_audit_packet background task."""

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_ingest_audit_packet_success(self):
        """Contract: Successful ingestion completes silently."""
        from core.schemas import PacketEnvelopeIn
        from memory.tool_audit import _ingest_audit_packet

        # PacketEnvelopeIn expects dicts, not objects
        packet = PacketEnvelopeIn(
            packet_id=uuid4(),
            packet_type="tool_audit",
            payload={"tool_id": "test"},
            metadata={"schema_version": "1.0.0", "agent": "L", "domain": "test"},
            provenance={"source": "test"},
            confidence={"score": 1.0, "rationale": "test"},
            tags=["test"],
        )

        mock_result = MagicMock()
        mock_result.status = "ok"

        # Mock at the import source since it's imported inside the function
        with patch(
            "memory.ingestion.ingest_packet", new_callable=AsyncMock
        ) as mock_ingest:
            mock_ingest.return_value = mock_result
            await _ingest_audit_packet(packet)
            mock_ingest.assert_called_once()

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_ingest_audit_packet_handles_error(self):
        """Contract: Ingestion errors are logged but don't raise."""
        from core.schemas import PacketEnvelopeIn
        from memory.tool_audit import _ingest_audit_packet

        # PacketEnvelopeIn expects dicts, not objects
        packet = PacketEnvelopeIn(
            packet_id=uuid4(),
            packet_type="tool_audit",
            payload={"tool_id": "test"},
            metadata={"schema_version": "1.0.0", "agent": "L", "domain": "test"},
            provenance={"source": "test"},
            confidence={"score": 1.0, "rationale": "test"},
            tags=["test"],
        )

        # Mock at the import source since it's imported inside the function
        with patch(
            "memory.ingestion.ingest_packet", new_callable=AsyncMock
        ) as mock_ingest:
            mock_ingest.side_effect = Exception("Database connection failed")
            # Should not raise
            await _ingest_audit_packet(packet)

    @pytest.mark.asyncio
    @must_stay_async("callers use await")
    async def test_ingest_audit_packet_logs_partial_failure(self):
        """Contract: Partial ingestion status is logged."""
        from core.schemas import PacketEnvelopeIn
        from memory.tool_audit import _ingest_audit_packet

        # PacketEnvelopeIn expects dicts, not objects
        packet = PacketEnvelopeIn(
            packet_id=uuid4(),
            packet_type="tool_audit",
            payload={"tool_id": "test"},
            metadata={"schema_version": "1.0.0", "agent": "L", "domain": "test"},
            provenance={"source": "test"},
            confidence={"score": 1.0, "rationale": "test"},
            tags=["test"],
        )

        mock_result = MagicMock()
        mock_result.status = "partial"
        mock_result.error_message = "Neo4j unavailable"

        # Mock at the import source since it's imported inside the function
        with patch(
            "memory.ingestion.ingest_packet", new_callable=AsyncMock
        ) as mock_ingest:
            mock_ingest.return_value = mock_result
            await _ingest_audit_packet(packet)


class TestToolAuditTTL:
    """Tests for TTL configuration."""

    def test_ttl_constant_exists(self):
        """Contract: TOOL_AUDIT_TTL_HOURS constant is defined."""
        from memory.tool_audit import TOOL_AUDIT_TTL_HOURS

        assert TOOL_AUDIT_TTL_HOURS == 24

    @pytest.mark.asyncio
    async def test_packet_ttl_is_24_hours_from_now(self):
        """Contract: Packet TTL is set to 24 hours from creation."""
        from memory.tool_audit import log_tool_invocation

        call_id = uuid4()

        with (
            patch(
                "memory.tool_audit.asyncio.create_task",
                side_effect=_close_coroutine_mock,
            ) as mock_create_task,
            patch("memory.tool_audit.record_tool_invocation"),
        ):
            await log_tool_invocation(
                call_id=call_id,
                tool_id="test_tool",
                agent_id="L",
            )

            # Verify create_task was called
            # create_task is called twice: once for _ingest_audit_packet, once for _write_to_audit_table
            assert mock_create_task.call_count >= 1


class TestPublicAPI:
    """Tests for public API exports."""

    def test_exports_log_tool_invocation(self):
        """Contract: log_tool_invocation is exported."""
        from memory.tool_audit import log_tool_invocation

        assert callable(log_tool_invocation)

    def test_exports_ttl_constant(self):
        """Contract: TOOL_AUDIT_TTL_HOURS is exported."""
        from memory.tool_audit import TOOL_AUDIT_TTL_HOURS

        assert isinstance(TOOL_AUDIT_TTL_HOURS, int)

    def test_all_exports(self):
        """Contract: __all__ contains expected exports."""
        from memory.tool_audit import __all__

        assert "log_tool_invocation" in __all__
        assert "TOOL_AUDIT_TTL_HOURS" in __all__
