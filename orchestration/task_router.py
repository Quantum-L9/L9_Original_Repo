"""
L9 Orchestration - Task Router
==============================

Routes incoming tasks to appropriate execution paths based on:
- Task type (design, implement, review, etc.)
- Complexity assessment (simple → complex)
- Risk level (low → critical)
- Available resources and load
- Agent capabilities (security enforcement)

Routing Paths:
┌─────────────────────────────────────────────────────────────────┐
│                        TaskRouter                                │
│                            │                                     │
│   ┌────────────┬──────────┴──────────┬────────────────────┐     │
│   ▼            ▼                     ▼                    ▼     │
│ IR Engine  IR + Simulation    IR + Simulation +    Direct Cell  │
│  Only        (Standard)       Collaborative Cell   Execution    │
└─────────────────────────────────────────────────────────────────┘

Routing Rules:
- Simple tasks (low complexity, low risk) → IR Engine only
- Standard tasks → IR Engine + Simulation
- Complex/High-risk tasks → IR + Simulation + Collaborative cells
- Specialized tasks → Direct cell execution (Architect/Coder/Reviewer)

Security Features (v2.1.0):
- Capability-based tool access control
- Agent capability validation before routing
- Trace ID / Correlation ID support

Version: 2.1.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Task Router",
    "module_version": "2.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "data_models",
    "module_name": "task_router",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["orchestration.__init__", "orchestration.unified_controller"],
    },
}
# ============================================================================

import structlog
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

# Security imports
from core.schemas.capabilities import ToolName, AgentCapabilities

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums
# =============================================================================


class TaskType(str, Enum):
    """Types of tasks for routing decisions."""

    DESIGN = "design"
    IMPLEMENT = "implement"
    REVIEW = "review"
    TEST = "test"
    REFACTOR = "refactor"
    DEBUG = "debug"
    ANALYZE = "analyze"
    DEPLOY = "deploy"
    DOCUMENT = "document"
    GENERAL = "general"


class ExecutionTarget(str, Enum):
    """Execution targets for routing."""

    IR_ENGINE_ONLY = "ir_engine_only"
    IR_WITH_SIMULATION = "ir_with_simulation"
    IR_WITH_CELLS = "ir_with_cells"
    ARCHITECT_CELL = "architect_cell"
    CODER_CELL = "coder_cell"
    REVIEWER_CELL = "reviewer_cell"
    REFLECTION_CELL = "reflection_cell"
    DIRECT_AGENT = "direct_agent"


class TaskComplexity(str, Enum):
    """Complexity levels for tasks."""

    TRIVIAL = "trivial"  # Single-step, no dependencies
    SIMPLE = "simple"  # Few steps, minimal dependencies
    MODERATE = "moderate"  # Multiple steps, some dependencies
    COMPLEX = "complex"  # Many steps, cross-cutting concerns
    CRITICAL = "critical"  # System-wide changes, high coordination


class TaskRisk(str, Enum):
    """Risk levels for tasks."""

    LOW = "low"  # No production impact, reversible
    MEDIUM = "medium"  # Limited impact, mostly reversible
    HIGH = "high"  # Significant impact, difficult to reverse
    CRITICAL = "critical"  # Production-critical, requires approval


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class TaskRoute:
    """A route for task execution."""

    target: ExecutionTarget
    priority: int = 5  # 1-10, higher = more urgent
    requires_simulation: bool = True
    requires_collaboration: bool = False
    cell_types: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    fallback_target: Optional[ExecutionTarget] = None
    estimated_duration_ms: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target.value,
            "priority": self.priority,
            "requires_simulation": self.requires_simulation,
            "requires_collaboration": self.requires_collaboration,
            "cell_types": self.cell_types,
            "fallback_target": self.fallback_target.value
            if self.fallback_target
            else None,
        }


@dataclass
class RoutingDecision:
    """Result of routing decision."""

    decision_id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    task_type: TaskType = TaskType.GENERAL
    complexity: TaskComplexity = TaskComplexity.MODERATE
    risk: TaskRisk = TaskRisk.MEDIUM
    primary_route: TaskRoute = field(
        default_factory=lambda: TaskRoute(ExecutionTarget.IR_WITH_SIMULATION)
    )
    secondary_routes: list[TaskRoute] = field(default_factory=list)
    confidence: float = 0.8
    reasoning: str = ""
    analysis: dict[str, Any] = field(default_factory=dict)
    decided_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": str(self.decision_id),
            "task_id": str(self.task_id),
            "task_type": self.task_type.value,
            "complexity": self.complexity.value,
            "risk": self.risk.value,
            "primary_target": self.primary_route.target.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


# =============================================================================
# Task Analysis Patterns
# =============================================================================

# Keywords for task type classification
TASK_TYPE_PATTERNS = {
    TaskType.DESIGN: [
        r"\b(design|architect|plan|structure|blueprint|schema|model)\b",
        r"\b(how\s+should|what\s+approach|architecture)\b",
    ],
    TaskType.IMPLEMENT: [
        r"\b(implement|create|build|write|develop|add|make)\b",
        r"\b(new\s+feature|add\s+support|implement\s+the)\b",
    ],
    TaskType.REVIEW: [
        r"\b(review|check|audit|assess|evaluate|inspect)\b",
        r"\b(code\s+review|security\s+audit|quality\s+check)\b",
    ],
    TaskType.TEST: [
        r"\b(test|qa|quality|coverage|unit\s+test|integration\s+test)\b",
        r"\b(write\s+tests|add\s+tests|test\s+coverage)\b",
    ],
    TaskType.REFACTOR: [
        r"\b(refactor|improve|optimize|clean|simplify|restructure)\b",
        r"\b(code\s+cleanup|performance\s+optimization)\b",
    ],
    TaskType.DEBUG: [
        r"\b(debug|fix|bug|error|issue|problem|broken)\b",
        r"\b(doesn't\s+work|not\s+working|failing|crash)\b",
    ],
    TaskType.ANALYZE: [
        r"\b(analyze|understand|explain|investigate|study)\b",
        r"\b(how\s+does|what\s+is|why\s+does)\b",
    ],
    TaskType.DEPLOY: [
        r"\b(deploy|release|publish|ship|launch|rollout)\b",
        r"\b(production|staging|ci\s*\/?\s*cd)\b",
    ],
    TaskType.DOCUMENT: [
        r"\b(document|docs|readme|api\s+doc|comment)\b",
        r"\b(write\s+documentation|update\s+docs)\b",
    ],
}

# Complexity indicators
COMPLEXITY_INDICATORS = {
    "high": [
        r"\b(entire|whole|complete|all|every)\b",
        r"\b(system|architecture|infrastructure|platform)\b",
        r"\b(migration|rewrite|overhaul)\b",
        r"\b(multiple|several|various|different)\b.*\b(components?|services?|modules?)\b",
    ],
    "medium": [
        r"\b(feature|module|component|service)\b",
        r"\b(integrate|connect|extend)\b",
        r"\b(modify|update|change)\b.*\b(existing|current)\b",
    ],
    "low": [
        r"\b(simple|quick|small|minor|single)\b",
        r"\b(typo|spelling|rename|format)\b",
        r"\b(add\s+a|create\s+a|fix\s+the)\b",
    ],
}

# Risk indicators
RISK_INDICATORS = {
    "critical": [
        r"\b(production|live|customer|user\s+data)\b",
        r"\b(security|authentication|authorization|encryption)\b",
        r"\b(payment|billing|financial|sensitive)\b",
        r"\b(database|migration|schema\s+change)\b",
    ],
    "high": [
        r"\b(api|endpoint|interface|contract)\b",
        r"\b(performance|scale|load)\b",
        r"\b(breaking\s+change|backwards?\s+compat)\b",
    ],
    "medium": [
        r"\b(feature|functionality|behavior)\b",
        r"\b(configuration|setting|option)\b",
    ],
}


# =============================================================================
# Task Router
# =============================================================================


class TaskRouter:
    """
    Routes tasks to appropriate execution targets.

    Analyzes task requirements using NLP patterns to determine:
    - Task type (design, implement, review, etc.)
    - Complexity level (trivial → critical)
    - Risk level (low → critical)

    Then selects the optimal execution path:
    - Simple, low-risk → IR Engine only
    - Standard → IR Engine + Simulation
    - Complex/high-risk → Full pipeline with collaborative cells

    Usage:
        router = TaskRouter()
        decision = router.route({
            "text": "Implement user authentication with OAuth2",
            "context": {"project": "my-app"},
        })
        # decision.primary_route.target == ExecutionTarget.IR_WITH_CELLS
    """

    def __init__(self):
        """Initialize the task router."""
        self._routing_history: list[RoutingDecision] = []
        self._target_load: dict[ExecutionTarget, int] = {
            target: 0 for target in ExecutionTarget
        }

        # Compile regex patterns
        self._type_patterns = {
            task_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for task_type, patterns in TASK_TYPE_PATTERNS.items()
        }
        self._complexity_patterns = {
            level: [re.compile(p, re.IGNORECASE) for p in patterns]
            for level, patterns in COMPLEXITY_INDICATORS.items()
        }
        self._risk_patterns = {
            level: [re.compile(p, re.IGNORECASE) for p in patterns]
            for level, patterns in RISK_INDICATORS.items()
        }

        logger.info("TaskRouter initialized")

    # =========================================================================
    # Main Routing
    # =========================================================================

    def route(
        self,
        task: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> RoutingDecision:
        """
        Route a task to appropriate target.

        Args:
            task: Task specification with at least 'text' or 'description'
            context: Optional context (project info, user preferences)

        Returns:
            RoutingDecision with target and metadata
        """
        task_id = UUID(task.get("task_id", str(uuid4())))
        task_text = task.get("text", task.get("description", ""))
        context = context or {}

        # Analyze task
        task_type = self._classify_task_type(task_text, task)
        complexity = self._assess_complexity(task_text, task)
        risk = self._assess_risk(task_text, task)

        # Build analysis record
        analysis = {
            "text_length": len(task_text),
            "task_type_matches": self._get_type_matches(task_text),
            "complexity_indicators": self._get_complexity_indicators(task_text),
            "risk_indicators": self._get_risk_indicators(task_text),
        }

        # Determine primary route
        primary_route = self._select_route(task_type, complexity, risk, task, context)

        # Determine fallback routes
        secondary_routes = self._select_fallback_routes(
            task_type, complexity, risk, primary_route
        )

        # Calculate confidence
        confidence = self._calculate_confidence(task_type, complexity, risk, task_text)

        # Build reasoning
        reasoning = self._build_reasoning(task_type, complexity, risk, primary_route)

        decision = RoutingDecision(
            task_id=task_id,
            task_type=task_type,
            complexity=complexity,
            risk=risk,
            primary_route=primary_route,
            secondary_routes=secondary_routes,
            confidence=confidence,
            reasoning=reasoning,
            analysis=analysis,
        )

        # Update load tracking
        self._target_load[primary_route.target] += 1

        # Store in history
        self._routing_history.append(decision)

        logger.info(
            f"Routed task {task_id}: type={task_type.value}, "
            f"complexity={complexity.value}, risk={risk.value} → {primary_route.target.value}"
        )

        return decision

    # =========================================================================
    # Task Classification
    # =========================================================================

    def _classify_task_type(
        self,
        task_text: str,
        task: dict[str, Any],
    ) -> TaskType:
        """Classify task type from text and metadata."""
        # Check explicit type in task
        if "type" in task:
            try:
                return TaskType(task["type"])
            except ValueError:
                pass

        # Score each type by pattern matches
        scores: dict[TaskType, int] = {t: 0 for t in TaskType}

        for task_type, patterns in self._type_patterns.items():
            for pattern in patterns:
                if pattern.search(task_text):
                    scores[task_type] += 1

        # Return highest scoring type, default to GENERAL
        best_type = max(scores.items(), key=lambda x: x[1])
        if best_type[1] > 0:
            return best_type[0]

        return TaskType.GENERAL

    def _assess_complexity(
        self,
        task_text: str,
        task: dict[str, Any],
    ) -> TaskComplexity:
        """Assess task complexity from text and metadata."""
        # Check explicit complexity
        if "complexity" in task:
            try:
                return TaskComplexity(task["complexity"])
            except ValueError:
                pass

        # Score complexity levels
        high_score = sum(
            1 for p in self._complexity_patterns["high"] if p.search(task_text)
        )
        medium_score = sum(
            1 for p in self._complexity_patterns["medium"] if p.search(task_text)
        )
        low_score = sum(
            1 for p in self._complexity_patterns["low"] if p.search(task_text)
        )

        # Text length as secondary indicator
        if len(task_text) > 500:
            high_score += 1
        elif len(task_text) < 50:
            low_score += 1

        # Determine level
        if high_score >= 2:
            return TaskComplexity.CRITICAL
        elif high_score >= 1:
            return TaskComplexity.COMPLEX
        elif medium_score >= 2:
            return TaskComplexity.MODERATE
        elif low_score >= 2:
            return TaskComplexity.TRIVIAL

        return TaskComplexity.SIMPLE

    def _assess_risk(
        self,
        task_text: str,
        task: dict[str, Any],
    ) -> TaskRisk:
        """Assess task risk from text and metadata."""
        # Check explicit risk
        if "risk" in task:
            try:
                return TaskRisk(task["risk"])
            except ValueError:
                pass

        # Score risk levels
        critical_score = sum(
            1 for p in self._risk_patterns["critical"] if p.search(task_text)
        )
        high_score = sum(1 for p in self._risk_patterns["high"] if p.search(task_text))
        medium_score = sum(
            1 for p in self._risk_patterns["medium"] if p.search(task_text)
        )

        # Determine level
        if critical_score >= 2:
            return TaskRisk.CRITICAL
        elif critical_score >= 1 or high_score >= 2:
            return TaskRisk.HIGH
        elif high_score >= 1 or medium_score >= 2:
            return TaskRisk.MEDIUM

        return TaskRisk.LOW

    # =========================================================================
    # Route Selection
    # =========================================================================

    def _select_route(
        self,
        task_type: TaskType,
        complexity: TaskComplexity,
        risk: TaskRisk,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> TaskRoute:
        """Select primary route based on analysis."""

        # Critical risk or complexity → Full pipeline with cells
        if risk == TaskRisk.CRITICAL or complexity == TaskComplexity.CRITICAL:
            return TaskRoute(
                target=ExecutionTarget.IR_WITH_CELLS,
                priority=10,
                requires_simulation=True,
                requires_collaboration=True,
                cell_types=self._get_cell_types_for_task(task_type),
                fallback_target=ExecutionTarget.IR_WITH_SIMULATION,
                estimated_duration_ms=120000,
            )

        # High risk/complexity → IR + Simulation + potential cells
        if risk == TaskRisk.HIGH or complexity == TaskComplexity.COMPLEX:
            return TaskRoute(
                target=ExecutionTarget.IR_WITH_SIMULATION,
                priority=8,
                requires_simulation=True,
                requires_collaboration=task_type in (TaskType.DESIGN, TaskType.REVIEW),
                cell_types=self._get_cell_types_for_task(task_type)
                if task_type in (TaskType.DESIGN, TaskType.REVIEW)
                else [],
                fallback_target=ExecutionTarget.IR_ENGINE_ONLY,
                estimated_duration_ms=60000,
            )

        # Design tasks → Architect cell preferred
        if task_type == TaskType.DESIGN:
            return TaskRoute(
                target=ExecutionTarget.ARCHITECT_CELL,
                priority=6,
                requires_simulation=False,
                requires_collaboration=True,
                cell_types=["architect"],
                fallback_target=ExecutionTarget.IR_WITH_SIMULATION,
                estimated_duration_ms=45000,
            )

        # Review tasks → Reviewer cell
        if task_type == TaskType.REVIEW:
            return TaskRoute(
                target=ExecutionTarget.REVIEWER_CELL,
                priority=5,
                requires_simulation=False,
                requires_collaboration=True,
                cell_types=["reviewer"],
                fallback_target=ExecutionTarget.IR_ENGINE_ONLY,
                estimated_duration_ms=30000,
            )

        # Implement/Debug → Coder cell for complex, IR for simple
        if task_type in (TaskType.IMPLEMENT, TaskType.DEBUG, TaskType.REFACTOR):
            if complexity in (TaskComplexity.MODERATE, TaskComplexity.COMPLEX):
                return TaskRoute(
                    target=ExecutionTarget.CODER_CELL,
                    priority=5,
                    requires_simulation=False,
                    requires_collaboration=True,
                    cell_types=["coder"],
                    fallback_target=ExecutionTarget.IR_WITH_SIMULATION,
                    estimated_duration_ms=45000,
                )

        # Trivial/Simple + Low risk → IR Engine only
        if (
            complexity in (TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE)
            and risk == TaskRisk.LOW
        ):
            return TaskRoute(
                target=ExecutionTarget.IR_ENGINE_ONLY,
                priority=3,
                requires_simulation=False,
                requires_collaboration=False,
                cell_types=[],
                fallback_target=None,
                estimated_duration_ms=15000,
            )

        # Default: IR + Simulation
        return TaskRoute(
            target=ExecutionTarget.IR_WITH_SIMULATION,
            priority=5,
            requires_simulation=True,
            requires_collaboration=False,
            cell_types=[],
            fallback_target=ExecutionTarget.IR_ENGINE_ONLY,
            estimated_duration_ms=30000,
        )

    def _get_cell_types_for_task(self, task_type: TaskType) -> list[str]:
        """Get recommended cell types for a task type."""
        mapping = {
            TaskType.DESIGN: ["architect", "reviewer"],
            TaskType.IMPLEMENT: ["coder", "reviewer"],
            TaskType.REVIEW: ["reviewer", "reflection"],
            TaskType.TEST: ["coder", "reviewer"],
            TaskType.REFACTOR: ["coder", "reviewer"],
            TaskType.DEBUG: ["coder", "reflection"],
            TaskType.ANALYZE: ["reflection", "architect"],
            TaskType.DEPLOY: ["coder", "reviewer"],
            TaskType.DOCUMENT: ["architect", "reviewer"],
            TaskType.GENERAL: ["coder"],
        }
        return mapping.get(task_type, ["coder"])

    def _select_fallback_routes(
        self,
        task_type: TaskType,
        complexity: TaskComplexity,
        risk: TaskRisk,
        primary_route: TaskRoute,
    ) -> list[TaskRoute]:
        """Select fallback routes in case primary fails."""
        fallbacks = []

        # Always include IR Engine as ultimate fallback
        if primary_route.target != ExecutionTarget.IR_ENGINE_ONLY:
            fallbacks.append(
                TaskRoute(
                    target=ExecutionTarget.IR_ENGINE_ONLY,
                    priority=primary_route.priority - 2,
                    requires_simulation=False,
                    requires_collaboration=False,
                )
            )

        # If using cells, fallback to IR + Simulation
        if primary_route.requires_collaboration:
            if primary_route.target not in (
                ExecutionTarget.IR_WITH_SIMULATION,
                ExecutionTarget.IR_ENGINE_ONLY,
            ):
                fallbacks.insert(
                    0,
                    TaskRoute(
                        target=ExecutionTarget.IR_WITH_SIMULATION,
                        priority=primary_route.priority - 1,
                        requires_simulation=True,
                        requires_collaboration=False,
                    ),
                )

        # For analysis/debug, add reflection cell as option
        if task_type in (TaskType.ANALYZE, TaskType.DEBUG):
            fallbacks.append(
                TaskRoute(
                    target=ExecutionTarget.REFLECTION_CELL,
                    priority=primary_route.priority - 2,
                    requires_simulation=False,
                    requires_collaboration=True,
                    cell_types=["reflection"],
                )
            )

        return fallbacks

    # =========================================================================
    # Confidence and Reasoning
    # =========================================================================

    def _calculate_confidence(
        self,
        task_type: TaskType,
        complexity: TaskComplexity,
        risk: TaskRisk,
        task_text: str,
    ) -> float:
        """Calculate confidence in routing decision."""
        confidence = 0.6  # Base

        # Higher confidence for clearly typed tasks
        if task_type != TaskType.GENERAL:
            confidence += 0.15

        # Higher confidence for longer, more detailed tasks
        if len(task_text) > 100:
            confidence += 0.1
        elif len(task_text) > 50:
            confidence += 0.05

        # Slightly lower confidence for critical complexity/risk
        if complexity == TaskComplexity.CRITICAL or risk == TaskRisk.CRITICAL:
            confidence -= 0.05

        return min(0.95, max(0.5, confidence))

    def _build_reasoning(
        self,
        task_type: TaskType,
        complexity: TaskComplexity,
        risk: TaskRisk,
        route: TaskRoute,
    ) -> str:
        """Build human-readable reasoning for the decision."""
        parts = [
            f"Task classified as {task_type.value}",
            f"with {complexity.value} complexity",
            f"and {risk.value} risk.",
        ]

        if route.requires_collaboration:
            parts.append(
                f"Routing to {route.target.value} with collaborative cells: {', '.join(route.cell_types)}."
            )
        else:
            parts.append(f"Routing to {route.target.value}.")

        if route.requires_simulation:
            parts.append("Simulation required.")

        return " ".join(parts)

    # =========================================================================
    # Analysis Helpers
    # =========================================================================

    def _get_type_matches(self, task_text: str) -> dict[str, list[str]]:
        """Get pattern matches for task type classification."""
        matches = {}
        for task_type, patterns in self._type_patterns.items():
            type_matches = []
            for pattern in patterns:
                found = pattern.findall(task_text)
                type_matches.extend(found)
            if type_matches:
                matches[task_type.value] = type_matches
        return matches

    def _get_complexity_indicators(self, task_text: str) -> dict[str, list[str]]:
        """Get complexity indicator matches."""
        indicators = {}
        for level, patterns in self._complexity_patterns.items():
            level_matches = []
            for pattern in patterns:
                found = pattern.findall(task_text)
                level_matches.extend(found)
            if level_matches:
                indicators[level] = level_matches
        return indicators

    def _get_risk_indicators(self, task_text: str) -> dict[str, list[str]]:
        """Get risk indicator matches."""
        indicators = {}
        for level, patterns in self._risk_patterns.items():
            level_matches = []
            for pattern in patterns:
                found = pattern.findall(task_text)
                level_matches.extend(found)
            if level_matches:
                indicators[level] = level_matches
        return indicators

    # =========================================================================
    # Batch Routing
    # =========================================================================

    def route_batch(
        self,
        tasks: list[dict[str, Any]],
        context: Optional[dict[str, Any]] = None,
    ) -> list[RoutingDecision]:
        """
        Route multiple tasks.

        Args:
            tasks: List of task specifications
            context: Shared context

        Returns:
            List of routing decisions
        """
        return [self.route(task, context) for task in tasks]

    def route_with_dependencies(
        self,
        tasks: list[dict[str, Any]],
        dependencies: dict[str, list[str]],
    ) -> list[RoutingDecision]:
        """
        Route tasks considering dependencies.

        Args:
            tasks: List of tasks with 'id' field
            dependencies: Map of task_id → list of dependency task_ids

        Returns:
            Ordered list of routing decisions
        """
        # Build task map
        task_map = {t.get("id", str(uuid4())): t for t in tasks}

        # Topological sort
        ordered_ids: list[str] = []
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visited:
                return
            visited.add(task_id)
            for dep_id in dependencies.get(task_id, []):
                if dep_id in task_map:
                    visit(dep_id)
            ordered_ids.append(task_id)

        for task_id in task_map:
            visit(task_id)

        # Route in order
        decisions = []
        for task_id in ordered_ids:
            task = task_map[task_id]
            task["task_id"] = task_id
            decision = self.route(task)
            decisions.append(decision)

        return decisions

    # =========================================================================
    # Load Management
    # =========================================================================

    def get_load(self, target: ExecutionTarget) -> int:
        """Get current load for a target."""
        return self._target_load.get(target, 0)

    def release_load(self, target: ExecutionTarget) -> None:
        """Release load from a target after task completion."""
        if target in self._target_load:
            self._target_load[target] = max(0, self._target_load[target] - 1)

    def get_load_summary(self) -> dict[str, int]:
        """Get load summary for all targets."""
        return {target.value: load for target, load in self._target_load.items()}

    # =========================================================================
    # History
    # =========================================================================

    def get_routing_history(self, limit: int = 100) -> list[RoutingDecision]:
        """Get recent routing history."""
        return self._routing_history[-limit:]

    def clear_history(self) -> None:
        """Clear routing history and reset loads."""
        self._routing_history.clear()
        self._target_load = {target: 0 for target in ExecutionTarget}


# =============================================================================
# Capability Enforcement (Security Layer)
# =============================================================================


def is_tool_allowed(agent_caps: AgentCapabilities, tool: ToolName) -> bool:
    """
    Check if a tool is allowed for an agent based on capabilities.

    This is the primary entry point for capability enforcement.
    Should be called before dispatching any tool task.

    Args:
        agent_caps: Agent's capability set
        tool: Tool being requested

    Returns:
        True if allowed, False otherwise

    Usage:
        caps = AgentCapabilities(
            agent_id="coder-1",
            capabilities=[Capability(tool=ToolName.SHELL, allowed=True)]
        )
        if is_tool_allowed(caps, ToolName.SHELL):
            execute_shell_command(...)
    """
    for cap in agent_caps.capabilities:
        if cap.tool == tool:
            return cap.allowed

    # Fall back to default
    return agent_caps.default_allowed


def check_tool_rate_limit(
    agent_caps: AgentCapabilities,
    tool: ToolName,
    current_invocations: int,
) -> bool:
    """
    Check if tool invocation is within rate limit.

    Args:
        agent_caps: Agent's capability set
        tool: Tool being requested
        current_invocations: Current invocation count this minute

    Returns:
        True if within limit, False if rate limited
    """
    cap = agent_caps.get_capability(tool)

    if cap is None:
        return True  # No capability defined, no rate limit

    if cap.rate_limit is None:
        return True  # No rate limit set

    return current_invocations < cap.rate_limit


def validate_agent_capabilities(
    agent_caps: AgentCapabilities,
    required_tools: list[ToolName],
) -> tuple[bool, list[ToolName]]:
    """
    Validate that an agent has all required capabilities.

    Args:
        agent_caps: Agent's capability set
        required_tools: List of tools required for a task

    Returns:
        Tuple of (all_allowed, missing_tools)
    """
    missing = []

    for tool in required_tools:
        if not is_tool_allowed(agent_caps, tool):
            missing.append(tool)

    return len(missing) == 0, missing


def get_tools_for_target(target: ExecutionTarget) -> list[ToolName]:
    """
    Get the tools typically required for an execution target.

    Args:
        target: Execution target

    Returns:
        List of typically required tools
    """
    mapping = {
        ExecutionTarget.IR_ENGINE_ONLY: [
            ToolName.MEMORY_READ,
            ToolName.WORLD_MODEL_QUERY,
        ],
        ExecutionTarget.IR_WITH_SIMULATION: [
            ToolName.MEMORY_READ,
            ToolName.MEMORY_WRITE,
            ToolName.WORLD_MODEL_QUERY,
        ],
        ExecutionTarget.IR_WITH_CELLS: [
            ToolName.MEMORY_READ,
            ToolName.MEMORY_WRITE,
            ToolName.WORLD_MODEL_QUERY,
            ToolName.PYTHON,
        ],
        ExecutionTarget.ARCHITECT_CELL: [
            ToolName.MEMORY_READ,
            ToolName.MEMORY_WRITE,
            ToolName.WORLD_MODEL_QUERY,
        ],
        ExecutionTarget.CODER_CELL: [
            ToolName.SHELL,
            ToolName.PYTHON,
            ToolName.FILE_ACCESS,
            ToolName.MEMORY_READ,
            ToolName.MEMORY_WRITE,
        ],
        ExecutionTarget.REVIEWER_CELL: [
            ToolName.MEMORY_READ,
            ToolName.FILE_ACCESS,
        ],
        ExecutionTarget.REFLECTION_CELL: [
            ToolName.MEMORY_READ,
            ToolName.WORLD_MODEL_QUERY,
        ],
        ExecutionTarget.DIRECT_AGENT: [
            ToolName.MEMORY_READ,
        ],
    }
    return mapping.get(target, [])


class CapabilityEnforcedRouter(TaskRouter):
    """
    TaskRouter with capability enforcement.

    Extends TaskRouter to validate agent capabilities before routing.

    Usage:
        router = CapabilityEnforcedRouter()

        # Set agent capabilities
        caps = AgentCapabilities(agent_id="coder-1", ...)

        # Route with enforcement
        decision = router.route_with_capabilities(task, caps)
    """

    def route_with_capabilities(
        self,
        task: dict[str, Any],
        agent_caps: AgentCapabilities,
        context: Optional[dict[str, Any]] = None,
    ) -> RoutingDecision:
        """
        Route a task with capability enforcement.

        Validates that the agent has required capabilities for the
        selected route. If not, attempts to find an alternative route
        that the agent can execute.

        Args:
            task: Task specification
            agent_caps: Agent's capability set
            context: Optional context

        Returns:
            RoutingDecision (may have modified target if capabilities insufficient)
        """
        # Get initial routing decision
        decision = self.route(task, context)

        # Check capabilities for primary route
        required_tools = get_tools_for_target(decision.primary_route.target)
        all_allowed, missing = validate_agent_capabilities(agent_caps, required_tools)

        if all_allowed:
            # Agent can execute primary route
            logger.info(
                f"Capability check passed for {agent_caps.agent_id} → "
                f"{decision.primary_route.target.value}"
            )
            return decision

        # Try secondary routes
        logger.warning(
            f"Agent {agent_caps.agent_id} missing capabilities {missing} "
            f"for {decision.primary_route.target.value}"
        )

        for secondary in decision.secondary_routes:
            sec_tools = get_tools_for_target(secondary.target)
            sec_allowed, sec_missing = validate_agent_capabilities(
                agent_caps, sec_tools
            )

            if sec_allowed:
                # Found viable alternative
                logger.info(
                    f"Rerouting {agent_caps.agent_id} to {secondary.target.value} "
                    f"(original: {decision.primary_route.target.value})"
                )

                # Update decision
                decision.primary_route = secondary
                decision.reasoning += " [Rerouted due to capability restrictions]"
                decision.confidence *= 0.9  # Slight confidence reduction

                return decision

        # No viable route found - return original with warning
        decision.warnings = getattr(decision, "warnings", []) or []
        decision.warnings.append(
            f"Agent {agent_caps.agent_id} lacks capabilities {missing}. Task may fail."
        )

        return decision


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-032",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.schemas.capabilities"],
    "tags": [
        "api",
        "auth",
        "batch-processing",
        "data-models",
        "dataclass",
        "debugging",
        "intelligence",
        "logging",
        "migration",
        "rest-api",
    ],
    "keywords": [
        "agent",
        "allowed",
        "based",
        "batch",
        "capabilities",
        "capability",
        "cell",
        "check",
    ],
    "business_value": "Provides task router components including TaskType, ExecutionTarget, TaskComplexity",
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
