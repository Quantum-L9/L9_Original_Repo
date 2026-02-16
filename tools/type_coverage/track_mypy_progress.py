#!/usr/bin/env python3
"""
Type Coverage Tracker for L9

Analyzes mypy errors across all modules and generates:
- JSON coverage report (reports/type_coverage/coverage.json)
- Markdown roadmap (readme/TYPE_COVERAGE_ROADMAP.md)
- Shields.io badges for documentation

Usage:
    python tools/type_coverage/track_mypy_progress.py
    python tools/type_coverage/track_mypy_progress.py --update-precommit
    python tools/type_coverage/track_mypy_progress.py --help

Part of GMP Phase 2 - Enhancement 1
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import structlog

logger = structlog.get_logger()


@dataclass
class ModuleCoverage:
    """Type coverage data for a single module."""

    module_path: str
    error_count: int
    total_checks: int
    status: Literal["clean", "warning", "error"]
    errors: list[str]
    imported_by_count: int
    priority: Literal["critical", "high", "medium", "low"]
    auto_fixable: bool


def run_mypy_on_module(module_path: Path) -> tuple[int, list[str]]:
    """Run mypy on a single module and extract errors.

    Args:
        module_path: Path to Python module

    Returns:
        Tuple of (error_count, error_details)
    """
    try:
        result = subprocess.run(  # noqa: S603 — trusted cmd, no shell
            ["mypy", "--config-file=pyproject.toml", str(module_path)],  # noqa: S607 — trusted system command
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Parse errors from output
        errors = []
        for line in result.stdout.splitlines():
            if module_path.name in line and "error:" in line:
                errors.append(line.strip())

        return len(errors), errors

    except subprocess.TimeoutExpired:
        logger.warning("mypy_timeout", module=str(module_path))
        return 999, [f"TIMEOUT: {module_path}"]
    except Exception as e:
        logger.error("mypy_execution_failed", module=str(module_path), error=str(e))
        return 999, [f"ERROR: {e}"]


def calculate_coverage_tier(error_count: int) -> Literal["clean", "warning", "error"]:
    """Map error count to coverage tier.

    Args:
        error_count: Number of mypy errors

    Returns:
        Coverage tier
    """
    if error_count == 0:
        return "clean"
    if error_count <= 5:
        return "warning"
    return "error"


def calculate_import_priority(
    imported_by_count: int,
) -> Literal["critical", "high", "medium", "low"]:
    """Calculate module priority based on import frequency.

    Args:
        imported_by_count: Number of modules importing this one

    Returns:
        Priority tier
    """
    if imported_by_count >= 20:
        return "critical"
    if imported_by_count >= 10:
        return "high"
    if imported_by_count >= 3:
        return "medium"
    return "low"


def analyze_imports(repo_root: Path) -> dict[str, int]:
    """Count how many files import each module.

    Args:
        repo_root: Repository root directory

    Returns:
        Dict mapping module_path -> import_count
    """
    import_counts = defaultdict(int)

    for py_file in repo_root.rglob("*.py"):
        if "tests/" in str(py_file) or "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text()
            for line in content.splitlines():
                if line.strip().startswith(("import ", "from ")):
                    # Extract module name (simplified)
                    parts = line.split()
                    if len(parts) >= 2:
                        module_ref = parts[1].replace(".", "/") + ".py"
                        import_counts[module_ref] += 1
        except Exception as e:
            logger.debug("audit.file_skipped", error=str(e))
            continue

    return dict(import_counts)


def detect_auto_fixable_errors(errors: list[str]) -> bool:
    """Check if errors are likely auto-fixable.

    Args:
        errors: List of mypy error messages

    Returns:
        True if most errors appear auto-fixable
    """
    fixable_patterns = [
        "Missing return statement",
        "Function is missing a return type annotation",
        "Need type annotation for",
        "Incompatible return value type",
        "has no attribute",  # Often just needs TYPE_CHECKING import
    ]

    if not errors:
        return False

    fixable_count = sum(
        1 for error in errors if any(pattern in error for pattern in fixable_patterns)
    )

    return fixable_count >= len(errors) * 0.7  # 70%+ fixable


def generate_coverage_json(modules: list[ModuleCoverage], output_path: Path) -> None:
    """Write coverage report to JSON.

    Args:
        modules: List of module coverage data
        output_path: Where to write JSON report
    """
    total_modules = len(modules)
    clean_modules = sum(1 for m in modules if m.status == "clean")
    overall_coverage = (clean_modules / total_modules * 100) if total_modules > 0 else 0

    report = {
        "timestamp": datetime.now(UTC).isoformat() + "Z",
        "overall_coverage": round(overall_coverage, 2),
        "total_modules": total_modules,
        "clean_modules": clean_modules,
        "modules": {m.module_path: asdict(m) for m in modules},
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))
    logger.info(
        "coverage_json_written", path=str(output_path), coverage=overall_coverage
    )


def generate_roadmap_markdown(modules: list[ModuleCoverage], output_path: Path) -> None:
    """Generate Markdown roadmap document.

    Args:
        modules: List of module coverage data
        output_path: Where to write roadmap
    """
    # Group by priority
    by_priority = defaultdict(list)
    for mod in modules:
        by_priority[mod.priority].append(mod)

    # Calculate stats
    total = len(modules)
    clean = sum(1 for m in modules if m.status == "clean")
    overall_pct = (clean / total * 100) if total > 0 else 0

    lines = [
        "# L9 Type Coverage Roadmap",
        "",
        f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Current Status",
        "",
        f"- **Overall Coverage:** {overall_pct:.1f}% ({clean}/{total} modules clean)",
        f"- **CRITICAL tier:** {len([m for m in by_priority['critical'] if m.status == 'clean'])}/{len(by_priority['critical'])} clean",
        f"- **HIGH tier:** {len([m for m in by_priority['high'] if m.status == 'clean'])}/{len(by_priority['high'])} clean",
        f"- **MEDIUM tier:** {len([m for m in by_priority['medium'] if m.status == 'clean'])}/{len(by_priority['medium'])} clean",
        "",
    ]

    # Critical modules section
    if by_priority["critical"]:
        lines.append("## Phase 1: CRITICAL Modules")
        lines.append("")
        lines.append("**High-leverage modules imported by 20+ files:**")
        lines.append("")
        lines.append("| Module | Status | Errors | Imported By | Auto-Fix? |")
        lines.append("|--------|--------|--------|-------------|-----------|")

        for mod in sorted(by_priority["critical"], key=lambda m: m.error_count):
            status_emoji = (
                "✅"
                if mod.status == "clean"
                else "⚠️"
                if mod.status == "warning"
                else "❌"
            )
            auto_fix = "Yes ✅" if mod.auto_fixable else "No"
            lines.append(
                f"| `{mod.module_path}` | {status_emoji} {mod.status.upper()} | {mod.error_count} | {mod.imported_by_count} | {auto_fix} |"
            )
        lines.append("")

    # High priority section
    if by_priority["high"]:
        lines.append("## Phase 2: HIGH Priority Modules")
        lines.append("")
        lines.append("**Modules imported by 10-19 files:**")
        lines.append("")
        lines.append("| Module | Errors | Imported By | Auto-Fix? |")
        lines.append("|--------|--------|-------------|-----------|")

        for mod in sorted(by_priority["high"], key=lambda m: m.error_count):
            if mod.status != "clean":
                auto_fix = "Yes ✅" if mod.auto_fixable else "No"
                lines.append(
                    f"| `{mod.module_path}` | {mod.error_count} | {mod.imported_by_count} | {auto_fix} |"
                )
        lines.append("")

    # Auto-fix patterns
    all_errors = [err for mod in modules for err in mod.errors]
    missing_return_type = sum(1 for e in all_errors if "return type annotation" in e)
    any_usage = sum(1 for e in all_errors if "Any" in e or "type annotation" in e)

    lines.extend(
        [
            "## Common Auto-Fixable Patterns",
            "",
            f"1. **Missing return types:** {missing_return_type} occurrences",
            "   - **Fix:** Add `-> ReturnType` to function signatures",
            "",
            f"2. **Generic type annotations:** {any_usage} occurrences",
            "   - **Fix:** Replace `Any` with concrete types",
            "   - **Fix:** Add explicit type hints to variables",
            "",
            "3. **TYPE_CHECKING imports:** (common for avoiding circular imports)",
            "   - **Fix:** Use `if TYPE_CHECKING:` blocks per ADR-0002",
            "",
            "## Incremental Enforcement Strategy",
            "",
            "1. **Fix CRITICAL modules first** (highest ROI)",
            "2. **Update `.pre-commit-config.yaml`** to enforce on clean modules",
            "3. **Run:** `make type-coverage-update-precommit` after cleaning each module",
            "4. **Prevent regressions** via pre-commit hooks",
            "",
            "## Usage",
            "",
            "```bash",
            "# Generate this report",
            "make type-coverage",
            "",
            "# Update pre-commit with newly-cleaned modules",
            "make type-coverage-update-precommit",
            "",
            "# Check specific module",
            "mypy --config-file=pyproject.toml path/to/module.py",
            "```",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    logger.info("roadmap_written", path=str(output_path))


def update_precommit_config(clean_modules: list[str], precommit_path: Path) -> None:
    """Update .pre-commit-config.yaml with list of clean modules.

    Args:
        clean_modules: List of module paths with zero mypy errors
        precommit_path: Path to .pre-commit-config.yaml
    """
    if not precommit_path.exists():
        logger.error("precommit_not_found", path=str(precommit_path))
        return

    content = precommit_path.read_text()

    # Build regex pattern for clean modules
    # Format: ^(module1\.py|module2\.py|module3\.py)$
    pattern = (
        "^(" + "|".join(m.replace("/", "\\.") for m in clean_modules[:30]) + ")$"
    )  # Limit to 30 for readability

    # Find mypy hook and update files pattern
    lines = content.splitlines()
    new_lines = []
    in_mypy_hook = False

    for line in lines:
        if "id: mypy" in line:
            in_mypy_hook = True
        elif in_mypy_hook and line.strip().startswith("files:"):
            new_lines.append(f"        files: {pattern}")
            in_mypy_hook = False
            continue
        new_lines.append(line)

    precommit_path.write_text("\n".join(new_lines))
    logger.info("precommit_updated", clean_count=len(clean_modules))


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Track mypy type coverage across L9 repository"
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path("."), help="Repository root directory"
    )
    parser.add_argument(
        "--update-precommit",
        action="store_true",
        help="Update .pre-commit-config.yaml with clean modules",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    logger.info("analyzing_type_coverage", repo=str(repo_root))

    # Analyze imports
    logger.info("analyzing_imports")
    import_counts = analyze_imports(repo_root)

    # Scan all Python modules
    modules = []
    py_files = list(repo_root.rglob("*.py"))
    logger.info("scanning_modules", total=len(py_files))

    for py_file in py_files:
        # Skip tests and tooling
        rel_path = py_file.relative_to(repo_root)
        if any(
            part.startswith(("test_", "tests", "__pycache__", "."))
            for part in rel_path.parts
        ):
            continue

        # Run mypy
        error_count, errors = run_mypy_on_module(py_file)

        # Calculate metrics
        status = calculate_coverage_tier(error_count)
        imported_by = import_counts.get(str(rel_path), 0)
        priority = calculate_import_priority(imported_by)
        auto_fixable = detect_auto_fixable_errors(errors)

        modules.append(
            ModuleCoverage(
                module_path=str(rel_path),
                error_count=error_count,
                total_checks=1,  # Simplified
                status=status,
                errors=errors[:10],  # Limit to first 10
                imported_by_count=imported_by,
                priority=priority,
                auto_fixable=auto_fixable,
            )
        )

    logger.info("analysis_complete", modules=len(modules))

    # Generate outputs
    reports_dir = repo_root / "reports" / "type_coverage"
    generate_coverage_json(modules, reports_dir / "coverage.json")

    readme_dir = repo_root / "readme"
    generate_roadmap_markdown(modules, readme_dir / "TYPE_COVERAGE_ROADMAP.md")

    # Update pre-commit if requested
    if args.update_precommit:
        clean_modules = [m.module_path for m in modules if m.status == "clean"]
        update_precommit_config(clean_modules, repo_root / ".pre-commit-config.yaml")

    # Print summary
    total = len(modules)
    clean = sum(1 for m in modules if m.status == "clean")
    coverage_pct = (clean / total * 100) if total > 0 else 0

    print("\n✅ Type Coverage Analysis Complete")
    print(f"   Overall: {coverage_pct:.1f}% ({clean}/{total} modules)")
    print("   Report: reports/type_coverage/coverage.json")
    print("   Roadmap: readme/TYPE_COVERAGE_ROADMAP.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
