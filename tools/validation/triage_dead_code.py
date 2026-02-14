#!/usr/bin/env python3
"""
Dead Code Triage — L9
======================

Classifies "dead" code (unused symbols, orphan files) into actionable categories:

  USED           — External consumers exist. Healthy.
  INTERNAL_ONLY  — Used within the package but not externally. NOT dead.
  TEST_ONLY      — Only referenced in tests. Keep if tested intentionally.
  DYNAMIC_LOAD   — Loaded dynamically (agents, webhooks, CLI). NOT dead.
  WIP            — Recently created (<60 days), not yet wired. Needs integration.
  ASPIRATIONAL   — In __all__ but zero references anywhere. Trim or wire.
  SUPERSEDED     — Older file with a newer file doing the same thing. Remove candidate.
  TRULY_DEAD     — No references, old, no similar replacement. Remove candidate.

Signals used:
  1. External usage (from Level C audit)
  2. Internal usage (within-package references via rg)
  3. Git creation age (git log --diff-filter=A)
  4. Duplicate detection (similar class/function names in same package)

Usage:
    python tools/validation/triage_dead_code.py memory
    python tools/validation/triage_dead_code.py --all
    python tools/validation/triage_dead_code.py --all --report reports/audits/TRIAGE_REPORT.md

Requires: ripgrep (rg), git
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
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

# Packages whose symbols are loaded dynamically (agent configs, webhooks, CLI)
# rather than via static imports.  These should never be flagged as ZERO_REF.
DYNAMIC_LOAD_PACKAGES = {"agents", "mac_agent", "services"}
DYNAMIC_LOAD_FILE_PREFIXES = ("webhook_", "agent_", "cli_")

# Age thresholds (days)
WIP_THRESHOLD = 60
OLD_THRESHOLD = 90


def find_repo_root() -> Path:
    cur = Path(__file__).resolve().parent
    for _ in range(6):
        if (cur / "memory" / "__init__.py").exists():
            return cur
        cur = cur.parent
    return Path.cwd()


def rg_count_in(pattern: str, search_dir: Path, *, type_filter: str = "py") -> int:
    """Count files matching pattern within a directory."""
    cmd = ["rg", "-l", "--type", type_filter, pattern, str(search_dir)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return len(r.stdout.strip().splitlines()) if r.returncode == 0 else 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0


def rg_count_outside(
    pattern: str,
    repo_root: Path,
    exclude_pkg: str,
    *,
    type_filter: str = "py",
    exclude_tests: bool = False,
) -> int:
    """Count files matching pattern OUTSIDE a package directory."""
    cmd = [
        "rg",
        "-l",
        "--type",
        type_filter,
        "--glob",
        f"!{exclude_pkg}/**",
        pattern,
        str(repo_root),
    ]
    if exclude_tests:
        cmd.extend(["--glob", "!tests/**"])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return len(r.stdout.strip().splitlines()) if r.returncode == 0 else 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0


def git_creation_date(filepath: str, repo_root: Path) -> datetime | None:
    """Get the date a file was first committed."""
    cmd = [
        "git",
        "log",
        "--follow",
        "--diff-filter=A",
        "--format=%aI",
        "--",
        filepath,
    ]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10, cwd=str(repo_root)
        )
        if r.returncode == 0 and r.stdout.strip():
            date_str = r.stdout.strip().splitlines()[-1]
            return datetime.fromisoformat(date_str)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def git_last_meaningful_date(filepath: str, repo_root: Path) -> datetime | None:
    """Get the last commit date that wasn't a bulk/automated operation."""
    # Skip commits that are clearly automated sweeps
    auto_keywords = ["dora", "readme", "tech-debt", "formatting", "index", "deploy"]
    cmd = [
        "git",
        "log",
        "--format=%aI|%s",
        "-20",
        "--",
        filepath,
    ]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10, cwd=str(repo_root)
        )
        if r.returncode == 0 and r.stdout.strip():
            for line in r.stdout.strip().splitlines():
                parts = line.split("|", 1)
                if len(parts) == 2:
                    date_str, msg = parts
                    msg_lower = msg.lower()
                    if not any(kw in msg_lower for kw in auto_keywords):
                        return datetime.fromisoformat(date_str)
            # All commits were automated — use the oldest one as proxy
            last_line = r.stdout.strip().splitlines()[-1]
            return datetime.fromisoformat(last_line.split("|")[0])
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def extract_all_names(init_path: Path) -> set[str]:
    """Extract __all__ names via AST."""
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


