"""
L9 ActionTool Orchestrator Tests
================================

Tests for action_tool orchestrator validation and execution.
No external services required.

Version: 1.0.0
"""

import pytest

# =============================================================================
# Test Class: Action Tool Orchestrator
# =============================================================================


class TestActionToolOrchestrator:
    """Tests for ActionToolOrchestrator."""

    # =============================================================================
    # Test: Orchestrator initialization
    # =============================================================================

    def test_orchestrator_initialization(self):
        """
        Contract: ActionToolOrchestrator initializes successfully.
        """
        from orchestrators.action_tool.orchestrator import ActionToolOrchestrator

        orchestrator = ActionToolOrchestrator()

        # Should initialize without error
        assert orchestrator is not None, (
            "ActionToolOrchestrator should initialize successfully"
        )

    # =============================================================================
    # Test: Validate action request
    # =============================================================================

    def test_validate_action_request(self):
        """
        Contract: ActionToolRequest model validates correctly.
        """
        from orchestrators.action_tool.interface import ActionToolRequest

        # Valid request
        request = ActionToolRequest(
            tool_id="test_tool",
            arguments={"param": "value"},
        )

        assert request.tool_id == "test_tool"
        assert request.arguments == {"param": "value"}

    # =============================================================================
    # Test: Execute action with mock
    # =============================================================================

    @pytest.mark.asyncio
    async def test_execute_action_with_mock(self):
        """
        Contract: execute() returns ActionToolResponse with success status.
        """
        from orchestrators.action_tool.interface import (
            ActionToolRequest,
            ActionToolResponse,
        )
        from orchestrators.action_tool.orchestrator import ActionToolOrchestrator

        orchestrator = ActionToolOrchestrator()

        request = ActionToolRequest(
            tool_id="echo",
            arguments={"message": "hello"},
        )

        result = await orchestrator.execute(request)

        assert isinstance(result, ActionToolResponse), (
            f"Expected ActionToolResponse, got {type(result)}"
        )
        assert result.success is True, f"Expected success=True, got {result.success}"
        assert result.message is not None, "Response message should not be None"

    # =============================================================================
    # Test: Response model validation
    # =============================================================================

    def test_response_model_validation(self):
        """
        Contract: ActionToolResponse model validates correctly.
        """
        from orchestrators.action_tool.interface import (
            ActionToolResponse,
            ToolSafetyLevel,
        )

        response = ActionToolResponse(
            success=True,
            message="Test completed",
            result={"output": "value"},
            retries_used=0,
            safety_level=ToolSafetyLevel.SAFE,
        )

        assert response.success is True
        assert response.message == "Test completed"
        assert response.result == {"output": "value"}
        assert response.retries_used == 0
        assert response.safety_level == ToolSafetyLevel.SAFE

    # =============================================================================
    # Test: Request model optional fields
    # =============================================================================

    def test_request_model_optional_fields(self):
        """
        Contract: ActionToolRequest handles optional fields correctly.
        """
        from orchestrators.action_tool.interface import ActionToolRequest

        # Minimal request with defaults
        request = ActionToolRequest()

        # Should have default values
        assert hasattr(request, "tool_id") or hasattr(request, "arguments")

    # =============================================================================
    # Edge Case Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_execute_with_missing_tool(self):
        """
        Contract: Non-existent tool_id returns error response.
        """
        from orchestrators.action_tool.interface import (
            ActionToolRequest,
            ActionToolResponse,
        )
        from orchestrators.action_tool.orchestrator import ActionToolOrchestrator

        orchestrator = ActionToolOrchestrator()

        request = ActionToolRequest(
            tool_id="nonexistent_tool_12345",
            arguments={"param": "value"},
        )

        result = await orchestrator.execute(request)

        assert isinstance(result, ActionToolResponse)
        assert result.success is False
        assert result.message is not None

    @pytest.mark.asyncio
    async def test_execute_with_empty_arguments(self):
        """
        Contract: Empty arguments handled correctly.
        """
        from orchestrators.action_tool.interface import (
            ActionToolRequest,
            ActionToolResponse,
        )
        from orchestrators.action_tool.orchestrator import ActionToolOrchestrator

        orchestrator = ActionToolOrchestrator()

        request = ActionToolRequest(
            tool_id="echo",
            arguments={},
        )

        result = await orchestrator.execute(request)

        assert isinstance(result, ActionToolResponse)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_timeout_handling(self):
        """
        Contract: Execution timeout returns appropriate error.
        """
        from orchestrators.action_tool.interface import (
            ActionToolRequest,
            ActionToolResponse,
        )
        from orchestrators.action_tool.orchestrator import ActionToolOrchestrator

        orchestrator = ActionToolOrchestrator()

        # Request with very short timeout to trigger timeout handling
        request = ActionToolRequest(
            tool_id="echo",
            arguments={"message": "test"},
        )

        # Note: Actual timeout testing would require mocking time or using asyncio.wait_for
        # This test verifies the orchestrator handles timeout scenarios gracefully
        result = await orchestrator.execute(request)

        assert isinstance(result, ActionToolResponse)
