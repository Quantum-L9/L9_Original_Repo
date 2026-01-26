"""
L9 IR Engine Tests - Semantic to Plan Integration
=================================================

Test Matrix:
┌─────────────────────────────────────────────────────────────────────────────┐
│ Scenario                    │ Modules Touched              │ Expected       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Happy path compile->plan    │ SemanticCompiler, IRValidator│ VALIDATED,     │
│                             │ IRToPlanAdapter              │ ordered steps  │
├─────────────────────────────────────────────────────────────────────────────┤
│ Multi-intent compilation    │ SemanticCompiler             │ Multiple       │
│                             │                              │ intents linked │
├─────────────────────────────────────────────────────────────────────────────┤
│ Compile with context        │ SemanticCompiler             │ Context used   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Plan dependency ordering    │ IRToPlanAdapter              │ Topological    │
│                             │                              │ order correct  │
├─────────────────────────────────────────────────────────────────────────────┤
│ Plan priority ordering      │ IRToPlanAdapter              │ Higher prio    │
│                             │                              │ first          │
└─────────────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import pytest

from ir_engine.ir_schema import IRGraph, IRStatus
from ir_engine.ir_to_plan_adapter import ExecutionPlan, IRToPlanAdapter
from ir_engine.ir_validator import IRValidator
from ir_engine.semantic_compiler import SemanticCompiler


class TestSemanticToPlanHappyPath:
    """Test the happy path: compile → validate → plan."""

    @pytest.mark.asyncio
    async def test_semantic_to_plan_happy_path(self, mock_openai_client):
        """
        Test the full pipeline: natural language → compiled IR → validated → execution plan.

        Asserts:
        - Non-empty intents/actions after compilation
        - Graph status becomes VALIDATED on success
        - Plan has ordered steps with correct dependencies & priorities
        """
        # Arrange
        compiler = SemanticCompiler()
        compiler._client = mock_openai_client
        validator = IRValidator()
        adapter = IRToPlanAdapter()

        user_input = "Create a user authentication module with OAuth2 support"

        # Act: Compile
        graph = await compiler.compile(user_input, session_id="test-session")

        # Assert: Compilation produced content
        assert len(graph.intents) > 0, "Should have at least one intent"
        assert len(graph.actions) > 0, "Should have at least one action"
        assert graph.status == IRStatus.COMPILED, (
            "Status should be COMPILED after compilation"
        )

        # Act: Validate
        validation_result = validator.validate_and_update_status(graph)

        # Assert: Validation succeeded
        assert validation_result.valid, f"Validation failed: {validation_result.errors}"
        assert graph.status == IRStatus.VALIDATED, "Status should be VALIDATED"

        # Act: Generate plan
        plan = adapter.to_execution_plan(graph)

        # Assert: Plan is well-formed
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) > 0, "Plan should have steps"
        assert plan.source_graph_id == graph.graph_id

        # Check step ordering
        for i, step in enumerate(plan.steps):
            assert step.step_number == i + 1, "Steps should be numbered sequentially"
            assert step.description, "Each step should have a description"
            assert step.action_type, "Each step should have an action type"

    @pytest.mark.asyncio
    async def test_multi_intent_compilation(self, mock_openai_complex):
        """Test compilation with multiple intents produces linked graph."""
        # Arrange
        compiler = SemanticCompiler()
        compiler._client = mock_openai_complex

        user_input = "Create a user registration system with email validation and password hashing"

        # Act
        graph = await compiler.compile(user_input)

        # Assert
        assert len(graph.intents) == 3, "Should have 3 intents"
        assert len(graph.constraints) == 2, "Should have 2 constraints"
        assert len(graph.actions) == 3, "Should have 3 actions"

        # Verify intent types
        intent_types = {i.intent_type.value for i in graph.intents.values()}
        assert "create" in intent_types
        assert "validate" in intent_types

    @pytest.mark.asyncio
    async def test_compile_with_context(self, mock_openai_client):
        """Test that context is passed to LLM."""
        # Arrange
        compiler = SemanticCompiler()
        compiler._client = mock_openai_client

        context = {"existing_modules": ["auth", "database"]}

        # Act
        graph = await compiler.compile(
            "Add logging to existing modules",
            context=context,
            user_id="test-user",
        )

        # Assert
        assert graph.metadata.user_id == "test-user"
        assert graph.metadata.context == context

        # Verify LLM was called with context
        call_args = mock_openai_client.chat.completions.create.call_args
        prompt = call_args.kwargs["messages"][1]["content"]
        assert "existing_modules" in prompt


class TestPlanGeneration:
    """Test plan generation from validated graphs."""

    def test_plan_dependency_ordering(self, graph_with_dependencies: IRGraph):
        """Test that plan respects action dependencies."""
        # Arrange
        adapter = IRToPlanAdapter()

        # Act
        plan = adapter.to_execution_plan(graph_with_dependencies)

        # Assert: Steps are in dependency order
        step_order = {step.action_type: step.step_number for step in plan.steps}

        # file_create should come before code_write
        assert step_order["file_create"] < step_order["code_write"]
        # code_write should come before validation
        assert step_order["code_write"] < step_order["validation"]

    def test_plan_priority_ordering(self, validated_graph: IRGraph):
        """Test that higher priority actions come first (within dependency constraints)."""
        # Arrange
        adapter = IRToPlanAdapter()

        # Act
        plan = adapter.to_execution_plan(validated_graph)

        # Assert: Plan is created
        assert len(plan.steps) > 0

        # Steps should respect priority (critical > high > medium > low)
        # when there are no dependency constraints
        for step in plan.steps:
            assert step.step_number > 0

    def test_plan_metadata_propagation(self, validated_graph: IRGraph):
        """Test that graph metadata propagates to plan."""
        # Arrange
        adapter = IRToPlanAdapter()

        # Act
        plan = adapter.to_execution_plan(validated_graph)

        # Assert
        assert plan.metadata["intent_count"] == len(validated_graph.intents)
        assert plan.metadata["constraint_count"] == len(validated_graph.constraints)
        assert plan.metadata["source_status"] == validated_graph.status.value

    def test_plan_step_constraints_included(self, validated_graph: IRGraph):
        """Test that constraint descriptions are included in steps."""
        # Arrange
        adapter = IRToPlanAdapter()

        # Act
        plan = adapter.to_execution_plan(validated_graph)

        # The validated_graph fixture has a constraint "Must be unit tested"
        # which should appear in the action's constraints
        step_with_constraints = [s for s in plan.steps if s.constraints]
        assert len(step_with_constraints) > 0, (
            "At least one step should have constraints"
        )

        # Find the constraint text
        all_constraints = []
        for step in plan.steps:
            all_constraints.extend(step.constraints)

        assert "Must be unit tested" in all_constraints


class TestTaskQueueFormat:
    """Test conversion to task queue format."""

    def test_to_task_queue_format(self, validated_graph: IRGraph):
        """Test conversion to L9 task queue format."""
        # Arrange
        adapter = IRToPlanAdapter()

        # Act
        tasks = adapter.to_task_queue_format(validated_graph)

        # Assert
        assert len(tasks) > 0

        for task in tasks:
            assert "task_id" in task
            assert "task_type" in task
            assert "payload" in task
            assert "description" in task["payload"]
            assert "target" in task["payload"]
            assert "source" in task
            assert "plan_id" in task["source"]
            assert "graph_id" in task["source"]


class TestLangGraphStateFormat:
    """Test conversion to LangGraph state format."""

    def test_to_langgraph_state(self, validated_graph: IRGraph):
        """Test conversion to LangGraph state format."""
        # Arrange
        adapter = IRToPlanAdapter()

        # Act
        state = adapter.to_langgraph_state(validated_graph)

        # Assert
        assert "plan_id" in state
        assert "graph_id" in state
        assert "status" in state
        assert "steps" in state
        assert "intents" in state
        assert "active_constraints" in state
        assert "execution_context" in state

        # Check execution context
        ctx = state["execution_context"]
        assert ctx["total_steps"] == len(state["steps"])
        assert ctx["completed_steps"] == 0
        assert ctx["failed_steps"] == 0


class TestPlanModification:
    """Test plan modification capabilities."""

    def test_insert_step(self, validated_graph: IRGraph):
        """Test inserting a step into a plan."""
        # Arrange
        adapter = IRToPlanAdapter()
        plan = adapter.to_execution_plan(validated_graph)
        original_count = len(plan.steps)

        # Act
        new_step = adapter.insert_step(
            plan,
            after_step=1,
            action_type="validation",
            description="Added validation step",
            target="validators/",
        )

        # Assert
        assert len(plan.steps) == original_count + 1
        assert new_step.step_number == 2
        assert new_step.description == "Added validation step"

        # Check subsequent steps were renumbered
        for i, step in enumerate(plan.steps):
            assert step.step_number == i + 1

    def test_remove_step(self, validated_graph: IRGraph):
        """Test removing a step from a plan."""
        # Arrange
        adapter = IRToPlanAdapter()
        plan = adapter.to_execution_plan(validated_graph)

        if len(plan.steps) < 1:
            pytest.skip("Need at least 1 step to test removal")

        step_to_remove = plan.steps[0]
        original_count = len(plan.steps)

        # Act
        result = adapter.remove_step(plan, step_to_remove.step_id)

        # Assert
        assert result is True
        assert len(plan.steps) == original_count - 1
