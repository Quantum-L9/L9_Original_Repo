"""
Violation Tracker Service
=========================

Tracks lesson violations with pattern detection, local audit logging,
and MCP Memory sync for cross-session persistence.

Design Source: .cursor-commands/ops/feedback_loop_config.yaml

Response Actions:
    - log_to_audit: Write to audit_log.jsonl
    - increment_violation_count: Track per-lesson counts
    - emit_mcp_memory_entry: Sync to MCP Memory
    - update_lesson_effectiveness: Track which lessons are being violated

Auto-generated scaffold by L9 CodeGenAgent, implementation by governance design.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Violation Tracker Service",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T00:41:22Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "violation_tracker_service",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API"],
        "memory_layers": [],
        "imported_by": ["workers.__init__"],
    },
}
# ============================================================================

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid5, NAMESPACE_DNS

import structlog
from pydantic import BaseModel, Field
from core.decorators import must_stay_async

from workers.violation_patterns import (
    ViolationPatterns,
    ViolationPatternsRequest,
    ViolationMatch,
    ViolationSeverity,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# MODULE CONSTANTS
# =============================================================================

MODULE_ID = "violation_tracker_service"
MODULE_NAME = "Violation Tracker Service"

# Default paths
DEFAULT_AUDIT_LOG = (
    Path.home() / "Projects/L9/.cursor-commands/learning/failures/audit_log.jsonl"
)
DEFAULT_VIOLATIONS_LOG = (
    Path.home() / "Projects/L9/.cursor-commands/learning/failures/violations.jsonl"
)

# Escalation threshold
ESCALATION_THRESHOLD = 3


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ViolationRecord(BaseModel):
    """A recorded violation."""

    violation_id: str
    lesson_id: str
    severity: ViolationSeverity
    pattern: str
    description: str
    source: str
    context: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    violation_count: int = 1


class ViolationTrackerServiceRequest(BaseModel):
    """Input request for ViolationTrackerService."""

    request_id: str = Field(
        default_factory=lambda: str(uuid5(NAMESPACE_DNS, str(datetime.utcnow())))
    )
    content: str = Field(..., description="Content to scan for violations")
    source: str = Field(
        ..., description="Source of the content (file path, command, etc.)"
    )
    user_id: str = Field(default="cursor_agent", description="User or agent ID")
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"extra": "forbid"}


class ViolationTrackerServiceResponse(BaseModel):
    """Output response from ViolationTrackerService."""

    ok: bool = Field(..., description="Whether the operation succeeded")
    request_id: str = Field(..., description="Original request ID")
    violations_found: int = Field(default=0)
    violations: List[ViolationRecord] = Field(default_factory=list)
    escalation_triggered: bool = Field(default=False)
    escalated_lessons: List[str] = Field(default_factory=list)
    error: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: int = Field(
        default=0, description="Processing duration in milliseconds"
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================


class ViolationTrackerService:
    """
    Violation Tracker Service.

    Tracks lesson violations with pattern detection, logging, and MCP sync.
    """

    def __init__(
        self,
        pattern_matcher: Optional[ViolationPatterns] = None,
        audit_log_path: Optional[Path] = None,
        violations_log_path: Optional[Path] = None,
        mcp_enabled: bool = True,
    ):
        """
        Initialize the violation tracker.

        Args:
            pattern_matcher: ViolationPatterns instance
            audit_log_path: Path to audit log file
            violations_log_path: Path to violations log file
            mcp_enabled: Whether to sync to MCP Memory
        """
        self._initialized = False
        self._pattern_matcher = pattern_matcher or ViolationPatterns()
        self._audit_log_path = audit_log_path or DEFAULT_AUDIT_LOG
        self._violations_log_path = violations_log_path or DEFAULT_VIOLATIONS_LOG
        self._mcp_enabled = mcp_enabled

        # In-memory violation counts per lesson
        self._violation_counts: Dict[str, int] = {}

        # Stats
        self._stats = {
            "total_scans": 0,
            "total_violations": 0,
            "escalations_triggered": 0,
        }

        logger.info("violation_tracker_service_initialized")

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def startup(self) -> None:
        """Initialize resources on startup."""
        logger.info("violation_tracker_service_starting")

        # Start pattern matcher
        await self._pattern_matcher.startup()

        # Ensure log directories exist
        self._audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        self._violations_log_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing violation counts from log
        await self._load_violation_counts()

        self._initialized = True
        logger.info(
            "violation_tracker_service_started",
            audit_log=str(self._audit_log_path),
            violations_log=str(self._violations_log_path),
            mcp_enabled=self._mcp_enabled,
        )

    async def shutdown(self) -> None:
        """Clean up resources on shutdown."""
        logger.info("violation_tracker_service_shutting_down")

        await self._pattern_matcher.shutdown()

        self._initialized = False
        logger.info(
            "violation_tracker_service_shutdown_complete",
            stats=self._stats,
        )

    # =========================================================================
    # Main API
    # =========================================================================

    async def process(
        self, request: ViolationTrackerServiceRequest
    ) -> ViolationTrackerServiceResponse:
        """
        Scan content for violations and track them.

        Args:
            request: Input request with content to scan

        Returns:
            ViolationTrackerServiceResponse with violations found and actions taken
        """
        start_time = datetime.utcnow()
        violations: List[ViolationRecord] = []
        escalated_lessons: List[str] = []

        try:
            logger.info(
                "violation_tracker_service_process_start",
                request_id=request.request_id,
                source=request.source,
                content_length=len(request.content),
            )

            self._stats["total_scans"] += 1

            # Step 1: Scan for violations
            pattern_request = ViolationPatternsRequest(
                content=request.content,
                source=request.source,
                context=request.context,
            )
            pattern_response = await self._pattern_matcher.process(pattern_request)

            if not pattern_response.ok:
                raise Exception(f"Pattern matching failed: {pattern_response.error}")

            # Step 2: Process each violation
            for match in pattern_response.matches:
                violation = await self._process_violation(match, request)
                violations.append(violation)

                # Check for escalation
                if (
                    self._violation_counts.get(match.lesson_id, 0)
                    >= ESCALATION_THRESHOLD
                ):
                    if match.lesson_id not in escalated_lessons:
                        escalated_lessons.append(match.lesson_id)
                        await self._trigger_escalation(match.lesson_id)

            self._stats["total_violations"] += len(violations)
            if escalated_lessons:
                self._stats["escalations_triggered"] += len(escalated_lessons)

            duration_ms = self._calc_duration(start_time)

            logger.info(
                "violation_tracker_service_process_complete",
                request_id=request.request_id,
                violations_found=len(violations),
                escalations=len(escalated_lessons),
                duration_ms=duration_ms,
            )

            return ViolationTrackerServiceResponse(
                ok=True,
                request_id=request.request_id,
                violations_found=len(violations),
                violations=violations,
                escalation_triggered=bool(escalated_lessons),
                escalated_lessons=escalated_lessons,
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.exception(
                "violation_tracker_service_process_error",
                request_id=request.request_id,
                error=str(e),
            )

            return ViolationTrackerServiceResponse(
                ok=False,
                request_id=request.request_id,
                violations=violations,
                error=str(e),
                duration_ms=self._calc_duration(start_time),
            )

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _process_violation(
        self,
        match: ViolationMatch,
        request: ViolationTrackerServiceRequest,
    ) -> ViolationRecord:
        """
        Process a single violation match.

        Actions:
            1. Increment violation count
            2. Log to audit
            3. Log to violations
            4. Emit to MCP Memory (if enabled)
        """
        # Increment count
        self._violation_counts[match.lesson_id] = (
            self._violation_counts.get(match.lesson_id, 0) + 1
        )
        count = self._violation_counts[match.lesson_id]

        violation = ViolationRecord(
            violation_id=f"viol-{request.request_id}-{match.lesson_id}",
            lesson_id=match.lesson_id,
            severity=match.severity,
            pattern=match.pattern,
            description=match.description,
            source=request.source,
            context=match.context,
            violation_count=count,
        )

        # Log to audit
        await self._log_to_audit(violation, request)

        # Log to violations
        await self._log_to_violations(violation)

        # Emit to MCP Memory
        if self._mcp_enabled:
            await self._emit_to_mcp_memory(violation)

        logger.warning(
            "violation_detected",
            lesson_id=match.lesson_id,
            severity=match.severity.value,
            violation_count=count,
            source=request.source,
        )

        return violation

    @must_stay_async("callers use await")
    async def _log_to_audit(
        self,
        violation: ViolationRecord,
        request: ViolationTrackerServiceRequest,
    ) -> None:
        """Write violation to audit log."""
        entry = {
            "timestamp_utc": datetime.utcnow().isoformat(),
            "change_type": "lesson_violation",
            "trigger_source": "violation_tracker",
            "outcome": "detected",
            "lesson_id": violation.lesson_id,
            "violation_count": violation.violation_count,
            "severity": violation.severity.value,
            "source": violation.source,
            "user_id": request.user_id,
        }

        try:
            with open(self._audit_log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error("audit_log_write_failed", error=str(e))

    @must_stay_async("callers use await")
    async def _log_to_violations(self, violation: ViolationRecord) -> None:
        """Write violation to violations log."""
        entry = {
            "violation_id": violation.violation_id,
            "timestamp": violation.timestamp.isoformat(),
            "lesson_id": violation.lesson_id,
            "severity": violation.severity.value,
            "pattern": violation.pattern,
            "description": violation.description,
            "source": violation.source,
            "context": violation.context,
            "violation_count": violation.violation_count,
        }

        try:
            with open(self._violations_log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error("violations_log_write_failed", error=str(e))

    @must_stay_async("callers use await")
    async def _emit_to_mcp_memory(self, violation: ViolationRecord) -> None:
        """Emit violation to MCP Memory for cross-session persistence."""
        # In production, this would call the MCP Memory API
        # For now, we log the intent
        logger.info(
            "mcp_memory_emit",
            kind="lesson_violation",
            lesson_id=violation.lesson_id,
            violation_count=violation.violation_count,
        )

        # TODO: Implement actual MCP call
        # async with httpx.AsyncClient() as client:
        #     await client.post(
        #         "https://l9.quantumaipartners.com/mcp/tools/save_memory",
        #         json={
        #             "content": f"VIOLATION: {violation.lesson_id} violated ({violation.violation_count}x). Pattern: {violation.pattern}",
        #             "kind": "lesson_violation",
        #             "scope": "cursor",
        #             "metadata": {
        #                 "lesson_id": violation.lesson_id,
        #                 "violation_count": violation.violation_count,
        #             }
        #         }
        #     )

    @must_stay_async("callers use await")
    async def _trigger_escalation(self, lesson_id: str) -> None:
        """Trigger escalation for repeated violations."""
        count = self._violation_counts.get(lesson_id, 0)

        logger.error(
            "escalation_triggered",
            lesson_id=lesson_id,
            violation_count=count,
            threshold=ESCALATION_THRESHOLD,
            action="alert_igor",
        )

        # Log escalation to audit
        entry = {
            "timestamp_utc": datetime.utcnow().isoformat(),
            "change_type": "escalation",
            "trigger_source": "violation_tracker",
            "outcome": "escalated",
            "lesson_id": lesson_id,
            "violation_count": count,
            "next_steps": "Requires Igor review",
        }

        try:
            with open(self._audit_log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error("escalation_log_failed", error=str(e))

    @must_stay_async("callers use await")
    async def _load_violation_counts(self) -> None:
        """Load existing violation counts from log."""
        if not self._violations_log_path.exists():
            return

        try:
            with open(self._violations_log_path, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        lesson_id = entry.get("lesson_id")
                        if lesson_id:
                            self._violation_counts[lesson_id] = (
                                self._violation_counts.get(lesson_id, 0) + 1
                            )
                    except json.JSONDecodeError:
                        continue

            logger.info(
                "violation_counts_loaded",
                lesson_count=len(self._violation_counts),
                total_violations=sum(self._violation_counts.values()),
            )
        except Exception as e:
            logger.warning("violation_counts_load_failed", error=str(e))

    def _calc_duration(self, start_time: datetime) -> int:
        """Calculate duration in milliseconds."""
        return int((datetime.utcnow() - start_time).total_seconds() * 1000)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_violation_count(self, lesson_id: str) -> int:
        """Get current violation count for a lesson."""
        return self._violation_counts.get(lesson_id, 0)

    def get_all_violation_counts(self) -> Dict[str, int]:
        """Get all violation counts."""
        return self._violation_counts.copy()

    def reset_violation_count(self, lesson_id: str) -> None:
        """Reset violation count for a lesson (after review)."""
        if lesson_id in self._violation_counts:
            del self._violation_counts[lesson_id]
            logger.info("violation_count_reset", lesson_id=lesson_id)

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        pattern_health = await self._pattern_matcher.health_check()

        return {
            "module": MODULE_ID,
            "name": MODULE_NAME,
            "status": "healthy" if self._initialized else "not_initialized",
            "stats": self._stats,
            "violation_counts": len(self._violation_counts),
            "mcp_enabled": self._mcp_enabled,
            "components": {
                "pattern_matcher": pattern_health,
            },
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_violation_tracker_service(
    pattern_matcher: Optional[ViolationPatterns] = None,
    mcp_enabled: bool = True,
) -> ViolationTrackerService:
    """Factory function to create ViolationTrackerService."""
    return ViolationTrackerService(
        pattern_matcher=pattern_matcher,
        mcp_enabled=mcp_enabled,
    )


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    "ViolationTrackerService",
    "ViolationTrackerServiceRequest",
    "ViolationTrackerServiceResponse",
    "ViolationRecord",
    "create_violation_tracker_service",
    "MODULE_ID",
    "MODULE_NAME",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-004",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "async",
        "audit-tool",
        "data-models",
        "filesystem",
        "logging",
        "messaging",
        "operations",
        "pydantic",
        "schema",
    ],
    "keywords": [
        "all",
        "audit",
        "check",
        "count",
        "counts",
        "create",
        "design",
        "detection",
    ],
    "business_value": "Provides violation tracker service components including ViolationRecord, ViolationTrackerServiceRequest, ViolationTrackerServiceResponse",
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
