#!/usr/bin/env python3
"""
Try-Run Validator for L9
========================

Attempts to actually run a Python file and reports pass/fail with traceback.
Goes beyond syntax checking — catches missing imports, broken kwargs,
runtime NameErrors, and any other exception that fires on load/execution.

Usage:
    python tools/validation/try_run.py scripts/benchmark_caching_and_vector.py
    python tools/validation/try_run.py scripts/my_script.py --timeout 30
    python tools/validation/try_run.py scripts/my_script.py --syntax-only
    python tools/validation/try_run.py scripts/my_script.py --import-only

Levels (from lightest to heaviest):
    --syntax-only   : ast.parse() only (same as ci/check_syntax.py)
    --import-only   : attempt to import the module (catches missing deps)
    (default)       : run the file in a subprocess (catches everything)

Exit codes:
    0 = PASS
    1 = FAIL (with traceback)
    2 = TIMEOUT

See: readme/bug_patterns/PATTERN_002_external_code_generation.md
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
import time
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

__dora_meta__ = {
    "component_name": "Try-Run Validator",
    "module_version": "1.0.0",
    "status": "active",
}


def check_syntax(file_path: Path) -> tuple[bool, str]:
    """Check if file has valid Python syntax.

    Returns:
        (passed, message) tuple.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(file_path))
        return True, "Syntax OK"
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}"


def check_import(file_path: Path, repo_root: Path) -> tuple[bool, str]:
    """Try to import the file as a module in a subprocess.

    Returns:
        (passed, message) tuple.
    """
    # Convert file path to module path: scripts/foo.py -> scripts.foo
    try:
        relative = file_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return False, f"File {file_path} is not under repo root {repo_root}"

    module_path = str(relative.with_suffix("")).replace("/", ".")

    result = subprocess.run(  # noqa: S603 — trusted cmd, no shell
        [sys.executable, "-c", f"import {module_path}"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        timeout=30,
        env=_build_env(repo_root),
    )

    if result.returncode == 0:
        return True, f"Import OK: {module_path}"

    # Extract the last line of traceback for a concise message
    stderr = result.stderr.strip()
    last_line = stderr.splitlines()[-1] if stderr else "Unknown error"
    return False, f"Import FAILED: {last_line}\n\n{stderr}"


def check_run(
    file_path: Path, repo_root: Path, timeout: int = 60
) -> tuple[bool, str, float, bool]:
    """Run the file in a subprocess and report pass/fail.

    Returns:
        (passed, message, elapsed_seconds, timed_out) tuple.
    """
    start = time.monotonic()

    try:
        result = subprocess.run(  # noqa: S603 — trusted cmd, no shell
            [sys.executable, str(file_path)],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            timeout=timeout,
            env=_build_env(repo_root),
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return False, f"TIMEOUT after {timeout}s", elapsed, True

    elapsed = time.monotonic() - start

    if result.returncode == 0:
        stdout_preview = _truncate(result.stdout, 500)
        return True, f"Run OK ({elapsed:.1f}s)\n{stdout_preview}", elapsed, False

    stderr = result.stderr.strip()
    stdout = result.stdout.strip()

    # Build a useful error message
    parts = []
    if stderr:
        parts.append(f"STDERR:\n{_truncate(stderr, 1500)}")
    if stdout:
        parts.append(f"STDOUT:\n{_truncate(stdout, 500)}")

    msg = f"Exit code {result.returncode} ({elapsed:.1f}s)\n" + "\n\n".join(parts)
    return False, msg, elapsed, False


def _build_env(repo_root: Path) -> dict[str, str]:
    """Build environment with PYTHONPATH set to repo root."""
    import os

    env = os.environ.copy()
    # Ensure repo root is on PYTHONPATH so local imports resolve
    existing = env.get("PYTHONPATH", "")
    repo_str = str(repo_root.resolve())
    if repo_str not in existing:
        env["PYTHONPATH"] = f"{repo_str}:{existing}" if existing else repo_str
    return env


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text with ellipsis indicator."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... ({len(text) - max_chars} chars truncated)"


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Try-run a Python file and report pass/fail with traceback"
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Python file to validate",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="L9 repository root (default: current directory)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds for run mode (default: 60)",
    )
    parser.add_argument(
        "--syntax-only",
        action="store_true",
        help="Only check syntax (ast.parse), don't run",
    )
    parser.add_argument(
        "--import-only",
        action="store_true",
        help="Only try importing the module, don't run __main__",
    )
    args = parser.parse_args()

    file_path = args.file
    repo_root = args.repo_root.resolve()

    if not file_path.exists():
        logger.error("file_not_found", path=str(file_path))
        sys.stderr.write(f"File not found: {file_path}\n")
        return 1

    if not file_path.suffix == ".py":
        sys.stderr.write(f"Not a Python file: {file_path}\n")
        return 1

    # ── Level 1: Syntax ──────────────────────────────────────────────
    sys.stdout.write(f"{'=' * 60}\n")
    sys.stdout.write(f"TRY-RUN: {file_path}\n")
    sys.stdout.write(f"{'=' * 60}\n\n")

    sys.stdout.write("1. Syntax check... ")
    passed, msg = check_syntax(file_path)
    sys.stdout.write(f"{'PASS' if passed else 'FAIL'}\n")
    if not passed:
        sys.stdout.write(f"   {msg}\n")
        sys.stdout.write(f"\n{'=' * 60}\n")
        sys.stdout.write("RESULT: FAIL (syntax error)\n")
        sys.stdout.write(f"{'=' * 60}\n")
        return 1

    if args.syntax_only:
        sys.stdout.write(f"\n{'=' * 60}\n")
        sys.stdout.write("RESULT: PASS (syntax only)\n")
        sys.stdout.write(f"{'=' * 60}\n")
        return 0

    # ── Level 2: Import ──────────────────────────────────────────────
    sys.stdout.write("2. Import check... ")
    passed, msg = check_import(file_path, repo_root)
    status = "PASS" if passed else "FAIL"
    sys.stdout.write(f"{status}\n")
    if not passed:
        sys.stdout.write(f"   {msg}\n")
        sys.stdout.write(f"\n{'=' * 60}\n")
        sys.stdout.write("RESULT: FAIL (import error)\n")
        sys.stdout.write(f"{'=' * 60}\n")
        return 1

    if args.import_only:
        sys.stdout.write(f"\n{'=' * 60}\n")
        sys.stdout.write("RESULT: PASS (import only)\n")
        sys.stdout.write(f"{'=' * 60}\n")
        return 0

    # ── Level 3: Run ─────────────────────────────────────────────────
    sys.stdout.write(f"3. Full run (timeout={args.timeout}s)... ")
    passed, msg, elapsed, timed_out = check_run(
        file_path, repo_root, timeout=args.timeout
    )

    if passed:
        sys.stdout.write(f"PASS ({elapsed:.1f}s)\n")
        sys.stdout.write(f"\n{'=' * 60}\n")
        sys.stdout.write("RESULT: PASS\n")
        sys.stdout.write(f"{'=' * 60}\n")
        return 0

    sys.stdout.write(f"FAIL ({elapsed:.1f}s)\n")
    sys.stdout.write(f"\n{msg}\n")
    sys.stdout.write(f"\n{'=' * 60}\n")

    if timed_out:
        sys.stdout.write("RESULT: TIMEOUT\n")
        sys.stdout.write(f"{'=' * 60}\n")
        return 2

    sys.stdout.write("RESULT: FAIL (runtime error)\n")
    sys.stdout.write(f"{'=' * 60}\n")
    return 1


__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}


if __name__ == "__main__":
    sys.exit(main())
