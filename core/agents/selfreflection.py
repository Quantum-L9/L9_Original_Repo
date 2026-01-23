"""
L9 Self-Reflection Module
=========================

Provides behavioral gap detection for kernel-aware agents.
Analyzes task execution results to identify patterns that suggest
kernel updates may be needed.

Version: 1.0.0
GMP: kernel_boot_frontier_phase1
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Selfreflection",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-08T15:53:43Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "selfreflection",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "core.agents.executor",
            "core.agents.kernelevolution",
            "tests.integration.test_governance_tracking_e2e",
            "tests.integration.test_kernel_evolution_flow",
        ],
    },
}
# ============================================================================

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# Configurable Thresholds (env-based)
# =============================================================================

# Iteration threshold: tasks exceeding this are flagged as excessive
ITERATION_THRESHOLD = int(os.environ.get("L9_REFLECTION_ITERATION_THRESHOLD", "8"))

# Token threshold: tasks exceeding this are flagged for token overuse
TOKEN_THRESHOLD = int(os.environ.get("L9_REFLECTION_TOKEN_THRESHOLD", "50000"))

# Tool failure threshold: repeated failures at or above this count are flagged
TOOL_FAILURE_THRESHOLD = int(
    os.environ.get("L9_REFLECTION_TOOL_FAILURE_THRESHOLD", "3")
)

logger.debug(
    "selfreflection.thresholds_loaded",
    iteration_threshold=ITERATION_THRESHOLD,
    token_threshold=TOKEN_THRESHOLD,
    tool_failure_threshold=TOOL_FAILURE_THRESHOLD,
)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class BehaviorGap:
    """Represents a detected behavioral gap."""

    gap_id: str
    gap_type: str  # CAPABILITY, CONSTRAINT, POLICY, PERFORMANCE, SAFETY
    description: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    kernel_id: Optional[str]  # Which kernel might need updating
    evidence: List[str]  # Evidence supporting the gap detection
    suggested_action: str  # What action to take
    confidence: float  # 0.0 to 1.0
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "gap_id": self.gap_id,
            "gap_type": self.gap_type,
            "description": self.description,
            "severity": self.severity,
            "kernel_id": self.kernel_id,
            "evidence": self.evidence,
            "suggested_action": self.suggested_action,
            "confidence": self.confidence,
            "detected_at": self.detected_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class TaskExecutionContext:
    """Context from a completed task execution for analysis."""

    task_id: str
    agent_id: str
    task_kind: str
    success: bool
    duration_ms: float
    tool_calls: List[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]
    iterations: int
    tokens_used: int
    governance_blocks: List[Dict[str, Any]]
    user_corrections: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReflectionResult:
    """Result of self-reflection analysis."""

    reflection_id: str
    task_id: str
    agent_id: str
    gaps_detected: List[BehaviorGap]
    patterns_observed: List[str]
    recommendations: List[str]
    kernel_update_needed: bool
    analysis_duration_ms: float
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Gap Detection Patterns
# =============================================================================


class GapDetectionPattern:
    """Base class for gap detection patterns."""

    pattern_id: str
    pattern_name: str
    target_kernel: Optional[str] = None

    def detect(self, context: TaskExecutionContext) -> Optional[BehaviorGap]:
        """Detect a gap from the execution context. Override in subclasses."""
        raise NotImplementedError


class RepeatedToolFailurePattern(GapDetectionPattern):
    """Detects repeated failures of the same tool."""

    pattern_id = "REPEATED_TOOL_FAILURE"
    pattern_name = "Repeated Tool Failure"
    target_kernel = "execution"

    def detect(self, context: TaskExecutionContext) -> Optional[BehaviorGap]:
        # Count tool failures by tool_id
        tool_failures: Dict[str, int] = {}
        for call in context.tool_calls:
            if not call.get("success", True):
                tool_id = call.get("tool_id", "unknown")
                tool_failures[tool_id] = tool_failures.get(tool_id, 0) + 1

        # Check for repeated failures (configurable threshold)
        for tool_id, count in tool_failures.items():
            if count >= TOOL_FAILURE_THRESHOLD:
                return BehaviorGap(
                    gap_id=str(uuid4()),
                    gap_type="CAPABILITY",
                    description=f"Tool '{tool_id}' failed {count} times in a single task",
                    severity="MEDIUM" if count < 5 else "HIGH",
                    kernel_id=self.target_kernel,
                    evidence=[
                        f"Tool {tool_id} failed {count} times",
                        f"Task ID: {context.task_id}",
                    ],
                    suggested_action=f"Review tool '{tool_id}' usage patterns and add retry/fallback logic",
                    confidence=min(0.5 + (count * 0.1), 0.95),
                    metadata={"tool_id": tool_id, "failure_count": count},
                )
        return None


class GovernanceBlockPattern(GapDetectionPattern):
    """Detects when governance blocks legitimate actions."""

    pattern_id = "GOVERNANCE_BLOCK"
    pattern_name = "Governance Block"
    target_kernel = "safety"

    def detect(self, context: TaskExecutionContext) -> Optional[BehaviorGap]:
        if not context.governance_blocks:
            return None

        # Check for blocks that might be overly restrictive
        legitimate_blocks = []
        for block in context.governance_blocks:
            reason = block.get("reason", "")
            # If task succeeded despite blocks, the blocks might be too strict
            if context.success and "denied" in reason.lower():
                legitimate_blocks.append(block)

        if legitimate_blocks:
            return BehaviorGap(
                gap_id=str(uuid4()),
                gap_type="POLICY",
                description="Governance blocked actions but task still succeeded - policy may be overly restrictive",
                severity="LOW",
                kernel_id=self.target_kernel,
                evidence=[
                    f"Task succeeded despite {len(legitimate_blocks)} governance blocks",
                    f"Block reasons: {[b.get('reason', 'unknown')[:50] for b in legitimate_blocks[:3]]}",
                ],
                suggested_action="Review governance policies for potential over-restriction",
                confidence=0.6,
                metadata={"block_count": len(legitimate_blocks)},
            )
        return None


class UserCorrectionPattern(GapDetectionPattern):
    """Detects when user corrections indicate behavioral gaps."""

    pattern_id = "USER_CORRECTION"
    pattern_name = "User Correction"
    target_kernel = "behavioral"

    def detect(self, context: TaskExecutionContext) -> Optional[BehaviorGap]:
        if not context.user_corrections:
            return None

        # Analyze correction patterns
        correction_count = len(context.user_corrections)
        if correction_count >= 2:
            return BehaviorGap(
                gap_id=str(uuid4()),
                gap_type="CONSTRAINT",
                description=f"User made {correction_count} corrections during task execution",
                severity="MEDIUM" if correction_count < 4 else "HIGH",
                kernel_id=self.target_kernel,
                evidence=[
                    f"Correction count: {correction_count}",
                    f"Corrections: {context.user_corrections[:3]}",
                ],
                suggested_action="Analyze corrections to identify missing behavioral constraints",
                confidence=0.7 + (correction_count * 0.05),
                metadata={
                    "correction_count": correction_count,
                    "corrections": context.user_corrections[:5],
                },
            )
        return None


class ExcessiveIterationPattern(GapDetectionPattern):
    """Detects when tasks take too many iterations."""

    pattern_id = "EXCESSIVE_ITERATION"
    pattern_name = "Excessive Iteration"
    target_kernel = "cognitive"

    def detect(self, context: TaskExecutionContext) -> Optional[BehaviorGap]:
        # Configurable threshold for excessive iterations
        if context.iterations > ITERATION_THRESHOLD:
            return BehaviorGap(
                gap_id=str(uuid4()),
                gap_type="PERFORMANCE",
                description=f"Task required {context.iterations} iterations (threshold: {ITERATION_THRESHOLD})",
                severity=(
                    "MEDIUM"
                    if context.iterations < ITERATION_THRESHOLD * 1.5
                    else "HIGH"
                ),
                kernel_id=self.target_kernel,
                evidence=[
                    f"Iterations: {context.iterations}",
                    f"Task kind: {context.task_kind}",
                    f"Duration: {context.duration_ms}ms",
                ],
                suggested_action="Review task decomposition and planning strategies",
                confidence=0.65,
                metadata={
                    "iterations": context.iterations,
                    "task_kind": context.task_kind,
                },
            )
        return None


class TokenOverusePattern(GapDetectionPattern):
    """Detects excessive token usage."""

    pattern_id = "TOKEN_OVERUSE"
    pattern_name = "Token Overuse"
    target_kernel = "memory"

    def detect(self, context: TaskExecutionContext) -> Optional[BehaviorGap]:
        # Configurable threshold for token overuse
        if context.tokens_used > TOKEN_THRESHOLD:
            return BehaviorGap(
                gap_id=str(uuid4()),
                gap_type="PERFORMANCE",
                description=f"Task used {context.tokens_used} tokens (threshold: {TOKEN_THRESHOLD})",
                severity=(
                    "MEDIUM" if context.tokens_used < TOKEN_THRESHOLD * 2 else "HIGH"
                ),
                kernel_id=self.target_kernel,
                evidence=[
                    f"Tokens used: {context.tokens_used}",
                    f"Task kind: {context.task_kind}",
                ],
                suggested_action="Review context window management and summarization strategies",
                confidence=0.7,
                metadata={"tokens_used": context.tokens_used},
            )
        return None


# =============================================================================
# Self-Reflection Engine
# =============================================================================


# Default patterns to apply
DEFAULT_PATTERNS: List[GapDetectionPattern] = [
    RepeatedToolFailurePattern(),
    GovernanceBlockPattern(),
    UserCorrectionPattern(),
    ExcessiveIterationPattern(),
    TokenOverusePattern(),
]


def detect_behavior_gaps(
    context: TaskExecutionContext,
    patterns: Optional[List[GapDetectionPattern]] = None,
) -> List[BehaviorGap]:
    """
    Detect behavioral gaps from a task execution context.

    Args:
        context: The task execution context to analyze
        patterns: Optional list of patterns to apply (defaults to DEFAULT_PATTERNS)

    Returns:
        List of detected BehaviorGap instances
    """
    if patterns is None:
        patterns = DEFAULT_PATTERNS

    gaps: List[BehaviorGap] = []

    for pattern in patterns:
        try:
            gap = pattern.detect(context)
            if gap is not None:
                gaps.append(gap)
                logger.info(
                    "selfreflection.gap_detected",
                    pattern_id=pattern.pattern_id,
                    gap_id=gap.gap_id,
                    gap_type=gap.gap_type,
                    severity=gap.severity,
                )
        except Exception as e:
            logger.warning(
                "selfreflection.pattern_error",
                pattern_id=pattern.pattern_id,
                error=str(e),
            )

    return gaps


@must_stay_async("callers use await")
async def analyze_task_execution(
    context: TaskExecutionContext,
    patterns: Optional[List[GapDetectionPattern]] = None,
) -> ReflectionResult:
    """
    Perform full self-reflection analysis on a task execution.

    Args:
        context: The task execution context to analyze
        patterns: Optional list of patterns to apply

    Returns:
        ReflectionResult with detected gaps and recommendations
    """
    import time

    start_time = time.time()

    # Detect gaps
    gaps = detect_behavior_gaps(context, patterns)

    # Generate patterns observed
    patterns_observed = []
    if context.success:
        patterns_observed.append("Task completed successfully")
    else:
        patterns_observed.append("Task failed")

    if context.iterations > 5:
        patterns_observed.append(f"High iteration count ({context.iterations})")

    if context.tool_calls:
        failed_tools = [c for c in context.tool_calls if not c.get("success", True)]
        if failed_tools:
            patterns_observed.append(f"{len(failed_tools)} tool failures")

    # Generate recommendations
    recommendations = []
    kernel_update_needed = False

    for gap in gaps:
        recommendations.append(gap.suggested_action)
        if gap.severity in ("HIGH", "CRITICAL"):
            kernel_update_needed = True

    if not recommendations:
        recommendations.append("No immediate action required")

    duration_ms = (time.time() - start_time) * 1000

    result = ReflectionResult(
        reflection_id=str(uuid4()),
        task_id=context.task_id,
        agent_id=context.agent_id,
        gaps_detected=gaps,
        patterns_observed=patterns_observed,
        recommendations=recommendations,
        kernel_update_needed=kernel_update_needed,
        analysis_duration_ms=duration_ms,
    )

    logger.info(
        "selfreflection.analysis_complete",
        reflection_id=result.reflection_id,
        task_id=context.task_id,
        gaps_count=len(gaps),
        kernel_update_needed=kernel_update_needed,
        duration_ms=duration_ms,
    )

    return result


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Data models
    "BehaviorGap",
    "TaskExecutionContext",
    "ReflectionResult",
    # Patterns
    "GapDetectionPattern",
    "RepeatedToolFailurePattern",
    "GovernanceBlockPattern",
    "UserCorrectionPattern",
    "ExcessiveIterationPattern",
    "TokenOverusePattern",
    "DEFAULT_PATTERNS",
    # Functions
    "detect_behavior_gaps",
    "analyze_task_execution",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-037",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "agent-execution",
        "api",
        "async",
        "dataclass",
        "debugging",
        "foundation",
        "logging",
        "rest-api",
    ],
    "keywords": [
        "analyze",
        "behavior",
        "block",
        "correction",
        "detect",
        "detection",
        "excessive",
        "execution",
    ],
    "business_value": "Provides behavioral gap detection for kernel-aware agents. Analyzes task execution results to identify patterns that suggest kernel updates may be needed. Version: 1.0.0 GMP: kernel_boot_frontier_phas",
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
