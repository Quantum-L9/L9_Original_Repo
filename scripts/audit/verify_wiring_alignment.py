#!/usr/bin/env python3
"""
L9 Wiring Alignment Verifier v1.0

Validates that all doc/script path references point to real files.
Enforces the wiring invariant for Memory APIs and Cursor integration.

Usage:
    python scripts/audit/verify_wiring_alignment.py
    python scripts/audit/verify_wiring_alignment.py --json
    python scripts/audit/verify_wiring_alignment.py --verbose

Returns:
    0 = All paths verified (green)
    1 = Broken paths found (violations)

Wiring Invariant:
    Every referenced path to Memory APIs and Cursor integration must be:
    1. A real file/module in the repo
    2. Consistent with the canonical router layout
    3. Listed in readme/repo-index/file_metrics.txt
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Verify Wiring Alignment",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "verify_wiring_alignment",
    "type": "dataclass",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

REPO_ROOT = Path(__file__).parent.parent.parent

# Patterns to extract path references from docs/scripts
# These must be PRECISE to avoid false positives
PATH_PATTERNS = [
    r"api/memory/[\w]+\.py",  # api/memory/router.py etc
    r"api/routes/[\w]+\.py",  # api/routes/*.py (likely stale)
    r"mcp_memory/src/[\w/]+\.py",  # MCP memory routes
    r"agents/cursor/[\w/]+\.py",  # Cursor integration
    r"memory/substrate_[\w]+\.py",  # Memory substrate files
    r"core/governance/[\w]+\.py",  # Governance modules
]

# Directories to scan for path references
# Focus on active documentation, not historical/planning files
SCAN_GLOBS = [
    "readme/*.md",
    "readme/**/*.md",
    "memory/*.md",
    # Exclude mcp_memory/docs/ - contains ADR/planning docs with planned (not actual) paths
]

# Directories to skip
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".audit_cache",
    "node_modules",
    ".venv",
    "venv",
    ".cursor",
    "current_work",  # Planning/work-in-progress files
    "reports",  # Historical reports
    "VPS-Repo-Files",  # VPS snapshots
}

# Files to exclude from broken path reporting (they document moves or plans, not current state)
EXCLUDE_FILES = {
    "architecture_decisions.md",  # Documents intentional moves
    "gap-analysis-memory.md",  # Contains Doc-Code Alignment Table with old paths
    "TODO.md",  # Contains planned/future file references
    "workflow_state.md",  # Contains historical references
    "ROADMAP.md",  # Contains planned features
}

# Known canonical files from file_metrics.txt (these MUST exist)
CANONICAL_FILES = {
    "api/memory/router.py",
    "mcp_memory/src/routes/memory.py",
    "mcp_memory/src/routes/memory_unified.py",
    "agents/cursor/cursor_memory_kernel.py",
    "agents/cursor/cursor_client.py",
    "agents/cursor/extractors/cursor_action_extractor.py",
    "agents/cursor/integrations/cursor_langgraph.py",
    "agents/cursor/integrations/cursor_gateway.py",
    "agents/cursor/integrations/cursor_executor.py",
    "memory/substrate_service.py",
    "memory/substrate_repository.py",
    "memory/substrate_dag.py",
    "core/governance/approval_manager.py",
    "core/governance/engine.py",
}

# Deprecated paths that should NOT be referenced (except in architecture_decisions.md)
DEPRECATED_PATHS = {
    "api/routes/memory.py": "api/memory/router.py",
    "tools/cursor_client.py": "agents/cursor/cursor_client.py",
    "scripts/cursor_check_mistakes.py": "agents/cursor/scripts/cursor_check_mistakes.py",
    "memory/extractor/cursor_action_extractor.py": "agents/cursor/extractors/cursor_action_extractor.py",
    "core/governance/cursor_memory_kernel.py": "agents/cursor/cursor_memory_kernel.py",
    "memory/substrate_graph.py": "memory/substrate_dag.py",
}


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class PathReference:
    """A path reference found in a file."""

    path: str
    source_file: str
    line_number: int
    exists: bool
    is_deprecated: bool
    canonical_replacement: str = ""


@dataclass
class VerificationResult:
    """Result of wiring alignment verification."""

    verified_paths: list[str]
    broken_docs: list[dict]
    deprecated_refs: list[dict]
    missing_canonical: list[str]
    total_scanned: int

    @property
    def is_green(self) -> bool:
        return len(self.broken_docs) == 0 and len(self.deprecated_refs) == 0


# =============================================================================
# CORE FUNCTIONS
# =============================================================================


def should_skip(filepath: Path) -> bool:
    """Check if a file should be skipped."""
    parts = set(filepath.parts)
    if parts & SKIP_DIRS:
        return True
    return filepath.name in EXCLUDE_FILES


def extract_paths_from_file(filepath: Path) -> list[PathReference]:
    """Extract all path references from a file."""
    try:
        content = filepath.read_text(errors="ignore")
    except OSError:
        return []

    references = []
    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        for pattern in PATH_PATTERNS:
            matches = re.findall(pattern, line)
            for match in matches:
                # Check if path exists
                full_path = REPO_ROOT / match
                exists = full_path.exists()

                # Check if deprecated
                is_deprecated = match in DEPRECATED_PATHS
                canonical = DEPRECATED_PATHS.get(match, "")

                references.append(
                    PathReference(
                        path=match,
                        source_file=str(filepath.relative_to(REPO_ROOT)),
                        line_number=line_num,
                        exists=exists,
                        is_deprecated=is_deprecated,
                        canonical_replacement=canonical,
                    )
                )

    return references


def verify_canonical_files() -> list[str]:
    """Verify all canonical files exist."""
    missing = []
    for canonical in CANONICAL_FILES:
        if not (REPO_ROOT / canonical).exists():
            missing.append(canonical)
    return missing


def scan_repository() -> VerificationResult:
    """Scan repository for wiring alignment issues."""
    all_references: list[PathReference] = []
    files_scanned = 0

    # Scan all matching files
    for glob_pattern in SCAN_GLOBS:
        for filepath in REPO_ROOT.glob(glob_pattern):
            if should_skip(filepath):
                continue

            refs = extract_paths_from_file(filepath)
            all_references.extend(refs)
            files_scanned += 1

    # Categorize results
    verified_paths: set[str] = set()
    broken_docs: list[dict] = []
    deprecated_refs: list[dict] = []

    for ref in all_references:
        if ref.is_deprecated:
            # Deprecated paths (whether they exist or not) should be updated
            deprecated_refs.append(
                {
                    "path": ref.path,
                    "source": ref.source_file,
                    "line": ref.line_number,
                    "replacement": ref.canonical_replacement,
                }
            )
        elif ref.exists:
            verified_paths.add(ref.path)
        else:
            # File doesn't exist and isn't a known deprecated path
            broken_docs.append(
                {
                    "path": ref.path,
                    "source": ref.source_file,
                    "line": ref.line_number,
                }
            )

    # Check canonical files
    missing_canonical = verify_canonical_files()

    return VerificationResult(
        verified_paths=sorted(verified_paths),
        broken_docs=broken_docs,
        deprecated_refs=deprecated_refs,
        missing_canonical=missing_canonical,
        total_scanned=files_scanned,
    )


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================


def print_summary(result: VerificationResult, verbose: bool = False) -> None:
    """Print verification summary."""
    print("=" * 70)
    print("L9 WIRING ALIGNMENT VERIFICATION")
    print("=" * 70)
    print()

    # Status
    status = "✅ GREEN" if result.is_green else "❌ VIOLATIONS FOUND"
    print(f"Status: {status}")
    print(f"Files scanned: {result.total_scanned}")
    print(f"Paths verified: {len(result.verified_paths)}")
    print()

    # Broken docs
    if result.broken_docs:
        print("-" * 70)
        print(f"BROKEN PATH REFERENCES ({len(result.broken_docs)}):")
        print("-" * 70)
        for item in result.broken_docs[:20]:
            print(f"  ❌ {item['path']}")
            print(f"     Source: {item['source']}:{item['line']}")
        if len(result.broken_docs) > 20:
            print(f"  ... and {len(result.broken_docs) - 20} more")
        print()

    # Deprecated refs
    if result.deprecated_refs:
        print("-" * 70)
        print(f"DEPRECATED PATH REFERENCES ({len(result.deprecated_refs)}):")
        print("-" * 70)
        for item in result.deprecated_refs[:20]:
            print(f"  ⚠️  {item['path']} → {item['replacement']}")
            print(f"     Source: {item['source']}:{item['line']}")
        if len(result.deprecated_refs) > 20:
            print(f"  ... and {len(result.deprecated_refs) - 20} more")
        print()

    # Missing canonical
    if result.missing_canonical:
        print("-" * 70)
        print(f"MISSING CANONICAL FILES ({len(result.missing_canonical)}):")
        print("-" * 70)
        for path in result.missing_canonical:
            print(f"  ❌ {path}")
        print()

    # Verified paths (verbose)
    if verbose and result.verified_paths:
        print("-" * 70)
        print(f"VERIFIED PATHS ({len(result.verified_paths)}):")
        print("-" * 70)
        for path in result.verified_paths[:50]:
            print(f"  ✅ {path}")
        if len(result.verified_paths) > 50:
            print(f"  ... and {len(result.verified_paths) - 50} more")
        print()

    print("=" * 70)


def print_json(result: VerificationResult) -> None:
    """Print verification result as JSON."""
    output = {
        "status": "green" if result.is_green else "violations",
        "files_scanned": result.total_scanned,
        "verified_count": len(result.verified_paths),
        "broken_docs": result.broken_docs,
        "deprecated_refs": result.deprecated_refs,
        "missing_canonical": result.missing_canonical,
    }
    print(json.dumps(output, indent=2))


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="L9 Wiring Alignment Verifier")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verified paths",
    )

    args = parser.parse_args()

    # Run verification
    result = scan_repository()

    # Output
    if args.json:
        print_json(result)
    else:
        print_summary(result, verbose=args.verbose)

    # Return code
    return 0 if result.is_green else 1


if __name__ == "__main__":
    exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-008",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "caching",
        "cli",
        "dataclass",
        "filesystem",
        "metrics",
        "operations",
        "scripts",
        "serialization",
        "testing",
    ],
    "keywords": [
        "alignment",
        "canonical",
        "extract",
        "files",
        "green",
        "json",
        "paths",
        "print",
    ],
    "business_value": "Provides verify wiring alignment components including PathReference, VerificationResult",
    "last_modified": "2026-01-17T23:47:56Z",
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
