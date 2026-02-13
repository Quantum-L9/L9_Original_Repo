#!/usr/bin/env python3
"""
DORA Compliance CI Check
========================

Checks all Python and YAML files for missing DORA blocks and auto-injects if missing.

Usage:
    # Check only (CI mode - fails if missing)
    python ci/dora_compliance_check.py --check

    # Auto-fix missing blocks
    python ci/dora_compliance_check.py --fix

    # Check specific directory
    python ci/dora_compliance_check.py --check --path core/agents/

    # Dry run (show what would be fixed)
    python ci/dora_compliance_check.py --fix --dry-run

Exit codes:
    0 - All files compliant
    1 - Missing DORA blocks found (--check mode)
    2 - Error during execution
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Dora Compliance Check",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-18T03:39:59Z",
    "updated_at": "2026-01-31T22:21:50Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "dora_compliance_check",
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

import argparse
import subprocess
import sys
from pathlib import Path
import structlog

# Directories to skip

logger = structlog.get_logger(__name__)

SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    "_archived",
    "migrations",  # SQL migrations don't need DORA
}

# Files to skip
SKIP_FILES = {
    "__init__.py",  # Usually empty or simple imports
    "conftest.py",  # Pytest config
    "setup.py",
    "manage.py",
}

# Patterns to skip
SKIP_PATTERNS = [
    "test_*.py",  # Test files (optional - remove if you want DORA in tests)
]


def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped."""
    # Skip by directory
    for part in file_path.parts:
        if part in SKIP_DIRS:
            return True

    # Skip by filename
    if file_path.name in SKIP_FILES:
        return True

    # Skip by pattern
    return any(file_path.match(pattern) for pattern in SKIP_PATTERNS)


