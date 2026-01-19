#!/usr/bin/env python3
"""
CI Gate: Schema Deprecation Enforcement

Ensures deprecated PacketEnvelope schemas are not used in new code.
Enforces migration to core.schemas.packet_envelope_v2.

Architecture (GMP-74):
- PacketEnvelope, PacketEnvelopeIn, etc. → core.schemas.packet_envelope_v2
- PacketStoreRow, KnowledgeFact, etc. → memory.substrate_models (NOT deprecated)

This checker looks for:
1. Imports of PacketEnvelope from memory.substrate_models (will error - class removed)
2. Imports from core.schemas.packet_envelope (old v1 location, use v2)

Usage:
    python ci/check_schema_deprecation.py [--strict] [--phase N]

Options:
    --strict    Fail on any deprecated import (regardless of phase)
    --phase N   Override auto-detected phase (1-4)
    --fix-hint  Show migration hints for each violation

Exit codes:
    0 = Pass
    1 = Fail (deprecated imports found)
    2 = Error (script failure)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Check Schema Deprecation",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T15:07:54Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "check_schema_deprecation",
    "type": "cli",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import structlog
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

# =============================================================================
# Configuration
# =============================================================================


logger = structlog.get_logger(__name__)
PROJECT_ROOT = Path(__file__).parent.parent

# Deprecated import patterns (regex)
# NOTE: memory.substrate_models is NOT deprecated - it contains valid DB DTOs
# Only PacketEnvelope-related imports from there are deprecated (and removed as of GMP-74)
DEPRECATED_PATTERNS = [
    # PacketEnvelope from old locations (these will actually ImportError now)
    r"from\s+memory\.substrate_models\s+import\s+.*PacketEnvelope",
    r"from\s+memory\.substrate_models\s+import\s+.*PacketEnvelopeIn",
    r"from\s+memory\.substrate_models\s+import\s+.*PacketWriteResult",
    r"from\s+memory\.substrate_models\s+import\s+.*SemanticSearchRequest",
    r"from\s+memory\.substrate_models\s+import\s+.*SemanticHit",
    # Imports from old v1 location (use v2)
    r"from\s+core\.schemas\.packet_envelope\s+import",
    r"import\s+core\.schemas\.packet_envelope\b(?!_v2)",
    # Any reference to old schema versions
    r"PacketEnvelope.*schema_version.*['\"]1\.[0-1]\.[0-9]['\"]",
]

# Canonical import (what they should use)
CANONICAL_IMPORT = "from core.schemas import PacketEnvelope"

# Files/directories to exclude from checking
EXCLUDE_PATTERNS = [
    "archive/",
    "_archived/",
    "tests/",  # Tests may intentionally test deprecated paths
    "__pycache__/",
    ".git/",
    "venv/",
    ".venv/",
    "node_modules/",
    # The deprecated files themselves (they have legitimate self-references)
    "memory/substrate_models.py",
    "core/schemas/packet_envelope.py",
    # The v2 schema and registry (they import for migration)
    "core/schemas/packet_envelope_v2.py",
    "core/schemas/schema_registry.py",
    # CI scripts
    "ci/",
    # Docs
    "docs/",
    "reports/",
    # Work in progress
    "current_work/",
    # Audit snapshots (point-in-time copies)
    "igor/audit-memory/",
    # Code generation (templates, not production code)
    "codegen/",
]

# Sunset dates
DEPRECATION_DATE = datetime(2026, 1, 5)
SUNSET_WARNING_DATE = datetime(2026, 2, 20)  # Day 45
WRITE_BLOCK_DATE = datetime(2026, 3, 22)  # Day 75
READ_BLOCK_DATE = datetime(2026, 4, 5)  # Day 90


# =============================================================================
# Data Structures
# =============================================================================


class Violation(NamedTuple):
    """A single deprecated import violation."""

    file: Path
    line_number: int
    line_content: str
    pattern_matched: str


# =============================================================================
# Phase Detection
# =============================================================================


def get_current_phase() -> int:
    """
    Determine current enforcement phase based on date.

    Phase 1: Warnings only (deprecation announced)
    Phase 2: Errors in new files (sunset warning)
    Phase 3: Errors for all writes
    Phase 4: Complete block (migration required)
    """
    now = datetime.now()

    if now >= READ_BLOCK_DATE:
        return 4
    elif now >= WRITE_BLOCK_DATE:
        return 3
    elif now >= SUNSET_WARNING_DATE:
        return 2
    else:
        return 1


def get_phase_description(phase: int) -> str:
    """Get human-readable phase description."""
    descriptions = {
        1: "Phase 1 (Warnings): Deprecated imports logged, no failures",
        2: "Phase 2 (Sunset): Errors in new files, warnings in existing",
        3: "Phase 3 (Write Block): Errors for all deprecated imports",
        4: "Phase 4 (Read Block): Complete migration required",
    }
    return descriptions.get(phase, f"Unknown phase {phase}")


# =============================================================================
# File Scanning
# =============================================================================


def should_exclude(path: Path) -> bool:
    """Check if path should be excluded from scanning."""
    path_str = str(path)
    return any(excl in path_str for excl in EXCLUDE_PATTERNS)


def find_python_files() -> list[Path]:
    """Find all Python files in the project."""
    files = []
    for path in PROJECT_ROOT.rglob("*.py"):
        if not should_exclude(path):
            files.append(path)
    return sorted(files)


def scan_file(file_path: Path) -> list[Violation]:
    """Scan a single file for deprecated imports."""
    violations = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return violations

    lines = content.split("\n")

    for line_num, line in enumerate(lines, start=1):
        for pattern in DEPRECATED_PATTERNS:
            if re.search(pattern, line):
                violations.append(
                    Violation(
                        file=file_path,
                        line_number=line_num,
                        line_content=line.strip(),
                        pattern_matched=pattern,
                    )
                )
                break  # Only report once per line

    return violations


# =============================================================================
# Reporting
# =============================================================================


def print_violation(v: Violation, show_hint: bool = False) -> None:
    """Print a single violation."""
    rel_path = v.file.relative_to(PROJECT_ROOT)
    logger.info(f"  {rel_path}:{v.line_number}")
    logger.info(f"    {v.line_content}")

    if show_hint:
        logger.info(f"    💡 Replace with: {CANONICAL_IMPORT}")
    logger.info("")


def print_summary(
    violations: list[Violation],
    phase: int,
    strict: bool,
    show_hints: bool,
) -> None:
    """Print scan summary."""
    logger.info("=" * 70)
    logger.info("L9 Schema Deprecation Check")
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"Phase: {get_phase_description(phase)}")
    logger.info(f"Mode: {'STRICT' if strict else 'Normal'}")
    logger.info(f"Files scanned: {len(find_python_files())}")
    logger.info(f"Violations found: {len(violations)}")
    logger.info("")

    if violations:
        logger.info("Deprecated PacketEnvelope imports found:")
        logger.info("-" * 40)
        logger.info("")

        for v in violations:
            print_violation(v, show_hints)

        logger.info("-" * 40)
        logger.info("")
        logger.info("Migration required:")
        logger.info(
            "  ❌ Old: from memory.substrate_models import PacketEnvelope  # REMOVED in GMP-74"
        )
        logger.info(
            "  ❌ Old: from core.schemas.packet_envelope import PacketEnvelope  # Use v2"
        )
        logger.info(f"  ✅ New: {CANONICAL_IMPORT}")
        logger.info("")
        logger.info("Note: memory.substrate_models is NOT deprecated for:")
        logger.info("  PacketStoreRow, KnowledgeFact, ExtractedInsight, etc. (DB DTOs)")
        logger.info("")
        logger.info("For read operations with legacy data, use:")
        logger.info("  from core.schemas.schema_registry import read_packet")
        logger.info("  packet = read_packet(raw_dict)  # Auto-upcasts to v2.0.0")
        logger.info("")
    else:
        logger.info("✅ No deprecated imports found!")
        logger.info("")


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check for deprecated PacketEnvelope schema imports"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any deprecated import (regardless of phase)",
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4],
        help="Override auto-detected phase",
    )
    parser.add_argument(
        "--fix-hint",
        action="store_true",
        help="Show migration hints for each violation",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output on failure",
    )

    args = parser.parse_args()

    # Determine phase
    phase = args.phase if args.phase else get_current_phase()

    # Scan files
    violations = []
    for file_path in find_python_files():
        violations.extend(scan_file(file_path))

    # Determine pass/fail
    should_fail = False

    if args.strict:
        # Strict mode: any violation is a failure
        should_fail = len(violations) > 0
    else:
        # Phase-based enforcement
        if phase >= 3:
            # Phase 3+: All violations are errors
            should_fail = len(violations) > 0
        elif phase == 2:
            # Phase 2: Only new files cause errors (not implemented yet)
            # For now, treat as warning
            should_fail = False
        else:
            # Phase 1: Warnings only
            should_fail = False

    # Output
    if not args.quiet or violations:
        print_summary(violations, phase, args.strict, args.fix_hint)

    if should_fail:
        logger.error("❌ CI GATE FAILED: Deprecated schema imports must be migrated")
        logger.info("")
        logger.info(f"Sunset deadline: {READ_BLOCK_DATE.strftime('%Y-%m-%d')}")
        logger.info("")
        return 1
    elif violations:
        logger.warning("⚠️  WARNINGS: Deprecated imports found (not blocking yet)")
        logger.error(
            f"   These will become errors on {WRITE_BLOCK_DATE.strftime('%Y-%m-%d')}"
        )
        logger.info("")
        return 0
    else:
        if not args.quiet:
            logger.info("✅ CI GATE PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "caching",
        "ci",
        "cli",
        "filesystem",
        "logging",
        "migration",
        "operations",
        "testing",
    ],
    "keywords": [
        "check",
        "current",
        "deprecation",
        "description",
        "exclude",
        "files",
        "find",
        "phase",
    ],
    "business_value": "1. Imports of PacketEnvelope from memory.substrate_models (will error - class removed) 2. Imports from core.schemas.packet_envelope (old v1 location, use v2) python ci/check_schema_deprecation.py [--s",
    "last_modified": "2026-01-14T15:03:00Z",
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
