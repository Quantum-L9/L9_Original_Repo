"""
Violation Tracker Service Tests
================================

Unit tests for ViolationTrackerService.
Tests pattern matching, violation counting, and escalation logic.

GMP: GMP-Workers-Wiring
Phase: 4 (VALIDATE)
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workers.violation_tracker_service import (
    ViolationTrackerService,
    ViolationTrackerServiceRequest,
    ViolationTrackerServiceResponse,
    ViolationRecord,
)
from workers.violation_patterns import (
    ViolationPatterns,
    ViolationPatternsResponse,
    ViolationMatch,
    ViolationSeverity,
)


class TestViolationTrackerServiceInit:
    """Test ViolationTrackerService initialization."""

    def test_init_creates_pattern_matcher(self):
        """Service initializes with ViolationPatterns instance."""
        service = ViolationTrackerService()
        assert service._pattern_matcher is not None
        assert isinstance(service._pattern_matcher, ViolationPatterns)

    def test_init_with_custom_pattern_matcher(self):
        """Service accepts custom pattern matcher."""
        custom_matcher = ViolationPatterns()
        service = ViolationTrackerService(pattern_matcher=custom_matcher)
        assert service._pattern_matcher is custom_matcher

    def test_init_stats_zeroed(self):
        """Service starts with zero stats."""
        service = ViolationTrackerService()
        assert service._stats["total_scans"] == 0
        assert service._stats["total_violations"] == 0
        assert service._stats["escalations_triggered"] == 0

    def test_init_mcp_enabled_by_default(self):
        """MCP memory sync is enabled by default."""
        service = ViolationTrackerService()
        assert service._mcp_enabled is True

    def test_init_mcp_can_be_disabled(self):
        """MCP memory sync can be disabled."""
        service = ViolationTrackerService(mcp_enabled=False)
        assert service._mcp_enabled is False


class TestViolationCounting:
    """Test violation count tracking."""

    def test_get_violation_count_returns_zero_for_unknown(self):
        """Unknown lesson returns zero count."""
        service = ViolationTrackerService()
        assert service.get_violation_count("unknown-lesson") == 0

    def test_get_all_violation_counts_returns_copy(self):
        """get_all_violation_counts returns a copy."""
        service = ViolationTrackerService()
        service._violation_counts["test-lesson"] = 5
        counts = service.get_all_violation_counts()
        counts["test-lesson"] = 100
        assert service._violation_counts["test-lesson"] == 5

    def test_reset_violation_count_removes_lesson(self):
        """reset_violation_count removes the lesson from tracking."""
        service = ViolationTrackerService()
        service._violation_counts["test-lesson"] = 5
        service.reset_violation_count("test-lesson")
        assert "test-lesson" not in service._violation_counts


class TestViolationTrackerProcess:
    """Test ViolationTrackerService.process()."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked pattern matcher."""
        service = ViolationTrackerService(mcp_enabled=False)
        service._pattern_matcher = MagicMock()
        service._initialized = True
        return service

    @pytest.mark.asyncio
    async def test_process_returns_ok_on_no_violations(self, mock_service):
        """Process returns ok=True when no violations found."""
        # Mock pattern matcher to return no matches
        mock_service._pattern_matcher.process = AsyncMock(
            return_value=ViolationPatternsResponse(
                ok=True,
                request_id="test-123",
                violations_found=0,
                matches=[],
            )
        )

        request = ViolationTrackerServiceRequest(
            content="clean content",
            source="test.py",
        )

        response = await mock_service.process(request)

        assert response.ok is True
        assert response.violations_found == 0
        assert response.escalation_triggered is False

    @pytest.mark.asyncio
    async def test_process_detects_violations(self, mock_service):
        """Process returns violations when patterns match."""
        mock_service._pattern_matcher.process = AsyncMock(
            return_value=ViolationPatternsResponse(
                ok=True,
                request_id="test-123",
                violations_found=1,
                matches=[
                    ViolationMatch(
                        pattern="/Users/ib-mac/",
                        lesson_id="lesson-013",
                        severity=ViolationSeverity.CRITICAL,
                        description="Use $HOME",
                    )
                ],
            )
        )

        request = ViolationTrackerServiceRequest(
            content="/Users/ib-mac/Projects/test",
            source="config.py",
        )

        response = await mock_service.process(request)

        assert response.ok is True
        assert response.violations_found == 1
        assert len(response.violations) == 1
        assert response.violations[0].lesson_id == "lesson-013"

    @pytest.mark.asyncio
    async def test_process_increments_violation_count(self, mock_service):
        """Process increments violation count per lesson."""
        mock_service._pattern_matcher.process = AsyncMock(
            return_value=ViolationPatternsResponse(
                ok=True,
                request_id="test-123",
                violations_found=1,
                matches=[
                    ViolationMatch(
                        pattern="test",
                        lesson_id="lesson-test",
                        severity=ViolationSeverity.WARNING,
                        description="Test",
                    )
                ],
            )
        )

        request = ViolationTrackerServiceRequest(
            content="test content",
            source="test.py",
        )

        # Process twice
        await mock_service.process(request)
        await mock_service.process(request)

        assert mock_service.get_violation_count("lesson-test") == 2

    @pytest.mark.asyncio
    async def test_process_triggers_escalation_at_threshold(self, mock_service):
        """Process triggers escalation after 3 violations."""
        mock_service._pattern_matcher.process = AsyncMock(
            return_value=ViolationPatternsResponse(
                ok=True,
                request_id="test-123",
                violations_found=1,
                matches=[
                    ViolationMatch(
                        pattern="test",
                        lesson_id="lesson-escalate",
                        severity=ViolationSeverity.CRITICAL,
                        description="Test",
                    )
                ],
            )
        )

        request = ViolationTrackerServiceRequest(
            content="test content",
            source="test.py",
        )

        # Process 3 times to trigger escalation
        await mock_service.process(request)
        await mock_service.process(request)
        response = await mock_service.process(request)

        assert response.escalation_triggered is True
        assert "lesson-escalate" in response.escalated_lessons


class TestViolationRecord:
    """Test ViolationRecord model."""

    def test_record_has_required_fields(self):
        """ViolationRecord includes all required fields."""
        record = ViolationRecord(
            violation_id="viol-123",
            lesson_id="lesson-001",
            severity=ViolationSeverity.CRITICAL,
            pattern="/Users/ib-mac/",
            description="Use $HOME",
            source="config.py",
        )

        assert record.violation_id == "viol-123"
        assert record.lesson_id == "lesson-001"
        assert record.severity == ViolationSeverity.CRITICAL
        assert record.pattern == "/Users/ib-mac/"
        assert record.source == "config.py"
        assert record.violation_count == 1

    def test_record_timestamp_auto_generated(self):
        """ViolationRecord auto-generates timestamp."""
        record = ViolationRecord(
            violation_id="viol-123",
            lesson_id="lesson-001",
            severity=ViolationSeverity.WARNING,
            pattern="test",
            description="Test",
            source="test.py",
        )

        assert record.timestamp is not None
        assert isinstance(record.timestamp, datetime)
