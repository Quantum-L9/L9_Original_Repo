#!/usr/bin/env python3
"""
CodeGenAgent CLI
================

Command-line interface for L9 code generation from YAML specifications.

Usage:
    python -m agents.codegenagent generate <spec_path> [--dry-run]
    python -m agents.codegenagent preview <spec_path>
    python -m agents.codegenagent batch <specs_dir> [--dry-run]
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "  Main  ",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-16T00:17:23Z",
    "updated_at": "2026-01-16T00:17:23Z",
    "layer": "intelligence",
    "domain": "agent_execution",
    "module_name": "__main__",
    "type": "service",
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
import asyncio
import sys
from pathlib import Path

import structlog

from agents.codegenagent.codegen_agent import CodeGenAgent

logger = structlog.get_logger(__name__)


async def cmd_generate(args: argparse.Namespace) -> int:
    """Generate code from a spec file."""
    agent = CodeGenAgent()

    spec_path = Path(args.spec_path)
    if not spec_path.exists():
        print(f"❌ Spec file not found: {spec_path}")  # noqa: ADR-0019
        return 1

    print(f"🔧 Generating code from: {spec_path}")  # noqa: ADR-0019
    print(f"   Dry run: {args.dry_run}")  # noqa: ADR-0019
    print()  # noqa: ADR-0019

    result = await agent.generate_from_meta(str(spec_path), dry_run=args.dry_run)

    if result.success:
        print("✅ Generation successful!")  # noqa: ADR-0019
        print(f"   Module: {result.module_id}")  # noqa: ADR-0019
        print(f"   Files created: {len(result.files_created)}")  # noqa: ADR-0019
        for f in result.files_created:
            print(f"      + {f}")  # noqa: ADR-0019
        print(f"   Files modified: {len(result.files_modified)}")  # noqa: ADR-0019
        for f in result.files_modified:
            print(f"      ~ {f}")  # noqa: ADR-0019
        if result.duration_ms:
            print(f"   Duration: {result.duration_ms:.0f}ms")  # noqa: ADR-0019
        return 0
    print("❌ Generation failed!")  # noqa: ADR-0019
    print(f"   Module: {result.module_id}")  # noqa: ADR-0019
    for error in result.errors:
        print(f"   Error: {error}")  # noqa: ADR-0019
    return 1


async def cmd_preview(args: argparse.Namespace) -> int:
    """Preview what would be generated (dry run)."""
    agent = CodeGenAgent()

    spec_path = Path(args.spec_path)
    if not spec_path.exists():
        print(f"❌ Spec file not found: {spec_path}")  # noqa: ADR-0019
        return 1

    print(f"👁️  Previewing generation from: {spec_path}")  # noqa: ADR-0019
    print()  # noqa: ADR-0019

    result = await agent.preview(str(spec_path))

    print(f"Module: {result.module_id}")  # noqa: ADR-0019
    print(f"Validation: {'✅ Passed' if result.validation_passed else '❌ Failed'}")  # noqa: ADR-0019

    if result.validation_errors:
        print("\nValidation Errors:")  # noqa: ADR-0019
        for error in result.validation_errors:
            print(f"  - {error}")  # noqa: ADR-0019

    if result.files_to_create:
        print(f"\nFiles to create ({len(result.files_to_create)}):")  # noqa: ADR-0019
        for f in result.files_to_create:
            print(f"  + {f}")  # noqa: ADR-0019

    if result.files_to_modify:
        print(f"\nFiles to modify ({len(result.files_to_modify)}):")  # noqa: ADR-0019
        for f in result.files_to_modify:
            print(f"  ~ {f}")  # noqa: ADR-0019

    if result.generated_code:
        print(f"\nGenerated code preview ({len(result.generated_code)} files):")  # noqa: ADR-0019
        for path, code in result.generated_code.items():
            lines = len(code.split("\n"))
            print(f"  {path}: {lines} lines")  # noqa: ADR-0019

    return 0 if result.validation_passed else 1


async def cmd_batch(args: argparse.Namespace) -> int:
    """Generate code from all specs in a directory."""
    agent = CodeGenAgent()

    specs_dir = Path(args.specs_dir)
    if not specs_dir.exists():
        print(f"❌ Specs directory not found: {specs_dir}")  # noqa: ADR-0019
        return 1

    spec_files = list(specs_dir.glob("*.yaml"))
    if not spec_files:
        print(f"❌ No .yaml files found in: {specs_dir}")  # noqa: ADR-0019
        return 1

    print(f"🔧 Batch generating from {len(spec_files)} specs in: {specs_dir}")  # noqa: ADR-0019
    print(f"   Dry run: {args.dry_run}")  # noqa: ADR-0019
    print()  # noqa: ADR-0019

    results = await agent.generate_batch(str(specs_dir), dry_run=args.dry_run)

    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count

    print("\n📊 Batch Results:")  # noqa: ADR-0019
    print(f"   Success: {success_count}/{len(results)}")  # noqa: ADR-0019
    print(f"   Failed: {fail_count}/{len(results)}")  # noqa: ADR-0019

    for result in results:
        status = "✅" if result.success else "❌"
        print(f"   {status} {result.module_id}")  # noqa: ADR-0019
        if not result.success:
            for error in result.errors[:2]:  # Show first 2 errors
                print(f"      Error: {error}")  # noqa: ADR-0019

    return 0 if fail_count == 0 else 1


def main():
    """
    Main entry point for the CodeGenAgent CLI, orchestrating code generation commands from YAML specifications.

    Args:
        None

    Returns:
        None

    Raises:
        SystemExit: If argument parsing fails or required arguments are missing.
    """
    parser = argparse.ArgumentParser(
        description="L9 CodeGen Agent - Generate code from YAML specifications"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate command
    gen_parser = subparsers.add_parser(
        "generate", help="Generate code from a spec file"
    )
    gen_parser.add_argument("spec_path", help="Path to YAML spec file")
    gen_parser.add_argument(
        "--dry-run", action="store_true", help="Preview without writing files"
    )

    # preview command
    preview_parser = subparsers.add_parser(
        "preview", help="Preview generation (dry run with details)"
    )
    preview_parser.add_argument("spec_path", help="Path to YAML spec file")

    # batch command
    batch_parser = subparsers.add_parser(
        "batch", help="Generate from all specs in a directory"
    )
    batch_parser.add_argument(
        "specs_dir", help="Path to directory containing spec files"
    )
    batch_parser.add_argument(
        "--dry-run", action="store_true", help="Preview without writing files"
    )

    args = parser.parse_args()

    if args.command == "generate":
        return asyncio.run(cmd_generate(args))
    if args.command == "preview":
        return asyncio.run(cmd_preview(args))
    if args.command == "batch":
        return asyncio.run(cmd_batch(args))
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["agents.codegenagent.codegen_agent"],
    "tags": [
        "agent-execution",
        "async",
        "batch-processing",
        "cli",
        "config",
        "filesystem",
        "intelligence",
        "logging",
        "service",
    ],
    "keywords": ["batch", "cmd", "generate", "preview"],
    "business_value": "Utility module for   main  ",
    "last_modified": "2026-01-16T00:17:23Z",
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
