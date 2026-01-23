"""
Integration Test: Governance Tracking → Self-Reflection (End-to-End)
=====================================================================

GMP: governance_tracking_enterprise_frontier
Tests the complete flow:
1. AgentInstance tracks governance blocks and user corrections
2. ExecutionResult carries this data
3. Self-reflection patterns detect behavioral gaps

Version: 1.0.0
"""

import pytest
from uuid import uuid4

from core.agents.schemas import AgentTask, AgentConfig, AgentType, ExecutionResult
from core.agents.agent_instance import AgentInstance
from core.agents.selfreflection import (
    TaskExecutionContext,
    analyze_task_execution,
    GovernanceBlockPattern,
    UserCorrectionPattern,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def task():
    """Create a test task."""
    return AgentTask(
        id=uuid4(),
        agent_type=AgentType.EXECUTOR,
        agent_id="test-agent-001",
        source_id="test-harness",
        payload={"message": "Execute operation with governance oversight"},
        timeout_ms=30000,
        max_iterations=10,
    )


@pytest.fixture
def config():
    """Create a test agent config."""
    return AgentConfig(
        agent_id="test-agent-001",
        name="Test Agent",
        personality_id="test-v1",
        model="gpt-4o",
    )


@pytest.fixture
def instance(config, task):
    """Create an AgentInstance."""
    return AgentInstance(config=config, task=task)


# =============================================================================
# Unit Tests: AgentInstance Tracking
# =============================================================================


class TestAgentInstanceGovernanceTracking:
    """Tests for AgentInstance governance block tracking."""

    def test_add_governance_block_authority(self, instance):
        """Test tracking an authority block."""
        instance.add_governance_block(
            block_type="authority_block",
            violation="Permission denied for elevated operation",
        )

        assert len(instance.governance_blocks) == 1
        block = instance.governance_blocks[0]
        assert block["type"] == "authority_block"
        assert block["violation"] == "Permission denied for elevated operation"
        assert "timestamp" in block
        assert "agent_id" in block

    def test_add_governance_block_safety(self, instance):
        """Test tracking a safety block."""
        instance.add_governance_block(
            block_type="safety_block",
            violation="Dangerous pattern detected",
            pattern="rm -rf",
        )

        assert len(instance.governance_blocks) == 1
        block = instance.governance_blocks[0]
        assert block["type"] == "safety_block"
        assert block["pattern"] == "rm -rf"

    def test_add_governance_block_tool_approval(self, instance):
        """Test tracking a tool approval block."""
        instance.add_governance_block(
            block_type="tool_approval_block",
            tool_id="mac_agent_exec",
            metadata={"call_id": "test-call-id"},
        )

        assert len(instance.governance_blocks) == 1
        block = instance.governance_blocks[0]
        assert block["type"] == "tool_approval_block"
        assert block["tool_id"] == "mac_agent_exec"
        assert block["metadata"]["call_id"] == "test-call-id"

    def test_governance_blocks_copy_isolation(self, instance):
        """Test that governance_blocks property returns a copy."""
        instance.add_governance_block(block_type="test_block")
        blocks = instance.governance_blocks
        blocks.append({"type": "fake"})

        # Original should not be affected
        assert len(instance.governance_blocks) == 1


class TestAgentInstanceUserCorrectionTracking:
    """Tests for AgentInstance user correction tracking."""

    def test_add_user_correction(self, instance):
        """Test tracking a user correction."""
        instance.add_user_correction(
            correction="No, use soft-delete instead.",
            metadata={"context": "file operation"},
        )

        assert len(instance.user_corrections) == 1
        corr = instance.user_corrections[0]
        assert corr["correction"] == "No, use soft-delete instead."
        assert corr["metadata"]["context"] == "file operation"
        assert "timestamp" in corr
        assert "iteration" in corr

    def test_multiple_user_corrections(self, instance):
        """Test tracking multiple user corrections."""
        instance.add_user_correction("First correction")
        instance.add_user_correction("Second correction")
        instance.add_user_correction("Third correction")

        assert len(instance.user_corrections) == 3

    def test_user_corrections_copy_isolation(self, instance):
        """Test that user_corrections property returns a copy."""
        instance.add_user_correction("Test correction")
        corrections = instance.user_corrections
        corrections.append({"correction": "fake"})

        # Original should not be affected
        assert len(instance.user_corrections) == 1


# =============================================================================
# Integration Tests: ExecutionResult Wiring
# =============================================================================


class TestExecutionResultGovernanceWiring:
    """Tests for ExecutionResult carrying governance data."""

    def test_execution_result_with_governance_blocks(self, task, instance):
        """Test ExecutionResult carries governance blocks."""
        instance.add_governance_block(block_type="authority_block", violation="test")
        instance.add_governance_block(block_type="safety_block", violation="test")

        result = ExecutionResult(
            task_id=task.id,
            status="blocked",
            error="Blocked by governance",
            iterations=1,
            duration_ms=100,
            governance_blocks=instance.governance_blocks,
        )

        assert result.governance_blocks is not None
        assert len(result.governance_blocks) == 2

    def test_execution_result_with_user_corrections(self, task, instance):
        """Test ExecutionResult carries user corrections."""
        instance.add_user_correction("Correction 1")
        instance.add_user_correction("Correction 2")

        result = ExecutionResult(
            task_id=task.id,
            status="completed",
            result="Done",
            iterations=3,
            duration_ms=1000,
            user_corrections=instance.user_corrections,
        )

        assert result.user_corrections is not None
        assert len(result.user_corrections) == 2

    def test_execution_result_none_when_empty(self, task):
        """Test ExecutionResult can have None for empty tracking."""
        result = ExecutionResult(
            task_id=task.id,
            status="completed",
            result="Done",
            iterations=1,
            duration_ms=100,
            governance_blocks=None,
            user_corrections=None,
        )

        assert result.governance_blocks is None
        assert result.user_corrections is None


# =============================================================================
# Integration Tests: Self-Reflection Pattern Detection
# =============================================================================


class TestGovernanceBlockPatternDetection:
    """Tests for GovernanceBlockPattern firing correctly."""

    def test_governance_block_pattern_fires_on_denied_blocks(self):
        """Test GovernanceBlockPattern fires when blocks have 'denied' reason."""
        context = TaskExecutionContext(
            task_id="test-123",
            agent_id="test-agent",
            task_kind="execution",
            success=True,  # Task succeeded despite blocks
            duration_ms=1000.0,
            tool_calls=[],
            errors=[],
            warnings=[],
            iterations=3,
            tokens_used=1000,
            governance_blocks=[
                {"type": "authority_block", "reason": "Permission denied"},
                {"type": "safety_block", "reason": "Action denied by policy"},
            ],
            user_corrections=[],
        )

        pattern = GovernanceBlockPattern()
        gap = pattern.detect(context)

        assert gap is not None
        assert gap.gap_type == "POLICY"
        assert gap.kernel_id == "safety"
        assert "overly restrictive" in gap.description.lower()

    def test_governance_block_pattern_does_not_fire_on_failure(self):
        """Test GovernanceBlockPattern doesn't fire when task failed."""
        context = TaskExecutionContext(
            task_id="test-123",
            agent_id="test-agent",
            task_kind="execution",
            success=False,  # Task failed
            duration_ms=1000.0,
            tool_calls=[],
            errors=["Task failed"],
            warnings=[],
            iterations=3,
            tokens_used=1000,
            governance_blocks=[
                {"type": "authority_block", "reason": "Permission denied"},
            ],
            user_corrections=[],
        )

        pattern = GovernanceBlockPattern()
        gap = pattern.detect(context)

        # Should not fire because task didn't succeed
        assert gap is None

    def test_governance_block_pattern_no_denied_reason(self):
        """Test GovernanceBlockPattern doesn't fire without 'denied' reason."""
        context = TaskExecutionContext(
            task_id="test-123",
            agent_id="test-agent",
            task_kind="execution",
            success=True,
            duration_ms=1000.0,
            tool_calls=[],
            errors=[],
            warnings=[],
            iterations=3,
            tokens_used=1000,
            governance_blocks=[
                {"type": "authority_block", "violation": "test"},  # No 'reason' field
            ],
            user_corrections=[],
        )

        pattern = GovernanceBlockPattern()
        gap = pattern.detect(context)

        assert gap is None

    def test_governance_block_pattern_empty_blocks(self):
        """Test GovernanceBlockPattern doesn't fire with empty blocks."""
        context = TaskExecutionContext(
            task_id="test-123",
            agent_id="test-agent",
            task_kind="execution",
            success=True,
            duration_ms=1000.0,
            tool_calls=[],
            errors=[],
            warnings=[],
            iterations=3,
            tokens_used=1000,
            governance_blocks=[],
            user_corrections=[],
        )

        pattern = GovernanceBlockPattern()
        gap = pattern.detect(context)

        assert gap is None


class TestUserCorrectionPatternDetection:
    """Tests for UserCorrectionPattern firing correctly."""

    def test_user_correction_pattern_fires_on_multiple_corrections(self):
        """Test UserCorrectionPattern fires with >= 2 corrections."""
        context = TaskExecutionContext(
            task_id="test-123",
            agent_id="test-agent",
            task_kind="execution",
            success=True,
            duration_ms=1000.0,
            tool_calls=[],
            errors=[],
            warnings=[],
            iterations=5,
            tokens_used=2000,
            governance_blocks=[],
            user_corrections=[
                "No, do X instead",
                "Actually, use Y approach",
            ],
        )

        pattern = UserCorrectionPattern()
        gap = pattern.detect(context)

        assert gap is not None
        assert gap.gap_type == "CONSTRAINT"
        assert gap.kernel_id == "behavioral"
        assert "2 corrections" in gap.description

    def test_user_correction_pattern_severity_scales(self):
        """Test UserCorrectionPattern severity scales with correction count."""
        # 2-3 corrections = MEDIUM
        context_medium = TaskExecutionContext(
            task_id="test-123",
            agent_id="test-agent",
            task_kind="execution",
            success=True,
            duration_ms=1000.0,
            tool_calls=[],
            errors=[],
            warnings=[],
            iterations=5,
            tokens_used=2000,
            governance_blocks=[],
            user_corrections=["C1", "C2", "C3"],
        )

        # 4+ corrections = HIGH
        context_high = TaskExecutionContext(
            task_id="test-456",
            agent_id="test-agent",
            task_kind="execution",
            success=True,
            duration_ms=1000.0,
            tool_calls=[],
            errors=[],
            warnings=[],
            iterations=5,
            tokens_used=2000,
            governance_blocks=[],
            user_corrections=["C1", "C2", "C3", "C4"],
        )

        pattern = UserCorrectionPattern()
        gap_medium = pattern.detect(context_medium)
        gap_high = pattern.detect(context_high)

        assert gap_medium.severity == "MEDIUM"
        assert gap_high.severity == "HIGH"

    def test_user_correction_pattern_single_correction_no_fire(self):
        """Test UserCorrectionPattern doesn't fire with only 1 correction."""
        context = TaskExecutionContext(
            task_id="test-123",
            agent_id="test-agent",
            task_kind="execution",
            success=True,
            duration_ms=1000.0,
            tool_calls=[],
            errors=[],
            warnings=[],
            iterations=3,
            tokens_used=1000,
            governance_blocks=[],
            user_corrections=["Single correction"],
        )

        pattern = UserCorrectionPattern()
        gap = pattern.detect(context)

        assert gap is None

    def test_user_correction_pattern_empty_corrections(self):
        """Test UserCorrectionPattern doesn't fire with empty corrections."""
        context = TaskExecutionContext(
            task_id="test-123",
            agent_id="test-agent",
            task_kind="execution",
            success=True,
            duration_ms=1000.0,
            tool_calls=[],
            errors=[],
            warnings=[],
            iterations=3,
            tokens_used=1000,
            governance_blocks=[],
            user_corrections=[],
        )

        pattern = UserCorrectionPattern()
        gap = pattern.detect(context)

        assert gap is None


# =============================================================================
# End-to-End Integration Test
# =============================================================================


class TestGovernanceTrackingEndToEnd:
    """End-to-end test of the complete governance tracking flow."""

    @pytest.mark.asyncio
    async def test_full_flow_both_patterns_fire(self, task, instance):
        """
        Test complete flow:
        1. Track governance blocks on instance
        2. Track user corrections on instance
        3. Build ExecutionResult with tracked data
        4. Run self-reflection
        5. Verify both patterns fire
        """
        # Phase 1: Track governance blocks
        instance.add_governance_block(
            block_type="authority_block",
            violation="Permission denied",
            metadata={"reason": "Access denied for elevated operation"},
        )
        instance.add_governance_block(
            block_type="safety_block",
            violation="Dangerous pattern",
            pattern="rm -rf",
            metadata={"reason": "Action denied due to safety policy"},
        )

        # Phase 2: Track user corrections
        instance.add_user_correction("No, use soft-delete instead.")
        instance.add_user_correction("Query the database first.")

        # Phase 3: Build ExecutionResult
        result = ExecutionResult(
            task_id=task.id,
            status="completed",  # Task succeeded despite blocks
            result="Completed with workarounds",
            iterations=5,
            duration_ms=12500,
            error=None,
            trace_id=instance.instance_id,
            tokens_used=8500,
            governance_blocks=instance.governance_blocks,
            user_corrections=instance.user_corrections,
        )

        # Phase 4: Build TaskExecutionContext (same as _run_self_reflection)
        formatted_blocks = []
        for block in result.governance_blocks or []:
            formatted_block = dict(block)
            if "metadata" in formatted_block and formatted_block["metadata"]:
                if "reason" in formatted_block["metadata"]:
                    formatted_block["reason"] = formatted_block["metadata"]["reason"]
            formatted_blocks.append(formatted_block)

        context = TaskExecutionContext(
            task_id=str(task.id),
            agent_id=task.agent_id,
            task_kind=task.kind.value,
            success=True,
            duration_ms=float(result.duration_ms),
            tool_calls=[],
            errors=[],
            warnings=[],
            iterations=result.iterations,
            tokens_used=result.tokens_used or 0,
            governance_blocks=formatted_blocks,
            user_corrections=[
                uc.get("correction", str(uc)) for uc in (result.user_corrections or [])
            ],
            metadata={},
        )

        # Phase 5: Run analysis
        reflection_result = await analyze_task_execution(context)

        # Phase 6: Verify
        assert len(reflection_result.gaps_detected) >= 2

        gap_types = {gap.gap_type for gap in reflection_result.gaps_detected}
        assert "POLICY" in gap_types, "GovernanceBlockPattern should have fired"
        assert "CONSTRAINT" in gap_types, "UserCorrectionPattern should have fired"

        # Verify recommendations generated
        assert len(reflection_result.recommendations) >= 2

    @pytest.mark.asyncio
    async def test_no_patterns_fire_when_no_issues(self, task, instance):
        """Test that no patterns fire when there are no governance issues."""
        # Clean execution - no blocks, no corrections
        result = ExecutionResult(
            task_id=task.id,
            status="completed",
            result="Clean execution",
            iterations=2,
            duration_ms=500,
            error=None,
            tokens_used=1000,
            governance_blocks=None,
            user_corrections=None,
        )

        context = TaskExecutionContext(
            task_id=str(task.id),
            agent_id=task.agent_id,
            task_kind=task.kind.value,
            success=True,
            duration_ms=float(result.duration_ms),
            tool_calls=[],
            errors=[],
            warnings=[],
            iterations=result.iterations,
            tokens_used=result.tokens_used or 0,
            governance_blocks=[],
            user_corrections=[],
            metadata={},
        )

        reflection_result = await analyze_task_execution(context)

        # Should have no POLICY or CONSTRAINT gaps
        gap_types = {gap.gap_type for gap in reflection_result.gaps_detected}
        assert "POLICY" not in gap_types
        assert "CONSTRAINT" not in gap_types
