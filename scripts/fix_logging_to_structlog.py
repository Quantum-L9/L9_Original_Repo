#!/usr/bin/env python3
"""
Fix logging module usage to structlog per ADR-0019.

Dynamically scans all Python files in the repo and replaces:
- import logging -> import structlog
- logging.getLogger(__name__) -> structlog.get_logger(__name__)
- logging.getLogger("name") -> structlog.get_logger("name")
- logging.getLogger(f"...") -> structlog.get_logger(f"...")
- Removes stale '# noqa: ADR-0019' comments on the replaced lines

Usage:
    python3 scripts/fix_logging_to_structlog.py              # Dry-run (default)
    python3 scripts/fix_logging_to_structlog.py --fix        # Apply fixes
    python3 scripts/fix_logging_to_structlog.py --verbose    # Show skipped files
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Fix Logging To Structlog",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-02-16T14:30:00Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "fix_logging_to_structlog",
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
import sys
from pathlib import Path

L9_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Directories and files to SKIP (legitimate logging usage or non-production)
# Aligned with ci/check_forbidden_imports.py SKIP_PATTERNS
# ---------------------------------------------------------------------------
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    ".pytest_cache",
    "build",
    "dist",
    ".cursor",
    ".dora",
    "current_work",
    "igor",
    "data",
    "_archived",
    ".backup",
    # Documentation — contains example code snippets, not production
    "docs",
    "readme",
    "seed",
    # Codegen templates — separate fix needed for template generation
    "codegen",
    # Test files — may intentionally use logging as anti-pattern examples
    "tests",
    # CI scripts — CLI tools, print/logging acceptable
    "ci",
    # Scripts — CLI tools
    "scripts",
    # Tools — CLI tools
    "tools",
    # Workflows — CLI tools
    "workflows",
    # Bootstrap — CLI entry point
    "bootstrap",
    # MCP memory ingestion inbox — chat history archives
    "inbox",
}

SKIP_FILES = {
    # Logging wrapper module — MUST use stdlib logging by design
    "services/symbolic_computation/logger.py",
    # structlog stdlib interop — logging.basicConfig is required
    "mac_agent/runner.py",
    "mac_agent/websocket_client.py",  # logging.basicConfig in __main__ + noise suppression
    "mcp_memory/src/main.py",
    "mcp_memory/src/observability/logging.py",  # IS the logging config module
    "world_model/seed_loader.py",
    "core/reasoning/toth_engine.py",  # logging.basicConfig + structlog interop
    # Type hint only usage (logging.Logger as parameter type)
    "memory/extractor/base_extractor.py",
}


def should_skip(filepath: Path) -> str | None:
    """Return skip reason if file should be skipped, None otherwise."""
    rel = filepath.relative_to(L9_ROOT)
    rel_str = str(rel)

    # Check explicit file skip list
    if rel_str in SKIP_FILES:
        return f"whitelisted: {rel_str}"

    # Check directory skip list
    for part in rel.parts:
        if part in SKIP_DIRS:
            return f"in skip dir: {part}/"

    # Skip non-Python files
    if filepath.suffix != ".py":
        return "not a .py file"

    return None


def scan_file(filepath: Path) -> list[tuple[int, str]]:
    """Scan a file for logging violations. Returns list of (line_num, line_text)."""
    violations = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return violations

    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.lstrip()
        # Skip comments
        if stripped.startswith("#"):
            continue
        # Skip string literals (rough heuristic: inside triple quotes or docstrings)
        if stripped.startswith(('"""', "'''")):
            continue

        # Detect: import logging (standalone, not 'import structlog')
        if re.match(r"^import logging\b", stripped) or re.match(r"^from logging\b", stripped) or ("logging.getLogger" in line and not stripped.startswith("#")):
            violations.append((i, line))

    return violations


