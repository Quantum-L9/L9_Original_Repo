#!/usr/bin/env python3
"""
Package Export Audit — L9
=========================

Checks that a Python package's __init__.py has consistent re-exports:
- Every name in __all__ is bound by an import (no broken re-exports).
- Every name imported from the package's own submodules is in __all__ (no missing re-exports).

Usage:
    python tools/validation/audit_package_exports.py memory
    python tools/validation/audit_package_exports.py core --report reports/core_export_audit.md
    python tools/validation/audit_package_exports.py --all                    # Audit all packages
    python tools/validation/audit_package_exports.py --all --report-dir reports/audits/  # With reports

Reference: reports/memory_export_audit.md, reports/COMPONENT_WIRING_AUDIT_GUIDE.md
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def find_repo_root() -> Path:
    """Resolve repo root (directory containing memory/, core/, etc.)."""
    cur = Path(__file__).resolve().parent
    for _ in range(6):
        if (cur / "memory" / "__init__.py").exists() and (
            cur / "core" / "__init__.py"
        ).exists():
            return cur
        cur = cur.parent
    return Path.cwd()


def extract_all_names_ast(tree: ast.AST) -> set[str]:
    """Extract __all__ list literal via AST."""
    names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    if isinstance(node.value, ast.List):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(
                                elt.value, str
                            ):
                                names.add(elt.value)
                    break
    return names


def extract_import_bound_names_ast(
    tree: ast.AST, package_dot: str
) -> tuple[set[str], set[str]]:
    """
    Extract names bound by imports via AST.
    Returns (all_bound_names, from_own_submodule_names).
    """
    all_bound: set[str] = set()
    from_own: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            module = node.module
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                if name == "*":
                    continue
                all_bound.add(name)
                if module.startswith(package_dot) or module == package_dot.rstrip("."):
                    from_own.add(name)
    return all_bound, from_own


def audit_package(package_name: str, repo_root: Path) -> dict:
    """Run export consistency audit for a top-level package."""
    init_path = repo_root / package_name / "__init__.py"
    if not init_path.exists():
        return {"error": f"Package has no __init__.py: {init_path}"}

    content = init_path.read_text(encoding="utf-8")
    package_dot = f"{package_name}."

    try:
        tree = ast.parse(content, filename=str(init_path))
    except SyntaxError as e:
        return {"error": f"SyntaxError in {init_path}: {e}"}

    all_names = extract_all_names_ast(tree)
    all_bound, from_own_submodule = extract_import_bound_names_ast(tree, package_dot)

    # Exclude common non-export names / intentional direct-import-only
    skip = {"graph_client", "content"}
    from_own_submodule = {n for n in from_own_submodule if n not in skip}

    in_all_not_imported = all_names - all_bound
    imported_from_own_not_in_all = from_own_submodule - all_names

    return {
        "package": package_name,
        "init_path": str(init_path),
        "all_count": len(all_names),
        "bound_count": len(all_bound),
        "from_own_count": len(from_own_submodule),
        "in_all_not_imported": sorted(in_all_not_imported),
        "imported_from_own_not_in_all": sorted(imported_from_own_not_in_all),
        "all_names": all_names,
        "from_own_submodule": from_own_submodule,
    }


def format_report(data: dict) -> str:
    """Produce a human-readable report."""
    if "error" in data:
        return f"Error: {data['error']}\n"

    lines = [
        f"# Package Export Audit: {data['package']}",
        "",
        f"- `__all__` count: {data['all_count']}",
        f"- Names bound by imports: {data['bound_count']}",
        f"- Names imported from {data['package']}.* submodules: {data['from_own_count']}",
        "",
        "## 1. In __all__ but NOT bound by any import (broken re-export)",
        "",
    ]
    if data["in_all_not_imported"]:
        for name in data["in_all_not_imported"]:
            lines.append(f"- {name}")
    else:
        lines.append("None")
    lines.extend(
        [
            "",
            "## 2. Imported from this package's submodules but NOT in __all__ (missing re-export)",
            "",
        ]
    )
    if data["imported_from_own_not_in_all"]:
        for name in data["imported_from_own_not_in_all"]:
            lines.append(f"- {name}")
    else:
        lines.append("None")
    lines.append("")
    return "\n".join(lines)


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


def discover_auditable_packages(repo_root: Path) -> list[dict]:
    """Discover all top-level packages and classify them.

    Returns a list of dicts with keys:
        name, py_files, has_all, all_count, import_count, status, category
    """
    results = []
    for d in sorted(repo_root.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or d.name in SKIP_DIRS:
            continue
        init = d / "__init__.py"
        if not init.exists():
            continue

        try:
            tree = ast.parse(init.read_text(encoding="utf-8"), filename=str(init))
        except SyntaxError:
            results.append(
                {
                    "name": d.name,
                    "py_files": 0,
                    "has_all": False,
                    "all_count": 0,
                    "import_count": 0,
                    "status": "PARSE_ERROR",
                    "category": "error",
                }
            )
            continue

        all_names = extract_all_names_ast(tree)
        _, from_own = extract_import_bound_names_ast(tree, f"{d.name}.")
        py_files = len([f for f in d.glob("*.py") if f.name != "__init__.py"])

        has_all = len(all_names) > 0
        all_count = len(all_names)
        import_count = len(from_own)

        if has_all and import_count > 0:
            status = "READY"
            category = "auditable"
        elif has_all:
            status = "ALL_NO_IMPORTS"
            category = "auditable"
        elif import_count > 0:
            status = "IMPORTS_NO_ALL"
            category = "auditable"
        elif py_files > 5:
            status = "SHOULD_HAVE_API"
            category = "flagged"
        else:
            status = "EMPTY_INIT"
            category = "skip"

        results.append(
            {
                "name": d.name,
                "py_files": py_files,
                "has_all": has_all,
                "all_count": all_count,
                "import_count": import_count,
                "status": status,
                "category": category,
            }
        )
    return results


def format_consolidated_report(all_results: list[dict]) -> str:
    """Produce a consolidated markdown report across all packages."""
    lines = [
        "# L9 Component Export Audit — Consolidated Report",
        "",
        f"**Generated:** {__import__('datetime').datetime.now(tz=__import__('datetime').timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Summary",
        "",
        "| Package | Files | `__all__` | Imports | Broken | Missing | Status |",
        "|---------|------:|----------:|--------:|-------:|--------:|--------|",
    ]

    totals = {"ok": 0, "fail": 0, "skip": 0, "flag": 0}
    detail_sections: list[str] = []

    for r in all_results:
        pkg = r["name"]
        if r.get("error"):
            lines.append(f"| `{pkg}` | - | - | - | - | - | ERROR |")
            totals["skip"] += 1
            continue
        if r["category"] == "skip":
            lines.append(
                f"| `{pkg}` | {r['py_files']} | {r['all_count']} | {r['import_count']} "
                f"| - | - | EMPTY |"
            )
            totals["skip"] += 1
            continue

        broken = len(r.get("in_all_not_imported", []))
        missing = len(r.get("imported_from_own_not_in_all", []))
        has_gaps = broken > 0 or missing > 0
        status_icon = "FAIL" if has_gaps else "OK"

        if r["status"] == "ALL_NO_IMPORTS":
            status_icon = "WARN (all, no imports)"
        elif r["status"] == "IMPORTS_NO_ALL":
            status_icon = "WARN (imports, no __all__)"
        elif r["status"] == "SHOULD_HAVE_API":
            status_icon = "FLAG (should have API)"

        lines.append(
            f"| `{pkg}` | {r['py_files']} | {r['all_count']} | {r['import_count']} "
            f"| {broken} | {missing} | {status_icon} |"
        )

        if has_gaps:
            totals["fail"] += 1
        elif r["category"] == "flagged":
            totals["flag"] += 1
        else:
            totals["ok"] += 1

        # Detail section for packages with gaps
        if has_gaps:
            detail_sections.append(
                f"\n### `{pkg}` — {broken} broken, {missing} missing\n"
            )
            if r.get("in_all_not_imported"):
                detail_sections.append("**In `__all__` but not imported (broken):**")
                for n in r["in_all_not_imported"]:
                    detail_sections.append(f"- `{n}`")
            if r.get("imported_from_own_not_in_all"):
                detail_sections.append("**Imported but not in `__all__` (missing):**")
                for n in r["imported_from_own_not_in_all"]:
                    detail_sections.append(f"- `{n}`")

    lines.extend(
        [
            "",
            f"**Totals:** {totals['ok']} OK, {totals['fail']} FAIL, "
            f"{totals['flag']} flagged, {totals['skip']} skipped",
            "",
        ]
    )

    if detail_sections:
        lines.append("## Details — Packages with Gaps")
        lines.extend(detail_sections)
    else:
        lines.append("## Details")
        lines.append("")
        lines.append("All auditable packages are clean.")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit a package's __init__.py for export consistency (__all__ vs imports).",
    )
    parser.add_argument(
        "package",
        nargs="*",
        help="Top-level package name(s), e.g. memory core runtime",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="audit_all",
        help="Discover and audit ALL packages in the repo.",
    )
    parser.add_argument(
        "--report",
        metavar="PATH",
        help="Write markdown report to this path (single package only).",
    )
    parser.add_argument(
        "--report-dir",
        metavar="DIR",
        help="Write per-package reports to this directory (with --all).",
    )
    parser.add_argument(
        "--consolidated",
        metavar="PATH",
        help="Write consolidated report to this path (with --all).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print summary line per package.",
    )
    args = parser.parse_args()
    repo_root = find_repo_root()

    # --all mode: discover and audit everything
    if args.audit_all:
        packages = discover_auditable_packages(repo_root)
        all_results = []

        for pkg_info in packages:
            name = pkg_info["name"]
            if pkg_info["category"] == "skip":
                all_results.append(pkg_info)
                if args.quiet:
                    print(f"{name}: SKIP ({pkg_info['status']})")
                continue

            data = audit_package(name, repo_root)
            if "error" in data:
                pkg_info["error"] = data["error"]
                all_results.append(pkg_info)
                if args.quiet:
                    print(f"{name}: ERROR ({data['error']})")
                continue

            # Merge audit data into pkg_info
            pkg_info["in_all_not_imported"] = data["in_all_not_imported"]
            pkg_info["imported_from_own_not_in_all"] = data[
                "imported_from_own_not_in_all"
            ]
            all_results.append(pkg_info)

            broken = len(data["in_all_not_imported"])
            missing = len(data["imported_from_own_not_in_all"])
            has_gaps = broken > 0 or missing > 0
            status = "FAIL" if has_gaps else "OK"
            print(
                f"{name}: {status} "
                f"(all={data['all_count']} imports={data['from_own_count']} "
                f"broken={broken} missing={missing})"
            )

            # Per-package report
            if args.report_dir:
                report_dir = Path(args.report_dir)
                report_dir.mkdir(parents=True, exist_ok=True)
                report_path = report_dir / f"{name}_export_audit.md"
                report_path.write_text(format_report(data), encoding="utf-8")

        # Consolidated report
        consolidated_path = args.consolidated or (
            str(Path(args.report_dir) / "CONSOLIDATED_AUDIT.md")
            if args.report_dir
            else None
        )
        if consolidated_path:
            Path(consolidated_path).parent.mkdir(parents=True, exist_ok=True)
            Path(consolidated_path).write_text(
                format_consolidated_report(all_results),
                encoding="utf-8",
            )
            print(f"\nConsolidated report: {consolidated_path}")

        # Exit code
        has_any_fail = any(
            len(r.get("in_all_not_imported", []))
            + len(r.get("imported_from_own_not_in_all", []))
            > 0
            for r in all_results
        )
        return 1 if has_any_fail else 0

    # Single/multi package mode (original behavior)
    if not args.package:
        parser.error("Provide package name(s) or use --all")

    exit_code = 0
    for package_name in args.package:
        data = audit_package(package_name, repo_root)
        if "error" in data:
            print(data["error"], file=sys.stderr)
            exit_code = 1
            continue

        report_text = format_report(data)
        if args.report and len(args.package) == 1:
            Path(args.report).write_text(report_text, encoding="utf-8")
            if not args.quiet:
                print(f"Wrote {args.report}")
        else:
            if not args.quiet:
                print(report_text)

        has_gaps = data["in_all_not_imported"] or data["imported_from_own_not_in_all"]
        if has_gaps:
            exit_code = 1
        if args.quiet:
            status = "FAIL" if has_gaps else "OK"
            print(
                f"{package_name}: {status} (all={data['all_count']} bound={data['bound_count']} gaps={len(data['in_all_not_imported']) + len(data['imported_from_own_not_in_all'])})"
            )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
