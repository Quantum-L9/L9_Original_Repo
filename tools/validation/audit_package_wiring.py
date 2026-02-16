#!/usr/bin/env python3
"""
Package Wiring Audit — L9 (Levels B + C)
==========================================

Level B: For each .py file in a package, checks:
  - Has external consumers? (imported by files OUTSIDE the package)
  - Has tests? (matching test file or test references)
  - Is re-exported via __init__.py __all__?

Level C: For each public symbol (in __all__), checks:
  - Is it used outside the package? (excluding tests)
  - Is it used only in tests?
  - Is it unused (dead API)?
  Also flags packages that SHOULD have __all__ but don't.

Uses ripgrep (rg) for speed — no Python imports, no runtime needed.

Usage:
    python tools/validation/audit_package_wiring.py memory
    python tools/validation/audit_package_wiring.py --all
    python tools/validation/audit_package_wiring.py --all --report-dir reports/audits/
    python tools/validation/audit_package_wiring.py memory --level b   # Level B only
    python tools/validation/audit_package_wiring.py memory --level c   # Level C only

Requires: ripgrep (rg) installed and on PATH.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared helpers (duplicated from audit_package_exports.py to keep standalone)
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

# Packages that are CLI/entrypoint/test — never need __all__
NO_API_PACKAGES = {"scripts", "ci", "tests", "tools", "migrations"}


def find_repo_root() -> Path:
    cur = Path(__file__).resolve().parent
    for _ in range(6):
        if (cur / "memory" / "__init__.py").exists() and (
            cur / "core" / "__init__.py"
        ).exists():
            return cur
        cur = cur.parent
    return Path.cwd()


def rg_count(
    pattern: str,
    repo_root: Path,
    *,
    type_filter: str = "py",
    exclude_dir: str | None = None,
    include_dir: str | None = None,
) -> int:
    """Run rg --count and return total match count (files with matches)."""
    cmd = ["rg", "-l", "--type", type_filter, pattern, str(repo_root)]
    if exclude_dir:
        cmd.extend(["--glob", f"!{exclude_dir}/**"])
    if include_dir:
        cmd = ["rg", "-l", "--type", type_filter, pattern, str(repo_root / include_dir)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)  # noqa: S603 — trusted cmd, no shell
        if result.returncode == 0:
            return len(result.stdout.strip().splitlines())
        return 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0


def rg_files(
    pattern: str,
    repo_root: Path,
    *,
    type_filter: str = "py",
    glob_exclude: list[str] | None = None,
) -> list[str]:
    """Run rg -l and return list of matching file paths (relative)."""
    cmd = ["rg", "-l", "--type", type_filter, pattern, str(repo_root)]
    for g in glob_exclude or []:
        cmd.extend(["--glob", f"!{g}"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)  # noqa: S603 — trusted cmd, no shell
        if result.returncode == 0:
            lines = result.stdout.strip().splitlines()
            # Make relative to repo_root
            return [str(Path(f).relative_to(repo_root)) for f in lines if f.strip()]
        return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def extract_all_names(init_path: Path) -> set[str]:
    """Extract __all__ names via AST."""
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


def extract_public_names_from_module(filepath: Path) -> list[str]:
    """Extract public class/function names from a .py file (no leading _)."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
    except SyntaxError:
        return []
    names = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.append(node.name)
    return names


# ---------------------------------------------------------------------------
# Level B: File-level wiring
# ---------------------------------------------------------------------------


