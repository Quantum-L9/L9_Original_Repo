"""
Violation Patterns
==================

Pattern matching engine for detecting lesson violations.

Patterns loaded from: .cursor-commands/ops/feedback_loop_config.yaml

Auto-generated scaffold by L9 CodeGenAgent, implementation by governance design.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Violation Patterns",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T00:41:22Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "violation_patterns",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API"],
        "memory_layers": [],
        "imported_by": ["workers.__init__", "workers.violation_tracker_service"],
    },
}
# ============================================================================

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid5, NAMESPACE_DNS

import structlog
from pydantic import BaseModel, Field
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# MODULE CONSTANTS
# =============================================================================

MODULE_ID = "violation_patterns"
MODULE_NAME = "Violation Patterns"


class ViolationSeverity(str, Enum):
    """Violation severity levels."""

    WARNING = "warning"
    CRITICAL = "critical"
    ULTRA_CRITICAL = "ultra-critical"


# =============================================================================
# PATTERN DEFINITIONS
# =============================================================================


@dataclass
class ViolationPattern:
    """A pattern that indicates a potential lesson violation."""

    pattern: str
    lesson_id: str
    severity: ViolationSeverity
    description: str
    is_regex: bool = False


# Patterns from feedback_loop_config.yaml
DEFAULT_PATTERNS: List[ViolationPattern] = [
    # Ultra-Critical
    ViolationPattern(
        pattern="Library/Application Support/Cursor",
        lesson_id="lesson-012-dropbox-not-library",
        severity=ViolationSeverity.ULTRA_CRITICAL,
        description="GlobalCommands should be in Dropbox, not Library",
    ),
    # Critical
    ViolationPattern(
        pattern="/Users/ib-mac/",
        lesson_id="lesson-013-use-home-variable",
        severity=ViolationSeverity.CRITICAL,
        description="Use $HOME instead of hardcoded paths",
    ),
    ViolationPattern(
        pattern="docker-compose.yaml",
        lesson_id="lesson-014-root-docker-compose",
        severity=ViolationSeverity.CRITICAL,
        description="Use ROOT docker-compose.yml, not docs version",
    ),
    ViolationPattern(
        pattern="may not be fully implemented",
        lesson_id="lesson-015-investigate-first",
        severity=ViolationSeverity.CRITICAL,
        description="Investigate before claiming completion",
    ),
    ViolationPattern(
        pattern="likely generated",
        lesson_id="lesson-015-investigate-first",
        severity=ViolationSeverity.CRITICAL,
        description="Investigate before claiming completion",
    ),
    ViolationPattern(
        pattern="probably exists",
        lesson_id="lesson-015-investigate-first",
        severity=ViolationSeverity.CRITICAL,
        description="Investigate before claiming completion",
    ),
    # Warning patterns
    ViolationPattern(
        pattern=r"print\s*\(",
        lesson_id="lesson-016-use-structlog",
        severity=ViolationSeverity.WARNING,
        description="Use structlog instead of print",
        is_regex=True,
    ),
    ViolationPattern(
        pattern=r"import\s+logging\b",
        lesson_id="lesson-016-use-structlog",
        severity=ViolationSeverity.WARNING,
        description="Use structlog instead of logging",
        is_regex=True,
    ),
    ViolationPattern(
        pattern=r"import\s+requests\b",
        lesson_id="lesson-017-use-httpx",
        severity=ViolationSeverity.WARNING,
        description="Use httpx instead of requests",
        is_regex=True,
    ),
    ViolationPattern(
        pattern=r"import\s+aiohttp\b",
        lesson_id="lesson-017-use-httpx",
        severity=ViolationSeverity.WARNING,
        description="Use httpx instead of aiohttp",
        is_regex=True,
    ),
]


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ViolationMatch(BaseModel):
    """A single violation match."""

    pattern: str
    lesson_id: str
    severity: ViolationSeverity
    description: str
    location: Optional[str] = None
    line_number: Optional[int] = None
    context: str = ""


class ViolationPatternsRequest(BaseModel):
    """Input request for ViolationPatterns."""

    request_id: str = Field(
        default_factory=lambda: str(uuid5(NAMESPACE_DNS, str(datetime.utcnow())))
    )
    content: str = Field(..., description="Content to scan for violations")
    source: str = Field(default="unknown", description="Source of the content")
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"extra": "forbid"}


class ViolationPatternsResponse(BaseModel):
    """Output response from ViolationPatterns."""

    ok: bool = Field(..., description="Whether the scan succeeded")
    request_id: str = Field(..., description="Original request ID")
    violations_found: int = Field(default=0)
    matches: List[ViolationMatch] = Field(default_factory=list)
    highest_severity: Optional[ViolationSeverity] = None
    error: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: int = Field(
        default=0, description="Processing duration in milliseconds"
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================


class ViolationPatterns:
    """
    Violation Patterns Service.

    Scans content for patterns that indicate lesson violations.
    """

    def __init__(self, custom_patterns: Optional[List[ViolationPattern]] = None):
        """Initialize with optional custom patterns."""
        self._initialized = False
        self._patterns = DEFAULT_PATTERNS + (custom_patterns or [])
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        logger.info("violation_patterns_initialized", pattern_count=len(self._patterns))

    # =========================================================================
    # Lifecycle
    # =========================================================================

    @must_stay_async("health endpoint")
    async def startup(self) -> None:
        """Initialize resources on startup."""
        logger.info("violation_patterns_starting")

        # Pre-compile regex patterns
        for pattern in self._patterns:
            if pattern.is_regex:
                try:
                    self._compiled_patterns[pattern.pattern] = re.compile(
                        pattern.pattern, re.IGNORECASE
                    )
                except re.error as e:
                    logger.warning(
                        "invalid_regex_pattern",
                        pattern=pattern.pattern,
                        error=str(e),
                    )

        self._initialized = True
        logger.info(
            "violation_patterns_started",
            pattern_count=len(self._patterns),
            compiled_regex_count=len(self._compiled_patterns),
        )

    @must_stay_async("health endpoint")
    async def shutdown(self) -> None:
        """Clean up resources on shutdown."""
        logger.info("violation_patterns_shutting_down")
        self._compiled_patterns.clear()
        self._initialized = False
        logger.info("violation_patterns_shutdown_complete")

    # =========================================================================
    # Main API
    # =========================================================================

    async def process(
        self, request: ViolationPatternsRequest
    ) -> ViolationPatternsResponse:
        """
        Scan content for violation patterns.

        Args:
            request: Input request with content to scan

        Returns:
            ViolationPatternsResponse with matches found
        """
        start_time = datetime.utcnow()

        try:
            logger.info(
                "violation_patterns_process_start",
                request_id=request.request_id,
                content_length=len(request.content),
                source=request.source,
            )

            matches = await self._execute(request)

            highest_severity = None
            if matches:
                severity_order = {
                    ViolationSeverity.ULTRA_CRITICAL: 3,
                    ViolationSeverity.CRITICAL: 2,
                    ViolationSeverity.WARNING: 1,
                }
                matches.sort(
                    key=lambda m: severity_order.get(m.severity, 0), reverse=True
                )
                highest_severity = matches[0].severity

            duration_ms = self._calc_duration(start_time)

            logger.info(
                "violation_patterns_process_complete",
                request_id=request.request_id,
                violations_found=len(matches),
                highest_severity=highest_severity.value if highest_severity else None,
                duration_ms=duration_ms,
            )

            return ViolationPatternsResponse(
                ok=True,
                request_id=request.request_id,
                violations_found=len(matches),
                matches=matches,
                highest_severity=highest_severity,
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.exception(
                "violation_patterns_process_error",
                request_id=request.request_id,
                error=str(e),
            )

            return ViolationPatternsResponse(
                ok=False,
                request_id=request.request_id,
                error=str(e),
                duration_ms=self._calc_duration(start_time),
            )

    # =========================================================================
    # Internal Methods
    # =========================================================================

    @must_stay_async("callers use await")
    async def _execute(self, request: ViolationPatternsRequest) -> List[ViolationMatch]:
        """
        Execute pattern matching.

        Args:
            request: Input request

        Returns:
            List of ViolationMatch for each pattern found
        """
        matches: List[ViolationMatch] = []
        content = request.content
        lines = content.split("\n")

        for pattern in self._patterns:
            if pattern.is_regex:
                # Use compiled regex
                compiled = self._compiled_patterns.get(pattern.pattern)
                if compiled:
                    for i, line in enumerate(lines, 1):
                        if compiled.search(line):
                            matches.append(
                                ViolationMatch(
                                    pattern=pattern.pattern,
                                    lesson_id=pattern.lesson_id,
                                    severity=pattern.severity,
                                    description=pattern.description,
                                    location=request.source,
                                    line_number=i,
                                    context=line.strip()[:100],
                                )
                            )
            else:
                # Simple substring match
                if pattern.pattern in content:
                    # Find line number
                    for i, line in enumerate(lines, 1):
                        if pattern.pattern in line:
                            matches.append(
                                ViolationMatch(
                                    pattern=pattern.pattern,
                                    lesson_id=pattern.lesson_id,
                                    severity=pattern.severity,
                                    description=pattern.description,
                                    location=request.source,
                                    line_number=i,
                                    context=line.strip()[:100],
                                )
                            )
                            break
                    else:
                        # Pattern found but not on a specific line
                        matches.append(
                            ViolationMatch(
                                pattern=pattern.pattern,
                                lesson_id=pattern.lesson_id,
                                severity=pattern.severity,
                                description=pattern.description,
                                location=request.source,
                            )
                        )

        return matches

    def _calc_duration(self, start_time: datetime) -> int:
        """Calculate duration in milliseconds."""
        return int((datetime.utcnow() - start_time).total_seconds() * 1000)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def add_pattern(self, pattern: ViolationPattern) -> None:
        """Add a new pattern at runtime."""
        self._patterns.append(pattern)
        if pattern.is_regex:
            try:
                self._compiled_patterns[pattern.pattern] = re.compile(
                    pattern.pattern, re.IGNORECASE
                )
            except re.error:
                pass
        logger.info("pattern_added", lesson_id=pattern.lesson_id)

    def get_patterns_for_lesson(self, lesson_id: str) -> List[ViolationPattern]:
        """Get all patterns associated with a lesson."""
        return [p for p in self._patterns if p.lesson_id == lesson_id]

    # =========================================================================
    # Health Check
    # =========================================================================

    @must_stay_async("health endpoint")
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        return {
            "module": MODULE_ID,
            "name": MODULE_NAME,
            "status": "healthy" if self._initialized else "not_initialized",
            "pattern_count": len(self._patterns),
            "compiled_regex_count": len(self._compiled_patterns),
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_violation_patterns(
    custom_patterns: Optional[List[ViolationPattern]] = None,
) -> ViolationPatterns:
    """Factory function to create ViolationPatterns."""
    return ViolationPatterns(custom_patterns=custom_patterns)


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    "ViolationPatterns",
    "ViolationPatternsRequest",
    "ViolationPatternsResponse",
    "ViolationMatch",
    "ViolationPattern",
    "ViolationSeverity",
    "create_violation_patterns",
    "DEFAULT_PATTERNS",
    "MODULE_ID",
    "MODULE_NAME",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": ["api", "async", "data-models", "dataclass", "logging", "messaging", "operations", "pydantic", "validation"],
    "keywords": ["check", "create", "governance", "health", "lesson", "match", "pattern", "patterns"],
    "business_value": "Provides violation patterns components including ViolationSeverity, ViolationPattern, ViolationMatch",
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
