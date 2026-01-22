"""
Integration tests for GMP-16: Closed-Loop Learning from Approvals.

Tests:
- Governance pattern creation on approve/reject
- Pattern retrieval for adaptive prompting
- Adaptive context generation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# Test Adaptive Prompting (uses core.agents which doesn't have memory import at top)
# =============================================================================


class TestAdaptivePrompting:
    """Test adaptive context generation."""

    def test_generate_context_from_rejections(self):
        """Test adaptive context from rejection patterns."""
        from core.agents.adaptive_prompting import generate_adaptive_context

        patterns = [
            {
                "tool_name": "gmprun",
                "decision": "rejected",
                "reason": "Missing tests",
                "conditions": ["requires_tests"],
            },
            {
                "tool_name": "gmprun",
                "decision": "rejected",
                "reason": "No runbook",
                "conditions": ["requires_runbook"],
            },
        ]

        context = generate_adaptive_context(patterns)

        assert "AVOID THESE" in context
        assert "test" in context.lower()
        assert "runbook" in context.lower()

    def test_generate_context_from_approvals(self):
        """Test adaptive context from approval patterns."""
        from core.agents.adaptive_prompting import generate_adaptive_context

        patterns = [
            {
                "tool_name": "git_commit",
                "decision": "approved",
                "reason": "Good tests",
                "conditions": ["good_test_coverage"],
            },
        ]

        context = generate_adaptive_context(patterns)

        assert "FOLLOW THESE" in context
        assert "test" in context.lower()

    def test_generate_context_mixed(self):
        """Test adaptive context from mixed patterns."""
        from core.agents.adaptive_prompting import generate_adaptive_context

        patterns = [
            {
                "tool_name": "gmprun",
                "decision": "rejected",
                "reason": "Too broad",
                "conditions": ["scope_concern"],
            },
            {
                "tool_name": "gmprun",
                "decision": "approved",
                "reason": "Incremental change",
                "conditions": ["incremental_change"],
            },
        ]

        context = generate_adaptive_context(patterns)

        assert "AVOID THESE" in context
        assert "FOLLOW THESE" in context
        assert "scope" in context.lower() or "broad" in context.lower()
        assert "incremental" in context.lower()

    def test_empty_patterns(self):
        """Test with no patterns."""
        from core.agents.adaptive_prompting import generate_adaptive_context

        context = generate_adaptive_context([])

        assert context == ""


# =============================================================================
# Test Pattern Retrieval with Mock
# =============================================================================


class TestPatternRetrieval:
    """Test governance pattern retrieval."""

    @pytest.mark.asyncio
    async def test_get_adaptive_context_for_tool(self):
        """Test getting adaptive context for a tool."""
        mock_patterns = [
            {
                "tool_name": "gmprun",
                "decision": "rejected",
                "reason": "No tests",
                "conditions": ["requires_tests"],
            },
        ]

        # Mock the entire memory.retrieval module
        mock_retrieval = MagicMock()
        mock_retrieval.get_governance_patterns = AsyncMock(return_value=mock_patterns)

        with patch.dict("sys.modules", {"memory.retrieval": mock_retrieval}):
            # Need to reimport after patching
            import sys

            if "core.agents.adaptive_prompting" in sys.modules:
                del sys.modules["core.agents.adaptive_prompting"]

            from core.agents.adaptive_prompting import \
                get_adaptive_context_for_tool

            context = await get_adaptive_context_for_tool("gmprun")

            assert "test" in context.lower()
            assert "AVOID THESE" in context


# =============================================================================
# Test ApprovalManager Pattern Writing (Mocked)
# =============================================================================


class TestApprovalManagerPatternWriting:
    """Test that ApprovalManager writes governance patterns."""

    @pytest.mark.asyncio
    async def test_approve_creates_pattern(self):
        """Test that approve_task creates a governance pattern."""
        # Mock all memory dependencies
        mock_substrate_models = MagicMock()
        mock_substrate_models.PacketEnvelopeIn = MagicMock()

        mock_governance_patterns = MagicMock()
        mock_governance_patterns.DecisionType = MagicMock()
        mock_governance_patterns.DecisionType.APPROVED = "approved"
        mock_governance_patterns.GovernancePattern = MagicMock()
        mock_governance_patterns.GovernancePattern.return_value.to_packet_payload.return_value = (
            {}
        )
        mock_governance_patterns.extract_conditions_from_reason = MagicMock(
            return_value=["good_test_coverage"]
        )

        with patch.dict(
            "sys.modules",
            {
                "memory.substrate_models": mock_substrate_models,
                "memory.governance_patterns": mock_governance_patterns,
            },
        ):
            # Import after mocking
            import sys

            if "core.governance.approvals" in sys.modules:
                del sys.modules["core.governance.approvals"]

            from core.governance.approvals import ApprovalManager

            mock_substrate = AsyncMock()
            mock_substrate.write_packet = AsyncMock()

            manager = ApprovalManager(mock_substrate)

            result = await manager.approve_task(
                task_id="task-approve-test",
                approved_by="Igor",
                reason="Good implementation",
                tool_name="git_commit",
                task_type="code_deploy",
                context={"files": ["src/main.py"]},
            )

            assert result is True
            # Should have been called twice: approval_record + governance_pattern
            assert mock_substrate.write_packet.call_count == 2

    @pytest.mark.asyncio
    async def test_unauthorized_approve_fails(self):
        """Test that non-Igor cannot approve."""
        mock_substrate_models = MagicMock()
        mock_substrate_models.PacketEnvelopeIn = MagicMock()

        mock_governance_patterns = MagicMock()
        mock_governance_patterns.DecisionType = MagicMock()
        mock_governance_patterns.extract_conditions_from_reason = MagicMock(
            return_value=[]
        )

        with patch.dict(
            "sys.modules",
            {
                "memory.substrate_models": mock_substrate_models,
                "memory.governance_patterns": mock_governance_patterns,
            },
        ):
            import sys

            if "core.governance.approvals" in sys.modules:
                del sys.modules["core.governance.approvals"]

            from core.governance.approvals import ApprovalManager

            mock_substrate = AsyncMock()
            manager = ApprovalManager(mock_substrate)

            result = await manager.approve_task(
                task_id="task-unauth",
                approved_by="NotIgor",
                reason="Trying to approve",
            )

            assert result is False
            mock_substrate.write_packet.assert_not_called()


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
