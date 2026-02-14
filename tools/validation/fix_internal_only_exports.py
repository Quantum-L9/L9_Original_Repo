#!/usr/bin/env python3
"""
Fix Internal-Only Exports — L9
================================

Removes symbols from __all__ that are only used WITHIN the package (internal-only).
These symbols are alive but should not be part of the public API surface.

This script:
1. Runs the triage classifier to find INTERNAL_ONLY symbols per package
2. Edits each package's __init__.py to remove those symbols from __all__
3. Reports what was changed

Usage:
    python tools/validation/fix_internal_only_exports.py --dry-run     # Preview changes
    python tools/validation/fix_internal_only_exports.py               # Apply changes
    python tools/validation/fix_internal_only_exports.py memory runtime # Specific packages

Safety: Does NOT delete any code. Only removes names from __all__ lists.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers (from triage_dead_code.py — kept standalone)
# ---------------------------------------------------------------------------

SKIP_DIRS = {
    "__pycache__",
    ".venv",
    "node_modules",
    ".git",
    ".backup",
    ".cursor",
    ".cursor-commands",
    ".github",
}
NO_API_PACKAGES = {"scripts", "ci", "tests", "tools", "migrations"}


def find_repo_root() -> Path:
    cur = Path(__file__).resolve().parent
    for _ in range(6):
        if (cur / "memory" / "__init__.py").exists():
            return cur
        cur = cur.parent
    return Path.cwd()


def rg_count_in(pattern: str, search_dir: Path) -> int:
    cmd = ["rg", "-l", "--type", "py", pattern, str(search_dir)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return len(r.stdout.strip().splitlines()) if r.returncode == 0 else 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0


def rg_count_outside(pattern: str, repo_root: Path, exclude_pkg: str) -> int:
    cmd = [
        "rg",
        "-l",
        "--type",
        "py",
        "--glob",
        f"!{exclude_pkg}/**",
        "--glob",
        "!tests/**",
        pattern,
        str(repo_root),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return len(r.stdout.strip().splitlines()) if r.returncode == 0 else 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0


def extract_all_names(init_path: Path) -> set[str]:
    if not init_path.exists():
        return set()
    try:
        tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(
                                elt.value, str
                            ):
                                names.add(elt.value)
    return names


def find_internal_only_symbols(package: str, repo_root: Path) -> list[str]:
    """Find symbols that are in __all__ but only used within the package."""
    pkg_dir = repo_root / package
    init_path = pkg_dir / "__init__.py"
    all_names = extract_all_names(init_path)
    if not all_names:
        return []

    internal_only = []
    for sym in sorted(all_names):
        # External usage (outside package, outside tests)
        ext = rg_count_outside(f"\\b{sym}\\b", repo_root, package)
        if ext > 0:
            continue

        # Test-only usage
        test_cmd = [
            "rg",
            "-l",
            "--type",
            "py",
            "--glob",
            f"!{package}/**",
            f"\\b{sym}\\b",
            str(repo_root),
        ]
        try:
            r = subprocess.run(test_cmd, capture_output=True, text=True, timeout=15)
            test_files = len(r.stdout.strip().splitlines()) if r.returncode == 0 else 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            test_files = 0

        if test_files > 0:
            # Has test consumers — skip (TEST_ONLY, not INTERNAL_ONLY)
            continue

        # Internal usage (within package)
        internal = rg_count_in(f"\\b{sym}\\b", pkg_dir)
        # Subtract definition + __init__.py re-export
        internal = max(0, internal - 2)

        if internal > 0:
            internal_only.append(sym)

    return internal_only


def remove_from_all(init_path: Path, symbols_to_remove: set[str], dry_run: bool) -> int:
    """Remove specific symbols from __all__ in an __init__.py file.

    Returns count of symbols removed.
    """
    content = init_path.read_text(encoding="utf-8")
    removed = 0

    for sym in sorted(symbols_to_remove):
        # Match patterns like:
        #   "SymbolName",
        #   "SymbolName",  # comment
        #   "symbol_name",
        # With optional leading whitespace and trailing comma/whitespace
        patterns = [
            # Full line with quotes and comma
            rf'^\s*"{re.escape(sym)}",?\s*(?:#.*)?\n',
            rf"^\s*'{re.escape(sym)}',?\s*(?:#.*)?\n",
        ]
        for pattern in patterns:
            new_content = re.sub(pattern, "", content, count=1, flags=re.MULTILINE)
            if new_content != content:
                content = new_content
                removed += 1
                break

    if removed > 0 and not dry_run:
        init_path.write_text(content, encoding="utf-8")

    return removed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def discover_packages(repo_root: Path) -> list[str]:
    pkgs = []
    for d in sorted(repo_root.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or d.name in SKIP_DIRS:
            continue
        if (d / "__init__.py").exists() and d.name not in NO_API_PACKAGES:
            pkgs.append(d.name)
    return pkgs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove internal-only symbols from __all__ across packages.",
    )
    parser.add_argument("package", nargs="*", help="Specific packages (default: all)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without modifying files"
    )
    args = parser.parse_args()
    repo_root = find_repo_root()

    packages = args.package or discover_packages(repo_root)
    dry_label = " [DRY RUN]" if args.dry_run else ""

    total_removed = 0
    changes: list[tuple[str, list[str], int]] = []

    for pkg in packages:
        pkg_dir = repo_root / pkg
        init_path = pkg_dir / "__init__.py"
        if not init_path.exists():
            continue

        all_names = extract_all_names(init_path)
        if not all_names:
            continue

        print(f"Scanning {pkg} ({len(all_names)} in __all__)...", end=" ", flush=True)
        internal_only = find_internal_only_symbols(pkg, repo_root)

        if not internal_only:
            print("no internal-only symbols")
            continue

        print(f"found {len(internal_only)} internal-only")

        for sym in internal_only:
            print(f"  - {sym}")

        removed = remove_from_all(init_path, set(internal_only), args.dry_run)
        total_removed += removed
        changes.append((pkg, internal_only, removed))

        action = "would remove" if args.dry_run else "removed"
        print(f"  → {action} {removed} from __all__{dry_label}")

    print(f"\n{'=' * 60}")
    print(
        f"Total: {total_removed} symbols {'would be ' if args.dry_run else ''}removed "
        f"from __all__ across {len(changes)} packages{dry_label}"
    )

    if changes:
        print("\nPackages modified:")
        for pkg, syms, count in changes:
            print(f"  {pkg}/__init__.py: {count} removed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