def extract_public_names(filepath: Path) -> list[str]:
    """Extract public class/function names from a .py file."""
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
# Classification engine
# ---------------------------------------------------------------------------


def classify_symbol(
    symbol: str,
    package: str,
    repo_root: Path,
) -> dict:
    """Classify a single symbol into a triage category."""
    pkg_dir = repo_root / package

    # Signal 1: External usage (outside package, outside tests)
    ext_usage = rg_count_outside(
        f"\\b{symbol}\\b", repo_root, package, exclude_tests=True
    )

    # Signal 2: Test-only usage
    test_usage = rg_count_outside(f"\\b{symbol}\\b", repo_root, package)
    test_only = test_usage - ext_usage

    # Signal 3: Internal usage (within package)
    internal_usage = rg_count_in(f"\\b{symbol}\\b", pkg_dir)
    # Subtract 1 for the definition itself and 1 for __init__.py re-export
    internal_usage = max(0, internal_usage - 2)

    # Classification
    if ext_usage > 0:
        category = "USED"
    elif internal_usage > 0:
        category = "INTERNAL_ONLY"
    elif test_only > 0:
        category = "TEST_ONLY"
    elif package in DYNAMIC_LOAD_PACKAGES:
        category = "DYNAMIC_LOAD"
    else:
        category = "ZERO_REF"

    return {
        "symbol": symbol,
        "ext_usage": ext_usage,
        "test_only": test_only,
        "internal_usage": internal_usage,
        "category": category,
    }


def classify_file(
    filepath: Path,
    package: str,
    repo_root: Path,
    now: datetime,
) -> dict:
    """Classify a single orphan file."""
    module = filepath.stem
    fqn = f"{package}.{module}"
    rel_path = str(filepath.relative_to(repo_root))

    # Signal 1: External consumers
    ext_count = rg_count_outside(f"from {fqn}|import {fqn}", repo_root, package)

    # Signal 2: Internal consumers (other files in same package importing this)
    internal_count = rg_count_in(
        f"from {fqn}|import {fqn}|from \\.{module}", filepath.parent
    )
    internal_count = max(0, internal_count - 1)  # Subtract self

    # Signal 3: Git age
    creation_date = git_creation_date(rel_path, repo_root)
    meaningful_date = git_last_meaningful_date(rel_path, repo_root)
    age_days = (now - creation_date).days if creation_date else 999
    meaningful_age_days = (now - meaningful_date).days if meaningful_date else 999

    # Signal 4: Has similar-named file in package? (duplicate detection)
    stem_words = set(module.split("_"))
    siblings = [
        f.stem
        for f in filepath.parent.glob("*.py")
        if f.name != filepath.name and f.name != "__init__.py"
    ]
    similar = [s for s in siblings if len(stem_words & set(s.split("_"))) >= 2]

    # Classification
    is_dynamic = package in DYNAMIC_LOAD_PACKAGES or any(
        module.startswith(pfx) for pfx in DYNAMIC_LOAD_FILE_PREFIXES
    )
    if ext_count > 0:
        category = "WIRED"
    elif internal_count > 0:
        category = "INTERNAL_ONLY"
    elif is_dynamic:
        category = "DYNAMIC_LOAD"
    elif age_days <= WIP_THRESHOLD:
        category = "WIP"
    elif similar and meaningful_age_days > OLD_THRESHOLD:
        category = "SUPERSEDED"
    elif meaningful_age_days > OLD_THRESHOLD:
        category = "TRULY_DEAD"
    else:
        category = "ASPIRATIONAL"

    return {
        "file": rel_path,
        "module": module,
        "ext_consumers": ext_count,
        "internal_consumers": internal_count,
        "age_days": age_days,
        "meaningful_age_days": meaningful_age_days,
        "similar_files": similar,
        "category": category,
    }


