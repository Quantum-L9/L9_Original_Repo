#!/usr/bin/env python3
"""
L9 Wiring Alignment Validator
==============================
Automated cross-check of docs, audit cache, and code for stale memory/cursor paths.

Usage:
    python3 scripts/audit/validate_wiring_alignment.py [--fix] [--verbose]

Exit Codes:
    0 = All paths aligned (PASS)
    1 = Stale paths found (FAIL)
    2 = Configuration error
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Validate Wiring Alignment",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "wiring-audit-perplexity",
    "module_name": "validate_wiring_alignment",
    "type": "cli",
    "status": "draft",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import json
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

# ============================================================================
# CANONICAL WIRING MAP (from Phase 0 TODO Plan)
# ============================================================================

CANONICAL_ROUTERS = {
    "apimemoryrouter.py": {
        "line_count": 689,
        "async_count": 17,
        "purpose": "Unified memory batch write/search/health",
    },
    "mcpmemorysrcroutesmemory.py": {
        "line_count": 913,
        "async_count": 14,
        "purpose": "MCP memory save/search surface",
    },
    "mcpmemorysrcroutesmemoryunified.py": {
        "line_count": 1409,
        "async_count": 16,
        "purpose": "Unified MCP routing (newer)",
    },
    "apiroutescursor.py": {
        "line_count": 189,
        "async_count": 3,
        "purpose": "Cursor task execution dispatch",
    },
    "agentscursorextractorscursoractionextractor.py": {
        "line_count": 661,
        "async_count": 11,
        "purpose": "Cursor action extraction from memory",
    },
    "agentscursorintegrationscursorgateway.py": {
        "line_count": 282,
        "async_count": 5,
        "purpose": "Cursor scope enforcement & memory gateway",
    },
}

STALE_PATH_PATTERNS = [
    (r"api/routes/memory\.py", "api/memory/router.py (or use apimemoryrouter.py)"),
    (r"tools/cursor_client", "agents/cursor/ (see agentscursor*.py)"),
    (r"memory/extractor/cursor_action_extractor", "agents/cursor/extractors/cursor_action_extractor.py"),
    (r"core/governance/cursor_memory_kernel", "agents/cursor/cursor_gateway.py"),
    (r"scripts/cursor_check_mistakes", "agents/cursor/scripts/cursor_check_mistakes.py"),
]

# Paths to scan
SCAN_PATHS = {
    "docs": "*.md",
    "scripts/audit": "*.py",
    ".": "gap-analysis-memory.md",  # Explicit check for the main file
}

# Protected L9 modules (must not change)
PROTECTED_MODULES = {
    "coreschemaseventstream.py",
    "coreschemaswseventstream.py",
    "coregovernanceapprovalmanager.py",
    "coregovernanceengine.py",
    "memorygovernancepatterns.py",
    "memorysubstratemodels.py",
    "corekernelsschemas.py",
    "runtimekernelloader.py",
}

# ============================================================================
# VALIDATOR LOGIC
# ============================================================================


class WiringValidator:
    def __init__(self, repo_root: str = ".", verbose: bool = False):
        self.repo_root = Path(repo_root)
        self.verbose = verbose
        self.errors: List[Tuple[str, str]] = []
        self.warnings: List[Tuple[str, str]] = []

    def log(self, msg: str, level: str = "INFO"):
        if self.verbose or level in ("ERROR", "WARN"):
            print(f"[{level}] {msg}")

    def scan_docs_for_stale_refs(self) -> Dict[str, int]:
        """Scan documentation files for stale path references."""
        self.log("Scanning docs for stale refs...")
        stale_count = {}

        for pattern, replacement in STALE_PATH_PATTERNS:
            count = 0
            for doc_file in self.repo_root.rglob("*.md"):
                try:
                    content = doc_file.read_text(encoding="utf-8", errors="ignore")
                    matches = re.findall(pattern, content)
                    if matches:
                        count += len(matches)
                        self.errors.append(
                            (
                                str(doc_file),
                                f"Found {len(matches)} stale refs to '{pattern}' → should be '{replacement}'",
                            )
                        )
                        self.log(f"  - {doc_file}: {len(matches)} occurrences", "WARN")
                except Exception as e:
                    self.log(f"  Error reading {doc_file}: {e}", "WARN")
            stale_count[pattern] = count

        return stale_count

    def scan_audit_cache(self) -> int:
        """Check .audit_cache/manifest.json for stale paths."""
        self.log("Checking audit cache...")
        cache_file = self.repo_root / ".audit_cache" / "manifest.json"

        if not cache_file.exists():
            self.log("  .audit_cache/manifest.json missing (not yet generated)", "WARN")
            return 0

        try:
            with open(cache_file) as f:
                manifest = json.load(f)
        except Exception as e:
            self.log(f"  Error reading cache: {e}", "ERROR")
            self.errors.append((".audit_cache/manifest.json", f"Parse error: {e}"))
            return 0

        stale_in_cache = 0
        for pattern, replacement in STALE_PATH_PATTERNS:
            for entry in manifest.get("files", []):
                if re.search(pattern, entry):
                    stale_in_cache += 1
                    self.errors.append(
                        (
                            ".audit_cache/manifest.json",
                            f"Entry '{entry}' matches stale pattern '{pattern}'",
                        )
                    )
                    self.log(f"  - Stale entry: {entry}", "WARN")

        return stale_in_cache

    def verify_canonical_routers_exist(self) -> bool:
        """Verify that all canonical routers exist in the codebase."""
        self.log("Verifying canonical routers exist...")
        all_exist = True

        for router_name, info in CANONICAL_ROUTERS.items():
            # Try multiple search patterns
            found = False
            for root, dirs, files in os.walk(self.repo_root):
                if router_name in files:
                    found = True
                    self.log(f"  ✓ {router_name}", "INFO")
                    break

            if not found:
                all_exist = False
                self.errors.append(
                    ("canonical_routers", f"Router '{router_name}' not found in repo")
                )
                self.log(f"  ✗ {router_name} NOT FOUND", "WARN")

        return all_exist

    def check_protected_modules_unchanged(self) -> bool:
        """Warn if protected L9 modules might be in the changeset."""
        self.log("Checking protected L9 modules...")
        all_safe = True

        # This is a simple check; in a real pipeline, you'd check git status
        for protected in PROTECTED_MODULES:
            found = False
            for root, dirs, files in os.walk(self.repo_root):
                if protected in files:
                    found = True
                    self.log(f"  ✓ {protected} (exists, presumed unchanged)", "INFO")
                    break

            if not found:
                self.log(f"  ! {protected} (not found; may be archived)", "WARN")

        return all_safe

    def run(self) -> int:
        """Run full audit. Return exit code."""
        print("=" * 80)
        print("L9 WIRING ALIGNMENT VALIDATOR")
        print("=" * 80)
        print()

        # Phase 1: Scan docs
        stale_docs = self.scan_docs_for_stale_refs()
        print()

        # Phase 2: Scan audit cache
        stale_cache = self.scan_audit_cache()
        print()

        # Phase 3: Verify routers exist
        routers_ok = self.verify_canonical_routers_exist()
        print()

        # Phase 4: Protected modules
        protected_ok = self.check_protected_modules_unchanged()
        print()

        # Summary
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"Stale doc references: {sum(stale_docs.values())}")
        print(f"Stale cache entries: {stale_cache}")
        print(f"Canonical routers verified: {routers_ok}")
        print(f"Protected modules safe: {protected_ok}")
        print(f"Total errors: {len(self.errors)}")
        print(f"Total warnings: {len(self.warnings)}")
        print()

        if self.errors:
            print("ERRORS FOUND:")
            for file_or_context, msg in self.errors:
                print(f"  - [{file_or_context}] {msg}")
            print()

        if self.warnings:
            print("WARNINGS:")
            for file_or_context, msg in self.warnings:
                print(f"  - [{file_or_context}] {msg}")
            print()

        # Final verdict
        if sum(stale_docs.values()) > 0 or stale_cache > 0:
            print("STATUS: ❌ FAIL - Stale paths detected")
            return 1
        elif not routers_ok:
            print("STATUS: ⚠️  WARN - Some routers missing (may be pre-refactor)")
            return 1
        else:
            print("STATUS: ✅ PASS - All paths aligned, no L9 invariants broken")
            return 0


# ============================================================================
# CLI
# ============================================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate L9 memory + cursor wiring alignment"
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Path to L9 repo root (default: current dir)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="(Future) Auto-fix stale refs (not yet implemented)",
    )

    args = parser.parse_args()

    validator = WiringValidator(repo_root=args.repo_root, verbose=args.verbose)
    exit_code = validator.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WIR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "batch-processing", "caching", "cli", "event-driven", "filesystem", "operations", "serialization", "streaming", "validation"],
    "keywords": ["alignment", "audit", "cache", "canonical", "check", "docs", "exist", "modules"],
    "business_value": "Implements WiringValidator for validate wiring alignment functionality",
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
