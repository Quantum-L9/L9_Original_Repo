"""
L9 IR Engine Tests - Validation and Status
==========================================

Test Matrix:
┌─────────────────────────────────────────────────────────────────────────────┐
│ Scenario                    │ Error Code                   │ Expected       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Missing intent description  │ INTENT_NO_DESCRIPTION        │ Error          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Missing action description  │ ACTION_NO_DESCRIPTION        │ Error          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Missing constraint desc     │ CONSTRAINT_NO_DESCRIPTION    │ Error          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Invalid intent confidence   │ INTENT_INVALID_CONFIDENCE    │ Error          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Invalid parent reference    │ INTENT_INVALID_PARENT        │ Error          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Invalid child reference     │ INTENT_INVALID_CHILD         │ Error          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Invalid dependency          │ ACTION_INVALID_DEPENDENCY    │ Error          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Circular dependency         │ DEPENDENCY_CYCLE             │ Error          │
├─────────────────────────────────────────────────────────────────────────────┤
│ No intents                  │ NO_INTENTS                   │ Error          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Constraint conflict         │ CONSTRAINT_CONFLICT          │ Warning        │
├─────────────────────────────────────────────────────────────────────────────┤
│ Orphan constraint           │ CONSTRAINT_ORPHAN            │ Info           │
├─────────────────────────────────────────────────────────────────────────────┤
│ Intent no action            │ INTENT_NO_ACTION             │ Info           │
└─────────────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from uuid import uuid4

from ir_engine.ir_schema import (
    ActionNode,
    ActionType,
    ConstraintNode,
    ConstraintStatus,
    ConstraintType,
    IntentNode,
    IntentType,
    IRGraph,
    IRMetadata,
    IRStatus,
    IRValidationResult,
)
from ir_engine.ir_validator import IRValidator


class TestSchemaValidation:
    """Test schema compliance validation."""

    def test_missing_intent_description_error(
        self,
        graph_missing_descriptions: IRGraph,
    ):
        """Test that missing intent description produces error."""
        # Arrange
        validator = IRValidator()

        # Act
        result = validator.validate(graph_missing_descriptions)

        # Assert
        assert not result.valid
        error_codes = [e.code for e in result.errors]
        assert "INTENT_NO_DESCRIPTION" in error_codes

    def test_missing_constraint_description_error(
        self,
        graph_missing_descriptions: IRGraph,
    ):
        """Test that missing constraint description produces error."""
        # Arrange
        validator = IRValidator()

        # Act
        result = validator.validate(graph_missing_descriptions)

        # Assert
        error_codes = [e.code for e in result.errors]
        assert "CONSTRAINT_NO_DESCRIPTION" in error_codes

    def test_missing_action_description_error(
        self,
        graph_missing_descriptions: IRGraph,
    ):
        """Test that missing action description produces error."""
        # Arrange
        validator = IRValidator()

        # Act
        result = validator.validate(graph_missing_descriptions)

        # Assert
        error_codes = [e.code for e in result.errors]
        assert "ACTION_NO_DESCRIPTION" in error_codes

    def test_missing_intent_target_warning(self):
        """Test that missing intent target produces warning."""
        # Arrange
        validator = IRValidator()
        graph = IRGraph(metadata=IRMetadata(source="test"))

        intent = IntentNode(
            intent_type=IntentType.CREATE,
            description="Create something",
            target="",  # Empty target
        )
        graph.add_intent(intent)

        # Act
        result = validator.validate(graph)

        # Assert
        warning_codes = [w.code for w in result.warnings]
        assert "INTENT_NO_TARGET" in warning_codes

    def test_valid_graph_passes(self, simple_valid_graph: IRGraph):
        """Test that a valid graph passes validation."""
        # Arrange
        validator = IRValidator()

        # Act
        result = validator.validate(simple_valid_graph)

        # Assert
        assert result.valid, f"Errors: {result.errors}"
        assert len(result.errors) == 0


class TestReferentialIntegrity:
    """Test referential integrity validation."""

    def test_invalid_parent_intent_error(
        self,
        graph_with_invalid_references: IRGraph,
    ):
        """Test that invalid parent intent reference produces error."""
        # Arrange
        validator = IRValidator()

        # Act
        result = validator.validate(graph_with_invalid_references)

        # Assert
        error_codes = [e.code for e in result.errors]
        assert "INTENT_INVALID_PARENT" in error_codes

    def test_invalid_child_intent_error(
        self,
        graph_with_invalid_references: IRGraph,
    ):
        """Test that invalid child intent reference produces error."""
        # Arrange
        validator = IRValidator()

        # Act
        result = validator.validate(graph_with_invalid_references)

        # Assert
        error_codes = [e.code for e in result.errors]
        assert "INTENT_INVALID_CHILD" in error_codes

    def test_invalid_action_dependency_error(
        self,
        graph_with_invalid_references: IRGraph,
    ):
        """Test that invalid action dependency produces error."""
        # Arrange
        validator = IRValidator()

        # Act
        result = validator.validate(graph_with_invalid_references)

        # Assert
        error_codes = [e.code for e in result.errors]
        assert "ACTION_INVALID_DEPENDENCY" in error_codes

    def test_invalid_derived_from_intent_warning(
        self,
        graph_with_invalid_references: IRGraph,
    ):
        """Test that invalid derived_from_intent produces warning."""
        # Arrange
        validator = IRValidator()

        # Act
        result = validator.validate(graph_with_invalid_references)

        # Assert
        warning_codes = [w.code for w in result.warnings]
        assert "ACTION_INVALID_INTENT_REF" in warning_codes


class TestDependencyValidation:
    """Test action dependency validation."""

    def test_circular_dependency_error(
        self,
        graph_with_circular_dependency: IRGraph,
    ):
        """Test that circular dependencies produce error."""
        # Arrange
        validator = IRValidator()

        # Act
        result = validator.validate(graph_with_circular_dependency)

        # Assert
        assert not result.valid
        error_codes = [e.code for e in result.errors]
        assert "DEPENDENCY_CYCLE" in error_codes

    def test_valid_dependencies_pass(self, graph_with_dependencies: IRGraph):
        """Test that valid dependencies pass validation."""
        # Arrange
        validator = IRValidator()

        # Act
        result = validator.validate(graph_with_dependencies)

        # Assert: No dependency cycle errors
        error_codes = [e.code for e in result.errors]
        assert "DEPENDENCY_CYCLE" not in error_codes


class TestConstraintValidation:
    """Test constraint consistency validation."""

    def test_orphan_constraint_info(self):
        """Test that orphan constraints produce info message."""
        # Arrange
        validator = IRValidator()
        graph = IRGraph(metadata=IRMetadata(source="test"))

        intent = IntentNode(
            intent_type=IntentType.CREATE,
            description="Create something",
            target="target",
        )
        graph.add_intent(intent)

        # Orphan constraint (applies_to is empty)
        constraint = ConstraintNode(
            constraint_type=ConstraintType.EXPLICIT,
            description="Some constraint",
            applies_to=[],  # Orphan - doesn't apply to anything
        )
        graph.add_constraint(constraint)

        # Act
        result = validator.validate(graph)

        # Assert
        info_codes = [i.code for i in result.info]
        assert "CONSTRAINT_ORPHAN" in info_codes

    def test_conflicting_constraints_warning(self):
        """Test that potentially conflicting constraints produce warning."""
        # Arrange
        validator = IRValidator()
        graph = IRGraph(metadata=IRMetadata(source="test"))

        intent = IntentNode(
            intent_type=IntentType.CREATE,
            description="Create module",
            target="module",
        )
        intent_id = graph.add_intent(intent)

        # Two constraints that might conflict
        c1 = ConstraintNode(
            constraint_type=ConstraintType.EXPLICIT,
            description="Must include all features",
            applies_to=[intent_id],
        )

        c2 = ConstraintNode(
            constraint_type=ConstraintType.EXPLICIT,
            description="Must not include optional features",
            applies_to=[intent_id],
        )

        graph.add_constraint(c1)
        graph.add_constraint(c2)

        # Act
        result = validator.validate(graph)

        # Assert: May have conflict warning
        warning_codes = [w.code for w in result.warnings]
        assert "CONSTRAINT_CONFLICT" in warning_codes

    def test_false_constraint_active_warning(self):
        """Test that false constraints still active produce warning."""
        # Arrange
        validator = IRValidator()
        graph = IRGraph(metadata=IRMetadata(source="test"))

        intent = IntentNode(
            intent_type=IntentType.CREATE,
            description="Create something",
            target="target",
        )
        intent_id = graph.add_intent(intent)

        # False constraint that's still active
        constraint = ConstraintNode(
            constraint_type=ConstraintType.FALSE,
            description="This constraint is false",
            status=ConstraintStatus.ACTIVE,  # Should not be active
            applies_to=[intent_id],
        )
        graph.add_constraint(constraint)

        # Act
        result = validator.validate(graph)

        # Assert
        warning_codes = [w.code for w in result.warnings]
        assert "FALSE_CONSTRAINT_ACTIVE" in warning_codes


class TestCompletenessValidation:
    """Test graph completeness validation."""

    def test_no_intents_error(self, empty_graph: IRGraph):
        """Test that graph with no intents produces error."""
        # Arrange
        validator = IRValidator()

        # Act
        result = validator.validate(empty_graph)

        # Assert
        assert not result.valid
        error_codes = [e.code for e in result.errors]
        assert "NO_INTENTS" in error_codes

    def test_no_actions_warning(self):
        """Test that graph with no actions produces warning."""
        # Arrange
        validator = IRValidator(require_actions=True)
        graph = IRGraph(metadata=IRMetadata(source="test"))

        intent = IntentNode(
            intent_type=IntentType.CREATE,
            description="Create something",
            target="target",
        )
        graph.add_intent(intent)

        # Act
        result = validator.validate(graph)

        # Assert
        warning_codes = [w.code for w in result.warnings]
        assert "NO_ACTIONS" in warning_codes

    def test_intent_without_action_info(self):
        """Test that intent without derived action produces info."""
        # Arrange
        validator = IRValidator()
        graph = IRGraph(metadata=IRMetadata(source="test"))

        intent = IntentNode(
            intent_type=IntentType.CREATE,
            description="Create module",
            target="module",
        )
        graph.add_intent(intent)

        # Action that doesn't derive from intent
        action = ActionNode(
            action_type=ActionType.CODE_WRITE,
            description="Write some code",
            target="file.py",
            derived_from_intent=None,  # Not derived from any intent
        )
        graph.add_action(action)

        # Act
        result = validator.validate(graph)

        # Assert
        info_codes = [i.code for i in result.info]
        assert "INTENT_NO_ACTION" in info_codes


class TestValidateAndUpdateStatus:
    """Test validate_and_update_status method."""

    def test_valid_graph_becomes_validated(self, simple_valid_graph: IRGraph):
        """Test that valid graph status becomes VALIDATED."""
        # Arrange
        validator = IRValidator()
        assert simple_valid_graph.status != IRStatus.VALIDATED

        # Act
        result = validator.validate_and_update_status(simple_valid_graph)

        # Assert
        assert result.valid
        assert simple_valid_graph.status == IRStatus.VALIDATED

    def test_invalid_graph_becomes_draft(
        self,
        graph_missing_descriptions: IRGraph,
    ):
        """Test that invalid graph status becomes DRAFT."""
        # Arrange
        validator = IRValidator()
        graph_missing_descriptions.set_status(IRStatus.COMPILED)

        # Act
        result = validator.validate_and_update_status(graph_missing_descriptions)

        # Assert
        assert not result.valid
        assert graph_missing_descriptions.status == IRStatus.DRAFT

    def test_status_change_logged(self, simple_valid_graph: IRGraph):
        """Test that status change is logged."""
        # Arrange
        validator = IRValidator()
        initial_log_length = len(simple_valid_graph.processing_log)

        # Act
        validator.validate_and_update_status(simple_valid_graph)

        # Assert
        assert len(simple_valid_graph.processing_log) > initial_log_length

        # Find status change event
        status_events = [
            e
            for e in simple_valid_graph.processing_log
            if e["event"] == "status_changed"
        ]
        assert len(status_events) > 0


class TestQuickValidate:
    """Test quick_validate method."""

    def test_quick_validate_returns_bool(self, simple_valid_graph: IRGraph):
        """Test that quick_validate returns boolean."""
        # Arrange
        validator = IRValidator()

        # Act
        result = validator.quick_validate(simple_valid_graph)

        # Assert
        assert isinstance(result, bool)
        assert result is True

    def test_quick_validate_false_for_invalid(
        self,
        graph_missing_descriptions: IRGraph,
    ):
        """Test quick_validate returns False for invalid graphs."""
        # Arrange
        validator = IRValidator()

        # Act
        result = validator.quick_validate(graph_missing_descriptions)

        # Assert
        assert result is False


class TestStrictMode:
    """Test strict mode validation."""

    def test_strict_mode_warnings_dont_affect_validity(self):
        """Test that in non-strict mode, warnings don't fail validation."""
        # Arrange
        validator = IRValidator(strict_mode=False)
        graph = IRGraph(metadata=IRMetadata(source="test"))

        intent = IntentNode(
            intent_type=IntentType.CREATE,
            description="Create something",
            target="",  # Missing target -> warning
        )
        graph.add_intent(intent)

        # Add an action to avoid NO_ACTIONS warning
        action = ActionNode(
            action_type=ActionType.CODE_WRITE,
            description="Write code",
            target="file.py",
        )
        graph.add_action(action)

        # Act
        result = validator.validate(graph)

        # Assert: Should be valid despite warnings
        assert result.valid
        assert len(result.warnings) > 0


class TestValidationResult:
    """Test IRValidationResult methods."""

    def test_add_error_sets_invalid(self):
        """Test that add_error sets valid to False."""
        # Arrange
        result = IRValidationResult(valid=True)

        # Act
        result.add_error("TEST_ERROR", "Test error message")

        # Assert
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "TEST_ERROR"

    def test_add_warning_preserves_validity(self):
        """Test that add_warning doesn't change validity."""
        # Arrange
        result = IRValidationResult(valid=True)

        # Act
        result.add_warning("TEST_WARNING", "Test warning")

        # Assert
        assert result.valid is True
        assert len(result.warnings) == 1

    def test_add_info_preserves_validity(self):
        """Test that add_info doesn't change validity."""
        # Arrange
        result = IRValidationResult(valid=True)

        # Act
        result.add_info("TEST_INFO", "Test info")

        # Assert
        assert result.valid is True
        assert len(result.info) == 1

    def test_error_includes_node_id(self):
        """Test that error can include node_id."""
        # Arrange
        result = IRValidationResult(valid=True)
        node_id = uuid4()

        # Act
        result.add_error("TEST_ERROR", "Error message", node_id=node_id)

        # Assert
        assert result.errors[0].node_id == node_id