def audit_level_b(package_name: str, repo_root: Path) -> dict:
    """Check each .py file for consumers, tests, and re-export status."""
    pkg_dir = repo_root / package_name
    if not pkg_dir.is_dir():
        return {"error": f"Package directory not found: {pkg_dir}"}

    init_path = pkg_dir / "__init__.py"
    all_names = extract_all_names(init_path) if init_path.exists() else set()

    # Read __init__.py source to check re-export references
    init_source = init_path.read_text(encoding="utf-8") if init_path.exists() else ""

    py_files = sorted(
        f
        for f in pkg_dir.glob("*.py")
        if f.name != "__init__.py" and f.name != "__pycache__"
    )

    results = []
    for f in py_files:
        module_name = f.stem
        fqn = f"{package_name}.{module_name}"

        # 1. External consumers (files outside this package that import from it)
        import_pattern = f"from {fqn}|import {fqn}"
        consumer_files = rg_files(
            import_pattern,
            repo_root,
            type_filter="py",
            glob_exclude=[f"{package_name}/*", f"{package_name}/**"],
        )
        # Also exclude __init__.py of the same package
        consumer_files = [
            c for c in consumer_files if not c.startswith(f"{package_name}/")
        ]
        ext_consumers = [c for c in consumer_files if not c.startswith("tests/")]
        test_consumers = [c for c in consumer_files if c.startswith("tests/")]

        # 2. Has dedicated test file?
        has_test_file = False
        test_paths_checked = [
            repo_root / "tests" / package_name / f"test_{module_name}.py",
            repo_root / "tests" / f"test_{module_name}.py",
        ]
        # Also check for subpackage tests
        test_subdir = repo_root / "tests" / package_name
        if test_subdir.is_dir():
            for tf in test_subdir.glob(f"*{module_name}*"):
                if tf.suffix == ".py":
                    has_test_file = True
                    break
        if not has_test_file:
            for tp in test_paths_checked:
                if tp.exists():
                    has_test_file = True
                    break

        # 3. Is it referenced in __init__.py? (re-exported)
        is_reexported = f"{package_name}.{module_name}" in init_source

        # 4. Is it an entrypoint? (has if __name__ == "__main__")
        try:
            source = f.read_text(encoding="utf-8")
            is_entrypoint = "__name__" in source and "__main__" in source
        except Exception:
            is_entrypoint = False

        # Classify
        if len(ext_consumers) > 0 and is_reexported:
            status = "WIRED"
        elif len(ext_consumers) > 0:
            status = "PARTIAL_NO_REEXPORT"
        elif is_reexported and len(ext_consumers) == 0 and len(test_consumers) > 0:
            status = "PARTIAL_TEST_ONLY"
        elif is_reexported and len(ext_consumers) == 0:
            status = "PARTIAL_NO_CONSUMERS"
        elif is_entrypoint:
            status = "ENTRYPOINT"
        elif len(test_consumers) > 0:
            status = "TEST_ONLY"
        else:
            status = "ORPHAN"

        results.append(
            {
                "file": f"{package_name}/{f.name}",
                "module": module_name,
                "ext_consumers": len(ext_consumers),
                "test_consumers": len(test_consumers),
                "has_test_file": has_test_file,
                "is_reexported": is_reexported,
                "is_entrypoint": is_entrypoint,
                "status": status,
            }
        )

    # Summarize
    wired = [r for r in results if r["status"] == "WIRED"]
    partial = [r for r in results if r["status"].startswith("PARTIAL")]
    orphans = [r for r in results if r["status"] == "ORPHAN"]
    entrypoints = [r for r in results if r["status"] == "ENTRYPOINT"]
    test_only = [r for r in results if r["status"] == "TEST_ONLY"]

    return {
        "package": package_name,
        "files_checked": len(results),
        "wired": len(wired),
        "partial": len(partial),
        "orphan": len(orphans),
        "entrypoint": len(entrypoints),
        "test_only": len(test_only),
        "details": results,
    }


# ---------------------------------------------------------------------------
# Level C: API instantiation
# ---------------------------------------------------------------------------


