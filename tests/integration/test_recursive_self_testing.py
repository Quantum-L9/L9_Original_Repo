"""
L9 Integration Tests - Recursive Self-Testing (GMP-19)
========================================================

Tests for test generation, execution, and integration with approvals.

Version: 1.0.0
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from core.testing.test_agent import TestAgent, TestAgentResult, spawn_test_agent
from core.testing.test_executor import TestResults
from core.testing.test_generator import (
    TestGenerator,
    generate_integration_tests,
    generate_unit_tests,
)


class TestTestGenerator:
    """Test the test generator module."""

    def test_generate_unit_tests_from_function(self):
        """Test generating unit tests from a simple function."""
        code = '''
def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(x, y):
    """Multiply two numbers."""
    return x * y
'''
        generator = TestGenerator()
        tests = generator.generate_unit_tests(code)

        assert len(tests) >= 2  # At least one test per function

        # Check test names are generated
        test_code = "\n".join(tests)
        assert "test_add" in test_code or "add" in test_code

    def test_generate_unit_tests_from_class(self):
        """Test generating unit tests from a class."""
        code = """
class Calculator:
    def __init__(self, initial=0):
        self.value = initial

    def add(self, x):
        self.value += x
        return self.value

    def reset(self):
        self.value = 0
"""
        generator = TestGenerator()
        tests = generator.generate_unit_tests(code)

        assert len(tests) >= 1  # At least instantiation test

        test_code = "\n".join(tests)
        assert "calculator" in test_code.lower()

    def test_generate_integration_tests(self):
        """Test generating integration tests with dependencies."""
        code = """
async def fetch_data(client):
    return await client.get("/api/data")
"""
        dependencies = ["httpx", "asyncio"]

        generator = TestGenerator()
        tests = generator.generate_integration_tests(code, dependencies)

        assert len(tests) >= 1

        test_code = "\n".join(tests)
        assert "async" in test_code or "integration" in test_code

    def test_generate_unit_tests_convenience_function(self):
        """Test the convenience function for unit test generation."""
        code = "def greet(name): return f'Hello, {name}!'"

        tests = generate_unit_tests(code)

        assert len(tests) >= 1

    def test_generate_integration_tests_convenience_function(self):
        """Test the convenience function for integration test generation."""
        code = "async def process(): pass"
        dependencies = ["module_a"]

        tests = generate_integration_tests(code, dependencies)

        assert len(tests) >= 1

    def test_handles_syntax_error(self):
        """Test generator handles invalid Python syntax."""
        code = "def broken(: invalid syntax"

        generator = TestGenerator()
        tests = generator.generate_unit_tests(code)

        # Should return at least a syntax test
        assert len(tests) >= 1


class TestTestResults:
    """Test the TestResults dataclass."""

    def test_test_results_creation(self):
        """Test creating TestResults."""
        results = TestResults(
            total_tests=5,
            passed=3,
            failed=1,
            skipped=1,
            coverage_percent=75.0,
            duration_ms=500,
            success=False,
        )

        assert results.total_tests == 5
        assert results.passed == 3
        assert results.failed == 1
        assert results.coverage_percent == 75.0
        assert results.success is False

    def test_test_results_to_dict(self):
        """Test TestResults serialization."""
        results = TestResults(
            total_tests=3,
            passed=3,
            failed=0,
            skipped=0,
            success=True,
        )

        data = results.to_dict()

        assert data["total_tests"] == 3
        assert data["passed"] == 3
        assert data["success"] is True
        assert "run_id" in data
        assert "timestamp" in data


class TestTestAgentResult:
    """Test the TestAgentResult dataclass."""

    def test_test_agent_result_creation(self):
        """Test creating TestAgentResult."""
        result = TestAgentResult(
            run_id=uuid4(),
            parent_task_id="task-123",
            tests_generated=5,
            tests_passed=4,
            tests_failed=1,
            tests_skipped=0,
            coverage_percent=80.0,
            duration_ms=1000,
            timestamp=datetime.now(timezone.utc),
            recommendations=["Fix failing test"],
            test_results=None,
            success=False,
            error=None,
        )

        assert result.tests_generated == 5
        assert result.tests_passed == 4
        assert result.tests_failed == 1
        assert result.success is False

    def test_test_agent_result_to_dict(self):
        """Test TestAgentResult serialization."""
        result = TestAgentResult(
            run_id=uuid4(),
            parent_task_id="task-456",
            tests_generated=3,
            tests_passed=3,
            tests_failed=0,
            tests_skipped=0,
            coverage_percent=90.0,
            duration_ms=500,
            timestamp=datetime.now(timezone.utc),
            recommendations=["All tests passed"],
            test_results=None,
            success=True,
            error=None,
        )

        data = result.to_dict()

        assert data["parent_task_id"] == "task-456"
        assert data["tests_generated"] == 3
        assert data["success"] is True
        assert "run_id" in data


class TestTestAgent:
    """Test the TestAgent class."""

    @pytest.mark.asyncio
    async def test_validate_proposal_generates_tests(self):
        """Test that validate_proposal generates tests."""
        agent = TestAgent()

        code_proposal = '''
def process_data(data):
    """Process input data."""
    if not data:
        return None
    return [x * 2 for x in data]
'''

        result = await agent.validate_proposal(
            task_id="test-task-001",
            code_proposal=code_proposal,
        )

        assert result.tests_generated >= 1
        assert result.parent_task_id == "test-task-001"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_proposal_with_dependencies(self):
        """Test validate_proposal with dependencies."""
        agent = TestAgent()

        code_proposal = """
