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
    verbose: bool = False, fast: bool = False, keyword: str = None
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
    result = subprocess.run(cmd, cwd=REPO_ROOT)

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