def triage_package(package: str, repo_root: Path) -> dict:
    """Run full triage on a package."""
    pkg_dir = repo_root / package
    if not pkg_dir.is_dir():
        return {"error": f"Not found: {pkg_dir}"}

    init_path = pkg_dir / "__init__.py"
    all_names = extract_all_names(init_path)
    now = datetime.now(tz=UTC)

    # Triage symbols (from __all__)
    symbol_results = []
    if all_names:
        for sym in sorted(all_names):
            result = classify_symbol(sym, package, repo_root)
            symbol_results.append(result)

    # Triage files (orphan detection)
    py_files = sorted(
        f for f in pkg_dir.glob("*.py") if f.name not in ("__init__.py", "__pycache__")
    )
    file_results = []
    for f in py_files:
        result = classify_file(f, package, repo_root, now)
        file_results.append(result)

    # Summarize
    sym_cats = {}
    for r in symbol_results:
        sym_cats.setdefault(r["category"], []).append(r["symbol"])

    file_cats = {}
    for r in file_results:
        file_cats.setdefault(r["category"], []).append(r["file"])

    return {
        "package": package,
        "symbol_count": len(symbol_results),
        "file_count": len(file_results),
        "symbol_categories": sym_cats,
        "file_categories": file_cats,
        "symbol_details": symbol_results,
        "file_details": file_results,
    }


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------


