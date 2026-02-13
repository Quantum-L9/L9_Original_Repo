"""
L9 Core Testing - Test Executor
================================

Executes tests in isolated sandbox environments.
Captures results, coverage, and output for validation.

Version: 1.0.0 (GMP-19)
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Test Executor",
    "module_version": "1.0.0 (GMP-19)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "test_executor",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "core.testing.__init__",
            "core.testing.test_agent",
            "tests.integration.test_recursive_self_testing",
        ],
    },
}
# ============================================================================

import asyncio
import os
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TestResult:
    """Result of a single test."""

    name: str
    passed: bool
    duration_ms: float
    error: str | None = None
    output: str | None = None


@dataclass
class TestResults:
    """Results of a test run."""

    run_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    coverage_percent: float | None = None
    duration_ms: float = 0.0
    results: list[TestResult] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    success: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "run_id": str(self.run_id),
            "timestamp": self.timestamp.isoformat(),
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "coverage_percent": self.coverage_percent,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


class TestExecutor:
    """
    Executes tests in a sandbox environment.

    Creates isolated test environments using temp directories
    or Docker containers for running generated tests.
    """

    def __init__(
        self,
        use_docker: bool = False,
        timeout_seconds: int = 60,
        coverage_enabled: bool = True,
    ):
        """
        Initialize TestExecutor.

        Args:
            use_docker: Whether to use Docker for isolation
            timeout_seconds: Max time for test execution
            coverage_enabled: Whether to collect coverage
        """
        self._use_docker = use_docker
        self._timeout = timeout_seconds
        self._coverage = coverage_enabled

    @must_stay_async("callers use await")
    async def run_tests(
        self,
        test_code: str,
        source_code: str | None = None,
        env_config: dict[str, str] | None = None,
    ) -> TestResults:
        """
        Run tests in a sandbox environment.

        Args:
            test_code: Python test code to execute
            source_code: Optional source code being tested
            env_config: Optional environment variables

        Returns:
            TestResults with execution results
        """
        start_time = datetime.now(UTC)

        # Create temp directory for test execution
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Write test file
            test_file = tmppath / "test_generated.py"
            test_file.write_text(test_code)

            # Write source file if provided
            if source_code:
                source_file = tmppath / "module_under_test.py"
                source_file.write_text(source_code)

            # Write conftest for pytest
            conftest = tmppath / "conftest.py"
            conftest.write_text("""
import pytest

@pytest.fixture
def mock_substrate():
    \"\"\"Mock substrate service fixture.\"\"\"
    from unittest.mock import AsyncMock
    return AsyncMock()
""")

            # Run pytest
            try:
                results = await self._run_pytest(tmppath, test_file, env_config)
            except Exception as e:
                logger.error(f"Test execution failed: {e}")
                results = TestResults(
                    success=False,
                    stderr=str(e),
                )

        # Calculate duration
        results.duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        return results

    @must_stay_async("callers use await")
    async def _run_pytest(
        self,
        working_dir: Path,
        test_file: Path,
        env_config: dict[str, str] | None,
    ) -> TestResults:
        """Run pytest and parse results."""
        # Build pytest command
        cmd = [
            "python3",
            "-m",
            "pytest",
            str(test_file),
            "-v",
            "--tb=short",
            "-q",
        ]

        if self._coverage:
            cmd.extend(["--cov=.", "--cov-report=term-missing"])

        # Set up environment
        env = os.environ.copy()
        env["PYTHONPATH"] = str(working_dir)
        if env_config:
            env.update(env_config)

        # Run pytest
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=working_dir,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._timeout,
            )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            return self._parse_pytest_output(stdout_str, stderr_str, process.returncode)

        except TimeoutError:
            return TestResults(
                success=False,
                stderr=f"Test execution timed out after {self._timeout}s",
            )

    def _parse_pytest_output(
        self,
        stdout: str,
        stderr: str,
        returncode: int,
    ) -> TestResults:
        """Parse pytest output into TestResults."""
        results = TestResults(
            stdout=stdout,
            stderr=stderr,
            success=(returncode == 0),
        )

        # Parse test counts from output
        # Example: "5 passed, 2 failed, 1 skipped"
        import re

        passed_match = re.search(r"(\d+) passed", stdout)
        failed_match = re.search(r"(\d+) failed", stdout)
        skipped_match = re.search(r"(\d+) skipped", stdout)

        if passed_match:
            results.passed = int(passed_match.group(1))
        if failed_match:
            results.failed = int(failed_match.group(1))
        if skipped_match:
            results.skipped = int(skipped_match.group(1))

        results.total_tests = results.passed + results.failed + results.skipped

        # Parse coverage if present
        cov_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", stdout)
        if cov_match:
            # nosemgrep: l9-float-requires-try-except (regex \d+ only matches digits)
            results.coverage_percent = float(cov_match.group(1))

        # Parse individual test results
        for line in stdout.split("\n"):
            if "PASSED" in line:
                test_name = (
                    line.split("::")[1].split()[0] if "::" in line else "unknown"
                )
                results.results.append(
                    TestResult(
                        name=test_name,
                        passed=True,
                        duration_ms=0,  # Would need timing info
                    )
                )
            elif "FAILED" in line:
                test_name = (
                    line.split("::")[1].split()[0] if "::" in line else "unknown"
                )
                results.results.append(
                    TestResult(
                        name=test_name,
                        passed=False,
                        duration_ms=0,
                        error="Test failed",
                    )
                )

        return results


async def run_tests_in_sandbox(
    test_code: str,
    source_code: str | None = None,
    env_config: dict[str, str] | None = None,
) -> TestResults:
    """
    Convenience function to run tests in sandbox.

    Args:
        test_code: Test code to execute
        source_code: Optional source code
        env_config: Optional environment config

    Returns:
        TestResults
    """
    executor = TestExecutor()
    return await executor.run_tests(test_code, source_code, env_config)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "TestExecutor",
    "TestResult",
    "TestResults",
    "run_tests_in_sandbox",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-079",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "core",
        "dataclass",
        "executor",
        "filesystem",
        "foundation",
        "logging",
        "mocking",
        "test",
    ],
    "keywords": [
        "executor",
        "mock",
        "results",
        "sandbox",
        "substrate",
        "test",
        "tests",
    ],
    "business_value": "Provides test executor components including TestResult, TestResults, TestExecutor",
    "last_modified": "2026-01-14T15:03:00Z",
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