def fix_file(filepath: Path) -> tuple[bool, int]:
    """Fix logging -> structlog in a file. Returns (was_modified, fix_count)."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False, 0

    original = content
    fix_count = 0

    # Track if file already has 'import structlog'
    has_structlog_import = bool(
        re.search(r"^import structlog\b", content, re.MULTILINE)
    )

    # Pattern 1: Replace 'import logging' with 'import structlog'
    # Also strip any trailing noqa comment
    new_content, n = re.subn(
        r"^import logging\b.*$",
        "import structlog" if not has_structlog_import else "",
        content,
        flags=re.MULTILINE,
    )
    if n > 0:
        content = new_content
        fix_count += n
        has_structlog_import = True

    # Pattern 2: Replace logging.getLogger(__name__) -> structlog.get_logger(__name__)
    new_content, n = re.subn(
        r"logging\.getLogger\(__name__\)",
        "structlog.get_logger(__name__)",
        content,
    )
    if n > 0:
        content = new_content
        fix_count += n

    # Pattern 3: Replace logging.getLogger("name") -> structlog.get_logger("name")
    new_content, n = re.subn(
        r'logging\.getLogger\("([^"]+)"\)',
        r'structlog.get_logger("\1")',
        content,
    )
    if n > 0:
        content = new_content
        fix_count += n

    # Pattern 4: Replace logging.getLogger(f"...") -> structlog.get_logger(f"...")
    new_content, n = re.subn(
        r"logging\.getLogger\(f\"([^\"]+)\"\)",
        r'structlog.get_logger(f"\1")',
        content,
    )
    if n > 0:
        content = new_content
        fix_count += n

    # Clean up: remove stale '# noqa: ADR-0019' on lines we just fixed
    new_content, n = re.subn(
        r"\s*# noqa: ADR-0019\b[^\n]*",
        "",
        content,
    )
    if n > 0:
        content = new_content

    # Clean up: remove blank lines left by removing 'import logging' when structlog existed
    content = re.sub(r"\n{3,}", "\n\n", content)

    # Ensure 'import structlog' exists if we replaced logging usage
    if fix_count > 0 and not re.search(r"^import structlog\b", content, re.MULTILINE):
        # Insert after the last import line
        lines = content.split("\n")
        last_import_idx = 0
        for idx, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                last_import_idx = idx
        lines.insert(last_import_idx + 1, "import structlog")
        content = "\n".join(lines)

    if content == original:
        return False, 0

    filepath.write_text(content, encoding="utf-8")
    return True, fix_count


def collect_python_files() -> list[Path]:
    """Collect all Python files in the repo, respecting skip rules."""
    files = []
    for filepath in sorted(L9_ROOT.rglob("*.py")):
        if should_skip(filepath) is None:
            files.append(filepath)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fix logging -> structlog per ADR-0019 (scanner mode)"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Apply fixes (default is dry-run)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show skipped files"
    )
    args = parser.parse_args()

    mode = "FIX" if args.fix else "DRY-RUN"
    print(f"[{mode}] Scanning for logging -> structlog violations (ADR-0019)\n")

    files = collect_python_files()
    print(f"Scanning {len(files)} production Python files...\n")

    violations_by_file: dict[str, list[tuple[int, str]]] = {}
    total_violations = 0
    fixed_files = 0
    fixed_count = 0

    for filepath in files:
        violations = scan_file(filepath)
        if violations:
            rel = str(filepath.relative_to(L9_ROOT))
            violations_by_file[rel] = violations
            total_violations += len(violations)

            if args.fix:
                was_modified, n = fix_file(filepath)
                if was_modified:
                    fixed_files += 1
                    fixed_count += n
                    print(f"  ✅ {rel} ({n} fixes)")
            else:
                print(f"  ❌ {rel}")
                for line_num, line_text in violations:
                    print(f"     L{line_num}: {line_text.strip()}")

    print(f"\n{'=' * 60}")
    if total_violations == 0:
        print("✅ No logging violations found — all production code uses structlog")
        return 0

    if args.fix:
        print(f"✅ Fixed {fixed_count} violations in {fixed_files} files")
        remaining = total_violations - fixed_count
        if remaining > 0:
            print(f"⚠️  {remaining} violations could not be auto-fixed (manual review needed)")
        return 0
    print(f"❌ Found {total_violations} violations in {len(violations_by_file)} files")
    print("\nRun with --fix to apply: python3 scripts/fix_logging_to_structlog.py --fix")
    return 1


if __name__ == "__main__":
    sys.exit(main())
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-021",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["cli", "linting", "logging", "operations", "scripts"],
    "keywords": ["fix", "logging", "structlog", "scanner", "adr-0019"],
    "business_value": "Auto-fixes logging -> structlog violations across the codebase",
    "last_modified": "2026-02-16T14:30:00Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "v2.0: Rewritten from hardcoded list to dynamic scanner",
}
# ============================================================================
