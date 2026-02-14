#!/usr/bin/env python3
"""
ingest_repo_indexes.py - Ingest L9 Repo Indexes to Memory
=========================================================

Reads the structured repo-index files and stores them in L9 memory
with proper chunking and metadata for retrieval.

Part of the full /index pipeline:
  1. export_repo_indexes.py → Generate index files
  2. ingest_repo_indexes.py → Store in pgvector (semantic search)
  3. load_indexes_to_neo4j.py → Store in Neo4j (graph queries)

Usage:
    python3 scripts/memory/ingest_repo_indexes.py [--dry-run] [--verbose] [--force]
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Ingest L9 Repo Indexes to Memory",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T17:12:49Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "operations",
    "domain": "memory_substrate",
    "module_name": "ingest_repo_indexes",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

# Add project root to path BEFORE importing core modules
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import structlog

from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

INDEX_DIR = PROJECT_ROOT / "reports" / "repo-index"
HASH_CACHE_FILE = PROJECT_ROOT / "reports" / ".index_hashes.json"

# Priority indexes to ingest (most valuable for retrieval)
PRIORITY_INDEXES = [
    (
        "class_definitions.txt",
        "index",
        "Classes with paths - use for 'where is class X?'",
    ),
    (
        "function_signatures.txt",
        "index",
        "Functions with signatures - use for 'what args does X take?'",
    ),
    (
        "inheritance_graph.txt",
        "index",
        "Inheritance relationships - use for 'what extends X?'",
    ),
    (
        "route_handlers.txt",
        "index",
        "API routes to handlers - use for 'what handles /api/X?'",
    ),
    ("tool_catalog.txt", "index", "Available tools - use for tool discovery"),
    (
        "method_catalog.txt",
        "index",
        "Class methods - use for 'what methods does X have?'",
    ),
    (
        "pydantic_models.txt",
        "index",
        "Pydantic schemas - use for 'what fields does X have?'",
    ),
    ("imports.txt", "index", "Import graph - use for 'what imports X?'"),
    ("wiring_map.txt", "index", "Service wiring - use for integration points"),
    ("agent_catalog.txt", "index", "Agent definitions - use for agent discovery"),
]


def load_hash_cache() -> dict:
    """Load cached file hashes to detect changes."""
    if HASH_CACHE_FILE.exists():
        try:
            return json.loads(HASH_CACHE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_hash_cache(cache: dict) -> None:
    """Save file hashes for change detection."""
    try:
        HASH_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        HASH_CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except Exception:
        pass


def compute_file_hash(filepath: Path) -> str:
    """Compute MD5 hash of file content."""
    if not filepath.exists():
        return ""
    content = filepath.read_bytes()
    return hashlib.md5(content).hexdigest()


def has_file_changed(filepath: Path, hash_cache: dict) -> bool:
    """Check if file has changed since last ingestion."""
    current_hash = compute_file_hash(filepath)
    cached_hash = hash_cache.get(filepath.name, "")
    return current_hash != cached_hash


def chunk_index_file(
    content: str, filename: str, max_chunk_size: int = 3000
) -> list[dict]:
    """
    Chunk an index file into memory-sized pieces.

    Strategy:
    - Split by double newlines (logical sections)
    - Keep chunks under max_chunk_size
    - Preserve context in each chunk
    """
    chunks = []
    lines = content.strip().split("\n")

    current_chunk: list[str] = []
    current_size = 0
    chunk_num = 0

    for line in lines:
        line_size = len(line) + 1

        if current_size + line_size > max_chunk_size and current_chunk:
            # Save current chunk
            chunk_num += 1
            chunks.append(
                {
                    "content": "\n".join(current_chunk),
                    "chunk_id": f"{filename}:chunk_{chunk_num}",
                    "total_lines": len(current_chunk),
                }
            )
            current_chunk = []
            current_size = 0

        current_chunk.append(line)
        current_size += line_size

    # Don't forget last chunk
    if current_chunk:
        chunk_num += 1
        chunks.append(
            {
                "content": "\n".join(current_chunk),
                "chunk_id": f"{filename}:chunk_{chunk_num}",
                "total_lines": len(current_chunk),
            }
        )

    return chunks


@must_stay_async("callers use await")
async def ingest_index(
    filename: str,
    kind: str,
    description: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Ingest a single index file to memory."""
    filepath = INDEX_DIR / filename

    if not filepath.exists():
        logger.info("  ⚠️  filename not found, skipping", filename=filename)
        return 0

    content = filepath.read_text()
    total_lines = len(content.strip().split("\n"))

    # Create summary for the whole file
    summary = f"L9 Repo Index: {filename}\n{description}\nTotal entries: {total_lines}"

    if verbose:
        logger.info(
            "  📄 filename: total lines lines",
            filename=filename,
            total_lines=total_lines,
        )

    if dry_run:
        logger.info("  [dry run] would ingest filename", filename=filename)
        return 1

    # Use cursor_memory_client to write
    import subprocess

    # Write summary packet (include tags in content since --tags not supported)
    tagged_summary = f"[REPO-INDEX:{filename.replace('.txt', '')}] {summary}"

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "agents" / "cursor" / "cursor_memory_client.py"),
            "write",
            tagged_summary,
            "--kind",
            kind,
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        logger.error(
            "  ❌ failed to write filename: {result.stderr}", filename=filename
        )
        return 0

    # For large files, also chunk and store key sections
    if total_lines > 100:
        chunks = chunk_index_file(content, filename, max_chunk_size=4000)

        # Store first chunk (usually most important - headers/top entries)
        if chunks:
            first_chunk = chunks[0]
            chunk_content = f"[REPO-INDEX:{filename.replace('.txt', '')}:chunk-1] L9 Index {filename} (part 1/{len(chunks)}):\n{first_chunk['content'][:3500]}"

            subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "agents" / "cursor" / "cursor_memory_client.py"),
                    "write",
                    chunk_content,
                    "--kind",
                    kind,
                ],
                capture_output=True,
                text=True,
                cwd=str(PROJECT_ROOT),
            )

    return 1