def audit_level_c(package_name: str, repo_root: Path) -> dict:
    """Check public API symbols for actual usage outside the package."""
    pkg_dir = repo_root / package_name
    init_path = pkg_dir / "__init__.py"

    all_names = extract_all_names(init_path) if init_path.exists() else set()
    py_files = len([f for f in pkg_dir.glob("*.py") if f.name != "__init__.py"])

    # Determine API status
    if all_names:
        api_status = "HAS_API"
    elif package_name in NO_API_PACKAGES:
        api_status = "NO_API_NEEDED"
    elif py_files > 5:
        api_status = "SHOULD_HAVE_API"
    else:
        api_status = "NO_API_NEEDED"

    if api_status == "NO_API_NEEDED":
        return {
            "package": package_name,
            "api_status": api_status,
            "symbols_checked": 0,
            "used": 0,
            "test_only": 0,
            "unused": 0,
            "details": [],
            "recommended_all": [],
            "missing_patterns": [],
        }

    # For HAS_API: check each __all__ symbol
    if api_status == "HAS_API":
        symbols_to_check = sorted(all_names)
    else:
        # SHOULD_HAVE_API: discover de-facto public symbols
        symbols_to_check = []
        for f in sorted(pkg_dir.glob("*.py")):
            if f.name == "__init__.py":
                continue
            symbols_to_check.extend(extract_public_names_from_module(f))

    details = []
    for sym in symbols_to_check:
        # Search for usage outside the package (word-boundary match)
        ext_files = rg_files(
            f"\\b{sym}\\b",
            repo_root,
            type_filter="py",
            glob_exclude=[f"{package_name}/*", f"{package_name}/**"],
        )
        ext_files = [f for f in ext_files if not f.startswith(f"{package_name}/")]

        ext_non_test = [f for f in ext_files if not f.startswith("tests/")]
        ext_test = [f for f in ext_files if f.startswith("tests/")]

        if len(ext_non_test) > 0:
            status = "USED"
        elif len(ext_test) > 0:
            status = "TEST_ONLY"
        else:
            status = "UNUSED"

        details.append(
            {
                "symbol": sym,
                "ext_consumers": len(ext_non_test),
                "test_consumers": len(ext_test),
                "status": status,
            }
        )

    used = [d for d in details if d["status"] == "USED"]
    test_only = [d for d in details if d["status"] == "TEST_ONLY"]
    unused = [d for d in details if d["status"] == "UNUSED"]

    # Missing patterns: look for get_*/create_*/Service/Config/Engine not in __all__
    missing_patterns = []
    if api_status == "HAS_API":
        for f in sorted(pkg_dir.glob("*.py")):
            if f.name == "__init__.py":
                continue
            for name in extract_public_names_from_module(f):
                is_api_pattern = (
                    name.startswith("get_")
                    or name.startswith("create_")
                    or name.endswith("Service")
                    or name.endswith("Config")
                    or name.endswith("Engine")
                    or name.endswith("Pipeline")
                    or name.endswith("Registry")
                )
                if is_api_pattern and name not in all_names:
                    missing_patterns.append(name)

    # Recommended __all__ entries (for SHOULD_HAVE_API)
    recommended_all = []
    if api_status == "SHOULD_HAVE_API":
        recommended_all = [d["symbol"] for d in details if d["status"] == "USED"]

    return {
        "package": package_name,
        "api_status": api_status,
        "symbols_checked": len(details),
        "used": len(used),
        "test_only": len(test_only),
        "unused": len(unused),
        "details": details,
        "recommended_all": sorted(recommended_all),
        "missing_patterns": sorted(missing_patterns),
    }


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------


def format_level_b_report(data: dict) -> str:
    if "error" in data:
        return f"Error: {data['error']}\n"
    lines = [
        f"## Level B: File Wiring — `{data['package']}`",
        "",
        f"Files checked: {data['files_checked']}",
        f"- WIRED: {data['wired']}",
        f"- PARTIAL: {data['partial']}",
        f"- ORPHAN: {data['orphan']}",
        f"- ENTRYPOINT: {data['entrypoint']}",
        f"- TEST_ONLY: {data['test_only']}",
        "",
        "| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |",
        "|------|-------------:|---------------:|-----------|-------------|--------|",
    ]
    for r in data["details"]:
        test_icon = "Y" if r["has_test_file"] else "-"
        reexp_icon = "Y" if r["is_reexported"] else "-"
        status_icon = {
            "WIRED": "OK",
            "PARTIAL_NO_REEXPORT": "PARTIAL",
            "PARTIAL_TEST_ONLY": "PARTIAL",
            "PARTIAL_NO_CONSUMERS": "PARTIAL",
            "ENTRYPOINT": "ENTRY",
            "TEST_ONLY": "TEST",
            "ORPHAN": "ORPHAN",
        }.get(r["status"], r["status"])
        lines.append(
            f"| `{r['file']}` | {r['ext_consumers']} | {r['test_consumers']} "
            f"| {test_icon} | {reexp_icon} | {status_icon} |"
        )
    lines.append("")
    return "\n".join(lines)


