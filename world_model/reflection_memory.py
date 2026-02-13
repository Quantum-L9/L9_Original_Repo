"""
L9 World Model - Reflection Memory
==================================

Stores reflection and meta-reasoning data.

Responsibilities:
- Store lessons learned per task
- Track what worked / failed
- Track which constraints were false
- Track which patterns improved metrics
- Maintain improvement history
- Provide reflection queries

Integration:
- World Model Engine: Receives reflection packets
- Causal Mapper: Links reflections to decisions/outcomes
- Orchestrators: Query reflections for context

Version: 1.2.0 (task-based reflection tracking)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Reflection Memory",
    "module_version": "1.2.0 (task-based reflection tracking)",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-14T16:24:36Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "reflection_memory",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": [
            "world_model.__init__",
            "world_model.engine",
            "world_model.runtime",
            "world_model.seed_loader",
            "world_model.world_model_service",
        ],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)


class ReflectionType(str, Enum):
    """Types of reflections."""

    LESSON = "lesson"
    PATTERN = "pattern"
    IMPROVEMENT = "improvement"
    FAILURE_ANALYSIS = "failure_analysis"
    SUCCESS_FACTOR = "success_factor"
    INSIGHT = "insight"


class ReflectionPriority(str, Enum):
    """Priority of reflections."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Reflection:
    """A stored reflection."""

    reflection_id: UUID = field(default_factory=uuid4)
    reflection_type: ReflectionType = ReflectionType.LESSON
    content: str = ""
    context: str = ""
    priority: ReflectionPriority = ReflectionPriority.MEDIUM
    confidence: float = 0.8
    source: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    access_count: int = 0
    last_accessed: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize reflection to dictionary."""
        return {
            "reflection_id": str(self.reflection_id),
            "reflection_type": self.reflection_type.value,
            "content": self.content,
            "context": self.context,
            "priority": self.priority.value,
            "confidence": self.confidence,
            "source": self.source,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Reflection:
        """Deserialize reflection from dictionary."""
        return cls(
            reflection_id=(
                UUID(data["reflection_id"]) if "reflection_id" in data else uuid4()
            ),
            reflection_type=ReflectionType(data.get("reflection_type", "lesson")),
            content=data.get("content", ""),
            context=data.get("context", ""),
            priority=ReflectionPriority(data.get("priority", "medium")),
            confidence=data.get("confidence", 0.8),
            source=data.get("source", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Pattern:
    """A recognized pattern."""

    pattern_id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    frequency: int = 1
    impact: str = "neutral"  # positive, negative, neutral
    examples: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    outcomes: list[str] = field(default_factory=list)
    confidence: float = 0.5
    first_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_seen: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize pattern to dictionary."""
        return {
            "pattern_id": str(self.pattern_id),
            "name": self.name,
            "description": self.description,
            "frequency": self.frequency,
            "impact": self.impact,
            "confidence": self.confidence,
        }


