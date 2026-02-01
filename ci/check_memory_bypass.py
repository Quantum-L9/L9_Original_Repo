#!/usr/bin/env python3
"""
CI Check: Memory Pipeline Bypass Detection
==========================================

Detects code that bypasses the L9 memory governance pipeline by writing
directly to memory tables instead of using MemorySubstrateService.

GOVERNANCE RULE (GMP-129):
All memory writes MUST flow through MemorySubstrateService.write_packet()
to ensure:
- PacketEnvelope wrapping with governance metadata
- Row-level security (RLS) enforcement
- Embedding generation for semantic search
- Audit trail in packet_store
- Graph sync to Neo4j

PROHIBITED PATTERNS:
- INSERT INTO memory.* (legacy tables)
- INSERT INTO semantic_memory (MCP direct path)
- Direct writes to packet_store without substrate service
- Any SQL INSERT to memory tables without governance context

ALLOWED:
- MemorySubstrateService.write_packet()
- MemorySubstrateService.ingest_packet()
- Tests with explicit bypass marker: # MEMORY_BYPASS_ALLOWED: <reason>

Exit codes:
- 0: No bypass violations found
- 1: Bypass violations detected
- 2: Script error

Created: 2026-01-31
GMP: GMP-129 (Memory Pipeline Governance)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Patterns that indicate memory pipeline bypass
BYPASS_PATTERNS = [
    # Direct INSERT to legacy memory.* tables
    (
        r"INSERT\s+INTO\s+memory\.\w+",
        "Direct INSERT to memory.* tables bypasses governance pipeline",
    ),
    # Direct INSERT to semantic_memory
    (
        r"INSERT\s+INTO\s+semantic_memory",
        "Direct INSERT to semantic_memory bypasses PacketEnvelope governance",
    ),
    # Direct INSERT to packet_store (without substrate service context)
    (
        r"execute\s*\(\s*[\"']INSERT\s+INTO\s+packet_store",
        "Direct INSERT to packet_store should use MemorySubstrateService",
    ),
    # Direct INSERT to memory_embeddings
    (
        r"INSERT\s+INTO\s+memory_embeddings",
        "Direct INSERT to memory_embeddings bypasses embedding pipeline",
    ),
    # Shell subprocess patterns (GMP-130)
    # These bypass the Python async pipeline entirely
    (
        r"subprocess\.run\(.*psql.*INSERT\s+INTO",
        "Shell subprocess psql INSERT bypasses async governance pipeline",
    ),
    (
        r"docker.*exec.*psql.*INSERT\s+INTO",
        "Docker exec psql INSERT bypasses async governance pipeline",
    ),
]

# Allowed bypass marker (must include reason)
BYPASS_MARKER = r"#?\s*MEMORY_BYPASS_ALLOWED:\s*\S+"

# File-level bypass marker in docstring (allows entire file to bypass)
FILE_BYPASS_MARKER = r"MEMORY_BYPASS_ALLOWED:\s*\S+"

# Files/directories to skip
SKIP_PATTERNS = [
    r"migrations/",  # SQL migrations are allowed
    r"\.sql$",  # SQL files are infrastructure
    r"tests/.*fixtures",  # Test fixtures may need direct access
    r"scripts/memory/bootstrap",  # Bootstrap scripts set up tables
    r"__pycache__",
    r"\.pyc$",
    r"\.git/",
    r"ci/check_memory_bypass\.py$",  # This file itself
]

# Directories to scan
SCAN_DIRS = [
    "mcp_memory/src",
    "memory/",
    "api/",
    "core/",
    "services/",
    "runtime/",
    "agents/",
]


class BypassViolation:
    """Represents a memory bypass violation."""

    def __init__(self, file: Path, line_num: int, line: str, pattern: str, reason: str):
        self.file = file
        self.line_num = line_num
        self.line = line.strip()
        self.pattern = pattern
        self.reason = reason

    def __str__(self) -> str:
        return f"{self.file}:{self.line_num}: {self.reason}\n  → {self.line}"


def should_skip_file(filepath: Path) -> bool:
    """Check if file should be skipped based on skip patterns."""
    path_str = str(filepath)
    return any(re.search(pattern, path_str) for pattern in SKIP_PATTERNS)


def has_bypass_marker(line: str) -> bool:
    """Check if line has explicit bypass marker with reason."""
    return bool(re.search(BYPASS_MARKER, line))


def has_file_level_bypass(content: str) -> bool:
    """Check if file has file-level bypass marker (in docstring or header)."""
    # Check first 50 lines for file-level bypass
    header = "\n".join(content.split("\n")[:50])
    return bool(re.search(FILE_BYPASS_MARKER, header))


def check_file(filepath: Path) -> list[BypassViolation]:
    """Check a single file for bypass violations."""
    violations = []

    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return violations

    # Check for file-level bypass marker
    if has_file_level_bypass(content):
        return violations  # Entire file is bypassed

    lines = content.split("\n")

    for line_num, line in enumerate(lines, start=1):
        # Skip if line has bypass marker
        if has_bypass_marker(line):
            continue

        # Check for bypass patterns
        for pattern, reason in BYPASS_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                # Check if any of the previous 5 lines has a bypass marker
                has_nearby_marker = False
                for prev_offset in range(1, 6):
                    if line_num - prev_offset >= 1:
                        prev_line = lines[line_num - prev_offset - 1]
                        if has_bypass_marker(prev_line):
                            has_nearby_marker = True
                            break

                if has_nearby_marker:
                    continue  # Bypass marker found nearby

                violations.append(
                    BypassViolation(filepath, line_num, line, pattern, reason)
                )

    return violations


def scan_directory(base_path: Path, scan_dirs: list[str]) -> list[BypassViolation]:
    """Scan directories for bypass violations."""
    all_violations = []

    for scan_dir in scan_dirs:
        dir_path = base_path / scan_dir
        if not dir_path.exists():
            continue

        for filepath in dir_path.rglob("*.py"):
            if should_skip_file(filepath):
                continue

            violations = check_file(filepath)
            all_violations.extend(violations)

    return all_violations


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check for memory pipeline bypass violations"
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Base path of the repository",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show files being scanned"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  MEMORY PIPELINE BYPASS CHECK (GMP-129)")
    print("=" * 60)
    print()

    violations = scan_directory(args.base_path, SCAN_DIRS)

    if violations:
        print(f"❌ FAILED: Found {len(violations)} bypass violation(s):\n")
        for v in violations:
            print(f"  {v}\n")

        print("\n" + "=" * 60)
        print("HOW TO FIX:")
        print("=" * 60)
        print("""
1. Replace direct INSERT with MemorySubstrateService:

   # BEFORE (VIOLATION)
   await execute("INSERT INTO memory.long_term ...")

   # AFTER (CORRECT)
   from memory.substrate_service import get_substrate_service
   substrate = get_substrate_service()
   await substrate.write_packet(envelope)

2. If bypass is intentionally required (rare), add marker:

   # MEMORY_BYPASS_ALLOWED: Migration script for schema setup
   await execute("INSERT INTO memory.audit_log ...")

3. For tests, use test fixtures that mock the substrate service.
""")
        return 1
    print("✅ PASSED: No memory pipeline bypass violations found")
    print(f"   Scanned directories: {', '.join(SCAN_DIRS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