def format_package_report(data: dict) -> str:
    if "error" in data:
        return f"Error: {data['error']}\n"

    pkg = data["package"]
    lines = [
        f"# Dead Code Triage: `{pkg}`",
        "",
        f"**Date:** {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    # Symbol summary
    lines.append("## Symbol Classification")
    lines.append("")
    sym_cats = data["symbol_categories"]
    for cat in ["USED", "INTERNAL_ONLY", "TEST_ONLY", "DYNAMIC_LOAD", "ZERO_REF"]:
        syms = sym_cats.get(cat, [])
        if syms:
            lines.append(
                f"**{cat}** ({len(syms)}): " + ", ".join(f"`{s}`" for s in syms[:20])
            )
            if len(syms) > 20:
                lines.append(f"  ... and {len(syms) - 20} more")
    lines.append("")

    # File summary
    lines.append("## File Classification")
    lines.append("")
    file_cats = data["file_categories"]
    for cat in [
        "WIRED",
        "INTERNAL_ONLY",
        "DYNAMIC_LOAD",
        "WIP",
        "ASPIRATIONAL",
        "SUPERSEDED",
        "TRULY_DEAD",
    ]:
        files = file_cats.get(cat, [])
        if files:
            lines.append(f"**{cat}** ({len(files)}):")
            for f in files:
                lines.append(f"- `{f}`")
    lines.append("")

    # Action items
    lines.append("## Recommended Actions")
    lines.append("")

    zero_ref = sym_cats.get("ZERO_REF", [])
    internal = sym_cats.get("INTERNAL_ONLY", [])
    dead_files = file_cats.get("TRULY_DEAD", [])
    superseded = file_cats.get("SUPERSEDED", [])
    wip_files = file_cats.get("WIP", [])

    if internal:
        lines.append(f"### Remove {len(internal)} internal-only symbols from `__all__`")
        lines.append(
            "These are used within the package but not externally. "
            "Remove from `__all__` to reduce API surface noise."
        )
        lines.append("")

    if zero_ref:
        lines.append(f"### Review {len(zero_ref)} zero-reference symbols")
        lines.append(
            "These have no references anywhere (not even internal). "
            "Either wire them or remove from `__all__`."
        )
        lines.append("")

    if dead_files:
        lines.append(f"### Remove {len(dead_files)} truly dead files")
        lines.append("Old files with no consumers and no internal references.")
        lines.append("")

    if superseded:
        lines.append(f"### Review {len(superseded)} potentially superseded files")
        lines.append("Old files with similar-named siblings — may be replaced.")
        lines.append("")

    if wip_files:
        lines.append(f"### Wire {len(wip_files)} WIP files")
        lines.append("Recently created but not yet integrated.")
        lines.append("")

    return "\n".join(lines)


def format_consolidated(all_results: list[dict]) -> str:
    lines = [
        "# L9 Dead Code Triage — Consolidated Report",
        "",
        f"**Generated:** {datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Classification Legend",
        "",
        "| Category | Meaning | Action |",
        "|----------|---------|--------|",
        "| USED | External consumers exist | None needed |",
        "| INTERNAL_ONLY | Used within package only | Consider removing from `__all__` |",
        "| TEST_ONLY | Only referenced in tests | Keep if tested intentionally |",
        "| DYNAMIC_LOAD | Loaded dynamically (agents, webhooks, CLI) | None needed |",
        "| ZERO_REF | No references anywhere | Wire or remove |",
        "| WIRED | File has external importers | None needed |",
        "| WIP | Created <60 days, no consumers | Wire or document intent |",
        "| ASPIRATIONAL | In API but never used | Wire or trim |",
        "| SUPERSEDED | Old + similar sibling exists | Review for removal |",
        "| TRULY_DEAD | Old, no refs, no similar | Remove candidate |",
        "",
        "## Symbol Summary",
        "",
        "| Package | Total | Used | Internal | Test | Dynamic | Zero-Ref |",
        "|---------|------:|-----:|---------:|-----:|--------:|---------:|",
    ]

    total_used = total_internal = total_test = total_dynamic = total_zero = 0
    for data in all_results:
        if "error" in data or data["symbol_count"] == 0:
            continue
        sc = data["symbol_categories"]
        used = len(sc.get("USED", []))
        internal = len(sc.get("INTERNAL_ONLY", []))
        test = len(sc.get("TEST_ONLY", []))
        dynamic = len(sc.get("DYNAMIC_LOAD", []))
        zero = len(sc.get("ZERO_REF", []))
        total_used += used
        total_internal += internal
        total_test += test
        total_dynamic += dynamic
        total_zero += zero
        lines.append(
            f"| `{data['package']}` | {data['symbol_count']} | {used} | {internal} "
            f"| {test} | {dynamic} | {zero} |"
        )

    lines.append(
        f"| **TOTAL** | **{total_used + total_internal + total_test + total_dynamic + total_zero}** "
        f"| **{total_used}** | **{total_internal}** | **{total_test}** "
        f"| **{total_dynamic}** | **{total_zero}** |"
    )

    lines.extend(
        [
            "",
            "## File Summary",
            "",
            "| Package | Total | Wired | Internal | Dynamic | WIP | Aspirational | Superseded | Dead |",
            "|---------|------:|------:|---------:|--------:|----:|-------------:|-----------:|-----:|",
        ]
    )

    total_wired = total_fint = total_fdyn = total_wip = total_asp = total_sup = (
        total_dead
    ) = 0
    for data in all_results:
        if "error" in data or data["file_count"] == 0:
            continue
        fc = data["file_categories"]
        wired = len(fc.get("WIRED", []))
        fint = len(fc.get("INTERNAL_ONLY", []))
        fdyn = len(fc.get("DYNAMIC_LOAD", []))
        wip = len(fc.get("WIP", []))
        asp = len(fc.get("ASPIRATIONAL", []))
        sup = len(fc.get("SUPERSEDED", []))
        dead = len(fc.get("TRULY_DEAD", []))
        total_wired += wired
        total_fint += fint
        total_fdyn += fdyn
        total_wip += wip
        total_asp += asp
        total_sup += sup
        total_dead += dead
        lines.append(
            f"| `{data['package']}` | {data['file_count']} | {wired} | {fint} "
            f"| {fdyn} | {wip} | {asp} | {sup} | {dead} |"
        )

    lines.append(
        f"| **TOTAL** | - | **{total_wired}** | **{total_fint}** | **{total_fdyn}** "
        f"| **{total_wip}** | **{total_asp}** | **{total_sup}** | **{total_dead}** |"
    )

    # Action summary
    lines.extend(
        [
            "",
            "## Action Summary",
            "",
            f"- **{total_internal} symbols** to consider removing from `__all__` (internal-only)",
            f"- **{total_zero} symbols** with zero references (wire or remove)",
            f"- **{total_dead} files** that are truly dead (remove candidates)",
            f"- **{total_sup} files** potentially superseded (review)",
            f"- **{total_wip} files** that are WIP (wire or document)",
            "",
        ]
    )

    # Per-package details for packages with issues
    lines.append("## Per-Package Details")
    lines.append("")
    for data in all_results:
        if "error" in data:
            continue
        sc = data["symbol_categories"]
        fc = data["file_categories"]
        has_issues = (
            sc.get("ZERO_REF")
            or sc.get("INTERNAL_ONLY")
            or fc.get("TRULY_DEAD")
            or fc.get("SUPERSEDED")
            or fc.get("WIP")
        )
        if not has_issues:
            continue

        lines.append(f"### `{data['package']}`")
        lines.append("")

        if sc.get("INTERNAL_ONLY"):
            syms = sc["INTERNAL_ONLY"]
            lines.append(
                f"**Remove from `__all__` (internal-only, {len(syms)}):** "
                + ", ".join(f"`{s}`" for s in syms[:15])
            )
            if len(syms) > 15:
                lines.append(f"  ... and {len(syms) - 15} more")

        if sc.get("ZERO_REF"):
            syms = sc["ZERO_REF"]
            lines.append(
                f"**Zero-ref symbols ({len(syms)}):** "
                + ", ".join(f"`{s}`" for s in syms[:15])
            )
            if len(syms) > 15:
                lines.append(f"  ... and {len(syms) - 15} more")

        if fc.get("TRULY_DEAD"):
            lines.append(
                "**Dead files:** " + ", ".join(f"`{f}`" for f in fc["TRULY_DEAD"])
            )

        if fc.get("SUPERSEDED"):
            lines.append(
                "**Possibly superseded:** "
                + ", ".join(f"`{f}`" for f in fc["SUPERSEDED"])
            )

        if fc.get("WIP"):
            lines.append(
                "**WIP (needs wiring):** " + ", ".join(f"`{f}`" for f in fc["WIP"])
            )

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def discover_packages(repo_root: Path) -> list[str]:
    pkgs = []
    for d in sorted(repo_root.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or d.name in SKIP_DIRS:
            continue
        if (d / "__init__.py").exists():
            pkgs.append(d.name)
    return pkgs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify dead code into actionable categories."
    )
    parser.add_argument("package", nargs="*", help="Package name(s)")
    parser.add_argument("--all", action="store_true", dest="audit_all")
    parser.add_argument("--report", metavar="PATH", help="Write report")
    parser.add_argument("--report-dir", metavar="DIR", help="Per-package reports")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    repo_root = find_repo_root()

    packages = discover_packages(repo_root) if args.audit_all else args.package
    if not packages:
        parser.error("Provide package name(s) or use --all")

    # Filter to packages with content
    packages = [
        p
        for p in packages
        if (repo_root / p).is_dir()
        and any((repo_root / p).glob("*.py"))
        and p not in NO_API_PACKAGES
    ]

    all_results = []
    for pkg in packages:
        print(f"Triaging {pkg}...", end=" ", flush=True)
        data = triage_package(pkg, repo_root)
        all_results.append(data)

        if "error" in data:
            print(f"ERROR: {data['error']}")
            continue

        sc = data["symbol_categories"]
        fc = data["file_categories"]
        print(
            f"symbols: {data['symbol_count']} "
            f"(used={len(sc.get('USED', []))} "
            f"internal={len(sc.get('INTERNAL_ONLY', []))} "
            f"dynamic={len(sc.get('DYNAMIC_LOAD', []))} "
            f"zero={len(sc.get('ZERO_REF', []))}) "
            f"files: {data['file_count']} "
            f"(wired={len(fc.get('WIRED', []))} "
            f"dynamic={len(fc.get('DYNAMIC_LOAD', []))} "
            f"dead={len(fc.get('TRULY_DEAD', []))} "
            f"wip={len(fc.get('WIP', []))})"
        )

        if args.report_dir:
            report_dir = Path(args.report_dir)
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / f"{pkg}_triage.md").write_text(
                format_package_report(data),
                encoding="utf-8",
            )

    # Consolidated report
    report_path = args.report or (
        str(Path(args.report_dir) / "TRIAGE_REPORT.md") if args.report_dir else None
    )
    if report_path:
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(report_path).write_text(format_consolidated(all_results), encoding="utf-8")
        print(f"\nTriage report: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
