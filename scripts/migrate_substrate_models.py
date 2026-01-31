#!/usr/bin/env python3
"""
GMP-63: Migrate files from memory.substrate_models to core.schemas.packet_envelope_v2

Usage:
    python scripts/migrate_substrate_models.py --dry-run  # Preview changes
    python scripts/migrate_substrate_models.py            # Apply changes
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Migrate Substrate Models",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "migrate_substrate_models",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import re
import sys
from pathlib import Path

# Symbols that moved from memory.substrate_models to core.schemas.packet_envelope_v2
V2_SYMBOLS = {
    "PacketEnvelope",
    "PacketEnvelopeIn",
    "PacketWriteResult",
    "PacketConfidence",
    "PacketProvenance",
    "PacketLineage",
    "PacketMetadata",
    "PacketKind",
    "DerivationType",
    "DeriveType",
    "SemanticSearchRequest",
    "SemanticSearchResult",
    "SemanticHit",
    "SCHEMA_VERSION",
    "SUPPORTED_VERSIONS",
    "VALID_DERIVE_TYPES",
}

# Symbols that stay in memory.substrate_models (not in v2)
LEGACY_ONLY_SYMBOLS = {
    "MemorySegment",
    "StructuredReasoningBlock",
    "SubstrateState",
    "AgentMemoryEventRow",
    "SemanticMemoryRow",
    "ReasoningTraceRow",
    "PacketStoreRow",
    "GraphCheckpointRow",
    "KnowledgeFact",
    "KnowledgeFactRow",
    "ExtractedInsight",
    "EnrichmentResult",
}

# Files to skip (docs, the source file itself, etc.)
SKIP_PATTERNS = [
    "memory/substrate_models.py",  # The source file
    "memory/README.md",
    "memory/WIRING.md",
    "readme/MEMORY-README.md",
    "prompts/",
    "current_work/",
    "gap-analysis-memory.md",
    "ci/check_schema_deprecation.py",  # This file checks for deprecation
    "__pycache__",
    ".pyc",
    "migrate_substrate_models.py",  # This script
]


def should_skip(path: Path) -> bool:
    """Check if file should be skipped."""
    path_str = str(path)
    return any(skip in path_str for skip in SKIP_PATTERNS)


def find_files_to_migrate(root: Path) -> list[Path]:
    """Find all Python files that import from memory.substrate_models."""
    files = []
    for path in root.rglob("*.py"):
        if should_skip(path):
            continue
        try:
            content = path.read_text()
            if "from memory.substrate_models import" in content:
                files.append(path)
        except Exception:
            continue
    return files


def parse_imports(content: str) -> tuple[list[str], str]:
    """
    Parse the substrate_models import statement and return:
    - List of imported symbols
    - The full import statement (for replacement)
    """
    # Match multi-line import with parentheses first (more specific)
    multi_pattern = r"from memory\.substrate_models import \(\s*([^)]+)\s*\)"
    match = re.search(multi_pattern, content, re.DOTALL)
    if match:
        import_str = match.group(1)
        # Split by comma or newline, strip whitespace
        symbols = []
        for s in re.split(r"[,\n]", import_str):
            s = s.strip()
            if s and not s.startswith("#"):
                symbols.append(s)
        return symbols, match.group(0)

    # Match single-line import
    single_pattern = r"from memory\.substrate_models import ([^\n]+)"
    match = re.search(single_pattern, content)
    if match:
        import_str = match.group(1).strip()
        # Handle parenthesized imports on single line
        if import_str.startswith("(") and import_str.endswith(")"):
            import_str = import_str[1:-1]
        symbols = [s.strip().rstrip(",") for s in import_str.split(",") if s.strip()]
        return symbols, match.group(0)

    return [], ""


def generate_new_imports(symbols: list[str]) -> str:
    """Generate new import statements based on which symbols go where."""
    v2_imports = []
    legacy_imports = []

    for sym in symbols:
        sym = sym.strip()
        if not sym:
            continue
        if sym in V2_SYMBOLS:
            v2_imports.append(sym)
        elif sym in LEGACY_ONLY_SYMBOLS:
            legacy_imports.append(sym)
        else:
            # Unknown symbol - keep in legacy for safety
            print(f"  ⚠ Unknown symbol '{sym}' - keeping in substrate_models")
            legacy_imports.append(sym)

    lines = []

    if v2_imports:
        if len(v2_imports) <= 3:
            lines.append(f"from core.schemas import {', '.join(sorted(v2_imports))}")
        else:
            lines.append("from core.schemas import (")
            for sym in sorted(v2_imports):
                lines.append(f"    {sym},")
            lines.append(")")

    if legacy_imports:
        if len(legacy_imports) <= 3:
            lines.append(
                f"from memory.substrate_models import {', '.join(sorted(legacy_imports))}"
            )
        else:
            lines.append("from memory.substrate_models import (")
            for sym in sorted(legacy_imports):
                lines.append(f"    {sym},")
            lines.append(")")

    return "\n".join(lines)


def migrate_file(path: Path, dry_run: bool = True) -> tuple[bool, str]:
    """
    Migrate a single file.

    Returns:
        (changed, message)
    """
    content = path.read_text()
    symbols, old_import = parse_imports(content)

    if not symbols:
        return False, f"Could not parse imports in {path}"

    new_import = generate_new_imports(symbols)

    # Check if all symbols were legacy-only (no change needed for v2)
    v2_count = sum(1 for s in symbols if s in V2_SYMBOLS)
    if v2_count == 0:
        return False, f"No v2 symbols in {path} (all legacy)"

    new_content = content.replace(old_import, new_import)

    if new_content == content:
        return False, f"No changes needed for {path}"

    if dry_run:
        short_old = old_import.replace("\n", " ")[:60]
        short_new = new_import.replace("\n", " ")[:60]
        return True, f"{path}\n    FROM: {short_old}...\n    TO:   {short_new}..."
    path.write_text(new_content)
    return True, f"Updated {path}"


def main():
    """
    Performs the main migration process from memory.substrate_models to core.schemas.packet_envelope_v2 in the substrate models migration script.



    Raises:
        Exception: If errors occur during file processing or migration steps.
    """
    dry_run = "--dry-run" in sys.argv

    # Find project root (parent of scripts/)
    script_path = Path(__file__).resolve()
    root = script_path.parent.parent

    print(
        f"{'DRY RUN - ' if dry_run else ''}Migrating from memory.substrate_models to core.schemas.packet_envelope_v2"
    )
    print(f"Project root: {root}")
    print("=" * 80)

    files = find_files_to_migrate(root)
    print(f"Found {len(files)} files to migrate\n")

    changed = 0
    skipped = 0
    errors = []

    for path in sorted(files):
        try:
            was_changed, msg = migrate_file(path, dry_run)
            if was_changed:
                changed += 1
                print(f"✓ {msg}")
            else:
                skipped += 1
                print(f"- {msg}")
        except Exception as e:
            errors.append((path, str(e)))
            print(f"✗ Error processing {path}: {e}")

    print("\n" + "=" * 80)
    print("Summary:")
    print(f"  Files {'would be ' if dry_run else ''}changed: {changed}")
    print(f"  Files skipped (no v2 symbols): {skipped}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for path, err in errors:
            print(f"    - {path}: {err}")

    if dry_run and changed > 0:
        print("\n🔸 Run without --dry-run to apply changes")
    elif not dry_run and changed > 0:
        print("\n✅ Migration complete! Run py_compile and tests to verify.")


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "caching",
        "cli",
        "event-driven",
        "filesystem",
        "messaging",
        "migration",
        "operations",
        "scripts",
        "testing",
        "tracing",
    ],
    "keywords": [
        "files",
        "find",
        "generate",
        "imports",
        "migrate",
        "models",
        "parse",
        "should",
    ],
    "business_value": "Utility module for migrate substrate models",
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
