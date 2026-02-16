"""
L9 Compliance - Audit Reporter
===============================

Generates compliance reports from audit trail data.

Version: 1.0.0 (GMP-21)
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Audit Reporter",
    "module_version": "1.0.0 (GMP-21)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "audit_reporter",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [
            "api.routes.compliance",
            "tests.integration.test_compliance_audit",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import structlog

from core.governance.tool_risk_policy import get_high_risk_tools

logger = structlog.get_logger(__name__)


@dataclass
class ComplianceReport:
    """Compliance report for a time period."""

    report_id: UUID = field(default_factory=uuid4)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    from_date: datetime = field(default_factory=lambda: datetime.now(UTC))
    to_date: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Summary counts
    total_commands: int = 0
    total_tool_calls: int = 0
    total_approvals: int = 0
    total_rejections: int = 0
    total_memory_writes: int = 0

    # Violations
    unapproved_high_risk_calls: int = 0
    failed_tool_calls: int = 0
    violations: list[dict[str, Any]] = field(default_factory=list)

    # Details
    commands_by_type: dict[str, int] = field(default_factory=dict)
    tools_by_name: dict[str, int] = field(default_factory=dict)
    memory_writes_by_segment: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "report_id": str(self.report_id),
            "generated_at": self.generated_at.isoformat(),
            "period": {
                "from": self.from_date.isoformat(),
                "to": self.to_date.isoformat(),
            },
            "summary": {
                "total_commands": self.total_commands,
                "total_tool_calls": self.total_tool_calls,
                "total_approvals": self.total_approvals,
                "total_rejections": self.total_rejections,
                "total_memory_writes": self.total_memory_writes,
            },
            "violations": {
                "unapproved_high_risk_calls": self.unapproved_high_risk_calls,
                "failed_tool_calls": self.failed_tool_calls,
                "details": self.violations,
            },
            "breakdown": {
                "commands_by_type": self.commands_by_type,
                "tools_by_name": self.tools_by_name,
                "memory_writes_by_segment": self.memory_writes_by_segment,
            },
        }


class ComplianceReporter:
    """
    Generates compliance reports from audit trail.

    Queries audit log entries and aggregates into reports
    with violation detection.
    """

    # GMP-104: Tool risk classification loaded from config/policies/high_risk_tools.yaml
    HIGH_RISK_TOOLS = get_high_risk_tools()

    def __init__(self, substrate_service: Any | None = None):
        """
        Initialize ComplianceReporter.

        Args:
            substrate_service: Memory substrate for querying audit data
        """
        self._substrate = substrate_service

    async def generate_daily_report(
        self,
        date: datetime | None = None,
    ) -> ComplianceReport:
        """
        Generate a compliance report for a specific day.

        Args:
            date: Date to generate report for (defaults to today)

        Returns:
            ComplianceReport
        """
        date = date or datetime.now(UTC)
        from_date = datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=UTC)
        to_date = from_date + timedelta(days=1)

        return await self.generate_report(from_date, to_date)

    @must_stay_async("callers use await")
    async def generate_report(
        self,
        from_date: datetime,
        to_date: datetime,
    ) -> ComplianceReport:
        """
        Generate a compliance report for a date range.

        Args:
            from_date: Start of report period
            to_date: End of report period

        Returns:
            ComplianceReport
        """
        report = ComplianceReport(
            from_date=from_date,
            to_date=to_date,
        )

        if self._substrate is None:
            logger.warning("No substrate, returning empty report")
            return report

        try:
            # Query command audit entries
            await self._process_commands(report, from_date, to_date)

            # Query tool execution audit entries
            await self._process_tool_calls(report, from_date, to_date)

            # Query approval audit entries
            await self._process_approvals(report, from_date, to_date)

            # Query memory write audit entries
            await self._process_memory_writes(report, from_date, to_date)

            logger.info(
                "Compliance report generated",
                report_id=str(report.report_id),
                from_date=from_date.isoformat(),
                to_date=to_date.isoformat(),
            )

        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")

        return report

    async def _process_commands(
        self,
        report: ComplianceReport,
        from_date: datetime,
        to_date: datetime,
    ) -> None:
        """Process command audit entries."""
        try:
            entries = await self._substrate.search_packets_by_type(
                packet_type="audit_command",
                limit=1000,
            )

            for entry in entries:
                payload = entry.get("payload", {})
                timestamp_str = payload.get("timestamp", "")

                # Filter by date range
                if not self._in_date_range(timestamp_str, from_date, to_date):
                    continue

                report.total_commands += 1

                # Count by type
                cmd_type = payload.get("command_type", "unknown")
                report.commands_by_type[cmd_type] = (
                    report.commands_by_type.get(cmd_type, 0) + 1
                )

        except Exception as e:
            logger.warning(f"Failed to process commands: {e}")

    async def _process_tool_calls(
        self,
        report: ComplianceReport,
        from_date: datetime,
        to_date: datetime,
    ) -> None:
        """Process tool execution audit entries."""
        try:
            entries = await self._substrate.search_packets_by_type(
                packet_type="audit_tool",
                limit=1000,
            )

            for entry in entries:
                payload = entry.get("payload", {})
                timestamp_str = payload.get("execution_timestamp", "")

                # Filter by date range
                if not self._in_date_range(timestamp_str, from_date, to_date):
                    continue

                report.total_tool_calls += 1

                # Count by tool name
                tool_name = payload.get("tool_name", "unknown")
                report.tools_by_name[tool_name] = (
                    report.tools_by_name.get(tool_name, 0) + 1
                )

                # Track failures
                if not payload.get("success", True):
                    report.failed_tool_calls += 1

                # Check for unapproved high-risk calls
                if tool_name in self.HIGH_RISK_TOOLS:
                    if not payload.get("approved_by"):
                        report.unapproved_high_risk_calls += 1
                        report.violations.append(
                            {
                                "type": "unapproved_high_risk",
                                "tool_name": tool_name,
                                "timestamp": timestamp_str,
                                "agent_id": payload.get("agent_id"),
                            }
                        )

        except Exception as e:
            logger.warning(f"Failed to process tool calls: {e}")

    async def _process_approvals(
        self,
        report: ComplianceReport,
        from_date: datetime,
        to_date: datetime,
    ) -> None:
        """Process approval audit entries."""
        try:
            entries = await self._substrate.search_packets_by_type(
                packet_type="audit_approval",
                limit=1000,
            )

            for entry in entries:
                payload = entry.get("payload", {})
                timestamp_str = payload.get("timestamp", "")

                # Filter by date range
                if not self._in_date_range(timestamp_str, from_date, to_date):
                    continue

                if payload.get("approved", False):
                    report.total_approvals += 1
                else:
                    report.total_rejections += 1

        except Exception as e:
            logger.warning(f"Failed to process approvals: {e}")

    async def _process_memory_writes(
        self,
        report: ComplianceReport,
        from_date: datetime,
        to_date: datetime,
    ) -> None:
        """Process memory write audit entries."""
        try:
            entries = await self._substrate.search_packets_by_type(
                packet_type="audit_memory_write",
                limit=1000,
            )

            for entry in entries:
                payload = entry.get("payload", {})
                timestamp_str = payload.get("timestamp", "")

                # Filter by date range
                if not self._in_date_range(timestamp_str, from_date, to_date):
                    continue

                report.total_memory_writes += 1

                # Count by segment
                segment = payload.get("segment", "unknown")
                report.memory_writes_by_segment[segment] = (
                    report.memory_writes_by_segment.get(segment, 0) + 1
                )

        except Exception as e:
            logger.warning(f"Failed to process memory writes: {e}")

    def _in_date_range(
        self,
        timestamp_str: str,
        from_date: datetime,
        to_date: datetime,
    ) -> bool:
        """Check if timestamp is within date range."""
        if not timestamp_str:
            return False

        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return from_date <= timestamp.replace(tzinfo=None) < to_date
        except (ValueError, AttributeError):
            return False

    @must_stay_async("callers use await")
    async def export_audit_log(
        self,
        from_date: datetime,
        to_date: datetime,
        format: str = "json",
    ) -> list[dict[str, Any]]:
        """
        Export raw audit log entries for a date range.

        Args:
            from_date: Start of export period
            to_date: End of export period
            format: Export format (json or csv)

        Returns:
            List of audit entries
        """
        if self._substrate is None:
            return []

        all_entries = []

        # Query all audit types
        for packet_type in [
            "audit_command",
            "audit_tool",
            "audit_approval",
            "audit_memory_write",
        ]:
            try:
                entries = await self._substrate.search_packets_by_type(
                    packet_type=packet_type,
                    limit=1000,
                )

                for entry in entries:
                    payload = entry.get("payload", {})

                    # Get timestamp from various fields
                    timestamp_str = (
                        payload.get("timestamp")
                        or payload.get("execution_timestamp")
                        or ""
                    )

                    if self._in_date_range(timestamp_str, from_date, to_date):
                        all_entries.append(
                            {
                                "packet_type": packet_type,
                                "payload": payload,
                                "created_at": entry.get("created_at"),
                            }
                        )

            except Exception as e:
                logger.warning(f"Failed to export {packet_type}: {e}")

        # Sort by timestamp
        all_entries.sort(key=lambda x: x.get("payload", {}).get("timestamp", ""))

        return all_entries


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "ComplianceReport",
    "ComplianceReporter",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-065",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "audit-tool",
        "core",
        "dataclass",
        "foundation",
        "logging",
    ],
    "keywords": [
        "audit",
        "compliance",
        "daily",
        "export",
        "generate",
        "log",
        "report",
        "reporter",
    ],
    "business_value": "Provides audit reporter components including ComplianceReport, ComplianceReporter",
    "last_modified": "2026-01-07T13:35:57Z",
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
