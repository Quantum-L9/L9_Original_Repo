#!/usr/bin/env python3
"""
L9 Dead Code Audit - Consolidated Runner
=========================================

Runs all 4 phases of dead code audit in sequence:
1. find_dead_code.py        → Baseline static analysis (vulture + ruff)
2. resolve_dead_code_refs.py → Attempt resolution of references
3. categorize_dead_code.py   → Risk categorization (HIGH/MEDIUM/LOW)
4. generate_gmp_todos.py     → AUTO-FIX + Generate completed GMP Report

Phase 4 automatically:
- Fixes safe dead code (unused imports, variables) via ruff --fix
- Skips false positives (test fixtures, exports, config fields)
- Generates completed GMP Report documenting all fixes

Usage:
  python scripts/audit/run_dead_code_audit.py           # Full audit + auto-fix
  python scripts/audit/run_dead_code_audit.py --quick   # Skip auto-fix (phases 1-3 only)
  python scripts/audit/run_dead_code_audit.py --phase 1 # Run specific phase only
  python scripts/audit/run_dead_code_audit.py --dry-run # Show what would be fixed

Version: 2.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Consolidated Runner",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "run_dead_code_audit",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import subprocess
import sys
import time
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent
AUDIT_DIR = REPO_ROOT / "scripts" / "audit"
REPORTS_DIR = REPO_ROOT / "reports"

# Phase scripts and their outputs
PHASES = [
    {
        "name": "Phase 1: Find Dead Code",
        "script": "find_dead_code.py",
        "output": "dead_code_baseline.json",
        "description": "Static analysis with vulture, ruff, AST",
    },
    {
        "name": "Phase 2: Resolve References",
        "script": "resolve_dead_code_refs.py",
        "output": "dead_code_resolved.json",
        "description": "Attempt to resolve unused references",
    },
    {
        "name": "Phase 3: Categorize Risk",
        "script": "categorize_dead_code.py",
        "output": "dead_code_risk_matrix.json",
        "description": "Risk categorization (HIGH/MEDIUM/LOW)",
    },
    {
        "name": "Phase 4: Auto-Fix + GMP Report",
        "script": "generate_gmp_todos.py",
        "output": "GMP_Report_DeadCode_*.md",
        "description": "AUTO-FIX safe items + generate completed GMP Report",
    },
]


def run_phase(phase_num: int, verbose: bool = False) -> tuple[bool, str]:
    """Run a single phase and return (success, output)."""
    phase = PHASES[phase_num - 1]
    script_path = AUDIT_DIR / phase["script"]

    if not script_path.exists():
        return False, f"Script not found: {script_path}"

    cmd = [sys.executable, str(script_path)]
    if verbose:
        cmd.append("--verbose")

    try:
        result = subprocess.run(  # noqa: S603 — trusted cmd, no shell
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per phase
        )

        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"

        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Timeout after 300s"
    except Exception as e:
        return False, f"Error: {e}"


def main():
    """
    Performs the main execution of the dead code audit process, orchestrating all phases in sequence.
    Raises:
        Exception: If an error occurs during argument parsing or execution.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="L9 Dead Code Audit - Consolidated Runner"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip GMP generation (phases 1-3 only)",
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4],
        help="Run specific phase only",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Minimal output (for startup)",
    )

    args = parser.parse_args()

    # Ensure reports directory exists
    REPORTS_DIR.mkdir(exist_ok=True)

    # Determine which phases to run
    if args.phase:
        phases_to_run = [args.phase]
    elif args.quick:
        phases_to_run = [1, 2, 3]
    else:
        phases_to_run = [1, 2, 3, 4]

    if not args.quiet:
        logger.info("=" * 60)
        logger.info("l9 dead code audit - consolidated runner")
        logger.info("=" * 60)

    start_time = time.time()
    results = []

    for phase_num in phases_to_run:
        phase = PHASES[phase_num - 1]

        if not args.quiet:
            logger.info("\n{'─' * 60}")
            logger.info("▶ {phase['name']}")
            logger.info("  {phase['description']}")
            logger.info("{'─' * 60}")

        success, output = run_phase(phase_num, verbose=args.verbose)
        results.append((phase_num, success, output))

        if args.verbose or not args.quiet:
            # Show last 10 lines of output
            lines = output.strip().split("\n")
            for line in lines[-10:]:
                logger.info("  line", line=line)

        if success:
            if not args.quiet:
                logger.info("  ✅ {phase['name']} complete → {phase['output']}")
        else:
            logger.error("  ❌ {phase['name']} failed")
            if not args.quick:
                # Stop on failure for full run
                break

    elapsed = time.time() - start_time

    # Summary
    if not args.quiet:
        logger.info("\n" + "=" * 60)
        logger.info("summary")
        logger.info("=" * 60)

        passed = sum(1 for _, success, _ in results if success)
        total = len(results)

        for phase_num, success, _ in results:
            phase = PHASES[phase_num - 1]
            status = "✅" if success else "❌"
            logger.info("  status {phase['name']}", status=status)

        logger.info("\nresult: passed/total phases passed", passed=passed, total=total)
        logger.info("time: {elapsed:.1f}s")

        if passed == total:
            logger.info("\n🎉 dead code audit complete!")
            if 4 in phases_to_run:
                logger.info("   gmp todo plan: reports/dead_code_gmp_todos.yaml")
        logger.info("=" * 60)
    else:
        # Quiet mode - just summary line
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        if passed == total:
            logger.info(
                "✅ dead code audit: passed/total phases ({elapsed:.1f}s)",
                passed=passed,
                total=total,
            )
        else:
            logger.info(
                "⚠️  dead code audit: passed/total phases ({elapsed:.1f}s)",
                passed=passed,
                total=total,
            )

    # Exit code: 0 if all passed, 1 if any failed
    return 0 if all(success for _, success, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "cli",
        "filesystem",
        "operations",
        "scripts",
        "static-analysis",
        "subprocess",
        "testing",
    ],
    "keywords": ["consolidated", "phase", "runner"],
    "business_value": "Utility module for run dead code audit",
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