def check_dora_blocks(file_path: Path) -> dict[str, bool]:
    """Check which DORA blocks exist in a file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {"header": False, "footer": False, "trace": False, "error": True}

    is_yaml = file_path.suffix in (".yaml", ".yml")

    if is_yaml:
        return {
            "header": "# component_name:" in content or "dora_meta:" in content,
            "footer": "# tags:" in content or "dora_footer:" in content,
            "trace": True,  # YAML files don't need trace
            "error": False,
        }
    return {
        "header": "__dora_meta__" in content,
        "footer": "__dora_footer__" in content,
        "trace": "__l9_trace__" in content,
        "error": False,
    }


def scan_files(root_path: Path, extensions: list[str]) -> list[Path]:
    """Scan for files with given extensions."""
    files = []
    for ext in extensions:
        for file_path in root_path.rglob(f"*{ext}"):
            if not should_skip_file(file_path):
                files.append(file_path)
    return sorted(files)


def check_compliance(root_path: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """
    Check all files for DORA compliance.

    Returns:
        Tuple of (missing_header, missing_footer, missing_trace) file lists
    """
    files = scan_files(root_path, [".py", ".yaml", ".yml"])

    missing_header = []
    missing_footer = []
    missing_trace = []

    for file_path in files:
        blocks = check_dora_blocks(file_path)

        if blocks.get("error"):
            continue

        if not blocks["header"]:
            missing_header.append(file_path)
        if not blocks["footer"]:
            missing_footer.append(file_path)
        if not blocks["trace"]:
            missing_trace.append(file_path)

    return missing_header, missing_footer, missing_trace


def fix_file(file_path: Path, repo_root: Path, dry_run: bool = False) -> bool:
    """Fix a single file using the injection script."""
    relative_path = file_path.relative_to(repo_root)

    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "audit" / "inject_dora_complete.py"),
        "--repo",
        str(repo_root),
        "--file",
        str(relative_path),
        "--execute",
        "--force",
    ]

    if dry_run:
        logger.info("  would run: {' '.join(cmd)}")
        return True

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=repo_root,
        )

        if result.returncode == 0:
            return True
        logger.error("  error fixing relative path: {result.stderr}", relative_path=relative_path)
        return False

    except Exception as e:
        logger.info("  exception fixing relative path: e", relative_path=relative_path, e=e)
        return False


def main():
    """
    Performs DORA compliance checks on Python and YAML files, auto-injecting missing DORA blocks as needed.

    Args:
        args: Command-line arguments specifying check options and file paths.

    Returns:
        None, exits with status code based on compliance check results.

    Raises:
        RuntimeError: If an unexpected error occurs during the check process.
    """
    parser = argparse.ArgumentParser(
        description="DORA Compliance CI Check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode - report missing blocks and exit with error if found",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix mode - auto-inject missing DORA blocks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without making changes",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Path to check (relative to repo root)",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include test files in check",
    )

    args = parser.parse_args()

    if not args.check and not args.fix:
        parser.error("Must specify --check or --fix")

    # Find repo root
    repo_root = Path(__file__).parent.parent
    check_path = repo_root / args.path

    if not check_path.exists():
        logger.info("❌ path not found: check path", check_path=check_path)
        sys.exit(2)

    # Modify skip patterns if including tests
    if args.include_tests:
        SKIP_PATTERNS.clear()

    logger.info("🔍 scanning check path...", check_path=check_path)
    logger.info("output", value=)

    # Check compliance
    missing_header, missing_footer, missing_trace = check_compliance(check_path)

    # Deduplicate - files missing any block
    all_missing = set(missing_header) | set(missing_footer) | set(missing_trace)

    if not all_missing:
        logger.info("✅ all files have complete dora blocks!")
        sys.exit(0)

    # Report findings
    logger.info("📊 dora compliance report")
    logger.info("{'=' * 60}")
    logger.info("  files scanned: {len(scan_files(check_path, ['.py', '.yaml', '.yml']))}")
    logger.info("  missing header: {len(missing_header)}")
    logger.info("  missing footer: {len(missing_footer)}")
    logger.info("  missing trace:  {len(missing_trace)}")
    logger.info("  total non-compliant: {len(all_missing)}")
    logger.info("output", value=)

    if args.check:
        # Check mode - report and exit with error
        logger.info("❌ non-compliant files:")
        for file_path in sorted(all_missing):
            relative = file_path.relative_to(repo_root)
            blocks = check_dora_blocks(file_path)
            missing = []
            if not blocks["header"]:
                missing.append("header")
            if not blocks["footer"]:
                missing.append("footer")
            if not blocks["trace"]:
                missing.append("trace")
            logger.info("  relative (missing: {', '.join(missing)})", relative=relative)

        logger.info("output", value=)
        logger.info("💡 run with --fix to auto-inject dora blocks")
        sys.exit(1)

    if args.fix:
        # Fix mode - inject missing blocks
        print(
            f"🔧 {'DRY RUN - ' if args.dry_run else ''}Fixing {len(all_missing)} files..."
        )
        logger.info("output", value=)

        fixed = 0
        failed = 0

        for file_path in sorted(all_missing):
            relative = file_path.relative_to(repo_root)
            logger.info("  fixing relative...", relative=relative)

            if fix_file(file_path, repo_root, dry_run=args.dry_run):
                fixed += 1
            else:
                failed += 1

        logger.info("output", value=)
        logger.info("📊 fix summary")
        logger.info("{'=' * 60}")
        logger.info("  fixed: fixed", fixed=fixed)
        logger.error("  failed: failed", failed=failed)

        if failed > 0:
            sys.exit(2)

        if args.dry_run:
            logger.info("output", value=)
            logger.info("💡 run without --dry-run to apply fixes")
        else:
            logger.info("output", value=)
            logger.info("✅ all files fixed!")


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-OPER-012",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "caching",
        "ci",
        "cli",
        "filesystem",
        "migration",
        "operations",
        "subprocess",
        "testing",
        "tracing",
    ],
    "keywords": [
        "blocks",
        "check",
        "compliance",
        "dora",
        "files",
        "fix",
        "scan",
        "should",
    ],
    "business_value": "Utility module for dora compliance check",
    "last_modified": "2026-01-31T22:21:50Z",
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