def format_level_c_report(data: dict) -> str:
    lines = [
        f"## Level C: API Instantiation — `{data['package']}`",
        "",
        f"API Status: **{data['api_status']}**",
        f"Symbols checked: {data['symbols_checked']}",
        f"- USED: {data['used']}",
        f"- TEST_ONLY: {data['test_only']}",
        f"- UNUSED: {data['unused']}",
        "",
    ]

    if data["details"]:
        # Only show problems (unused/test-only) and a count of used
        problems = [d for d in data["details"] if d["status"] != "USED"]
        if problems:
            lines.append("| Symbol | Ext | Test | Status |")
            lines.append("|--------|----:|-----:|--------|")
            for d in problems:
                lines.append(
                    f"| `{d['symbol']}` | {d['ext_consumers']} | {d['test_consumers']} "
                    f"| {d['status']} |"
                )
            lines.append("")

    if data["missing_patterns"]:
        lines.append("**API-pattern symbols NOT in `__all__`:**")
        for name in data["missing_patterns"]:
            lines.append(f"- `{name}`")
        lines.append("")

    if data["recommended_all"]:
        lines.append("**Recommended `__all__` entries (used externally):**")
        for name in data["recommended_all"]:
            lines.append(f"- `{name}`")
        lines.append("")

    return "\n".join(lines)


