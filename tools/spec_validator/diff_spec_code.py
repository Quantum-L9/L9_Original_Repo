#!/usr/bin/env python3
"""
Spec-Code Diff Validator

Compares Module-Spec YAML files against actual Python implementations to detect drift.

Usage:
    python tools/spec_validator/diff_spec_code.py
    python tools/spec_validator/diff_spec_code.py --spec services/research_factory/specs/quantum_kernel.yaml
    python tools/spec_validator/diff_spec_code.py --help

Part of GMP Phase 2 - Enhancement 4
"""

import argparse
import ast
import inspect
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import structlog
import yaml

logger = structlog.get_logger()


@dataclass
class Discrepancy:
    """Represents a mismatch between spec and code."""

    type: Literal[
        "missing_function", "signature_mismatch", "adr_violation", "extra_function"
    ]
    severity: Literal["critical", "high", "medium", "low"]
    spec_value: str
    actual_value: str
    file: str
    line: int
    fix_suggestion: str


def load_module_spec(spec_path: Path) -> dict[str, Any]:
    """Load Module-Spec YAML file.

    Args:
        spec_path: Path to YAML spec file

    Returns:
        Parsed spec dictionary
    """
    try:
        with open(spec_path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error("spec_load_failed", path=str(spec_path), error=str(e))
        return {}


def extract_function_signatures(module_path: Path) -> dict[str, inspect.Signature]:
    """Extract function signatures from Python module using AST.

    Args:
        module_path: Path to Python module

    Returns:
        Dict mapping function_name -> signature info
    """
    signatures = {}

    try:
        content = module_path.read_text()
        tree = ast.parse(content, filename=str(module_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Build signature string
                args = []
                for arg in node.args.args:
                    if arg.annotation:
                        args.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
                    else:
                        args.append(arg.arg)

                return_type = ast.unparse(node.returns) if node.returns else "None"

                sig_str = f"({', '.join(args)}) -> {return_type}"
                signatures[node.name] = sig_str

    except Exception as e:
        logger.error(
            "signature_extraction_failed", module=str(module_path), error=str(e)
        )

    return signatures


def compare_signatures(
    spec: dict[str, Any], actual_sigs: dict[str, str], module_path: Path
) -> list[Discrepancy]:
    """Compare spec signatures against actual code.

    Args:
        spec: Parsed YAML spec
        actual_sigs: Extracted function signatures
        module_path: Path to module for line number lookup

    Returns:
        List of discrepancies found
    """
    discrepancies = []

    # Get spec functions
    spec_functions = spec.get("functions", {})

    # Check for missing functions
    for func_name, func_spec in spec_functions.items():
        if func_name not in actual_sigs:
            discrepancies.append(
                Discrepancy(
                    type="missing_function",
                    severity="critical",
                    spec_value=f"{func_name}{func_spec.get('signature', '')}",
                    actual_value="NOT FOUND",
                    file=str(module_path),
                    line=0,
                    fix_suggestion=f"Implement {func_name} according to spec",
                )
            )
        else:
            # Check signature match
            spec_sig = func_spec.get("signature", "")
            actual_sig = actual_sigs[func_name]

            if spec_sig and spec_sig != actual_sig:
                discrepancies.append(
                    Discrepancy(
                        type="signature_mismatch",
                        severity="high",
                        spec_value=f"{func_name}{spec_sig}",
                        actual_value=f"{func_name}{actual_sig}",
                        file=str(module_path),
                        line=0,  # Would need full AST walk to get line number
                        fix_suggestion=f"Update {func_name} signature to match spec",
                    )
                )

    # Check for extra functions not in spec
    for func_name in actual_sigs:
        if func_name.startswith("_"):
            continue  # Skip private functions

        if func_name not in spec_functions:
            discrepancies.append(
                Discrepancy(
                    type="extra_function",
                    severity="low",
                    spec_value="NOT IN SPEC",
                    actual_value=f"{func_name}{actual_sigs[func_name]}",
                    file=str(module_path),
                    line=0,
                    fix_suggestion=f"Add {func_name} to spec or remove from code",
                )
            )

    return discrepancies


def check_adr_compliance(spec: dict[str, Any], module_path: Path) -> list[Discrepancy]:
    """Check if code follows ADRs specified in Module-Spec.

    Args:
        spec: Parsed YAML spec
        module_path: Path to module

    Returns:
        List of ADR violations
    """
    violations = []

    adr_refs = spec.get("adr_compliance", [])
    if not adr_refs:
        return violations

    content = module_path.read_text()

    # Check ADR-0019 (structlog)
    if "ADR-0019" in adr_refs or "0019" in adr_refs:
        if "import logging" in content and "import structlog" not in content:
            violations.append(
                Discrepancy(
                    type="adr_violation",
                    severity="critical",
                    spec_value="ADR-0019: Must use structlog",
                    actual_value="stdlib logging found",
                    file=str(module_path),
                    line=0,
                    fix_suggestion="Replace logging with structlog per ADR-0019",
                )
            )

    # Check ADR-0006 (PacketEnvelope)
    if "ADR-0006" in adr_refs or "0006" in adr_refs:
        if "PacketEnvelope" not in content:
            violations.append(
                Discrepancy(
                    type="adr_violation",
                    severity="high",
                    spec_value="ADR-0006: Must use PacketEnvelope",
                    actual_value="PacketEnvelope not found",
                    file=str(module_path),
                    line=0,
                    fix_suggestion="Use PacketEnvelope for data flow per ADR-0006",
                )
            )

    return violations


def generate_diff_report(discrepancies: list[Discrepancy], output_path: Path) -> None:
    """Generate JSON diff report.

    Args:
        discrepancies: List of found discrepancies
        output_path: Where to write report
    """
    report = {
        "total_discrepancies": len(discrepancies),
        "by_severity": {
            "critical": len([d for d in discrepancies if d.severity == "critical"]),
            "high": len([d for d in discrepancies if d.severity == "high"]),
            "medium": len([d for d in discrepancies if d.severity == "medium"]),
            "low": len([d for d in discrepancies if d.severity == "low"]),
        },
        "by_type": {
            "missing_function": len(
                [d for d in discrepancies if d.type == "missing_function"]
            ),
            "signature_mismatch": len(
                [d for d in discrepancies if d.type == "signature_mismatch"]
            ),
            "adr_violation": len(
                [d for d in discrepancies if d.type == "adr_violation"]
            ),
            "extra_function": len(
                [d for d in discrepancies if d.type == "extra_function"]
            ),
        },
        "discrepancies": [asdict(d) for d in discrepancies],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    import json

    output_path.write_text(json.dumps(report, indent=2))
    logger.info("diff_report_written", path=str(output_path))


def validate_spec_file(spec_path: Path, repo_root: Path) -> list[Discrepancy]:
    """Validate a single Module-Spec file against implementation.

    Args:
        spec_path: Path to YAML spec
        repo_root: Repository root

    Returns:
        List of discrepancies
    """
    logger.info("validating_spec", spec=str(spec_path))

    # Load spec
    spec = load_module_spec(spec_path)
    if not spec or not isinstance(spec, dict):
        return []

    # Find corresponding Python module
    module_rel_path = spec.get("module_path", "")
    if not module_rel_path:
        logger.warning("no_module_path_in_spec", spec=str(spec_path))
        return []

    module_path = repo_root / module_rel_path
    if not module_path.exists():
        return [
            Discrepancy(
                type="missing_function",
                severity="critical",
                spec_value=module_rel_path,
                actual_value="FILE NOT FOUND",
                file=module_rel_path,
                line=0,
                fix_suggestion=f"Create module at {module_rel_path}",
            )
        ]

    # Extract signatures
    actual_sigs = extract_function_signatures(module_path)

    # Compare
    discrepancies = []
    discrepancies.extend(compare_signatures(spec, actual_sigs, module_path))
    discrepancies.extend(check_adr_compliance(spec, module_path))

    return discrepancies


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Module-Spec YAML files against code implementations"
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path("."), help="Repository root directory"
    )
    parser.add_argument("--spec", type=Path, help="Validate specific spec file")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    output_dir = repo_root / "reports" / "spec_drift"

    # Find all spec files
    if args.spec:
        spec_files = [args.spec]
    else:
        spec_files = list(repo_root.rglob("**/specs/*.yaml"))
        spec_files.extend(repo_root.rglob("**/spec/*.yaml"))

    logger.info("validating_specs", count=len(spec_files))

    # Validate all specs
    all_discrepancies = []
    for spec_file in spec_files:
        discrepancies = validate_spec_file(spec_file, repo_root)
        all_discrepancies.extend(discrepancies)

    # Generate report
    if all_discrepancies:
        generate_diff_report(all_discrepancies, output_dir / "drift_report.json")

        # Print summary
        critical = sum(1 for d in all_discrepancies if d.severity == "critical")
        high = sum(1 for d in all_discrepancies if d.severity == "high")

        print("\n⚠️  Spec Drift Detected")
        print(f"   Total discrepancies: {len(all_discrepancies)}")
        print(f"   Critical: {critical}")
        print(f"   High: {high}")
        print(f"   Report: {output_dir / 'drift_report.json'}")

        if critical > 0:
            return 1
    else:
        print("\n✅ All specs match implementations")
        print(f"   Validated {len(spec_files)} spec files")

    return 0


if __name__ == "__main__":
    sys.exit(main())
