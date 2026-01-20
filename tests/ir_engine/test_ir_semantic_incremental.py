"""
L9 IR Engine Tests - Incremental Compilation
============================================

Test Matrix:
┌─────────────────────────────────────────────────────────────────────────────┐
│ Scenario                    │ Modules Touched              │ Expected       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Append new intents          │ SemanticCompiler             │ Intents added, │
│                             │ compile_incremental          │ not replaced   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Append constraints          │ SemanticCompiler             │ Constraints    │
│                             │ compile_incremental          │ accumulated    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Append actions              │ SemanticCompiler             │ Actions linked │
│                             │ compile_incremental          │ to new intents │
├─────────────────────────────────────────────────────────────────────────────┤
│ Processing log recorded     │ IRGraph                      │ Events logged  │
├─────────────────────────────────────────────────────────────────────────────┤
│ Context includes existing   │ SemanticCompiler             │ LLM sees       │
│                             │                              │ existing       │
└─────────────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from ir_engine.ir_schema import IRGraph, IRMetadata
from ir_engine.semantic_compiler import SemanticCompiler


class TestIncrementalCompilation:
    """Test incremental compilation functionality."""

    @pytest.fixture
    def incremental_response(self) -> dict:
        """Second response for incremental compilation."""
        return {
            "intents": [
                {
                    "type": "create",
                    "description": "Add logging functionality",
                    "target": "logging_module",
                    "parameters": {},
                    "priority": "medium",
                    "confidence": 0.9,
                }
            ],
            "constraints": [
                {
                    "type": "explicit",
                    "description": "Log to file and console",
                    "applies_to": ["Add logging functionality"],
                    "priority": "medium",
                }
            ],
            "suggested_actions": [
                {
                    "type": "code_write",
                    "description": "Implement logging handler",
                    "target": "logging/handler.py",
                    "parameters": {},
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_incremental_appends_intents(
        self,
        mock_openai_client,
        incremental_response,
        simple_valid_graph: IRGraph,
    ):
        """Test that incremental compilation appends intents, not replaces."""
        # Arrange
        compiler = SemanticCompiler()
        compiler._client = mock_openai_client

        initial_intent_count = len(simple_valid_graph.intents)
        initial_intent_ids = set(simple_valid_graph.intents.keys())

        # Configure mock for incremental response
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(incremental_response)))]
        )

        # Act
        updated_graph = await compiler.compile_incremental(
            simple_valid_graph,
            "Also add logging functionality",
        )

        # Assert: Original intents preserved
        assert len(updated_graph.intents) > initial_intent_count
        for original_id in initial_intent_ids:
            assert original_id in updated_graph.intents, "Original intent should be preserved"

        # Assert: New intent added
        new_intent_ids = set(updated_graph.intents.keys()) - initial_intent_ids
        assert len(new_intent_ids) == 1, "Should have exactly 1 new intent"

        new_intent = updated_graph.intents[list(new_intent_ids)[0]]
        assert "logging" in new_intent.description.lower()

    @pytest.mark.asyncio
    async def test_incremental_appends_constraints(
        self,
        mock_openai_client,
        incremental_response,
        simple_valid_graph: IRGraph,
    ):
        """Test that incremental compilation appends constraints."""
        # Arrange
        compiler = SemanticCompiler()
        compiler._client = mock_openai_client

        initial_constraint_count = len(simple_valid_graph.constraints)
        initial_constraint_ids = set(simple_valid_graph.constraints.keys())

        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(incremental_response)))]
        )

        # Act
        updated_graph = await compiler.compile_incremental(
            simple_valid_graph,
            "Add logging with file and console output",
        )

        # Assert: Original constraints preserved
        for original_id in initial_constraint_ids:
            assert original_id in updated_graph.constraints

        # Assert: New constraint added
        assert len(updated_graph.constraints) > initial_constraint_count

        # Find the new constraint
        new_constraint_ids = set(updated_graph.constraints.keys()) - initial_constraint_ids
        for cid in new_constraint_ids:
            constraint = updated_graph.constraints[cid]
            # New constraint should be from incremental response
            assert constraint.description

    @pytest.mark.asyncio
    async def test_incremental_appends_actions(
        self,
        mock_openai_client,
        incremental_response,
        simple_valid_graph: IRGraph,
    ):
        """Test that incremental compilation appends actions."""
        # Arrange
        compiler = SemanticCompiler()
        compiler._client = mock_openai_client

        initial_action_count = len(simple_valid_graph.actions)
        initial_action_ids = set(simple_valid_graph.actions.keys())

        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(incremental_response)))]
        )

        # Act
        updated_graph = await compiler.compile_incremental(
            simple_valid_graph,
            "Add logging handler implementation",
        )

        # Assert: Original actions preserved
        for original_id in initial_action_ids:
            assert original_id in updated_graph.actions

        # Assert: New action added
        assert len(updated_graph.actions) > initial_action_count

    @pytest.mark.asyncio
    async def test_processing_log_records_events(
        self,
        mock_openai_client,
        incremental_response,
        simple_valid_graph: IRGraph,
    ):
        """Test that processing_log records incremental compilation events."""
        # Arrange
        compiler = SemanticCompiler()
        compiler._client = mock_openai_client

        initial_log_length = len(simple_valid_graph.processing_log)

        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(incremental_response)))]
        )

        # Act
        updated_graph = await compiler.compile_incremental(
            simple_valid_graph,
            "Add logging",
        )

        # Assert: Log has new entries
        assert len(updated_graph.processing_log) > initial_log_length

        # Check for expected event types
        event_types = [entry["event"] for entry in updated_graph.processing_log]
        assert "intent_added" in event_types, "Should log intent_added events"

    @pytest.mark.asyncio
    async def test_incremental_context_includes_existing_intents(
        self,
        mock_openai_client,
        simple_valid_graph: IRGraph,
    ):
        """Test that LLM receives context about existing intents."""
        # Arrange
        compiler = SemanticCompiler()
        compiler._client = mock_openai_client

        # Act
        await compiler.compile_incremental(
            simple_valid_graph,
            "Add more features",
        )

        # Assert: LLM was called with existing intents context
        call_args = mock_openai_client.chat.completions.create.call_args
        prompt = call_args.kwargs["messages"][1]["content"]

        assert "existing_intents" in prompt, "Prompt should include existing intents context"


class TestIncrementalEdgeCases:
    """Test edge cases in incremental compilation."""

    @pytest.mark.asyncio
    async def test_incremental_on_empty_graph(self, mock_openai_client):
        """Test incremental compilation on an empty graph."""
        # Arrange
        compiler = SemanticCompiler()
        compiler._client = mock_openai_client

        empty_graph = IRGraph(metadata=IRMetadata(source="test"))

        # Act
        updated_graph = await compiler.compile_incremental(
            empty_graph,
            "Create a new feature",
        )

        # Assert: Should still work and add content
        assert len(updated_graph.intents) > 0 or len(updated_graph.actions) > 0

    @pytest.mark.asyncio
    async def test_incremental_preserves_graph_id(
        self,
        mock_openai_client,
        simple_valid_graph: IRGraph,
    ):
        """Test that graph ID is preserved after incremental compilation."""
        # Arrange
        compiler = SemanticCompiler()
        compiler._client = mock_openai_client

        original_graph_id = simple_valid_graph.graph_id

        # Act
        updated_graph = await compiler.compile_incremental(
            simple_valid_graph,
            "Add more",
        )

        # Assert
        assert updated_graph.graph_id == original_graph_id

    @pytest.mark.asyncio
    async def test_incremental_preserves_metadata(
        self,
        mock_openai_client,
        simple_valid_graph: IRGraph,
    ):
        """Test that original metadata is preserved."""
        # Arrange
        compiler = SemanticCompiler()
        compiler._client = mock_openai_client

        simple_valid_graph.metadata.user_id = "test-user"
        simple_valid_graph.metadata.session_id = "test-session"

        # Act
        updated_graph = await compiler.compile_incremental(
            simple_valid_graph,
            "Add feature",
        )

        # Assert
        assert updated_graph.metadata.user_id == "test-user"
        assert updated_graph.metadata.session_id == "test-session"

    @pytest.mark.asyncio
    async def test_multiple_incremental_compilations(
        self,
        mock_openai_client,
        simple_valid_graph: IRGraph,
    ):
        """Test multiple rounds of incremental compilation."""
        # Arrange
        compiler = SemanticCompiler()
        compiler._client = mock_openai_client

        initial_intent_count = len(simple_valid_graph.intents)

        # Create different responses for each round
        responses = [
            {
                "intents": [
                    {
                        "type": "create",
                        "description": f"Feature {i}",
                        "target": f"feature_{i}",
                        "parameters": {},
                        "priority": "medium",
                        "confidence": 0.9,
                    }
                ],
                "constraints": [],
                "suggested_actions": [],
            }
            for i in range(3)
        ]

        mock_openai_client.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps(r)))])
            for r in responses
        ]

        # Act: Three rounds of incremental compilation
        graph = simple_valid_graph
        for i in range(3):
            graph = await compiler.compile_incremental(graph, f"Add feature {i}")

        # Assert: All intents accumulated
        assert len(graph.intents) == initial_intent_count + 3


class TestIncrementalValidation:
    """Test validation after incremental compilation."""

    @pytest.mark.asyncio
    async def test_incremental_graph_remains_valid(
        self,
        mock_openai_client,
        validated_graph: IRGraph,
    ):
        """Test that a valid graph remains valid after incremental compilation."""
        from ir_engine.ir_validator import IRValidator

        # Arrange
        compiler = SemanticCompiler()
        compiler._client = mock_openai_client
        validator = IRValidator()

        response = {
            "intents": [
                {
                    "type": "modify",
                    "description": "Enhance existing module",
                    "target": "module",
                    "parameters": {},
                    "priority": "medium",
                    "confidence": 0.85,
                }
            ],
            "constraints": [],
            "suggested_actions": [
                {
                    "type": "code_modify",
                    "description": "Update module code",
                    "target": "src/module.py",
                    "parameters": {},
                }
            ],
        }

        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(response)))]
        )

        # Act
        updated_graph = await compiler.compile_incremental(
            validated_graph,
            "Enhance the module",
        )

        validation_result = validator.validate(updated_graph)

        # Assert
        assert validation_result.valid, f"Validation errors: {validation_result.errors}"
