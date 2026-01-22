"""
L9 IR Engine Tests - Shared Fixtures
====================================

Provides:
- LLM stub responses
- Pre-built IR graphs for testing
- Common test utilities
"""

from __future__ import annotations

import pytest

# Skip all ir_engine tests if ir_engine module not available
pytest.importorskip("ir_engine.ir_schema", reason="ir_engine module not available")

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from ir_engine.ir_schema import (ActionNode, ActionType, ConstraintNode,
                                 ConstraintType, IntentNode, IntentType,
                                 IRGraph, IRMetadata, IRStatus, NodePriority)

# =============================================================================
# LLM Response Stubs
# =============================================================================


def make_llm_extraction_response(
    intents: list[dict[str, Any]] | None = None,
    constraints: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a stubbed LLM extraction response."""
    return {
        "intents": intents
        or [
            {
                "type": "create",
                "description": "Create a new user authentication module",
                "target": "auth_module",
                "parameters": {"language": "python"},
                "priority": "high",
                "confidence": 0.95,
            }
        ],
        "constraints": constraints
        or [
            {
                "type": "explicit",
                "description": "Must use OAuth2 standard",
                "applies_to": ["Create a new user authentication module"],
                "priority": "high",
            }
        ],
        "suggested_actions": actions
        or [
            {
                "type": "code_write",
                "description": "Write OAuth2 authentication handler",
                "target": "auth/oauth2_handler.py",
                "parameters": {"template": "oauth2"},
            }
        ],
    }


def make_complex_llm_response() -> dict[str, Any]:
    """Create a complex multi-intent response."""
    return {
        "intents": [
            {
                "type": "create",
                "description": "Create user registration endpoint",
                "target": "api/endpoints",
                "parameters": {},
                "priority": "critical",
                "confidence": 0.98,
            },
            {
                "type": "create",
                "description": "Create user model",
                "target": "models/user.py",
                "parameters": {},
                "priority": "high",
                "confidence": 0.95,
            },
            {
                "type": "validate",
                "description": "Validate email format",
                "target": "validators",
                "parameters": {"format": "email"},
                "priority": "medium",
                "confidence": 0.9,
            },
        ],
        "constraints": [
            {
                "type": "explicit",
                "description": "Use bcrypt for password hashing",
                "applies_to": ["Create user registration endpoint"],
                "priority": "critical",
            },
            {
                "type": "system",
                "description": "Follow REST API conventions",
                "applies_to": ["Create user registration endpoint"],
                "priority": "high",
            },
        ],
        "suggested_actions": [
            {
                "type": "file_create",
                "description": "Create models directory",
                "target": "models/__init__.py",
                "parameters": {},
            },
            {
                "type": "code_write",
                "description": "Implement User model class",
                "target": "models/user.py",
                "parameters": {},
                "derived_from": "Create user model",
            },
            {
                "type": "code_write",
                "description": "Implement registration endpoint",
                "target": "api/endpoints/registration.py",
                "parameters": {},
                "derived_from": "Create user registration endpoint",
            },
        ],
    }


# =============================================================================
# Graph Fixtures
# =============================================================================


@pytest.fixture
def empty_graph() -> IRGraph:
    """Create an empty IR graph."""
    return IRGraph(
        metadata=IRMetadata(
            source="test",
            session_id="test-session",
        )
    )


@pytest.fixture
def simple_valid_graph() -> IRGraph:
    """Create a simple valid graph with intent, constraint, and action."""
    graph = IRGraph(
        metadata=IRMetadata(source="test"),
    )

    # Add intent
    intent = IntentNode(
        intent_type=IntentType.CREATE,
        description="Create a test module",
        target="test_module",
        priority=NodePriority.HIGH,
        confidence=0.95,
    )
    intent_id = graph.add_intent(intent)

    # Add constraint
    constraint = ConstraintNode(
        constraint_type=ConstraintType.EXPLICIT,
        description="Must be unit tested",
        applies_to=[intent_id],
        priority=NodePriority.HIGH,
    )
    constraint_id = graph.add_constraint(constraint)

    # Add action
    action = ActionNode(
        action_type=ActionType.CODE_WRITE,
        description="Write the test module code",
        target="src/test_module.py",
        derived_from_intent=intent_id,
        constrained_by=[constraint_id],
    )
    graph.add_action(action)

    graph.set_status(IRStatus.COMPILED)

    return graph


@pytest.fixture
def validated_graph(simple_valid_graph: IRGraph) -> IRGraph:
    """Create a pre-validated graph."""
    simple_valid_graph.set_status(IRStatus.VALIDATED)
    return simple_valid_graph


@pytest.fixture
def graph_with_dependencies() -> IRGraph:
    """Create a graph with action dependencies."""
    graph = IRGraph(metadata=IRMetadata(source="test"))

    # Add intent
    intent = IntentNode(
        intent_type=IntentType.CREATE,
        description="Create a web service",
        target="web_service",
    )
    intent_id = graph.add_intent(intent)

    # Add three actions with dependencies
    action1 = ActionNode(
        action_type=ActionType.FILE_CREATE,
        description="Create project structure",
        target="src/",
        priority=NodePriority.CRITICAL,
        derived_from_intent=intent_id,
    )
    action1_id = graph.add_action(action1)

    action2 = ActionNode(
        action_type=ActionType.CODE_WRITE,
        description="Write main module",
        target="src/main.py",
        priority=NodePriority.HIGH,
        derived_from_intent=intent_id,
        depends_on=[action1_id],
    )
    action2_id = graph.add_action(action2)

    action3 = ActionNode(
        action_type=ActionType.VALIDATION,
        description="Run tests",
        target="tests/",
        priority=NodePriority.MEDIUM,
        derived_from_intent=intent_id,
        depends_on=[action2_id],
    )
    graph.add_action(action3)

    graph.set_status(IRStatus.VALIDATED)

    return graph


@pytest.fixture
def graph_with_circular_dependency() -> IRGraph:
    """Create a graph with circular action dependencies (invalid)."""
    graph = IRGraph(metadata=IRMetadata(source="test"))

    intent = IntentNode(
        intent_type=IntentType.EXECUTE,
        description="Test circular deps",
        target="test",
    )
    graph.add_intent(intent)

    # Create actions with circular dependency
    action1_id = uuid4()
    action2_id = uuid4()
    action3_id = uuid4()

    action1 = ActionNode(
        node_id=action1_id,
        action_type=ActionType.CODE_WRITE,
        description="Action 1",
        target="file1.py",
        depends_on=[action3_id],  # Depends on action3
    )

    action2 = ActionNode(
        node_id=action2_id,
        action_type=ActionType.CODE_WRITE,
        description="Action 2",
        target="file2.py",
        depends_on=[action1_id],  # Depends on action1
    )

    action3 = ActionNode(
        node_id=action3_id,
        action_type=ActionType.CODE_WRITE,
        description="Action 3",
        target="file3.py",
        depends_on=[action2_id],  # Depends on action2 -> cycle!
    )

    graph.add_action(action1)
    graph.add_action(action2)
    graph.add_action(action3)

    return graph


@pytest.fixture
def graph_with_invalid_references() -> IRGraph:
    """Create a graph with invalid node references."""
    graph = IRGraph(metadata=IRMetadata(source="test"))

    intent = IntentNode(
        intent_type=IntentType.CREATE,
        description="Test invalid refs",
        target="test",
        parent_intent_id=uuid4(),  # Non-existent parent
        child_intent_ids=[uuid4(), uuid4()],  # Non-existent children
    )
    graph.add_intent(intent)

    action = ActionNode(
        action_type=ActionType.CODE_WRITE,
        description="Action with bad refs",
        target="file.py",
        derived_from_intent=uuid4(),  # Non-existent intent
        constrained_by=[uuid4()],  # Non-existent constraint
        depends_on=[uuid4()],  # Non-existent action
    )
    graph.add_action(action)

    return graph


@pytest.fixture
def graph_missing_descriptions() -> IRGraph:
    """Create a graph with missing descriptions (invalid)."""
    graph = IRGraph(metadata=IRMetadata(source="test"))

    intent = IntentNode(
        intent_type=IntentType.CREATE,
        description="",  # Empty description
        target="test",
    )
    graph.add_intent(intent)

    constraint = ConstraintNode(
        constraint_type=ConstraintType.EXPLICIT,
        description="",  # Empty description
    )
    graph.add_constraint(constraint)

    action = ActionNode(
        action_type=ActionType.CODE_WRITE,
        description="",  # Empty description
        target="file.py",
    )
    graph.add_action(action)

    return graph


@pytest.fixture
def graph_invalid_confidence() -> IRGraph:
    """Create a graph with invalid confidence values."""
    graph = IRGraph(metadata=IRMetadata(source="test"))

    # Note: Pydantic will clamp these values, but we test the validator catches issues
    intent = IntentNode(
        intent_type=IntentType.CREATE,
        description="Test confidence",
        target="test",
        confidence=0.5,  # Valid
    )
    graph.add_intent(intent)

    return graph


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock = AsyncMock()

    # Default response
    mock.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(content=json.dumps(make_llm_extraction_response()))
            )
        ]
    )

    return mock


@pytest.fixture
def mock_openai_complex(mock_openai_client):
    """Mock client with complex multi-intent response."""
    mock_openai_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(content=json.dumps(make_complex_llm_response()))
            )
        ]
    )
    return mock_openai_client


# =============================================================================
# Helper Functions
# =============================================================================


def assert_valid_uuid(value: Any) -> None:
    """Assert that a value is a valid UUID or UUID string."""
    if isinstance(value, UUID):
        return
    if isinstance(value, str):
        UUID(value)  # Raises if invalid
        return
    raise AssertionError(f"Expected UUID, got {type(value)}")


def assert_json_serializable(data: Any) -> str:
    """Assert that data is JSON serializable and return the JSON string."""
    try:
        return json.dumps(data, default=str)
    except (TypeError, ValueError) as e:
        raise AssertionError(f"Data is not JSON serializable: {e}")
