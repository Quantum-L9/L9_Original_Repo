"""
L9 Core Testing - Test Agent
=============================

Agent that orchestrates test generation and execution for high-risk proposals.

Spawned by the executor when gmprun, git_commit, or other high-risk tools
are called. Generates tests, runs them, and reports results.

Version: 1.0.0 (GMP-19)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Test Agent",
    "module_version": "1.0.0 (GMP-19)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T13:21:36Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "test_agent",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["tests.integration.test_recursive_self_testing"],
    },
}
# ============================================================================

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog

from core.testing.test_generator import TestGenerator
from core.testing.test_executor import TestExecutor, TestResults

logger = structlog.get_logger(__name__)


@dataclass
class TestAgentResult:
    """Result of test agent execution."""

    run_id: UUID
    parent_task_id: str
    tests_generated: int
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    coverage_percent: Optional[float]
    duration_ms: float
    timestamp: datetime
    recommendations: List[str]
    test_results: Optional[TestResults]
    success: bool
    error: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for memory storage."""
        return {
            "run_id": str(self.run_id),
            "parent_task_id": self.parent_task_id,
            "tests_generated": self.tests_generated,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "tests_skipped": self.tests_skipped,
            "coverage_percent": self.coverage_percent,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "recommendations": self.recommendations,
            "success": self.success,
            "error": self.error,
        }


class TestAgent:
    """
    Agent that generates and executes tests for code proposals.

    Spawned as a sibling task when high-risk operations are proposed.
    Writes results to the test_results memory segment.
    """

    def __init__(self, substrate_service: Optional[Any] = None):
        """
        Initialize TestAgent.

        Args:
            substrate_service: Memory substrate for storing results
        """
        self._substrate = substrate_service
        self._generator = TestGenerator()
        self._executor = TestExecutor()

    async def validate_proposal(
        self,
        task_id: str,
        code_proposal: str,
        proposal_type: str = "general",
        dependencies: Optional[List[str]] = None,
    ) -> TestAgentResult:
        """
        Validate a code proposal by generating and running tests.

        Args:
            task_id: Parent task ID
            code_proposal: Code to validate
            proposal_type: Type of proposal (gmp, git_commit, etc.)
            dependencies: List of module dependencies

        Returns:
            TestAgentResult with validation outcome
        """
        start_time = datetime.utcnow()
        run_id = uuid4()

        logger.info(
            "test_agent.validate_proposal.start",
            task_id=task_id,
            run_id=str(run_id),
            proposal_type=proposal_type,
        )

        try:
            # Generate unit tests
            unit_tests = self._generator.generate_unit_tests(code_proposal)

            # Generate integration tests if dependencies provided
            integration_tests = []
            if dependencies:
                integration_tests = self._generator.generate_integration_tests(
                    code_proposal, dependencies
                )

            all_tests = unit_tests + integration_tests
            tests_generated = len(all_tests)

            if tests_generated == 0:
                return TestAgentResult(
                    run_id=run_id,
                    parent_task_id=task_id,
                    tests_generated=0,
                    tests_passed=0,
                    tests_failed=0,
                    tests_skipped=0,
                    coverage_percent=None,
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    timestamp=datetime.utcnow(),
                    recommendations=["No testable code found in proposal"],
                    test_results=None,
                    success=True,  # No tests needed
                    error=None,
                )

            # Combine tests into a test file
            test_code = self._build_test_file(all_tests)

            # Execute tests
            test_results = await self._executor.run_tests(
                test_code=test_code,
                source_code=code_proposal,
            )

            # Generate recommendations
            recommendations = self._generate_recommendations(test_results)

            # Calculate duration
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            result = TestAgentResult(
                run_id=run_id,
                parent_task_id=task_id,
                tests_generated=tests_generated,
                tests_passed=test_results.passed,
                tests_failed=test_results.failed,
                tests_skipped=test_results.skipped,
                coverage_percent=test_results.coverage_percent,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
                recommendations=recommendations,
                test_results=test_results,
                success=test_results.failed == 0,
                error=None,
            )

            # Store results in memory
            await self._store_results(result)

            logger.info(
                "test_agent.validate_proposal.complete",
                task_id=task_id,
                run_id=str(run_id),
                tests_generated=tests_generated,
                tests_passed=test_results.passed,
                tests_failed=test_results.failed,
            )

            return result

        except Exception as e:
            logger.error(f"Test agent validation failed: {e}")
            return TestAgentResult(
                run_id=run_id,
                parent_task_id=task_id,
                tests_generated=0,
                tests_passed=0,
                tests_failed=0,
                tests_skipped=0,
                coverage_percent=None,
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                timestamp=datetime.utcnow(),
                recommendations=["Test generation/execution failed"],
                test_results=None,
                success=False,
                error=str(e),
            )

    def _build_test_file(self, tests: List[str]) -> str:
        """Build a complete test file from test functions."""
        header = '''"""
Auto-generated tests for code proposal validation.
Generated by L9 Test Agent.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

'''
        return header + "\n".join(tests)

    def _generate_recommendations(self, results: TestResults) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        if results.failed > 0:
            recommendations.append(
                f"Fix {results.failed} failing test(s) before proceeding"
            )

        if results.coverage_percent is not None:
            if results.coverage_percent < 50:
                recommendations.append(
                    f"Coverage is low ({results.coverage_percent}%). "
                    "Consider adding more tests."
                )
            elif results.coverage_percent < 80:
                recommendations.append(
                    f"Coverage is adequate ({results.coverage_percent}%). "
                    "Consider edge case coverage."
                )

        if results.skipped > 0:
            recommendations.append(
                f"{results.skipped} test(s) were skipped. Review skip conditions."
            )

        if not recommendations:
            recommendations.append("All tests passed. Proposal is safe to proceed.")

        return recommendations

    async def _store_results(self, result: TestAgentResult) -> None:
        """Store test results in memory substrate."""
        if self._substrate is None:
            logger.debug("No substrate, results not stored")
            return

        try:
            from core.schemas import PacketEnvelopeIn

            packet = PacketEnvelopeIn(
                packet_type="test_results",
                payload=result.to_dict(),
                metadata={
                    "segment": "test_results",
                    "parent_task_id": result.parent_task_id,
                },
            )
            await self._substrate.write_packet(packet_in=packet)

        except Exception as e:
            logger.warning(f"Failed to store test results: {e}")


async def spawn_test_agent(
    task_id: str,
    code_proposal: str,
    substrate_service: Optional[Any] = None,
    dependencies: Optional[List[str]] = None,
) -> TestAgentResult:
    """
    Spawn a test agent to validate a code proposal.

    Convenience function for spawning test validation.

    Args:
        task_id: Parent task ID
        code_proposal: Code to validate
        substrate_service: Optional memory substrate
        dependencies: Optional dependencies

    Returns:
        TestAgentResult
    """
    agent = TestAgent(substrate_service)
    return await agent.validate_proposal(
        task_id=task_id,
        code_proposal=code_proposal,
        dependencies=dependencies,
    )


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "TestAgent",
    "TestAgentResult",
    "spawn_test_agent",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-078",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.schemas",
        "core.testing.test_executor",
        "core.testing.test_generator",
    ],
    "tags": [
        "api",
        "async",
        "core",
        "dataclass",
        "debugging",
        "foundation",
        "logging",
        "mocking",
        "testing",
    ],
    "keywords": [
        "agent",
        "executor",
        "high",
        "proposal",
        "risk",
        "spawn",
        "test",
        "validate",
    ],
    "business_value": "Provides test agent components including TestAgentResult, TestAgent",
    "last_modified": "2026-01-14T13:21:36Z",
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
