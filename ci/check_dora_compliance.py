#!/usr/bin/env python3
"""
DORA Compliance CI Check
========================

Checks all Python and YAML files for missing DORA blocks and auto-injects if missing.

Usage:
    # Check only (CI mode - fails if missing)
    python ci/check_dora_compliance.py --check

    # Auto-fix missing blocks
    python ci/check_dora_compliance.py --fix

    # Check specific directory
    python ci/check_dora_compliance.py --check --path core/agents/

    # Dry run (show what would be fixed)
    python ci/check_dora_compliance.py --fix --dry-run

Exit codes:
    0 - All files compliant
    1 - Missing DORA blocks found (--check mode)
    2 - Error during execution
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Check DORA Compliance",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-18T03:39:59Z",
    "updated_at": "2026-01-31T22:21:50Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "check_dora_compliance",
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
import re
import subprocess
import sys
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# =============================================================================
# Field-level validation (GMP-143: merged from ci/validate_dora_blocks.py)
# =============================================================================

# Regex patterns for mandatory __dora_meta__ fields
DORA_FIELD_PATTERNS: dict[str, str] = {
    "component_name": r"^[A-Za-z0-9\s\-_]{2,100}$",
    "module_version": r"^\d+\.\d+\.\d+$",
    "status": r"^(active|deprecated|experimental|maintenance)$",
    "layer": r"^(foundation|intelligence|operations|learning|security|core)$",
    "domain": r"^[a-z0-9_\.\-]{2,100}$",
}

# Domains that must have governance_level critical or high
CRITICAL_DOMAINS = {"governance", "memory", "agents", "kernel", "kernel_loader"}


def validate_dora_fields(meta: dict) -> list[str]:
    """Validate __dora_meta__ field values against patterns.

    Returns list of error messages (empty = all good).
    """
    errors: list[str] = []
    for field_name, pattern in DORA_FIELD_PATTERNS.items():
        value = meta.get(field_name)
        if value is None:
            errors.append(f"missing field: {field_name}")
            continue
        if not re.match(pattern, str(value)):
            errors.append(
                f"field '{field_name}' value '{value}' doesn't match {pattern}"
            )

    # Governance level check for critical domains
    domain = meta.get("domain", "")
    gov = meta.get("governance_level", "")
    if domain in CRITICAL_DOMAINS and gov not in ("critical", "high"):
        errors.append(f"domain '{domain}' is critical but governance_level is '{gov}'")

    return errors


# =============================================================================
# Directory / file skip lists
# =============================================================================

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
    "codegen",
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


def extract_dora_meta(file_path: Path) -> dict | None:
    """Extract __dora_meta__ dict from a Python file for field validation.

    GMP-143: Merged from ci/validate_dora_blocks.py.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    if file_path.suffix != ".py":
        return None

    match = re.search(r"__dora_meta__\s*=\s*(\{.*?\})", content, re.DOTALL)
    if match:
        try:
            return eval(match.group(1))  # noqa: S307 — parsing trusted __dora_meta__ from repo files
        except Exception:
            return None
    return None


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
        logger.info("would_run", cmd=" ".join(cmd))
        return True

    try:
        result = subprocess.run(  # noqa: S603 — trusted cmd, no shell
            cmd,
            capture_output=True,
            text=True,
            cwd=repo_root,
        )

        if result.returncode == 0:
            return True
        logger.error("fix_error", file=str(relative_path), stderr=result.stderr)
        return False

    except Exception as e:
        logger.error("fix_exception", file=str(relative_path), error=str(e))
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
    parser.add_argument(
        "--validate-fields",
        action="store_true",
        help="GMP-143: Also validate __dora_meta__ field values against patterns",
    )

    args = parser.parse_args()

    if not args.check and not args.fix:
        parser.error("Must specify --check or --fix")

    # Find repo root
    repo_root = Path(__file__).parent.parent  # noqa: ADR-0001 - internal path
    check_path = repo_root / args.path

    if not check_path.exists():
        logger.info("❌ path not found: check path", check_path=check_path)
        sys.exit(2)

    # Modify skip patterns if including tests
    if args.include_tests:
        SKIP_PATTERNS.clear()

    logger.info("🔍 scanning check path...", check_path=check_path)
    logger.info("")

    # Check compliance
    missing_header, missing_footer, missing_trace = check_compliance(check_path)

    # Deduplicate - files missing any block
    all_missing = set(missing_header) | set(missing_footer) | set(missing_trace)

    if not all_missing:
        logger.info("✅ all files have complete dora blocks!")
        sys.exit(0)

    # Report findings
    logger.info("📊 dora compliance report")
    logger.info("=" * 60)
    logger.info(
        "dora_compliance_report",
        files_scanned=len(scan_files(check_path, [".py", ".yaml", ".yml"])),
        missing_header=len(missing_header),
        missing_footer=len(missing_footer),
        missing_trace=len(missing_trace),
        total_non_compliant=len(all_missing),
    )
    logger.info("")

    # GMP-143: Field-level validation (merged from validate_dora_blocks.py)
    field_errors: list[tuple[Path, list[str]]] = []
    if args.validate_fields:
        all_files = scan_files(check_path, [".py"])
        for file_path in all_files:
            meta = extract_dora_meta(file_path)
            if meta:
                errs = validate_dora_fields(meta)
                if errs:
                    field_errors.append((file_path, errs))

        if field_errors:
            logger.info("🔍 field validation errors", count=len(field_errors))
            for fp, errs in field_errors:
                rel = fp.relative_to(repo_root)
                for e in errs:
                    logger.warning("field_error", file=str(rel), error=e)

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
            logger.info("non_compliant", file=str(relative), missing=", ".join(missing))

        logger.info("")
        logger.info("💡 run with --fix to auto-inject dora blocks")
        exit_code = 1
        if args.validate_fields and field_errors:
            exit_code = 1  # field errors also fail
        sys.exit(exit_code)

    if args.fix:
        # Fix mode - inject missing blocks
        print(  # noqa: ADR-0019
            f"🔧 {'DRY RUN - ' if args.dry_run else ''}Fixing {len(all_missing)} files..."
        )
        logger.info("")

        fixed = 0
        failed = 0

        for file_path in sorted(all_missing):
            relative = file_path.relative_to(repo_root)
            logger.info("  fixing relative...", relative=relative)

            if fix_file(file_path, repo_root, dry_run=args.dry_run):
                fixed += 1
            else:
                failed += 1

        logger.info("")
        logger.info("📊 fix summary")
        logger.info("=" * 60)
        logger.info("  fixed: fixed", fixed=fixed)
        logger.error("  failed: failed", failed=failed)

        if failed > 0:
            sys.exit(2)

        if args.dry_run:
            logger.info("")
            logger.info("💡 run without --dry-run to apply fixes")
        else:
            logger.info("")
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
