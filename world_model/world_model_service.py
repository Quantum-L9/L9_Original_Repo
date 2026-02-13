"""
L9 World Model - Service Layer API
===================================

High-level service API for World Model operations.

Provides:
- get_context(): Get full context for reasoning tasks
- get_constraints(): Get active constraints from world state
- get_patterns(): Get matching architectural patterns
- get_heuristics(): Get applicable coding heuristics

This service is the primary integration point for:
- IR Engine: Query context and constraints for IR generation
- Orchestration: Get patterns for task planning
- Agents: Get heuristics for code generation
- Simulation: Get constraints for validation

Integration:
- WorldModelEngine: Core state and query operations
- WorldModelRuntime: Seed loading and packet processing
- ReflectionMemory: Lessons and examples
- CausalMapper: Causal relationships
- KnowledgeIngestor: Pattern/heuristic normalization

Version: 2.0.0 (full service layer per README_RUNTIMES.md)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Service Layer API",
    "module_version": "2.0.0 (full service layer per README_RUNTIMES.md)",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "learning",
    "domain": "world_model",
    "module_name": "world_model_service",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["world_model.__init__"],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog

if TYPE_CHECKING:
    from world_model.causal_mapper import CausalMapper
    from world_model.engine import WorldModelEngine
    from world_model.knowledge_ingestor import KnowledgeIngestor
    from world_model.reflection_memory import ReflectionMemory
    from world_model.runtime import WorldModelRuntime

logger = structlog.get_logger(__name__)


# =============================================================================
# Context and Query Data Classes
# =============================================================================


@dataclass
class WorldContext:
    """Full context for reasoning tasks."""

    context_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Entities and relationships
    entities: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)

    # Patterns and heuristics
    patterns: list[dict[str, Any]] = field(default_factory=list)
    heuristics: list[dict[str, Any]] = field(default_factory=list)

    # Constraints
    active_constraints: list[dict[str, Any]] = field(default_factory=list)
    hidden_constraints: list[dict[str, Any]] = field(default_factory=list)

    # Reflections
    lessons: list[dict[str, Any]] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)

    # Causal context
    causal_nodes: list[dict[str, Any]] = field(default_factory=list)
    causal_edges: list[dict[str, Any]] = field(default_factory=list)

    # Statistics
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "context_id": self.context_id,
            "timestamp": self.timestamp.isoformat(),
            "entities": self.entities,
            "relations": self.relations,
            "patterns": self.patterns,
            "heuristics": self.heuristics,
            "active_constraints": self.active_constraints,
            "hidden_constraints": self.hidden_constraints,
            "lessons": self.lessons,
            "examples": self.examples,
            "causal_nodes": self.causal_nodes,
            "causal_edges": self.causal_edges,
            "stats": self.stats,
        }


@dataclass
class ConstraintSet:
    """Set of constraints for validation."""

    constraint_set_id: str = field(default_factory=lambda: str(uuid4()))

    # Explicit constraints from IR/specs
    explicit_constraints: list[dict[str, Any]] = field(default_factory=list)

    # Hidden constraints detected from patterns
    hidden_constraints: list[dict[str, Any]] = field(default_factory=list)

    # Resource constraints
    resource_constraints: list[dict[str, Any]] = field(default_factory=list)

    # Temporal constraints
    temporal_constraints: list[dict[str, Any]] = field(default_factory=list)

    # False constraints (from reflection memory)
    false_constraints: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert constraint set to dictionary."""
        return {
            "constraint_set_id": self.constraint_set_id,
            "explicit_constraints": self.explicit_constraints,
            "hidden_constraints": self.hidden_constraints,
            "resource_constraints": self.resource_constraints,
            "temporal_constraints": self.temporal_constraints,
            "false_constraints": self.false_constraints,
            "total_count": (
                len(self.explicit_constraints)
                + len(self.hidden_constraints)
                + len(self.resource_constraints)
                + len(self.temporal_constraints)
            ),
        }


