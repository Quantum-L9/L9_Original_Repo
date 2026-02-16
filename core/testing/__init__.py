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

# ============================================================================
__dora_meta__ = {
    "component_name": "Recursive Self-Testing and Validation",
    "module_version": "2.0.0 (GMP-19 + LLM Enhancement)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "engine",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from core.testing.test_executor import TestExecutor, TestResults, run_tests_in_sandbox
from core.testing.test_generator import (
    MODEL_PRESETS,
    TestGenerator,
    generate_integration_tests,
    generate_test_file,
    generate_unit_tests,
)

__all__ = [
    "MODEL_PRESETS",
    "TestExecutor",
    "TestGenerator",
    "TestResults",
    "generate_integration_tests",
    "generate_test_file",
    "generate_unit_tests",
    "run_tests_in_sandbox",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-157",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.testing.test_executor", "core.testing.test_generator"],
    "tags": ["core", "engine", "foundation", "testing"],
    "keywords": [
        "agent",
        "core",
        "execution",
        "generation",
        "memory",
        "recursive",
        "test",
        "testing",
    ],
    "business_value": "Provides test generation and execution for L's proposals. TestGenerator: AST + LLM test generation (v2.0) TestExecutor: Runs tests in sandbox environment TestAgent: Agent that orchestrates test genera",
    "last_modified": "2026-01-31T22:27:11Z",
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
