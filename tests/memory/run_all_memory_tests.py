#!/usr/bin/env python3
"""
L9 Memory Test Suite Runner

Runs all memory tests with summary reporting.

Usage:
  python tests/memory/run_all_memory_tests.py           # Run all tests
  python tests/memory/run_all_memory_tests.py -v        # Verbose output
  python tests/memory/run_all_memory_tests.py --fast    # Skip slow tests
  python tests/memory/run_all_memory_tests.py -k governance  # Filter by keyword
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Run All Memory Tests",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-15T15:23:54Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "run_all_memory_tests",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import subprocess
import sys
import time
from pathlib import Path

TESTS_DIR = Path(__file__).parent
REPO_ROOT = TESTS_DIR.parent.parent

# All test files in tests/memory/
TEST_FILES = [
    "test_agent_persistence.py",
    "test_blob_offload.py",
    "test_consolidation_graph.py",
    "test_consolidation.py",
    "test_cross_client_consistency.py",
    "test_cypher_templates.py",
    "test_e2e_memory_audit.py",
    "test_embedding_filter.py",
    "test_extraction_pipeline.py",
    "test_governance_invariants.py",
    "test_graph_memory.py",
    "test_hybrid_rag.py",
    "test_ingestion_audit.py",
    "test_ingestion_pipeline_audit.py",
    "test_ingestion_transaction.py",
    "test_mcp_bypass_compliance.py",
    "test_memory_adapter_basic.py",
    "test_memory_ingestion.py",
    "test_packet_envelope_immutability.py",
    "test_packet_envelope.py",
    "test_packet_validation_v2.py",
    "test_pruning.py",
    "test_query_classifier.py",
    "test_reasoning_replay.py",
    "test_retrieval_audit.py",
    "test_rls_isolation.py",
    "test_saga.py",
    "test_substrate_alignment.py",
    "test_substrate_api.py",
    "test_substrate_dag_native.py",
    "test_substrate_semantic.py",
    "test_tool_audit.py",
    "test_tool_router.py",
    "test_unified_pipeline.py",
    "test_vector_index.py",
    "test_vector_search.py",
]


def run_all_tests(
    verbose: bool = False, fast: bool = False, keyword: str | None = None
) -> int:
    """
    Run all memory tests using pytest.

    Args:
        verbose: Enable verbose output
        fast: Skip slow/integration tests
        keyword: Filter tests by keyword (-k)

    Returns:
        Exit code (0 = success)
    """
    print("=" * 70)
    print("L9 MEMORY TEST SUITE")
    print("=" * 70)
    print(f"Test directory: {TESTS_DIR}")
    print(f"Test files: {len(TEST_FILES)}")
    print()

    start_time = time.time()

    # Build pytest command
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(TESTS_DIR),
        "--tb=short",
        "-q" if not verbose else "-v",
    ]

    if fast:
        cmd.extend(["-m", "not slow and not integration"])

    if keyword:
        cmd.extend(["-k", keyword])

    # Add color output
    cmd.append("--color=yes")

    print(f"Running: {' '.join(cmd)}")
    print("-" * 70)

    # Run tests
    result = subprocess.run(cmd, cwd=REPO_ROOT)  # noqa: S603 — trusted cmd, no shell

    duration = time.time() - start_time

    print()
    print("=" * 70)
    print(f"COMPLETED in {duration:.1f}s")
    print(f"Exit code: {result.returncode}")
    print("=" * 70)

    return result.returncode


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run all L9 memory tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("-k", "--keyword", type=str, help="Filter by keyword")

    args = parser.parse_args()

    exit_code = run_all_tests(
        verbose=args.verbose,
        fast=args.fast,
        keyword=args.keyword,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TES-OPER-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "cli",
        "filesystem",
        "memory-substrate",
        "operations",
        "subprocess",
        "testing",
    ],
    "keywords": ["all", "memory", "tests"],
    "business_value": "Utility module for run all memory tests",
    "last_modified": "2026-01-17T23:47:56Z",
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