@dataclass
class PatternMatch:
    """A matched architectural pattern."""

    pattern_id: str
    name: str
    category: str
    description: str
    match_score: float = 0.0
    applicable_when: list[str] = field(default_factory=list)
    anti_applicable_when: list[str] = field(default_factory=list)
    tradeoffs: dict[str, list[str]] = field(default_factory=dict)
    past_success_rate: float = 0.0
    example_uses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert pattern match to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "match_score": self.match_score,
            "applicable_when": self.applicable_when,
            "tradeoffs": self.tradeoffs,
            "past_success_rate": self.past_success_rate,
            "example_uses": self.example_uses,
        }


@dataclass
class HeuristicMatch:
    """A matched coding heuristic."""

    heuristic_id: str
    rule: str
    category: str
    severity: str
    description: str = ""
    match_score: float = 0.0
    example_good: str = ""
    example_bad: str = ""
    auto_fix_strategy: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert heuristic match to dictionary."""
        return {
            "heuristic_id": self.heuristic_id,
            "rule": self.rule,
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "match_score": self.match_score,
            "example_good": self.example_good,
            "example_bad": self.example_bad,
            "auto_fix_strategy": self.auto_fix_strategy,
            "confidence": self.confidence,
        }


# =============================================================================
# World Model Service
# =============================================================================


class WorldModelServiceAPI:
    """
    High-level service API for World Model operations.

    Provides unified access to:
    - Context gathering for reasoning
    - Constraint discovery and validation
    - Pattern matching for architecture decisions
    - Heuristic matching for code quality

    Usage:
        service = WorldModelServiceAPI(engine, runtime)

        # Get full context
        context = service.get_context(
            intent="create a REST API endpoint",
            include_patterns=True,
            include_heuristics=True,
        )

        # Get constraints
        constraints = service.get_constraints(
            context="api_development",
            include_hidden=True,
        )

        # Get matching patterns
        patterns = service.get_patterns(
            intent="create",
            category="structural",
        )

        # Get applicable heuristics
        heuristics = service.get_heuristics(
            code_context="python_async",
            severity_min="medium",
        )
    """

    def __init__(
        self,
        engine: WorldModelEngine | None = None,
        runtime: WorldModelRuntime | None = None,
    ):
        """
        Initialize the service API.

        Args:
            engine: WorldModelEngine instance
            runtime: WorldModelRuntime instance (optional, for seed access)
        """
        self._engine = engine
        self._runtime = runtime
        self._initialized = False

        # Lazy component references
        self._reflection_memory: ReflectionMemory | None = None
        self._causal_mapper: CausalMapper | None = None
        self._ingestor: KnowledgeIngestor | None = None

        logger.info("WorldModelServiceAPI initialized (v2.0.0)")

    async def initialize(self) -> dict[str, Any]:
        """
        Initialize the service and components.

        Returns:
            Initialization result dict
        """
        if self._initialized:
            return {"success": True, "already_initialized": True}

        errors: list[str] = []

        try:
            # Initialize engine if provided
            if self._engine and not self._engine.is_initialized:
                await self._engine.initialize_state()

            # Get component references from engine
            if self._engine:
                self._reflection_memory = self._engine.get_reflection_memory()
                self._causal_mapper = self._engine.get_causal_mapper()
                self._ingestor = self._engine.get_ingestor()

            # Load seeds via runtime if available
            if self._runtime and not self._runtime.seeds_loaded:
                seed_result = await self._runtime.load_seed_library()
                if not seed_result.get("success"):
                    errors.extend(seed_result.get("errors", []))

            self._initialized = True

        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            errors.append(str(e))

        return {
            "success": len(errors) == 0,
            "initialized": self._initialized,
            "errors": errors,
        }

    # ==========================================================================
    # get_context()
    # ==========================================================================

    def get_context(
        self,
        intent: str | None = None,
        task_id: str | None = None,
        include_entities: bool = True,
        include_relations: bool = True,
        include_patterns: bool = True,
        include_heuristics: bool = True,
        include_constraints: bool = True,
        include_lessons: bool = True,
        include_examples: bool = True,
        include_causal: bool = False,
        entity_types: list[str] | None = None,
        limit: int = 50,
    ) -> WorldContext:
        """
        Get full context for reasoning tasks.

        Gathers relevant information from all world model components
        to support IR generation, constraint challenging, and planning.

        Args:
            intent: Optional intent description to filter relevance
            task_id: Optional task ID to filter by
            include_entities: Include world model entities
            include_relations: Include entity relationships
            include_patterns: Include architectural patterns
            include_heuristics: Include coding heuristics
            include_constraints: Include constraints (explicit and hidden)
            include_lessons: Include lessons learned
            include_examples: Include relevant examples
            include_causal: Include causal graph structure
            entity_types: Filter entities by types
            limit: Maximum items per category

        Returns:
            WorldContext with gathered information
        """
        context = WorldContext()

        # Gather entities
        if include_entities and self._engine:
            state = self._engine.get_state()
            if state:
                entities = state.list_entities()

                # Filter by types if specified
                if entity_types:
                    entities = [e for e in entities if e.entity_type in entity_types]

                for entity in entities[:limit]:
                    context.entities.append(
                        {
                            "entity_id": entity.entity_id,
                            "entity_type": entity.entity_type,
                            "attributes": entity.attributes,
                        }
                    )

        # Gather relations
        if include_relations and self._engine:
            state = self._engine.get_state()
            if state:
                # Get all relations (limited)
                seen_relations = set()
                for entity in context.entities[: limit // 2]:
                    relations = state.get_relations(entity["entity_id"])
                    for rel in relations:
                        if rel.relation_id not in seen_relations:
                            context.relations.append(
                                {
                                    "relation_id": rel.relation_id,
                                    "relation_type": rel.relation_type,
                                    "source_id": rel.source_id,
                                    "target_id": rel.target_id,
                                }
                            )
                            seen_relations.add(rel.relation_id)
                            if len(context.relations) >= limit:
                                break

        # Gather patterns
        if include_patterns:
            patterns = self.get_patterns(intent=intent, limit=limit)
            context.patterns = [p.to_dict() for p in patterns]

        # Gather heuristics
        if include_heuristics:
            heuristics = self.get_heuristics(code_context=intent, limit=limit)
            context.heuristics = [h.to_dict() for h in heuristics]

        # Gather constraints
        if include_constraints:
            constraint_set = self.get_constraints(
                context=intent,
                include_hidden=True,
            )
            context.active_constraints = constraint_set.explicit_constraints
            context.hidden_constraints = constraint_set.hidden_constraints

        # Gather lessons
        if include_lessons and self._reflection_memory:
            lessons = self._reflection_memory.get_high_confidence_lessons(
                min_confidence=0.7
            )
            for lesson in lessons[:limit]:
                context.lessons.append(lesson.to_dict())

        # Gather examples
        if include_examples and self._reflection_memory:
            examples = self._reflection_memory.popup_examples_for_ir_engine(
                context=intent,
                limit=limit,
            )
            context.examples = examples

        # Gather causal structure
        if include_causal and self._causal_mapper:
            self._causal_mapper.get_stats()
            causal_data = self._causal_mapper.to_dict()

            context.causal_nodes = causal_data.get("nodes", [])[:limit]
            context.causal_edges = causal_data.get("edges", [])[:limit]

        # Compute statistics
        context.stats = {
            "entity_count": len(context.entities),
            "relation_count": len(context.relations),
            "pattern_count": len(context.patterns),
            "heuristic_count": len(context.heuristics),
            "constraint_count": len(context.active_constraints)
            + len(context.hidden_constraints),
            "lesson_count": len(context.lessons),
            "example_count": len(context.examples),
        }

        logger.info(f"Context gathered: {context.stats}")

        return context

    # ==========================================================================
    # get_constraints()
    # ==========================================================================

    def get_constraints(
        self,
        context: str | None = None,
        constraint_types: list[str] | None = None,
        include_hidden: bool = True,
        include_false: bool = True,
        min_confidence: float = 0.5,
    ) -> ConstraintSet:
        """
        Get active constraints from world state.

        Discovers and returns:
        - Explicit constraints from IR graphs and specifications
        - Hidden constraints detected from causal patterns
        - Resource constraints from outcome metrics
        - Temporal constraints from execution timing
        - False constraints identified from reflections

        Args:
            context: Optional context to filter relevance
            constraint_types: Filter by constraint types
            include_hidden: Include detected hidden constraints
            include_false: Include known false constraints
            min_confidence: Minimum confidence threshold

        Returns:
            ConstraintSet with categorized constraints
        """
        constraint_set = ConstraintSet()

        # Get explicit constraints from world model entities
        if self._engine:
            state = self._engine.get_state()
            if state:
                constraint_entities = state.list_entities("constraint")

                for entity in constraint_entities:
                    confidence = entity.attributes.get("confidence", 1.0)
                    if confidence < min_confidence:
                        continue

                    # Filter by type if specified
                    entity_type = entity.attributes.get("constraint_type", "unknown")
                    if constraint_types and entity_type not in constraint_types:
                        continue

                    constraint_set.explicit_constraints.append(
                        {
                            "constraint_id": entity.entity_id,
                            "constraint_type": entity_type,
                            "description": entity.attributes.get("description", ""),
                            "status": entity.attributes.get("status", "active"),
                            "confidence": confidence,
                        }
                    )

        # Get hidden constraints from causal mapper
        if include_hidden and self._causal_mapper:
            hidden = self._causal_mapper.detect_hidden_constraints(
                context={"domain": context} if context else None,
                min_confidence=min_confidence,
            )

            for constraint in hidden:
                c_type = constraint.get("constraint_type", "unknown")

                if c_type == "resource":
                    constraint_set.resource_constraints.append(constraint)
                elif c_type == "temporal":
                    constraint_set.temporal_constraints.append(constraint)
                else:
                    constraint_set.hidden_constraints.append(constraint)

        # Get false constraints from reflection memory
        if include_false and self._reflection_memory:
            false_constraints = self._reflection_memory.get_false_constraints(limit=20)

            for fc in false_constraints:
                constraint_set.false_constraints.append(
                    {
                        "description": fc,
                        "source": "reflection_memory",
                        "recommendation": "Consider removing or relaxing this constraint",
                    }
                )

        logger.info(
            f"Constraints gathered: {len(constraint_set.explicit_constraints)} explicit, "
            f"{len(constraint_set.hidden_constraints)} hidden, "
            f"{len(constraint_set.false_constraints)} false"
        )

        return constraint_set

    # ==========================================================================
    # get_patterns()
    # ==========================================================================

    def get_patterns(
        self,
        intent: str | None = None,
        category: str | None = None,
        applicable_to: list[str] | None = None,
        min_success_rate: float = 0.0,
        limit: int = 20,
    ) -> list[PatternMatch]:
        """
        Get matching architectural patterns.

        Returns patterns relevant to the given context with:
        - Match scoring based on applicability
        - Historical success rates from reflections
        - Example uses from past tasks

        Args:
            intent: Intent description to match against
            category: Filter by pattern category
            applicable_to: List of conditions to match
            min_success_rate: Minimum historical success rate
            limit: Maximum patterns to return

        Returns:
            List of PatternMatch instances sorted by relevance
        """
        matches: list[PatternMatch] = []

        if not self._engine:
            return matches

        state = self._engine.get_state()
        if not state:
            return matches

        # Get pattern entities
        pattern_entities = state.list_entities("architectural_pattern")

        for entity in pattern_entities:
            # Filter by category
            entity_category = entity.attributes.get("category", "unknown")
            if category and entity_category != category:
                continue

            # Calculate match score
            match_score = 0.0
            applicable_when = entity.attributes.get("applicable_when", [])
            anti_applicable_when = entity.attributes.get("anti_applicable_when", [])

            # Score based on intent matching
            if intent:
                intent_lower = intent.lower()
                name = entity.attributes.get("name", "").lower()
                description = entity.attributes.get("description", "").lower()

                if intent_lower in name or intent_lower in description:
                    match_score += 0.5

                # Check applicability conditions
                for condition in applicable_when:
                    if intent_lower in condition.lower():
                        match_score += 0.2

                # Reduce score for anti-applicability
                for anti_condition in anti_applicable_when:
                    if intent_lower in anti_condition.lower():
                        match_score -= 0.3
            else:
                # Default score if no intent filter
                match_score = 0.5

            # Check explicit applicable_to conditions
            if applicable_to:
                for condition in applicable_to:
                    if condition in applicable_when:
                        match_score += 0.3

            # Get historical success rate from reflection memory
            past_success_rate = 0.0
            example_uses: list[str] = []

            if self._reflection_memory:
                pattern_name = entity.attributes.get("name", "")
                patterns_data = self._reflection_memory.get_patterns_for_intent(
                    intent_description=intent or "",
                    limit=5,
                )

                for pd in patterns_data:
                    if pd.get("pattern_name", "") == pattern_name:
                        past_success_rate = pd.get("success_rate", 0.0)
                        example_uses = pd.get("example_tasks", [])
                        break

            # Apply success rate filter
            if past_success_rate < min_success_rate:
                continue

            # Skip if match score is too low
            if match_score <= 0:
                continue

            matches.append(
                PatternMatch(
                    pattern_id=entity.entity_id,
                    name=entity.attributes.get("name", "Unknown"),
                    category=entity_category,
                    description=entity.attributes.get("description", ""),
                    match_score=match_score,
                    applicable_when=applicable_when,
                    anti_applicable_when=anti_applicable_when,
                    tradeoffs=entity.attributes.get("tradeoffs", {}),
                    past_success_rate=past_success_rate,
                    example_uses=example_uses,
                )
            )

        # Sort by match score
        matches.sort(key=lambda p: p.match_score, reverse=True)

        logger.info(f"Found {len(matches[:limit])} matching patterns")

        return matches[:limit]

    # ==========================================================================
    # get_heuristics()
    # ==========================================================================

    def get_heuristics(
        self,
        code_context: str | None = None,
        category: str | None = None,
        severity_min: str = "low",
        language: str | None = None,
        limit: int = 20,
    ) -> list[HeuristicMatch]:
        """
        Get applicable coding heuristics.

        Returns heuristics relevant to the given context with:
        - Match scoring based on code context
        - Severity filtering
        - Auto-fix strategies where available

        Args:
            code_context: Code or description context to match
            category: Filter by heuristic category
            severity_min: Minimum severity level ("low", "medium", "high", "critical")
            language: Programming language filter
            limit: Maximum heuristics to return

        Returns:
            List of HeuristicMatch instances sorted by relevance
        """
        matches: list[HeuristicMatch] = []

        severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4, "info": 0}
        min_severity_value = severity_order.get(severity_min.lower(), 1)

        if not self._engine:
            return matches

        state = self._engine.get_state()
        if not state:
            return matches

        # Get heuristic entities
        heuristic_entities = state.list_entities("coding_heuristic")

        for entity in heuristic_entities:
            # Filter by category
            entity_category = entity.attributes.get("category", "unknown")
            if category and entity_category != category:
                continue

            # Filter by severity
            severity = entity.attributes.get("severity", "medium")
            severity_value = severity_order.get(severity.lower(), 2)
            if severity_value < min_severity_value:
                continue

            # Calculate match score
            match_score = 0.0

            if code_context:
                context_lower = code_context.lower()
                rule = entity.attributes.get("rule", "").lower()
                description = entity.attributes.get("description", "").lower()

                if context_lower in rule or context_lower in description:
                    match_score += 0.5

                # Language-specific boost
                if language:
                    if language.lower() in entity_category.lower():
                        match_score += 0.3
            else:
                # Default score if no context filter
                match_score = 0.5

            # Boost by severity
            match_score += severity_value * 0.1

            # Get confidence from entity
            confidence = entity.attributes.get("confidence", 1.0)

            matches.append(
                HeuristicMatch(
                    heuristic_id=entity.entity_id,
                    rule=entity.attributes.get("rule", ""),
                    category=entity_category,
                    severity=severity,
                    description=entity.attributes.get("description", ""),
                    match_score=match_score,
                    example_good=entity.attributes.get("example_good", ""),
                    example_bad=entity.attributes.get("example_bad", ""),
                    auto_fix_strategy=entity.attributes.get("auto_fix_strategy", []),
                    confidence=confidence,
                )
            )

        # Sort by match score
        matches.sort(key=lambda h: h.match_score, reverse=True)

        logger.info(f"Found {len(matches[:limit])} matching heuristics")

        return matches[:limit]

    # ==========================================================================
    # Additional Service Methods
    # ==========================================================================

    def get_examples_for_intent(
        self,
        intent_type: str,
        action_type: str | None = None,
        outcome_preference: str = "success",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get examples of past executions for an intent type.

        Delegates to ReflectionMemory.popup_examples_for_ir_engine().

        Args:
            intent_type: Type of intent to find examples for
            action_type: Optional action type filter
            outcome_preference: Preferred outcome filter
            limit: Maximum examples to return

        Returns:
            List of example dicts
        """
        if not self._reflection_memory:
            return []

        return self._reflection_memory.popup_examples_for_ir_engine(
            intent_type=intent_type,
            action_type=action_type,
            outcome_filter=outcome_preference,
            limit=limit,
        )

    def get_lessons_for_constraint(
        self,
        constraint_description: str,
        constraint_type: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get lessons about a specific constraint.

        Delegates to ReflectionMemory.get_lessons_for_constraint_challenge().

        Args:
            constraint_description: Constraint to get lessons about
            constraint_type: Optional constraint type
            limit: Maximum lessons to return

        Returns:
            List of lesson dicts
        """
        if not self._reflection_memory:
            return []

        return self._reflection_memory.get_lessons_for_constraint_challenge(
            constraint_description=constraint_description,
            constraint_type=constraint_type,
            limit=limit,
        )

    def record_decision_outcome(
        self,
        decision_id: str,
        description: str,
        outcome: str,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Record a decision outcome for causal learning.

        Args:
            decision_id: ID of the decision
            description: Description of what happened
            outcome: Result ("success", "failure", "partial")
            metrics: Optional metrics

        Returns:
            Recording result dict
        """
        if not self._causal_mapper:
            return {"success": False, "error": "Causal mapper not initialized"}

        outcome_obj = self._causal_mapper.record_outcome(
            outcome_id=f"outcome_{uuid4()}",
            outcome_type="execution_result",
            description=description,
            result=outcome,
            metrics=metrics or {},
            related_decisions=[decision_id],
        )

        return {
            "success": True,
            "outcome_id": outcome_obj.outcome_id,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        stats: dict[str, Any] = {
            "initialized": self._initialized,
            "has_engine": self._engine is not None,
            "has_runtime": self._runtime is not None,
            "has_reflection_memory": self._reflection_memory is not None,
            "has_causal_mapper": self._causal_mapper is not None,
        }

        if self._engine:
            stats["engine_stats"] = {
                "entity_count": self._engine.entity_count,
                "relation_count": self._engine.relation_count,
            }

        if self._reflection_memory:
            stats["reflection_stats"] = self._reflection_memory.get_stats()

        if self._causal_mapper:
            stats["causal_stats"] = self._causal_mapper.get_stats()

        return stats


# =============================================================================
# Singleton Access
# =============================================================================

_service: WorldModelServiceAPI | None = None


def get_world_model_service_api(
    engine: WorldModelEngine | None = None,
    runtime: WorldModelRuntime | None = None,
) -> WorldModelServiceAPI:
    """
    Get or create singleton service API.

    Args:
        engine: Optional WorldModelEngine to use
        runtime: Optional WorldModelRuntime to use

    Returns:
        WorldModelServiceAPI instance
    """
    global _service

    if _service is None:
        _service = WorldModelServiceAPI(engine=engine, runtime=runtime)
    elif engine is not None:
        _service._engine = engine
    elif runtime is not None:
        _service._runtime = runtime

    return _service


def reset_world_model_service_api() -> None:
    """Reset the singleton service API."""
    global _service
    _service = None
    logger.info("WorldModelServiceAPI reset")


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-LEAR-009",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "code-quality",
        "dataclass",
        "learning",
        "logging",
        "metrics",
        "rest-api",
        "service",
        "world-model",
    ],
    "keywords": [
        "api",
        "constraint",
        "constraints",
        "decision",
        "examples",
        "full",
        "generation",
        "heuristic",
    ],
    "business_value": "get_context(): Get full context for reasoning tasks get_constraints(): Get active constraints from world state get_patterns(): Get matching architectural patterns get_heuristics(): Get applicable codi",
    "last_modified": "2026-01-07T13:35:58Z",
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