def format_full_report(package: str, b_data: dict, c_data: dict) -> str:
    lines = [
        f"# Package Wiring Audit: {package}",
        "",
        f"**Date:** {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]
    lines.append(format_level_b_report(b_data))
    lines.append(format_level_c_report(c_data))
    return "\n".join(lines)


def format_consolidated(all_results: list[dict]) -> str:
    lines = [
        "# L9 Component Wiring Audit — Consolidated (Levels B + C)",
        "",
        f"**Generated:** {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Level B Summary: File Wiring",
        "",
        "| Package | Files | Wired | Partial | Orphan | Entry | Test-Only |",
        "|---------|------:|------:|--------:|-------:|------:|----------:|",
    ]
    for r in all_results:
        b = r.get("b", {})
        if "error" in b:
            lines.append(f"| `{r['name']}` | - | - | - | - | - | - |")
            continue
        if not b:
            continue
        lines.append(
            f"| `{r['name']}` | {b['files_checked']} | {b['wired']} | {b['partial']} "
            f"| {b['orphan']} | {b['entrypoint']} | {b['test_only']} |"
        )

    lines.extend(
        [
            "",
            "## Level C Summary: API Instantiation",
            "",
            "| Package | API Status | Checked | Used | Test-Only | Unused | Missing Patterns |",
            "|---------|-----------|--------:|-----:|----------:|-------:|-----------------:|",
        ]
    )
    for r in all_results:
        c = r.get("c", {})
        if not c:
            continue
        lines.append(
            f"| `{r['name']}` | {c['api_status']} | {c['symbols_checked']} | {c['used']} "
            f"| {c['test_only']} | {c['unused']} | {len(c.get('missing_patterns', []))} |"
        )

    # Detail sections for packages with issues
    lines.extend(["", "## Packages Needing Attention", ""])
    for r in all_results:
        b = r.get("b", {})
        c = r.get("c", {})
        has_orphans = b.get("orphan", 0) > 0
        has_unused = c.get("unused", 0) > 0
        has_missing = len(c.get("missing_patterns", [])) > 0
        has_recommended = len(c.get("recommended_all", [])) > 0

        if not (has_orphans or has_unused or has_missing or has_recommended):
            continue

        lines.append(f"### `{r['name']}`")
        lines.append("")

        if has_orphans:
            orphan_files = [
                d["file"] for d in b.get("details", []) if d["status"] == "ORPHAN"
            ]
            lines.append(
                f"**Orphan files ({len(orphan_files)}):** "
                + ", ".join(f"`{f}`" for f in orphan_files)
            )

        if has_unused:
            unused_syms = [
                d["symbol"] for d in c.get("details", []) if d["status"] == "UNUSED"
            ]
            lines.append(
                f"**Unused API symbols ({len(unused_syms)}):** "
                + ", ".join(f"`{s}`" for s in unused_syms[:15])
            )
            if len(unused_syms) > 15:
                lines.append(f"  ... and {len(unused_syms) - 15} more")

        if has_missing:
            lines.append(
                f"**API-pattern symbols not in `__all__` ({len(c['missing_patterns'])}):** "
                + ", ".join(f"`{s}`" for s in c["missing_patterns"][:10])
            )

        if has_recommended:
            lines.append(
                f"**Recommended `__all__` entries ({len(c['recommended_all'])}):** "
                + ", ".join(f"`{s}`" for s in c["recommended_all"][:10])
            )

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def discover_packages(repo_root: Path) -> list[str]:
    """Discover all top-level Python packages."""
    pkgs = []
    for d in sorted(repo_root.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or d.name in SKIP_DIRS:
            continue
        if (d / "__init__.py").exists():
            pkgs.append(d.name)
    return pkgs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit package file wiring (Level B) and API instantiation (Level C).",
    )
    parser.add_argument("package", nargs="*", help="Package name(s)")
    parser.add_argument(
        "--all", action="store_true", dest="audit_all", help="Audit all packages"
    )
    parser.add_argument(
        "--level",
        choices=["b", "c", "bc"],
        default="bc",
        help="Which levels to run (default: bc)",
    )
    parser.add_argument(
        "--report", metavar="PATH", help="Write report to this path (single package)"
    )
    parser.add_argument(
        "--report-dir",
        metavar="DIR",
        help="Write per-package reports to this directory",
    )
    parser.add_argument(
        "--consolidated", metavar="PATH", help="Write consolidated report"
    )
    parser.add_argument("--quiet", action="store_true", help="Summary lines only")
    args = parser.parse_args()
    repo_root = find_repo_root()

    packages = discover_packages(repo_root) if args.audit_all else args.package
    if not packages:
        parser.error("Provide package name(s) or use --all")

    run_b = "b" in args.level
    run_c = "c" in args.level

    all_results = []
    for pkg in packages:
        pkg_dir = repo_root / pkg
        if not pkg_dir.is_dir():
            print(f"{pkg}: SKIP (not a directory)", file=sys.stderr)
            continue

        py_files = len([f for f in pkg_dir.glob("*.py") if f.name != "__init__.py"])
        if py_files == 0:
            if not args.quiet:
                print(f"{pkg}: SKIP (no .py files)")
            continue

        entry = {"name": pkg}

        if run_b:
            b_data = audit_level_b(pkg, repo_root)
            entry["b"] = b_data
            if not args.quiet:
                if "error" in b_data:
                    print(f"{pkg} B: ERROR — {b_data['error']}")
                else:
                    print(
                        f"{pkg} B: {b_data['files_checked']} files "
                        f"(wired={b_data['wired']} partial={b_data['partial']} "
                        f"orphan={b_data['orphan']} entry={b_data['entrypoint']})"
                    )

        if run_c:
            c_data = audit_level_c(pkg, repo_root)
            entry["c"] = c_data
            if not args.quiet:
                print(
                    f"{pkg} C: {c_data['api_status']} "
                    f"(checked={c_data['symbols_checked']} used={c_data['used']} "
                    f"unused={c_data['unused']} missing_patterns={len(c_data.get('missing_patterns', []))})"
                )

        all_results.append(entry)

        # Per-package report
        if args.report_dir:
            report_dir = Path(args.report_dir)
            report_dir.mkdir(parents=True, exist_ok=True)
            b_data = entry.get("b", {})
            c_data = entry.get("c", {})
            report_text = format_full_report(pkg, b_data, c_data)
            (report_dir / f"{pkg}_wiring_audit.md").write_text(
                report_text, encoding="utf-8"
            )

        if args.report and len(packages) == 1:
            b_data = entry.get("b", {})
            c_data = entry.get("c", {})
            Path(args.report).write_text(
                format_full_report(pkg, b_data, c_data),
                encoding="utf-8",
            )

    # Consolidated report
    consolidated_path = args.consolidated or (
        str(Path(args.report_dir) / "CONSOLIDATED_WIRING_AUDIT.md")
        if args.report_dir
        else None
    )
    if consolidated_path and len(all_results) > 1:
        Path(consolidated_path).parent.mkdir(parents=True, exist_ok=True)
        Path(consolidated_path).write_text(
            format_consolidated(all_results),
            encoding="utf-8",
        )
        print(f"\nConsolidated report: {consolidated_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
