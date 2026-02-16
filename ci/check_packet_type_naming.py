#!/usr/bin/env python3
"""
L9 Packet Type Naming Linter
============================

Ensures PacketEnvelope-related code uses `packet_type` instead of `kind`.

Background:
- PacketEnvelope.packet_type is the canonical field (v2.0.0)
- `kind` was used in early code but is incorrect for PacketEnvelope
- `kind` IS valid in:
  - Memory API payloads (content type: preference, fact, etc.)
  - VectorHit dataclass (separate model)
  - Task/strategy objects (task_kind is different concept)

This CI check prevents regression to the old `kind` naming in packet contexts.

Usage:
    python ci/check_packet_type_naming.py              # Check all files
    python ci/check_packet_type_naming.py path/to/file.py  # Check specific file

Exit codes:
    0 - All checks pass
    1 - Violations found
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Check Packet Type Naming",
    "module_version": "1.0.0",
    "created_by": "L9 Agent",
    "created_at": "2026-01-26T00:00:00Z",
    "updated_at": "2026-01-26T00:00:00Z",
    "layer": "operations",
    "domain": "ci",
    "module_name": "check_packet_type_naming",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

import structlog

logger = structlog.get_logger(__name__)


class Violation(NamedTuple):
    """A single violation found in the code."""

    file: Path
    line_num: int
    line: str
    pattern: str
    message: str


# Patterns that indicate incorrect `kind` usage in packet contexts
# Each tuple: (regex_pattern, error_message, suggestion)
FORBIDDEN_PATTERNS = [
    # PacketEnvelope field access using .kind
    (
        r"packet\.kind\b",
        "Use packet.packet_type instead of packet.kind",
        "packet.packet_type",
    ),
    # PacketEnvelope constructor with kind=
    (
        r"PacketEnvelope\s*\([^)]*\bkind\s*=",
        "PacketEnvelope uses packet_type=, not kind=",
        "PacketEnvelope(..., packet_type=...)",
    ),
    (
        r"PacketEnvelopeIn\s*\([^)]*\bkind\s*=",
        "PacketEnvelopeIn uses packet_type=, not kind=",
        "PacketEnvelopeIn(..., packet_type=...)",
    ),
    # Validator REQUIRED_FIELDS with kind
    (
        r'REQUIRED_FIELDS\s*=\s*\[[^\]]*["\']kind["\']',
        "PacketEnvelope required field is packet_type, not kind",
        'REQUIRED_FIELDS = [..., "packet_type", ...]',
    ),
    # hasattr checks for kind on packets
    (
        r'hasattr\s*\(\s*packet\s*,\s*["\']kind["\']\s*\)',
        "Check for packet_type attribute, not kind",
        'hasattr(packet, "packet_type")',
    ),
    # envelope dict with "kind" key for packet type
    (
        r'"envelope"\s*:\s*\{[^}]*"kind"\s*:\s*"(?:MEMORY|REASONING|TOOL|DECISION|EVENT)"',
        'Envelope dict should use "packet_type", not "kind"',
        '{"envelope": {..., "packet_type": "..."}}',
    ),
]

# Files/directories to skip
SKIP_PATTERNS = [
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    ".pytest_cache",
    "build",
    "dist",
    "*.egg-info",
    "ci/check_packet_type_naming.py",  # This script
    "current_work/DONE",
    "docs/DONE",
    "codegen/extractions/",  # Archived extraction snapshots
    "codegen",
]

# Directories to always skip (not packet-related)
SKIP_DIRECTORIES = [
    "mcp_memory/src/routes/memory.py",  # Uses kind for content type (different concept)
    "mcp_memory/src/routes/memory_unified.py",  # Uses kind for content type
    "mcp_memory/src/mcp_server.py",  # Uses kind for content type
    "agents/cursor/cursor_memory_client.py",  # Uses kind for content type
]

# Line patterns to allow (these are legitimate uses of 'kind')
ALLOW_PATTERNS = [
    # Memory content type (different from packet_type)
    r'"kind"\s*:\s*"(?:preference|fact|context|error|success|note)"',
    r"'kind'\s*:\s*'(?:preference|fact|context|error|success|note)'",
    # task_kind is a different concept
    r"\btask_kind\b",
    # VectorHit.kind is a different model
    r"hit\.kind\b",
    r"VectorHit.*kind",
    # Comments/docstrings explaining kind
    r"#.*\bkind\b",
    r'""".*\bkind\b',
    r"'''.*\bkind\b",
    # PacketKind enum (valid)
    r"\bPacketKind\b",
    # Imports
    r"from.*import.*kind",
    r"import.*kind",
]