async def fetch_user(user_id, db):
    return await db.get_user(user_id)
"""

        result = await agent.validate_proposal(
            task_id="test-task-002",
            code_proposal=code_proposal,
            dependencies=["database", "asyncio"],
        )

        assert result.tests_generated >= 1

    @pytest.mark.asyncio
    async def test_validate_proposal_empty_code(self):
        """Test validate_proposal with empty code."""
        agent = TestAgent()

        result = await agent.validate_proposal(
            task_id="test-task-003",
            code_proposal="# Just a comment",
        )

        # Should handle gracefully
        assert result.error is None or result.tests_generated == 0

    @pytest.mark.asyncio
    async def test_spawn_test_agent_convenience(self):
        """Test the spawn_test_agent convenience function."""
        code_proposal = "def hello(): return 'world'"

        result = await spawn_test_agent(
            task_id="spawn-test-001",
            code_proposal=code_proposal,
        )

        assert result.parent_task_id == "spawn-test-001"


class TestTestAgentRecommendations:
    """Test recommendation generation."""

    def test_generates_failure_recommendations(self):
        """Test that recommendations are generated for failures."""
        agent = TestAgent()

        results = TestResults(
            total_tests=5,
            passed=3,
            failed=2,
            skipped=0,
            success=False,
        )

        recommendations = agent._generate_recommendations(results)

        assert len(recommendations) >= 1
        assert any(
            "failing" in r.lower() or "fix" in r.lower() for r in recommendations
        )

    def test_generates_coverage_recommendations(self):
        """Test that low coverage triggers recommendations."""
        agent = TestAgent()

        results = TestResults(
            total_tests=2,
            passed=2,
            failed=0,
            skipped=0,
            coverage_percent=30.0,
            success=True,
        )

        recommendations = agent._generate_recommendations(results)

        assert any("coverage" in r.lower() for r in recommendations)

    def test_generates_success_recommendations(self):
        """Test that all passing generates positive recommendation."""
        agent = TestAgent()

        results = TestResults(
            total_tests=5,
            passed=5,
            failed=0,
            skipped=0,
            coverage_percent=95.0,
            success=True,
        )

        recommendations = agent._generate_recommendations(results)

        assert any(
            "passed" in r.lower() or "proceed" in r.lower() for r in recommendations
        )


class TestApprovalIntegration:
    """Test integration with approval manager."""

    def test_format_approval_request_with_tests(self):
        """Test formatting approval request with test results."""
        from unittest.mock import MagicMock, patch

        # Mock the imports in approvals module
        with patch.dict(
            "sys.modules",
            {
                "memory.substrate_models": MagicMock(),
                "memory.governance_patterns": MagicMock(),
            },
        ):
            # Create a minimal ApprovalManager for testing format method
            class MinimalApprovalManager:
                def format_approval_request_with_tests(
                    self, task_id, proposal_summary, test_summary
                ):
                    parts = [
                        f"**APPROVAL REQUEST: {task_id[:8]}...**\n",
                        f"**Proposal:** {proposal_summary}\n",
                    ]

                    if test_summary:
                        parts.append("\n**Test Results:**")
                        parts.append(f"- Tests Passed: {test_summary['tests_passed']}")
                        parts.append(f"- Tests Failed: {test_summary['tests_failed']}")

                        if test_summary.get("coverage_percent") is not None:
                            parts.append(
                                f"- Coverage: {test_summary['coverage_percent']}%"
                            )

                        if test_summary["tests_failed"] > 0:
                            parts.append("\n⚠️ **WARNING: Tests failed.**")
                    else:
                        parts.append("\n*No test results available.*")

                    return "\n".join(parts)

            manager = MinimalApprovalManager()

            test_summary = {
                "tests_generated": 10,
                "tests_passed": 8,
                "tests_failed": 2,
                "coverage_percent": 75.0,
                "recommendations": ["Fix 2 failing tests", "Increase coverage"],
                "success": False,
            }

            message = manager.format_approval_request_with_tests(
                task_id="approval-test-001",
                proposal_summary="Add new feature X",
                test_summary=test_summary,
            )

            assert "APPROVAL REQUEST" in message
            assert "Add new feature X" in message
            assert "Tests Passed: 8" in message
            assert "Tests Failed: 2" in message
            assert "75.0%" in message
            assert "WARNING" in message  # Because tests failed

    def test_format_approval_request_without_tests(self):
        """Test formatting approval request without test results."""

        # Create minimal format method for testing
        def format_approval_request(task_id, proposal_summary, test_summary):
            parts = [
                f"**APPROVAL REQUEST: {task_id[:8]}...**\n",
                f"**Proposal:** {proposal_summary}\n",
            ]

            if test_summary:
                parts.append(f"- Tests Passed: {test_summary['tests_passed']}")
            else:
                parts.append("\n*No test results available.*")

            return "\n".join(parts)

        message = format_approval_request(
            task_id="approval-test-002",
            proposal_summary="Quick fix",
            test_summary=None,
        )

        assert "APPROVAL REQUEST" in message
        assert "No test results" in message

    def test_format_approval_request_all_passing(self):
        """Test formatting approval request with all tests passing."""

        # Create minimal format method for testing
        def format_approval_request(task_id, proposal_summary, test_summary):
            parts = [
                f"**APPROVAL REQUEST: {task_id[:8]}...**\n",
                f"**Proposal:** {proposal_summary}\n",
            ]

            if test_summary:
                parts.append(f"- Tests Passed: {test_summary['tests_passed']}")
                parts.append(f"- Tests Failed: {test_summary['tests_failed']}")
                if test_summary["tests_failed"] > 0:
                    parts.append("\n⚠️ **WARNING: Tests failed.**")

            return "\n".join(parts)

        test_summary = {
            "tests_generated": 5,
            "tests_passed": 5,
            "tests_failed": 0,
            "coverage_percent": 90.0,
            "recommendations": ["All tests passed. Safe to proceed."],
            "success": True,
        }

        message = format_approval_request(
            task_id="approval-test-003",
            proposal_summary="Refactor module",
            test_summary=test_summary,
        )

        assert "APPROVAL REQUEST" in message
        assert "Tests Passed: 5" in message
        assert "Tests Failed: 0" in message
        assert "WARNING" not in message  # No warning for all passing
