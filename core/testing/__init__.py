"""
L9 Core Testing - Recursive Self-Testing and Validation
=========================================================

Provides test generation and execution for L's proposals.

Components:
- TestGenerator: Generates unit/integration tests from code proposals
- TestExecutor: Runs tests in sandbox environment
- TestAgent: Agent that orchestrates test generation and execution

Version: 1.0.0 (GMP-19)
"""

from core.testing.test_executor import (TestExecutor, TestResults,
                                        run_tests_in_sandbox)
from core.testing.test_generator import (TestGenerator,
                                         generate_integration_tests,
                                         generate_unit_tests)

__all__ = [
    # Generator
    "TestGenerator",
    "generate_unit_tests",
    "generate_integration_tests",
    # Executor
    "TestExecutor",
    "TestResults",
    "run_tests_in_sandbox",
]
