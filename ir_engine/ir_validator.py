"""
L9 IR Engine - IR Validator
===========================

Validates IR graphs for completeness, consistency, and correctness.

Validation checks:
- Schema compliance
- Referential integrity
- Constraint consistency
- Action dependency cycles
- Completeness requirements
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "IR Validator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "ir_compilation",
    "module_name": "ir_validator",
    "type": "validator",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["ir_engine.__init__", "ir_engine.deliberation_cell", "orchestration.orchestrator_kernel", "orchestration.unified_controller", "tests.ir_engine.test_ir_semantic_incremental", "tests.ir_engine.test_ir_semantic_to_plan_integration", "tests.ir_engine.test_ir_validation_and_status"],
    },
}
# ============================================================================

import structlog
from uuid import UUID

from ir_engine.ir_schema import (
    IRGraph,
    IRValidationResult,
    ConstraintNode,
    ConstraintStatus,
    IRStatus,
)

logger = structlog.get_logger(__name__)


class IRValidator:
    """
    Validates IR graphs for correctness and completeness.

    Performs multiple validation passes:
    1. Schema validation
    2. Referential integrity
    3. Constraint consistency
    4. Dependency analysis
    5. Completeness checks
    """

    def __init__(
        self,
        strict_mode: bool = False,
        require_actions: bool = True,
        max_constraint_depth: int = 10,
    ):
        """
        Initialize the validator.

        Args:
            strict_mode: If True, warnings become errors
            require_actions: If True, graphs must have at least one action
            max_constraint_depth: Maximum constraint application depth
        """
        self._strict_mode = strict_mode
        self._require_actions = require_actions
        self._max_constraint_depth = max_constraint_depth

        logger.info(f"IRValidator initialized (strict={strict_mode})")

    # ==========================================================================
    # Main Validation
    # ==========================================================================

    def validate(self, graph: IRGraph) -> IRValidationResult:
        """
        Validate an IR graph.

        Args:
            graph: The IR graph to validate

        Returns:
            IRValidationResult with errors, warnings, info
        """
        logger.info(f"Validating graph {graph.graph_id}")

        result = IRValidationResult(valid=True)

        # Run validation passes
        self._validate_schema(graph, result)
        self._validate_referential_integrity(graph, result)
        self._validate_constraints(graph, result)
        self._validate_dependencies(graph, result)
        self._validate_completeness(graph, result)

        # Log result
        if result.valid:
            logger.info(f"Graph {graph.graph_id} validated successfully")
        else:
            logger.warning(
                f"Graph {graph.graph_id} validation failed: "
                f"{len(result.errors)} errors, {len(result.warnings)} warnings"
            )

        return result

    # ==========================================================================
    # Validation Passes
    # ==========================================================================

    def _validate_schema(self, graph: IRGraph, result: IRValidationResult) -> None:
        """Validate schema compliance for all nodes."""

        # Validate intents
        for intent_id, intent in graph.intents.items():
            if not intent.description:
                result.add_error(
                    "INTENT_NO_DESCRIPTION",
                    f"Intent {intent_id} has no description",
                    intent_id,
                )

            if not intent.target:
                result.add_warning(
                    "INTENT_NO_TARGET",
                    f"Intent {intent_id} has no target specified",
                    intent_id,
                )

            if intent.confidence < 0.0 or intent.confidence > 1.0:
                result.add_error(
                    "INTENT_INVALID_CONFIDENCE",
                    f"Intent {intent_id} has invalid confidence: {intent.confidence}",
                    intent_id,
                )

        # Validate constraints
        for constraint_id, constraint in graph.constraints.items():
            if not constraint.description:
                result.add_error(
                    "CONSTRAINT_NO_DESCRIPTION",
                    f"Constraint {constraint_id} has no description",
                    constraint_id,
                )

            if constraint.confidence < 0.0 or constraint.confidence > 1.0:
                result.add_error(
                    "CONSTRAINT_INVALID_CONFIDENCE",
                    f"Constraint {constraint_id} has invalid confidence: {constraint.confidence}",
                    constraint_id,
                )

        # Validate actions
        for action_id, action in graph.actions.items():
            if not action.description:
                result.add_error(
                    "ACTION_NO_DESCRIPTION",
                    f"Action {action_id} has no description",
                    action_id,
                )

            if not action.target:
                result.add_warning(
                    "ACTION_NO_TARGET",
                    f"Action {action_id} has no target specified",
                    action_id,
                )

    def _validate_referential_integrity(
        self, graph: IRGraph, result: IRValidationResult
    ) -> None:
        """Validate all references between nodes are valid."""

        all_intent_ids = set(graph.intents.keys())
        all_constraint_ids = set(graph.constraints.keys())
        all_action_ids = set(graph.actions.keys())

        # Check intent parent references
        for intent_id, intent in graph.intents.items():
            if (
                intent.parent_intent_id
                and intent.parent_intent_id not in all_intent_ids
            ):
                result.add_error(
                    "INTENT_INVALID_PARENT",
                    f"Intent {intent_id} references non-existent parent {intent.parent_intent_id}",
                    intent_id,
                )

            for child_id in intent.child_intent_ids:
                if child_id not in all_intent_ids:
                    result.add_error(
                        "INTENT_INVALID_CHILD",
                        f"Intent {intent_id} references non-existent child {child_id}",
                        intent_id,
                    )

        # Check constraint applies_to references
        for constraint_id, constraint in graph.constraints.items():
            for applies_to_id in constraint.applies_to:
                if (
                    applies_to_id not in all_intent_ids
                    and applies_to_id not in all_action_ids
                ):
                    result.add_warning(
                        "CONSTRAINT_INVALID_REFERENCE",
                        f"Constraint {constraint_id} applies to non-existent node {applies_to_id}",
                        constraint_id,
                    )

        # Check action references
        for action_id, action in graph.actions.items():
            if (
                action.derived_from_intent
                and action.derived_from_intent not in all_intent_ids
            ):
                result.add_warning(
                    "ACTION_INVALID_INTENT_REF",
                    f"Action {action_id} derived from non-existent intent {action.derived_from_intent}",
                    action_id,
                )

            for constraint_id in action.constrained_by:
                if constraint_id not in all_constraint_ids:
                    result.add_warning(
                        "ACTION_INVALID_CONSTRAINT_REF",
                        f"Action {action_id} constrained by non-existent constraint {constraint_id}",
                        action_id,
                    )

            for dep_id in action.depends_on:
                if dep_id not in all_action_ids:
                    result.add_error(
                        "ACTION_INVALID_DEPENDENCY",
                        f"Action {action_id} depends on non-existent action {dep_id}",
                        action_id,
                    )

    def _validate_constraints(self, graph: IRGraph, result: IRValidationResult) -> None:
        """Validate constraint consistency."""

        # Check for conflicting constraints
        active_constraints = graph.get_active_constraints()

        for i, c1 in enumerate(active_constraints):
            for c2 in active_constraints[i + 1 :]:
                # Check if constraints apply to same targets
                common_targets = set(c1.applies_to) & set(c2.applies_to)

                if common_targets:
                    # Check for obvious conflicts (simple heuristic)
                    if self._constraints_conflict(c1, c2):
                        result.add_warning(
                            "CONSTRAINT_CONFLICT",
                            f"Constraints {c1.node_id} and {c2.node_id} may conflict",
                            c1.node_id,
                        )

        # Check for orphan constraints
        for constraint_id, constraint in graph.constraints.items():
            if not constraint.applies_to:
                result.add_info(
                    "CONSTRAINT_ORPHAN",
                    f"Constraint {constraint_id} does not apply to any nodes",
                    constraint_id,
                )

        # Check for false constraints that haven't been handled
        for constraint_id, constraint in graph.constraints.items():
            if (
                constraint.constraint_type.value == "false"
                and constraint.status == ConstraintStatus.ACTIVE
            ):
                result.add_warning(
                    "FALSE_CONSTRAINT_ACTIVE",
                    f"False constraint {constraint_id} is still active",
                    constraint_id,
                )

    def _constraints_conflict(self, c1: ConstraintNode, c2: ConstraintNode) -> bool:
        """Check if two constraints might conflict (heuristic)."""
        # Simple keyword-based conflict detection
        conflict_pairs = [
            ("must", "must not"),
            ("required", "forbidden"),
            ("always", "never"),
            ("include", "exclude"),
        ]

        desc1 = c1.description.lower()
        desc2 = c2.description.lower()

        for pos, neg in conflict_pairs:
            if (pos in desc1 and neg in desc2) or (neg in desc1 and pos in desc2):
                return True

        return False

    def _validate_dependencies(
        self, graph: IRGraph, result: IRValidationResult
    ) -> None:
        """Validate action dependencies for cycles."""

        # Build dependency graph
        visited: set[UUID] = set()
        rec_stack: set[UUID] = set()

        def has_cycle(action_id: UUID) -> bool:
            """DFS cycle detection."""
            visited.add(action_id)
            rec_stack.add(action_id)

            action = graph.get_action(action_id)
            if action:
                for dep_id in action.depends_on:
                    if dep_id not in visited:
                        if has_cycle(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(action_id)
            return False

        # Check each action
        for action_id in graph.actions:
            if action_id not in visited:
                if has_cycle(action_id):
                    result.add_error(
                        "DEPENDENCY_CYCLE",
                        f"Circular dependency detected involving action {action_id}",
                        action_id,
                    )

    def _validate_completeness(
        self, graph: IRGraph, result: IRValidationResult
    ) -> None:
        """Validate graph completeness."""

        # Check for intents
        if not graph.intents:
            result.add_error("NO_INTENTS", "Graph has no intents defined", None)

        # Check for actions (if required)
        if self._require_actions and not graph.actions:
            result.add_warning("NO_ACTIONS", "Graph has no actions defined", None)

        # Check for unhandled intents
        intent_ids = set(graph.intents.keys())
        intents_with_actions = {
            a.derived_from_intent
            for a in graph.actions.values()
            if a.derived_from_intent
        }

        unhandled = intent_ids - intents_with_actions
        for intent_id in unhandled:
            result.add_info(
                "INTENT_NO_ACTION",
                f"Intent {intent_id} has no derived actions",
                intent_id,
            )

    # ==========================================================================
    # Utility Methods
    # ==========================================================================

    def validate_and_update_status(self, graph: IRGraph) -> IRValidationResult:
        """
        Validate graph and update its status accordingly.

        Args:
            graph: Graph to validate

        Returns:
            Validation result
        """
        result = self.validate(graph)

        if result.valid:
            graph.set_status(IRStatus.VALIDATED)
        else:
            graph.set_status(IRStatus.DRAFT)

        return result

    def quick_validate(self, graph: IRGraph) -> bool:
        """
        Quick validation check (returns bool only).

        Args:
            graph: Graph to validate

        Returns:
            True if valid, False otherwise
        """
        result = self.validate(graph)
        return result.valid

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "IR_-INTE-003",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["intelligence", "ir-compilation", "logging", "validation", "validator"],
    "keywords": ["completeness", "compliance", "consistency", "cycle", "quick", "status", "update", "validate"],
    "business_value": "Implements IRValidator for ir validator functionality",
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
