"""
Integration Tests for Kernel Evolution Flow
============================================

Tests the full flow from task execution → self-reflection →
gap detection → kernel evolution proposal generation.

Version: 1.0.0
GMP: kernel_boot_frontier_phase1
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from core.agents.selfreflection import (
    TaskExecutionContext,
    BehaviorGap,
    ReflectionResult,
    detect_behavior_gaps,
    analyze_task_execution,
)
from core.agents.kernelevolution import (
    KernelUpdateProposal,
    EvolutionPlan,
    generate_proposal_from_gap,
    create_evolution_plan,
    generate_gmp_spec_from_plan,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def successful_task_context():
    """A task context representing a successful execution."""
    return TaskExecutionContext(
        task_id=str(uuid4()),
        agent_id="l-cto",
        task_kind="REASONING",
        success=True,
        duration_ms=1500.0,
        tool_calls=[
            {"tool_id": "codebase_search", "success": True},
            {"tool_id": "read_file", "success": True},
        ],
        errors=[],
        warnings=[],
        iterations=3,
        tokens_used=5000,
        governance_blocks=[],
        user_corrections=[],
        metadata={},
    )


@pytest.fixture
def problematic_task_context():
    """A task context with multiple issues that should trigger gap detection."""
    return TaskExecutionContext(
        task_id=str(uuid4()),
        agent_id="l-cto",
        task_kind="CODE_GENERATION",
        success=True,  # Succeeded but with issues
        duration_ms=45000.0,
        tool_calls=[
            {"tool_id": "codebase_search", "success": True},
            {"tool_id": "write_file", "success": False},  # Failed
            {"tool_id": "write_file", "success": False},  # Failed again
            {"tool_id": "write_file", "success": False},  # Failed third time
            {"tool_id": "write_file", "success": True},  # Finally succeeded
        ],
        errors=["Permission denied", "File locked", "Retry limit"],
        warnings=["High token usage"],
        iterations=12,  # Excessive iterations
        tokens_used=75000,  # High token usage
        governance_blocks=[
            {"reason": "Tool denied: write_file requires approval"},
        ],
        user_corrections=[
            "Use a different approach",
            "Don't modify that file",
        ],
        metadata={},
    )


@pytest.fixture
def failed_task_context():
    """A task context representing a failed execution."""
    return TaskExecutionContext(
        task_id=str(uuid4()),
        agent_id="l-cto",
        task_kind="TOOL_USE",
        success=False,
        duration_ms=30000.0,
        tool_calls=[
            {"tool_id": "shell_exec", "success": False},
            {"tool_id": "shell_exec", "success": False},
            {"tool_id": "shell_exec", "success": False},
            {"tool_id": "shell_exec", "success": False},
        ],
        errors=["Command failed", "Timeout", "Permission denied", "Fatal error"],
        warnings=[],
        iterations=5,
        tokens_used=20000,
        governance_blocks=[],
        user_corrections=[],
        metadata={},
    )


# =============================================================================
# Self-Reflection Tests
# =============================================================================


class TestGapDetection:
    """Tests for behavioral gap detection."""

    def test_no_gaps_on_successful_execution(self, successful_task_context):
        """Successful execution with no issues should detect no gaps."""
        gaps = detect_behavior_gaps(successful_task_context)
        assert len(gaps) == 0

    def test_detects_repeated_tool_failures(self, problematic_task_context):
        """Should detect repeated tool failures."""
        gaps = detect_behavior_gaps(problematic_task_context)

        tool_failure_gaps = [g for g in gaps if g.gap_type == "CAPABILITY"]
        assert len(tool_failure_gaps) >= 1

        # Should identify write_file as the problematic tool
        gap = tool_failure_gaps[0]
        assert "write_file" in gap.description
        assert gap.severity in ("MEDIUM", "HIGH")

    def test_detects_excessive_iterations(self, problematic_task_context):
        """Should detect excessive iteration count."""
        gaps = detect_behavior_gaps(problematic_task_context)

        iteration_gaps = [
            g for g in gaps if g.gap_type == "PERFORMANCE" and "iteration" in g.description.lower()
        ]
        assert len(iteration_gaps) == 1
        assert iteration_gaps[0].metadata.get("iterations") == 12

    def test_detects_token_overuse(self, problematic_task_context):
        """Should detect excessive token usage."""
        gaps = detect_behavior_gaps(problematic_task_context)

        token_gaps = [
            g for g in gaps if g.gap_type == "PERFORMANCE" and "token" in g.description.lower()
        ]
        assert len(token_gaps) == 1
        assert token_gaps[0].metadata.get("tokens_used") == 75000

    def test_detects_user_corrections(self, problematic_task_context):
        """Should detect user corrections as behavioral gaps."""
        gaps = detect_behavior_gaps(problematic_task_context)

        correction_gaps = [g for g in gaps if g.gap_type == "CONSTRAINT"]
        assert len(correction_gaps) == 1
        assert correction_gaps[0].metadata.get("correction_count") == 2


class TestReflectionAnalysis:
    """Tests for full reflection analysis."""

    @pytest.mark.asyncio
    async def test_analyze_successful_task(self, successful_task_context):
        """Analyzing a successful task should produce minimal recommendations."""
        result = await analyze_task_execution(successful_task_context)

        assert isinstance(result, ReflectionResult)
        assert result.task_id == successful_task_context.task_id
        assert result.agent_id == successful_task_context.agent_id
        assert len(result.gaps_detected) == 0
        assert result.kernel_update_needed is False
        assert "No immediate action required" in result.recommendations

    @pytest.mark.asyncio
    async def test_analyze_problematic_task(self, problematic_task_context):
        """Analyzing a problematic task should detect multiple gaps."""
        result = await analyze_task_execution(problematic_task_context)

        assert isinstance(result, ReflectionResult)
        assert len(result.gaps_detected) >= 3  # Tool failures, iterations, tokens
        assert result.kernel_update_needed is True  # HIGH severity gaps present
        assert len(result.recommendations) >= 3

    @pytest.mark.asyncio
    async def test_reflection_includes_patterns_observed(self, failed_task_context):
        """Reflection should include observed patterns."""
        result = await analyze_task_execution(failed_task_context)

        assert "Task failed" in result.patterns_observed
        assert any("tool failure" in p.lower() for p in result.patterns_observed)


# =============================================================================
# Kernel Evolution Tests
# =============================================================================


class TestProposalGeneration:
    """Tests for kernel update proposal generation."""

    def test_generate_proposal_from_capability_gap(self):
        """Should generate appropriate proposal for capability gap."""
        gap = BehaviorGap(
            gap_id=str(uuid4()),
            gap_type="CAPABILITY",
            description="Tool 'write_file' failed 4 times",
            severity="HIGH",
            kernel_id="execution",
            evidence=["Tool write_file failed 4 times"],
            suggested_action="Add retry logic for write_file",
            confidence=0.85,
        )

        proposal = generate_proposal_from_gap(gap)

        assert isinstance(proposal, KernelUpdateProposal)
        assert proposal.kernel_id == "execution"
        assert proposal.update_type == "ADD_RULE"
        assert proposal.priority == "HIGH"
        assert proposal.requires_igor_approval is True  # HIGH severity
        assert len(proposal.proposed_changes) >= 1

    def test_generate_proposal_from_constraint_gap(self):
        """Should generate appropriate proposal for constraint gap."""
        gap = BehaviorGap(
            gap_id=str(uuid4()),
            gap_type="CONSTRAINT",
            description="User made 3 corrections",
            severity="MEDIUM",
            kernel_id=None,  # Should be mapped to behavioral
            evidence=["3 corrections made"],
            suggested_action="Add behavioral constraint",
            confidence=0.75,
        )

        proposal = generate_proposal_from_gap(gap)

        assert proposal.kernel_id == "behavioral"
        assert proposal.update_type == "ADD_CONSTRAINT"
        assert proposal.requires_igor_approval is False  # MEDIUM severity

    def test_generate_proposal_from_safety_gap(self):
        """Safety gaps should always require Igor approval."""
        gap = BehaviorGap(
            gap_id=str(uuid4()),
            gap_type="SAFETY",
            description="Unsafe operation attempted",
            severity="LOW",  # Even LOW severity safety gaps need approval
            kernel_id="safety",
            evidence=["Unsafe operation"],
            suggested_action="Add safety constraint",
            confidence=0.9,
        )

        proposal = generate_proposal_from_gap(gap)

        assert proposal.kernel_id == "safety"
        assert proposal.requires_igor_approval is True  # Safety always needs approval


class TestEvolutionPlan:
    """Tests for evolution plan creation."""

    @pytest.mark.asyncio
    async def test_create_evolution_plan(self, problematic_task_context):
        """Should create comprehensive evolution plan from reflection."""
        reflection = await analyze_task_execution(problematic_task_context)
        plan = await create_evolution_plan(reflection)

        assert isinstance(plan, EvolutionPlan)
        assert plan.reflection_id == reflection.reflection_id
        assert plan.agent_id == reflection.agent_id
        assert len(plan.proposals) == len(reflection.gaps_detected)
        assert plan.total_gaps_addressed == len(reflection.gaps_detected)

    @pytest.mark.asyncio
    async def test_evolution_plan_impact_assessment(self, problematic_task_context):
        """Plan should correctly assess impact level."""
        reflection = await analyze_task_execution(problematic_task_context)
        plan = await create_evolution_plan(reflection)

        # With multiple HIGH severity gaps, impact should be HIGH
        high_priority_count = sum(1 for p in plan.proposals if p.priority in ("HIGH", "CRITICAL"))

        if high_priority_count >= 2:
            assert plan.estimated_impact == "HIGH"
        elif high_priority_count == 1 or len(plan.proposals) >= 3:
            assert plan.estimated_impact in ("MEDIUM", "HIGH")

    @pytest.mark.asyncio
    async def test_evolution_plan_approval_requirement(self, problematic_task_context):
        """Plan should require approval if any proposal does."""
        reflection = await analyze_task_execution(problematic_task_context)
        plan = await create_evolution_plan(reflection)

        any_requires_approval = any(p.requires_igor_approval for p in plan.proposals)
        assert plan.requires_igor_approval == any_requires_approval


class TestGMPSpecGeneration:
    """Tests for GMP specification generation."""

    @pytest.mark.asyncio
    async def test_generate_gmp_spec(self, problematic_task_context):
        """Should generate valid GMP specification from plan."""
        reflection = await analyze_task_execution(problematic_task_context)
        plan = await create_evolution_plan(reflection)
        spec = generate_gmp_spec_from_plan(plan)

        assert isinstance(spec, str)
        assert "GMP Kernel Evolution Plan" in spec
        assert plan.plan_id in spec
        assert str(len(plan.proposals)) in spec
        assert plan.estimated_impact in spec

    @pytest.mark.asyncio
    async def test_proposal_to_gmp_spec(self):
        """Individual proposals should generate valid GMP specs."""
        gap = BehaviorGap(
            gap_id="test-gap-123",
            gap_type="CAPABILITY",
            description="Test gap",
            severity="MEDIUM",
            kernel_id="execution",
            evidence=["Evidence 1"],
            suggested_action="Add rule",
            confidence=0.8,
        )

        proposal = generate_proposal_from_gap(gap)
        spec = proposal.to_gmp_spec()

        assert "GMP Kernel Evolution Proposal" in spec
        assert proposal.proposal_id in spec
        assert proposal.kernel_id in spec
        assert proposal.priority in spec


# =============================================================================
# Integration Flow Tests
# =============================================================================


class TestFullEvolutionFlow:
    """Tests for the complete evolution flow."""

    @pytest.mark.asyncio
    async def test_end_to_end_flow(self, problematic_task_context):
        """Test complete flow from context to GMP spec."""
        # Step 1: Analyze task execution
        reflection = await analyze_task_execution(problematic_task_context)
        assert reflection.gaps_detected

        # Step 2: Create evolution plan
        plan = await create_evolution_plan(reflection)
        assert plan.proposals

        # Step 3: Generate GMP spec
        spec = generate_gmp_spec_from_plan(plan)
        assert spec

        # Verify chain of custody
        assert plan.reflection_id == reflection.reflection_id
        for proposal in plan.proposals:
            assert proposal.gaps_addressed[0] in [g.gap_id for g in reflection.gaps_detected]

    @pytest.mark.asyncio
    async def test_no_evolution_for_clean_execution(self, successful_task_context):
        """Clean executions should not generate evolution plans."""
        reflection = await analyze_task_execution(successful_task_context)

        assert len(reflection.gaps_detected) == 0
        assert reflection.kernel_update_needed is False

        # Plan should be empty
        plan = await create_evolution_plan(reflection)
        assert len(plan.proposals) == 0
        assert plan.estimated_impact == "LOW"


class TestExecutorIntegration:
    """Tests for executor integration with self-reflection."""

    @pytest.mark.asyncio
    async def test_executor_runs_self_reflection(self):
        """Executor should run self-reflection after task completion."""
        try:
            from core.agents.executor import AgentExecutorService, _has_self_reflection

            # Verify self-reflection is available
            assert _has_self_reflection is True
        except (ImportError, ModuleNotFoundError):
            # Skip if executor can't be imported (pytest path issues with memory module)
            pytest.skip("core.agents.executor not importable in test environment")

    @pytest.mark.asyncio
    async def test_self_reflection_does_not_fail_task(self):
        """Self-reflection errors should not cause task failure."""
        # This is a design requirement - self-reflection is observational only
        # and should never cause a task to fail

        context = TaskExecutionContext(
            task_id=str(uuid4()),
            agent_id="test-agent",
            task_kind="TEST",
            success=True,
            duration_ms=100.0,
            tool_calls=[],
            errors=[],
            warnings=[],
            iterations=1,
            tokens_used=100,
            governance_blocks=[],
            user_corrections=[],
        )

        # Even with mocked errors, analysis should not raise
        with patch(
            "core.agents.selfreflection.DEFAULT_PATTERNS",
            [MagicMock(detect=MagicMock(side_effect=Exception("Test error")))],
        ):
            gaps = detect_behavior_gaps(context)
            # Should return empty list, not raise
            assert gaps == []
