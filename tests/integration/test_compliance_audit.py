"""
L9 Integration Tests - Compliance Audit (GMP-21)
==================================================

Tests for audit logging, compliance reporting, and export.

Version: 1.0.0
"""

from datetime import timezone, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAuditLogger:
    """Test audit logger functionality."""

    @pytest.mark.asyncio
    async def test_log_command_without_substrate(self):
        """Test logging command without substrate (console only)."""
        from core.compliance.audit_log import AuditLogger

        logger = AuditLogger(substrate_service=None)

        result = await logger.log_command(
            command_id="cmd-001",
            command_type="analyze",
            user_id="Igor",
            action="execute",
            risk_level="low",
            raw_text="@L analyze codebase",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_approval_without_substrate(self):
        """Test logging approval without substrate."""
        from core.compliance.audit_log import AuditLogger

        logger = AuditLogger(substrate_service=None)

        result = await logger.log_approval(
            task_id="task-001",
            approved_by="Igor",
            approved=True,
            reason="Looks good",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_tool_execution_without_substrate(self):
        """Test logging tool execution without substrate."""
        from core.compliance.audit_log import AuditLogger

        logger = AuditLogger(substrate_service=None)

        result = await logger.log_tool_execution(
            tool_name="memory_write",
            agent_id="L",
            input_data={"segment": "test"},
            output_data={"success": True},
            success=True,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_log_memory_write_without_substrate(self):
        """Test logging memory write without substrate returns False (GMP-68)."""
        from core.compliance.audit_log import AuditLogger

        logger = AuditLogger(substrate_service=None)

        result = await logger.log_memory_write(
            agent_id="L",
            segment="governance_patterns",
            content_type="pattern",
            size_bytes=1024,
        )

        # GMP-68: Return False when substrate is None (audit was not logged)
        assert result is False

    @pytest.mark.asyncio
    async def test_log_command_with_substrate(self):
        """Test logging command with mock substrate."""
        from core.compliance.audit_log import AuditLogger

        # Mock substrate
        mock_substrate = AsyncMock()
        mock_substrate.write_packet = AsyncMock(return_value=True)

        logger = AuditLogger(substrate_service=mock_substrate)

        with patch.dict("sys.modules", {"memory.substrate_models": MagicMock()}):
            result = await logger.log_command(
                command_id="cmd-002",
                command_type="propose_gmp",
                user_id="Igor",
                action="execute",
                risk_level="high",
                raw_text="@L propose gmp: add feature",
            )

        # Should call write_packet
        assert mock_substrate.write_packet.called or result is True


class TestComplianceReport:
    """Test compliance report dataclass."""

    def test_report_creation(self):
        """Test creating a compliance report."""
        from core.compliance.audit_reporter import ComplianceReport

        report = ComplianceReport(
            total_commands=10,
            total_tool_calls=25,
            total_approvals=8,
            total_rejections=2,
            total_memory_writes=50,
        )

        assert report.total_commands == 10
        assert report.total_tool_calls == 25
        assert report.total_approvals == 8
        assert report.total_rejections == 2

    def test_report_to_dict(self):
        """Test report serialization."""
        from core.compliance.audit_reporter import ComplianceReport

        report = ComplianceReport(
            total_commands=5,
            total_tool_calls=10,
            total_approvals=3,
            total_rejections=1,
            unapproved_high_risk_calls=2,
            violations=[
                {"type": "unapproved_high_risk", "tool_name": "gmprun"},
            ],
        )

        data = report.to_dict()

        assert data["summary"]["total_commands"] == 5
        assert data["violations"]["unapproved_high_risk_calls"] == 2
        assert len(data["violations"]["details"]) == 1


class TestComplianceReporter:
    """Test compliance reporter functionality."""

    @pytest.mark.asyncio
    async def test_generate_daily_report_without_substrate(self):
        """Test generating daily report without substrate."""
        from core.compliance.audit_reporter import ComplianceReporter

        reporter = ComplianceReporter(substrate_service=None)

        report = await reporter.generate_daily_report()

        assert report is not None
        assert report.total_commands == 0  # No substrate, no data

    @pytest.mark.asyncio
    async def test_generate_report_with_mock_data(self):
        """Test generating report with mock audit data."""
        from core.compliance.audit_reporter import ComplianceReporter

        # Mock substrate with sample data
        mock_substrate = AsyncMock()

        now = datetime.now(timezone.utc)

        # Mock command entries
        mock_substrate.search_packets_by_type = AsyncMock(
            side_effect=[
                # Commands
                [
                    {
                        "payload": {
                            "audit_type": "command",
                            "command_type": "analyze",
                            "timestamp": now.isoformat(),
                        }
                    },
                ],
                # Tool calls
                [
                    {
                        "payload": {
                            "audit_type": "tool_execution",
                            "tool_name": "memory_write",
                            "execution_timestamp": now.isoformat(),
                            "success": True,
                        }
                    },
                    {
                        "payload": {
                            "audit_type": "tool_execution",
                            "tool_name": "gmprun",
                            "execution_timestamp": now.isoformat(),
                            "success": True,
                            "approved_by": "Igor",
                        }
                    },
                ],
                # Approvals
                [
                    {
                        "payload": {
                            "audit_type": "approval",
                            "approved": True,
                            "timestamp": now.isoformat(),
                        }
                    },
                ],
                # Memory writes
                [
                    {
                        "payload": {
                            "audit_type": "memory_write",
                            "segment": "governance_patterns",
                            "timestamp": now.isoformat(),
                        }
                    },
                ],
            ]
        )

        reporter = ComplianceReporter(substrate_service=mock_substrate)

        report = await reporter.generate_daily_report(date=now)

        assert report.total_commands == 1
        assert report.total_tool_calls == 2
        assert report.total_approvals == 1
        assert report.total_memory_writes == 1

    @pytest.mark.asyncio
    async def test_detect_unapproved_high_risk(self):
        """Test detection of unapproved high-risk tool calls."""
        from core.compliance.audit_reporter import ComplianceReporter

        mock_substrate = AsyncMock()
        now = datetime.now(timezone.utc)

        # Mock with unapproved gmprun
        mock_substrate.search_packets_by_type = AsyncMock(
            side_effect=[
                # Commands
                [],
                # Tool calls - unapproved gmprun
                [
                    {
                        "payload": {
                            "audit_type": "tool_execution",
                            "tool_name": "gmprun",
                            "execution_timestamp": now.isoformat(),
                            "success": True,
                            "approved_by": None,  # NO APPROVAL
                            "agent_id": "L",
                        }
                    },
                ],
                # Approvals
                [],
                # Memory writes
                [],
            ]
        )

        reporter = ComplianceReporter(substrate_service=mock_substrate)
        report = await reporter.generate_daily_report(date=now)

        assert report.unapproved_high_risk_calls == 1
        assert len(report.violations) == 1
        assert report.violations[0]["type"] == "unapproved_high_risk"
        assert report.violations[0]["tool_name"] == "gmprun"

    @pytest.mark.asyncio
    async def test_export_audit_log(self):
        """Test exporting audit log."""
        from core.compliance.audit_reporter import ComplianceReporter

        mock_substrate = AsyncMock()
        now = datetime.now(timezone.utc)

        mock_substrate.search_packets_by_type = AsyncMock(
            return_value=[
                {
                    "payload": {
                        "audit_type": "command",
                        "timestamp": now.isoformat(),
                    }
                }
            ]
        )

        reporter = ComplianceReporter(substrate_service=mock_substrate)

        entries = await reporter.export_audit_log(
            from_date=now - timedelta(days=1),
            to_date=now + timedelta(days=1),
        )

        # Should return entries from all packet types queried
        assert isinstance(entries, list)


class TestDateRangeFiltering:
    """Test date range filtering in reporter."""

    def test_in_date_range_valid(self):
        """Test valid timestamp in range."""
        from core.compliance.audit_reporter import ComplianceReporter

        reporter = ComplianceReporter()

        now = datetime.now(timezone.utc)
        from_date = now - timedelta(hours=1)
        to_date = now + timedelta(hours=1)

        assert (
            reporter._in_date_range(
                now.isoformat(),
                from_date,
                to_date,
            )
            is True
        )

    def test_in_date_range_before(self):
        """Test timestamp before range."""
        from core.compliance.audit_reporter import ComplianceReporter

        reporter = ComplianceReporter()

        now = datetime.now(timezone.utc)
        from_date = now + timedelta(hours=1)
        to_date = now + timedelta(hours=2)

        assert (
            reporter._in_date_range(
                now.isoformat(),
                from_date,
                to_date,
            )
            is False
        )

    def test_in_date_range_empty(self):
        """Test empty timestamp."""
        from core.compliance.audit_reporter import ComplianceReporter

        reporter = ComplianceReporter()

        now = datetime.now(timezone.utc)

        assert (
            reporter._in_date_range(
                "",
                now - timedelta(hours=1),
                now + timedelta(hours=1),
            )
            is False
        )


class TestAuditLoggerConvenience:
    """Test audit logger convenience functions."""

    @pytest.mark.asyncio
    async def test_log_command_to_audit(self):
        """Test convenience function for logging commands."""
        from core.compliance.audit_log import log_command_to_audit

        mock_substrate = AsyncMock()
        mock_substrate.write_packet = AsyncMock(return_value=True)

        with patch.dict("sys.modules", {"memory.substrate_models": MagicMock()}):
            result = await log_command_to_audit(
                substrate_service=mock_substrate,
                command_id="cmd-convenience-001",
                command_type="analyze",
                user_id="Igor",
                action="execute",
                risk_level="low",
                raw_text="@L analyze",
            )

        assert result is True or mock_substrate.write_packet.called