@dataclass
class Improvement:
    """A proposed or implemented improvement."""

    improvement_id: UUID = field(default_factory=uuid4)
    area: str = ""
    description: str = ""
    action_required: str = ""
    status: str = "proposed"  # proposed, in_progress, implemented, rejected
    priority: ReflectionPriority = ReflectionPriority.MEDIUM
    expected_impact: str = ""
    actual_impact: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    implemented_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize improvement to dictionary."""
        return {
            "improvement_id": str(self.improvement_id),
            "area": self.area,
            "description": self.description,
            "status": self.status,
            "priority": self.priority.value,
        }


# =============================================================================
# Task-Based Reflection (v1.2.0)
# =============================================================================


@dataclass
class TaskReflection:
    """
    A reflection scoped to a specific task.

    Captures lessons learned per task execution:
    - What worked / what failed
    - Which constraints were false assumptions
    - Which patterns improved metrics
    """

    task_id: str
    reflection_id: UUID = field(default_factory=uuid4)
    task_description: str = ""
    outcome: str = "unknown"  # success, partial, failure, unknown
    what_worked: list[str] = field(default_factory=list)
    what_failed: list[str] = field(default_factory=list)
    false_constraints: list[str] = field(default_factory=list)
    helpful_patterns: list[str] = field(default_factory=list)
    metrics_improved: dict[str, float] = field(default_factory=dict)
    metrics_degraded: dict[str, float] = field(default_factory=dict)
    lessons: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    related_decisions: list[str] = field(default_factory=list)
    execution_time_ms: float | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize task reflection to dictionary."""
        return {
            "task_id": self.task_id,
            "reflection_id": str(self.reflection_id),
            "task_description": self.task_description,
            "outcome": self.outcome,
            "what_worked": self.what_worked,
            "what_failed": self.what_failed,
            "false_constraints": self.false_constraints,
            "helpful_patterns": self.helpful_patterns,
            "metrics_improved": self.metrics_improved,
            "metrics_degraded": self.metrics_degraded,
            "lessons": self.lessons,
            "recommendations": self.recommendations,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskReflection:
        """Deserialize task reflection from dictionary."""
        return cls(
            task_id=data.get("task_id", ""),
            reflection_id=(
                UUID(data["reflection_id"]) if "reflection_id" in data else uuid4()
            ),
            task_description=data.get("task_description", ""),
            outcome=data.get("outcome", "unknown"),
            what_worked=data.get("what_worked", []),
            what_failed=data.get("what_failed", []),
            false_constraints=data.get("false_constraints", []),
            helpful_patterns=data.get("helpful_patterns", []),
            metrics_improved=data.get("metrics_improved", {}),
            metrics_degraded=data.get("metrics_degraded", {}),
            lessons=data.get("lessons", []),
            recommendations=data.get("recommendations", []),
            related_decisions=data.get("related_decisions", []),
            metadata=data.get("metadata", {}),
        )


class ReflectionMemory:
    """
    Stores and manages reflection data.

    Provides:
    - Lesson storage and retrieval
    - Task-based reflection tracking (v1.2.0)
    - Pattern recognition
    - Improvement tracking
    - Contextual queries

    Usage:
        memory = ReflectionMemory()

        # Record task-based reflection
        memory.record_reflection(
            task_id="task_001",
            data={
                "task_description": "Implement caching",
                "outcome": "success",
                "what_worked": ["Redis integration"],
                "what_failed": ["Initial timeout config"],
                "lessons": ["Start with conservative timeouts"],
            }
        )

        # Query reflections
        results = memory.query_reflections(
            task_id="task_001",
            filters={"outcome": "success"}
        )
    """

    def __init__(self, max_reflections: int = 10000):
        """
        Initialize reflection memory.

        Args:
            max_reflections: Maximum reflections to store
        """
        self._reflections: dict[UUID, Reflection] = {}
        self._patterns: dict[UUID, Pattern] = {}
        self._improvements: dict[UUID, Improvement] = {}
        self._max_reflections = max_reflections
        self._tag_index: dict[str, list[UUID]] = {}
        self._type_index: dict[ReflectionType, list[UUID]] = {
            rt: [] for rt in ReflectionType
        }

        # Task-based reflections (v1.2.0)
        self._task_reflections: dict[str, TaskReflection] = {}
        self._task_index: dict[str, list[str]] = {}  # tag -> task_ids

        logger.info("ReflectionMemory initialized (v1.2.0)")

    # ==========================================================================
    # Reflection Management
    # ==========================================================================

    def add_reflection(
        self,
        content: str,
        reflection_type: ReflectionType = ReflectionType.LESSON,
        context: str = "",
        priority: ReflectionPriority = ReflectionPriority.MEDIUM,
        confidence: float = 0.8,
        source: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Reflection:
        """
        Add a new reflection.

        Args:
            content: Reflection content
            reflection_type: Type of reflection
            context: Context of reflection
            priority: Priority level
            confidence: Confidence score
            source: Source of reflection
            tags: Tags for indexing
            metadata: Additional metadata

        Returns:
            Created Reflection
        """
        # Enforce max size
        if len(self._reflections) >= self._max_reflections:
            self._evict_old_reflections()

        reflection = Reflection(
            reflection_type=reflection_type,
            content=content,
            context=context,
            priority=priority,
            confidence=confidence,
            source=source,
            tags=tags or [],
            metadata=metadata or {},
        )

        self._reflections[reflection.reflection_id] = reflection

        # Index by type
        self._type_index[reflection_type].append(reflection.reflection_id)

        # Index by tags
        for tag in reflection.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(reflection.reflection_id)

        logger.debug(f"Added reflection: {reflection.reflection_id}")

        return reflection

    def get_reflection(self, reflection_id: UUID) -> Reflection | None:
        """Get a reflection by ID."""
        reflection = self._reflections.get(reflection_id)
        if reflection:
            reflection.access_count += 1
            reflection.last_accessed = datetime.now(UTC)
        return reflection

    def update_reflection(
        self,
        reflection_id: UUID,
        content: str | None = None,
        confidence: float | None = None,
        priority: ReflectionPriority | None = None,
    ) -> bool:
        """Update a reflection."""
        reflection = self._reflections.get(reflection_id)
        if not reflection:
            return False

        if content is not None:
            reflection.content = content
        if confidence is not None:
            reflection.confidence = confidence
        if priority is not None:
            reflection.priority = priority

        return True

    def delete_reflection(self, reflection_id: UUID) -> bool:
        """Delete a reflection."""
        reflection = self._reflections.get(reflection_id)
        if not reflection:
            return False

        # Remove from indexes
        if reflection_id in self._type_index[reflection.reflection_type]:
            self._type_index[reflection.reflection_type].remove(reflection_id)

        for tag in reflection.tags:
            if tag in self._tag_index and reflection_id in self._tag_index[tag]:
                self._tag_index[tag].remove(reflection_id)

        del self._reflections[reflection_id]
        return True

    def _evict_old_reflections(self) -> None:
        """Evict old/low-priority reflections."""
        # Sort by priority and access count
        sorted_reflections = sorted(
            self._reflections.values(),
            key=lambda r: (r.priority.value, -r.access_count, r.created_at),
            reverse=True,
        )

        # Remove bottom 10%
        to_remove = int(len(sorted_reflections) * 0.1)
        for reflection in sorted_reflections[-to_remove:]:
            self.delete_reflection(reflection.reflection_id)

    # ==========================================================================
    # Pattern Management
    # ==========================================================================

    def add_pattern(
        self,
        name: str,
        description: str,
        impact: str = "neutral",
        triggers: list[str] | None = None,
        outcomes: list[str] | None = None,
    ) -> Pattern:
        """
        Add or update a pattern.

        Args:
            name: Pattern name
            description: Pattern description
            impact: Impact type
            triggers: What triggers this pattern
            outcomes: Pattern outcomes

        Returns:
            Pattern
        """
        # Check if pattern exists
        existing = self.find_pattern_by_name(name)
        if existing:
            existing.frequency += 1
            existing.last_seen = datetime.now(UTC)
            existing.confidence = min(1.0, existing.confidence + 0.05)
            return existing

        pattern = Pattern(
            name=name,
            description=description,
            impact=impact,
            triggers=triggers or [],
            outcomes=outcomes or [],
        )

        self._patterns[pattern.pattern_id] = pattern
        return pattern

    def find_pattern_by_name(self, name: str) -> Pattern | None:
        """Find a pattern by name."""
        for pattern in self._patterns.values():
            if pattern.name.lower() == name.lower():
                return pattern
        return None

    def get_patterns_by_impact(self, impact: str) -> list[Pattern]:
        """Get patterns by impact type."""
        return [p for p in self._patterns.values() if p.impact == impact]

    # ==========================================================================
    # Improvement Management
    # ==========================================================================

    def add_improvement(
        self,
        area: str,
        description: str,
        action_required: str,
        priority: ReflectionPriority = ReflectionPriority.MEDIUM,
        expected_impact: str = "",
    ) -> Improvement:
        """
        Add an improvement proposal.

        Args:
            area: Improvement area
            description: What to improve
            action_required: Required action
            priority: Priority level
            expected_impact: Expected impact

        Returns:
            Improvement
        """
        improvement = Improvement(
            area=area,
            description=description,
            action_required=action_required,
            priority=priority,
            expected_impact=expected_impact,
        )

        self._improvements[improvement.improvement_id] = improvement
        return improvement

    def update_improvement_status(
        self,
        improvement_id: UUID,
        status: str,
        actual_impact: str | None = None,
    ) -> bool:
        """Update improvement status."""
        improvement = self._improvements.get(improvement_id)
        if not improvement:
            return False

        improvement.status = status
        if status == "implemented":
            improvement.implemented_at = datetime.now(UTC)
        if actual_impact:
            improvement.actual_impact = actual_impact

        return True

    def get_pending_improvements(self) -> list[Improvement]:
        """Get pending improvements sorted by priority."""
        pending = [
            i
            for i in self._improvements.values()
            if i.status in ("proposed", "in_progress")
        ]
        return sorted(pending, key=lambda i: i.priority.value)

    # ==========================================================================
    # Queries
    # ==========================================================================

    def get_recent_reflections(
        self,
        limit: int = 10,
    ) -> list[Reflection]:
        """Get most recent reflections."""
        sorted_reflections = sorted(
            self._reflections.values(),
            key=lambda r: r.created_at,
            reverse=True,
        )
        return sorted_reflections[:limit]

    def get_high_confidence_lessons(
        self,
        min_confidence: float = 0.8,
    ) -> list[Reflection]:
        """Get high-confidence lessons."""
        return self.query_reflections(
            reflection_type=ReflectionType.LESSON,
            min_confidence=min_confidence,
        )

    def search_by_context(
        self,
        context_query: str,
        limit: int = 10,
    ) -> list[Reflection]:
        """Search reflections by context similarity."""
        query_lower = context_query.lower()

        matches = []
        for reflection in self._reflections.values():
            # Simple keyword matching
            if (
                query_lower in reflection.context.lower()
                or query_lower in reflection.content.lower()
            ):
                matches.append(reflection)

        return matches[:limit]

    # ==========================================================================
    # Task-Based Reflection API (v1.2.0)
    # ==========================================================================

    def record_reflection(
        self,
        task_id: str,
        data: dict[str, Any],
    ) -> TaskReflection:
        """
        Record a reflection for a specific task.

        Stores lessons learned per task execution:
        - What worked / what failed
        - Which constraints were false assumptions
        - Which patterns improved metrics

        Args:
            task_id: Unique identifier for the task
            data: Reflection data dict with optional fields:
                - task_description: str
                - outcome: str (success, partial, failure, unknown)
                - what_worked: list[str]
                - what_failed: list[str]
                - false_constraints: list[str]
                - helpful_patterns: list[str]
                - metrics_improved: dict[str, float]
                - metrics_degraded: dict[str, float]
                - lessons: list[str]
                - recommendations: list[str]
                - related_decisions: list[str]
                - execution_time_ms: float

        Returns:
            Created TaskReflection instance
        """
        reflection = TaskReflection(
            task_id=task_id,
            task_description=data.get("task_description", ""),
            outcome=data.get("outcome", "unknown"),
            what_worked=data.get("what_worked", []),
            what_failed=data.get("what_failed", []),
            false_constraints=data.get("false_constraints", []),
            helpful_patterns=data.get("helpful_patterns", []),
            metrics_improved=data.get("metrics_improved", {}),
            metrics_degraded=data.get("metrics_degraded", {}),
            lessons=data.get("lessons", []),
            recommendations=data.get("recommendations", []),
            related_decisions=data.get("related_decisions", []),
            execution_time_ms=data.get("execution_time_ms"),
            metadata=data.get("metadata", {}),
        )

        self._task_reflections[task_id] = reflection

        # Index by outcome
        outcome_key = f"outcome:{reflection.outcome}"
        if outcome_key not in self._task_index:
            self._task_index[outcome_key] = []
        self._task_index[outcome_key].append(task_id)

        # Also create standard reflections from lessons
        for lesson in reflection.lessons:
            self.add_reflection(
                content=lesson,
                reflection_type=ReflectionType.LESSON,
                context=f"Task: {task_id}",
                source=task_id,
                tags=[f"task:{task_id}", f"outcome:{reflection.outcome}"],
            )

        # Create patterns from helpful patterns
        for pattern in reflection.helpful_patterns:
            self.add_pattern(
                name=pattern,
                description=f"Helpful pattern from task {task_id}",
                impact="positive" if reflection.outcome == "success" else "neutral",
            )

        logger.debug(f"Recorded task reflection: {task_id}")
        return reflection

    def query_reflections(
        self,
        task_id: str | None = None,
        filters: dict[str, Any] | None = None,
        reflection_type: ReflectionType | None = None,
        tags: list[str] | None = None,
        min_confidence: float = 0.0,
        priority: ReflectionPriority | None = None,
        limit: int = 100,
    ) -> list[Reflection | TaskReflection]:
        """
        Query reflections with flexible filters.

        Supports both task-based reflections and standard reflections.

        Args:
            task_id: Filter by specific task ID (returns TaskReflection)
            filters: Dict of additional filters:
                - outcome: str (success, partial, failure)
                - has_lessons: bool
                - has_false_constraints: bool
                - related_decision: str
            reflection_type: Filter standard reflections by type
            tags: Filter by tags (any match)
            min_confidence: Minimum confidence for standard reflections
            priority: Filter by priority
            limit: Maximum results

        Returns:
            List of matching Reflection or TaskReflection instances
        """
        results: list[Reflection | TaskReflection] = []
        filters = filters or {}

        # If task_id specified, query task reflections
        if task_id:
            task_reflection = self._task_reflections.get(task_id)
            if task_reflection:
                if self._matches_task_filters(task_reflection, filters):
                    results.append(task_reflection)
            return results

        # Query task reflections by filters
        if filters:
            for task_ref in self._task_reflections.values():
                if self._matches_task_filters(task_ref, filters):
                    results.append(task_ref)
                    if len(results) >= limit:
                        break

        # Also query standard reflections
        standard_results = self._query_standard_reflections(
            reflection_type=reflection_type,
            tags=tags,
            min_confidence=min_confidence,
            priority=priority,
            limit=limit - len(results),
        )
        results.extend(standard_results)

        return results[:limit]

    def _matches_task_filters(
        self,
        reflection: TaskReflection,
        filters: dict[str, Any],
    ) -> bool:
        """Check if task reflection matches filters."""
        # Outcome filter
        if "outcome" in filters and reflection.outcome != filters["outcome"]:
            return False

        # Has lessons filter
        if filters.get("has_lessons") and not reflection.lessons:
            return False

        # Has false constraints filter
        if filters.get("has_false_constraints"):
            if not reflection.false_constraints:
                return False

        # Related decision filter
        if "related_decision" in filters:
            if filters["related_decision"] not in reflection.related_decisions:
                return False

        return True

    def _query_standard_reflections(
        self,
        reflection_type: ReflectionType | None,
        tags: list[str] | None,
        min_confidence: float,
        priority: ReflectionPriority | None,
        limit: int,
    ) -> list[Reflection]:
        """Query standard reflections (existing method renamed internally)."""
        results: list[Reflection] = []

        if reflection_type:
            candidates = [
                self._reflections[rid]
                for rid in self._type_index.get(reflection_type, [])
                if rid in self._reflections
            ]
        else:
            candidates = list(self._reflections.values())

        for reflection in candidates:
            if reflection.confidence < min_confidence:
                continue

            if priority and reflection.priority != priority:
                continue

            if tags and not any(tag in reflection.tags for tag in tags):
                continue

            results.append(reflection)

            if len(results) >= limit:
                break

        return results

    def get_task_reflection(self, task_id: str) -> TaskReflection | None:
        """Get task reflection by ID."""
        return self._task_reflections.get(task_id)

    def get_successful_patterns(self, limit: int = 20) -> list[str]:
        """Get patterns that led to successful outcomes."""
        patterns = set()

        for reflection in self._task_reflections.values():
            if reflection.outcome == "success":
                patterns.update(reflection.helpful_patterns)

        return list(patterns)[:limit]

    def get_common_failures(self, limit: int = 20) -> list[str]:
        """Get commonly occurring failures."""
        failures: dict[str, int] = {}

        for reflection in self._task_reflections.values():
            for failure in reflection.what_failed:
                failures[failure] = failures.get(failure, 0) + 1

        sorted_failures = sorted(failures.items(), key=lambda x: x[1], reverse=True)
        return [f[0] for f in sorted_failures[:limit]]

    def get_false_constraints(self, limit: int = 20) -> list[str]:
        """Get constraints that were identified as false."""
        constraints = set()

        for reflection in self._task_reflections.values():
            constraints.update(reflection.false_constraints)

        return list(constraints)[:limit]

    def get_recommendations_for_context(
        self,
        context: str,
        limit: int = 10,
    ) -> list[str]:
        """Get recommendations relevant to a context."""
        context_lower = context.lower()
        recommendations: list[tuple[str, float]] = []

        for reflection in self._task_reflections.values():
            # Simple relevance scoring
            relevance = 0.0
            if context_lower in reflection.task_description.lower():
                relevance += 0.5
            for lesson in reflection.lessons:
                if context_lower in lesson.lower():
                    relevance += 0.3

            if relevance > 0:
                for rec in reflection.recommendations:
                    recommendations.append((rec, relevance))

        # Sort by relevance and dedupe
        sorted_recs = sorted(recommendations, key=lambda x: x[1], reverse=True)
        seen = set()
        unique_recs = []
        for rec, _ in sorted_recs:
            if rec not in seen:
                seen.add(rec)
                unique_recs.append(rec)
                if len(unique_recs) >= limit:
                    break

        return unique_recs

    # ==========================================================================
    # IR Engine Integration (v2.0.0)
    # ==========================================================================

    def popup_examples_for_ir_engine(
        self,
        intent_type: str | None = None,
        action_type: str | None = None,
        context: str | None = None,
        outcome_filter: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get relevant examples for the IR Engine.

        Provides contextual examples of past decisions and their outcomes
        to inform IR graph generation and constraint challenging.

        Args:
            intent_type: Filter by intent type (e.g., "create_file", "refactor")
            action_type: Filter by action type (e.g., "code_write", "api_call")
            context: Free-text context to match against
            outcome_filter: Filter by outcome ("success", "failure", "partial")
            limit: Maximum examples to return

        Returns:
            List of example dicts with:
                - task_id: str
                - task_description: str
                - outcome: str
                - relevant_lessons: list[str]
                - what_worked: list[str]
                - what_failed: list[str]
                - patterns_used: list[str]
                - relevance_score: float
        """
        examples: list[dict[str, Any]] = []

        for task_reflection in self._task_reflections.values():
            # Calculate relevance score
            relevance = 0.0
            matches: list[str] = []

            # Match by context
            if context:
                context_lower = context.lower()
                if context_lower in task_reflection.task_description.lower():
                    relevance += 0.4
                    matches.append("task_description")

                for lesson in task_reflection.lessons:
                    if context_lower in lesson.lower():
                        relevance += 0.2
                        matches.append("lesson")
                        break

                for pattern in task_reflection.helpful_patterns:
                    if context_lower in pattern.lower():
                        relevance += 0.2
                        matches.append("pattern")
                        break

            # Match by outcome
            if outcome_filter:
                if task_reflection.outcome == outcome_filter:
                    relevance += 0.3
                    matches.append("outcome")
                else:
                    continue  # Skip non-matching outcomes

            # Match by intent/action type in metadata
            metadata = task_reflection.metadata
            if intent_type:
                if metadata.get("intent_type") == intent_type:
                    relevance += 0.3
                    matches.append("intent_type")
                elif intent_type.lower() in task_reflection.task_description.lower():
                    relevance += 0.15
                    matches.append("intent_mention")

            if action_type:
                if metadata.get("action_type") == action_type:
                    relevance += 0.3
                    matches.append("action_type")
                elif (
                    action_type.lower()
                    in " ".join(
                        task_reflection.what_worked + task_reflection.what_failed
                    ).lower()
                ):
                    relevance += 0.15
                    matches.append("action_mention")

            # Add to examples if relevant
            if relevance > 0 or (not context and not intent_type and not action_type):
                # Default relevance for unfiltered queries
                if relevance == 0:
                    relevance = 0.1

                examples.append(
                    {
                        "task_id": task_reflection.task_id,
                        "task_description": task_reflection.task_description,
                        "outcome": task_reflection.outcome,
                        "relevant_lessons": task_reflection.lessons[:3],
                        "what_worked": task_reflection.what_worked[:3],
                        "what_failed": task_reflection.what_failed[:3],
                        "patterns_used": task_reflection.helpful_patterns[:3],
                        "relevance_score": relevance,
                        "match_reasons": matches,
                    }
                )

        # Sort by relevance and limit
        examples.sort(key=lambda x: x["relevance_score"], reverse=True)

        return examples[:limit]

    def get_lessons_for_constraint_challenge(
        self,
        constraint_description: str,
        constraint_type: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get lessons relevant to challenging a constraint.

        Provides evidence about whether similar constraints were
        actually necessary or turned out to be false assumptions.

        Args:
            constraint_description: Description of constraint to challenge
            constraint_type: Type of constraint (e.g., "security", "performance")
            limit: Maximum lessons to return

        Returns:
            List of lesson dicts with:
                - lesson: str
                - from_task_id: str
                - was_false_constraint: bool
                - confidence: float
                - context: str
        """
        lessons: list[dict[str, Any]] = []
        constraint_lower = constraint_description.lower()

        for task_reflection in self._task_reflections.values():
            # Check if constraint matches false constraints
            for false_constraint in task_reflection.false_constraints:
                if (
                    constraint_lower in false_constraint.lower()
                    or false_constraint.lower() in constraint_lower
                ):
                    # Found a similar constraint that was false
                    lessons.append(
                        {
                            "lesson": f"Constraint '{false_constraint}' was identified as unnecessary",
                            "from_task_id": task_reflection.task_id,
                            "was_false_constraint": True,
                            "confidence": 0.8,
                            "context": task_reflection.task_description,
                            "supporting_evidence": task_reflection.what_worked[:2],
                        }
                    )

            # Check lessons that mention the constraint
            for lesson in task_reflection.lessons:
                if constraint_lower in lesson.lower():
                    lessons.append(
                        {
                            "lesson": lesson,
                            "from_task_id": task_reflection.task_id,
                            "was_false_constraint": False,
                            "confidence": 0.6,
                            "context": task_reflection.task_description,
                        }
                    )

        # Sort by confidence and false constraint priority
        lessons.sort(
            key=lambda x: (x["was_false_constraint"], x["confidence"]),
            reverse=True,
        )

        return lessons[:limit]

    def get_patterns_for_intent(
        self,
        intent_description: str,
        intent_type: str | None = None,
        outcome_preference: str = "success",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get patterns that have worked for similar intents.

        Args:
            intent_description: Description of the intent
            intent_type: Type of intent (e.g., "create", "modify", "delete")
            outcome_preference: Preferred outcome ("success", "any")
            limit: Maximum patterns to return

        Returns:
            List of pattern dicts with:
                - pattern_name: str
                - success_count: int
                - failure_count: int
                - success_rate: float
                - example_tasks: list[str]
                - recommendations: list[str]
        """
        # Aggregate patterns across task reflections
        pattern_stats: dict[str, dict[str, Any]] = {}
        intent_lower = intent_description.lower()

        for task_reflection in self._task_reflections.values():
            # Check if task is relevant to intent
            relevant = intent_lower in task_reflection.task_description.lower()

            if not relevant and intent_type:
                relevant = (
                    intent_type.lower() in task_reflection.task_description.lower()
                )

            if not relevant:
                continue

            # Aggregate patterns from this task
            for pattern in task_reflection.helpful_patterns:
                if pattern not in pattern_stats:
                    pattern_stats[pattern] = {
                        "pattern_name": pattern,
                        "success_count": 0,
                        "failure_count": 0,
                        "example_tasks": [],
                        "recommendations": [],
                    }

                if task_reflection.outcome == "success":
                    pattern_stats[pattern]["success_count"] += 1
                else:
                    pattern_stats[pattern]["failure_count"] += 1

                pattern_stats[pattern]["example_tasks"].append(task_reflection.task_id)
                pattern_stats[pattern]["recommendations"].extend(
                    task_reflection.recommendations[:2]
                )

        # Calculate success rates and prepare results
        results = []
        for pattern_name, stats in pattern_stats.items():
            total = stats["success_count"] + stats["failure_count"]
            success_rate = stats["success_count"] / total if total > 0 else 0.0

            # Filter by outcome preference
            if outcome_preference == "success" and success_rate < 0.5:
                continue

            results.append(
                {
                    "pattern_name": pattern_name,
                    "success_count": stats["success_count"],
                    "failure_count": stats["failure_count"],
                    "success_rate": success_rate,
                    "example_tasks": list(set(stats["example_tasks"]))[:3],
                    "recommendations": list(set(stats["recommendations"]))[:3],
                }
            )

        # Sort by success rate
        results.sort(key=lambda x: x["success_rate"], reverse=True)

        return results[:limit]

    def store_lesson(
        self,
        lesson: str,
        context: str,
        task_id: str | None = None,
        tags: list[str] | None = None,
        confidence: float = 0.8,
    ) -> Reflection:
        """
        Store a lesson learned.

        Convenience method for adding lessons from IR Engine or other components.

        Args:
            lesson: The lesson content
            context: Context where lesson was learned
            task_id: Optional associated task ID
            tags: Optional tags for categorization
            confidence: Confidence in the lesson

        Returns:
            Created Reflection instance
        """
        effective_tags = tags or []
        if task_id:
            effective_tags.append(f"task:{task_id}")

        return self.add_reflection(
            content=lesson,
            reflection_type=ReflectionType.LESSON,
            context=context,
            priority=ReflectionPriority.MEDIUM,
            confidence=confidence,
            source=task_id or "ir_engine",
            tags=effective_tags,
        )

    def store_failure_analysis(
        self,
        failure_description: str,
        root_cause: str,
        task_id: str | None = None,
        recommended_fix: str | None = None,
        confidence: float = 0.7,
    ) -> Reflection:
        """
        Store a failure analysis.

        Args:
            failure_description: What failed
            root_cause: Why it failed
            task_id: Optional associated task ID
            recommended_fix: Suggested fix
            confidence: Confidence in analysis

        Returns:
            Created Reflection instance
        """
        content = f"Failure: {failure_description}\nRoot cause: {root_cause}"
        if recommended_fix:
            content += f"\nRecommended fix: {recommended_fix}"

        tags = ["failure_analysis"]
        if task_id:
            tags.append(f"task:{task_id}")

        return self.add_reflection(
            content=content,
            reflection_type=ReflectionType.FAILURE_ANALYSIS,
            context=failure_description,
            priority=ReflectionPriority.HIGH,
            confidence=confidence,
            source=task_id or "ir_engine",
            tags=tags,
            metadata={
                "root_cause": root_cause,
                "recommended_fix": recommended_fix,
            },
        )

    # ==========================================================================
    # Statistics
    # ==========================================================================

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        type_counts = {rt.value: len(ids) for rt, ids in self._type_index.items()}

        # Task reflection stats (v1.2.0)
        outcome_counts = {"success": 0, "partial": 0, "failure": 0, "unknown": 0}
        for ref in self._task_reflections.values():
            if ref.outcome in outcome_counts:
                outcome_counts[ref.outcome] += 1

        return {
            "total_reflections": len(self._reflections),
            "total_patterns": len(self._patterns),
            "total_improvements": len(self._improvements),
            "reflections_by_type": type_counts,
            "unique_tags": len(self._tag_index),
            "pending_improvements": len(self.get_pending_improvements()),
            # v1.2.0 additions
            "task_reflections": len(self._task_reflections),
            "task_outcomes": outcome_counts,
        }

    # ==========================================================================
    # Serialization
    # ==========================================================================

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "reflections": [r.to_dict() for r in self._reflections.values()],
            "patterns": [p.to_dict() for p in self._patterns.values()],
            "improvements": [i.to_dict() for i in self._improvements.values()],
            # v1.2.0 additions
            "task_reflections": [
                tr.to_dict() for tr in self._task_reflections.values()
            ],
        }

    def from_dict(self, data: dict[str, Any]) -> None:
        """Load from dictionary."""
        self._reflections.clear()
        self._patterns.clear()
        self._improvements.clear()
        self._tag_index.clear()
        self._type_index = {rt: [] for rt in ReflectionType}
        self._task_reflections.clear()
        self._task_index.clear()

        for r_data in data.get("reflections", []):
            reflection = Reflection.from_dict(r_data)
            self._reflections[reflection.reflection_id] = reflection
            self._type_index[reflection.reflection_type].append(
                reflection.reflection_id
            )
            for tag in reflection.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = []
                self._tag_index[tag].append(reflection.reflection_id)

        # v1.2.0: Restore task reflections
        for tr_data in data.get("task_reflections", []):
            task_ref = TaskReflection.from_dict(tr_data)
            self._task_reflections[task_ref.task_id] = task_ref

            # Rebuild index
            outcome_key = f"outcome:{task_ref.outcome}"
            if outcome_key not in self._task_index:
                self._task_index[outcome_key] = []
            self._task_index[outcome_key].append(task_ref.task_id)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-007",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "data-models",
        "dataclass",
        "debugging",
        "learning",
        "logging",
        "metrics",
        "rest-api",
    ],
    "keywords": [
        "analysis",
        "challenge",
        "common",
        "confidence",
        "constraint",
        "constraints",
        "delete",
        "engine",
    ],
    "business_value": "Provides reflection memory components including ReflectionType, ReflectionPriority, Reflection",
    "last_modified": "2026-01-14T16:24:36Z",
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