@must_stay_async("callers use await")
async def main():
    parser = argparse.ArgumentParser(description="Ingest repo indexes to L9 memory")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--priority-only",
        action="store_true",
        help="Ingest only priority indexes (default: all)",
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="Force re-ingest even if unchanged"
    )
    args = parser.parse_args()

    logger.info("🧠 l9 repo index ingestion")
    logger.info("=" * 50)

    if args.dry_run:
        logger.info("🔍 dry run mode - no changes will be made\n")

    # Load hash cache for change detection
    hash_cache = load_hash_cache()
    new_hash_cache = {}

    # Default: ingest ALL indexes (33 files)
    # Use --priority-only for just the 10 priority indexes
    if args.priority_only:
        indexes_to_process = list(PRIORITY_INDEXES)
    else:
        # Ingest ALL indexes - priority first, then the rest
        indexes_to_process = list(PRIORITY_INDEXES)
        all_files = list(INDEX_DIR.glob("*.txt"))
        priority_names = {p[0] for p in PRIORITY_INDEXES}
        for f in sorted(all_files):
            if f.name not in priority_names:
                indexes_to_process.append((f.name, "index", f"L9 index: {f.name}"))

    logger.info(
        "📁 processing {len(indexes to process)} index files from index dir\n",
        INDEX_DIR=INDEX_DIR,
    )

    success_count = 0
    skipped_count = 0

    for filename, kind, description in indexes_to_process:
        filepath = INDEX_DIR / filename

        # Check if file has changed
        if not args.force and not has_file_changed(filepath, hash_cache):
            if args.verbose:
                logger.info("  ⏭️  filename: unchanged, skipping", filename=filename)
            skipped_count += 1
            new_hash_cache[filename] = hash_cache.get(filename, "")
            continue

        count = await ingest_index(
            filename=filename,
            kind=kind,
            description=description,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

        if count > 0:
            success_count += count
            # Update hash cache with new hash
            new_hash_cache[filename] = compute_file_hash(filepath)
        else:
            new_hash_cache[filename] = hash_cache.get(filename, "")

    # Save updated hash cache
    if not args.dry_run:
        save_hash_cache(new_hash_cache)

    logger.info("=" * 50)
    total = len(indexes_to_process)
    print(
        f"✅ Ingested: {success_count} | Skipped (unchanged): {skipped_count} | Total: {total}"
    )

    if not args.dry_run:
        logger.info("\n📍 indexes now available in l9 memory for semantic search")
        logger.info(
            "   use: python3 agents/cursor/cursor_memory_client.py search 'class x'"
        )


if __name__ == "__main__":
    asyncio.run(main())
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-035",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "async",
        "caching",
        "cli",
        "filesystem",
        "memory-substrate",
        "operations",
        "rest-api",
        "security",
        "serialization",
    ],
    "keywords": [
        "cache",
        "changed",
        "chunk",
        "compute",
        "hash",
        "index",
        "indexes",
        "ingest",
    ],
    "business_value": "1. export_repo_indexes.py → Generate index files 2. ingest_repo_indexes.py → Store in pgvector (semantic search) 3. load_indexes_to_neo4j.py → Store in Neo4j (graph queries) python3 scripts/memory/ing",
    "last_modified": "2026-01-31T22:21:56Z",
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
