"""
L9 Core Testing - Recursive Self-Testing and Validation
=========================================================

Provides test generation and execution for L's proposals.

Components:
- TestGenerator: AST + LLM test generation (v2.0)
- TestExecutor: Runs tests in sandbox environment
- TestAgent: Agent that orchestrates test generation and execution

Version: 2.0.0 (GMP-19 + LLM Enhancement)

Usage:
    from core.testing import generate_test_file

    code = Path('memory/some_module.py').read_text()
    tests = generate_test_file(code, 'memory.some_module')
    Path('tests/memory/test_some_module.py').write_text(tests)
"""

from core.testing.test_executor import TestExecutor, TestResults, run_tests_in_sandbox
from core.testing.test_generator import (
    MODEL_PRESETS,
    TestGenerator,
    generate_integration_tests,
    generate_test_file,
    generate_unit_tests,
)

__all__ = [
    # Executor
    "TestExecutor",
    "TestResults",
    "run_tests_in_sandbox",
    # Generator (v2.1 - LLM powered with presets)
    "MODEL_PRESETS",
    "TestGenerator",
    "generate_integration_tests",
    "generate_test_file",  # RECOMMENDED entry point
    "generate_unit_tests",
]