def should_skip_path(path: Path) -> bool:
    """Check if path should be skipped."""
    path_str = str(path)
    for pattern in SKIP_PATTERNS:
        if pattern in path_str:
            return True
    return any(path_str.endswith(skip_dir) for skip_dir in SKIP_DIRECTORIES)


def is_allowed_usage(line: str) -> bool:
    """Check if the line contains an allowed usage of 'kind'."""
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in ALLOW_PATTERNS)


def check_file(file_path: Path) -> list[Violation]:
    """Check a single file for violations."""
    violations: list[Violation] = []

    if not file_path.exists():
        return violations

    if should_skip_path(file_path):
        return violations

    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return violations

    lines = content.splitlines()

    for line_num, line in enumerate(lines, start=1):
        # Skip allowed usages
        if is_allowed_usage(line):
            continue

        # Check each forbidden pattern
        for pattern, message, suggestion in FORBIDDEN_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append(
                    Violation(
                        file=file_path,
                        line_num=line_num,
                        line=line.strip(),
                        pattern=pattern,
                        message=f"{message}. Suggestion: {suggestion}",
                    )
                )

    return violations


def find_python_files(root: Path) -> list[Path]:
    """Find all Python files under root."""
    files = []
    for path in root.rglob("*.py"):
        if not should_skip_path(path):
            files.append(path)
    return files


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check for incorrect 'kind' usage in PacketEnvelope code"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to check (default: entire repo)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output",
    )
    args = parser.parse_args()

    # Determine paths to check
    paths = [Path(p) for p in args.paths] if args.paths else [Path.cwd()]  # noqa: ADR-0001 - internal path

    # Collect all Python files
    all_files: list[Path] = []
    for path in paths:
        if path.is_file():
            all_files.append(path)
        elif path.is_dir():
            all_files.extend(find_python_files(path))

    # Check all files
    all_violations: list[Violation] = []
    for file_path in all_files:
        violations = check_file(file_path)
        all_violations.extend(violations)

    # Report results
    if all_violations:
        logger.info("\n❌ packet type naming violations found\n")
        logger.info("packetenvelope uses 'packet_type', not 'kind'.")
        logger.info("=" * 60)

        for v in all_violations:
            logger.info("\n{v.file}:{v.line_num}")
            logger.info("  line: {v.line[:80]}{'...' if len(v.line) > 80 else ''}")
            logger.info("  issue: {v.message}")

        logger.info("\n\ntotal violations: {len(all_violations)}")
        logger.info("\nfix these before merging to prevent packet schema confusion.")
        return 1
    if args.verbose:
        logger.info(
            "✅ checked {len(all_files)} files - no packet_type naming violations"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CI-LINT-042",
    "governance_level": "standard",
    "compliance_required": True,
    "audit_trail": False,
    "dependencies": [],
    "tags": [
        "ci",
        "linter",
        "packet-envelope",
        "schema",
        "validation",
    ],
    "keywords": [
        "kind",
        "packet_type",
        "PacketEnvelope",
        "naming",
        "convention",
    ],
    "business_value": "Prevents regression to incorrect 'kind' field name in PacketEnvelope code",
    "last_modified": "2026-01-26T00:00:00Z",
    "modified_by": "L9_Agent",
    "change_summary": "Initial creation - enforce packet_type naming",
}
# ============================================================================
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
