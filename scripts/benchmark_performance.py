#!/usr/bin/env python3
"""
L9 Performance Benchmark Script

Benchmarks performance improvements from:
- N+1 query fixes (batch operations)
- Kernel configuration caching

Usage:
    python scripts/benchmark_performance.py
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Benchmark Performance",
    "module_version": "1.0.0",
    "created_by": "cryptoxdog",
    "created_at": "2026-01-23T15:55:39Z",
    "updated_at": "2026-01-31T22:21:56Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "benchmark_performance",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["episodic_memory", "semantic_memory", "working_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
import sys
import time
from pathlib import Path
from uuid import uuid4
import structlog

# Add project root to path

logger = structlog.get_logger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))


async def benchmark_batch_insert():
    """Benchmark batch insert performance"""
    import os

    from memory.substrate_repository import SubstrateRepository

    database_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/l9_memory"
    )
    repo = SubstrateRepository(database_url)

    try:
        await repo.connect()

        # Test data
        event_id = uuid4()
        fact_ids = [uuid4() for _ in range(100)]

        # Benchmark
        start = time.time()
        links_created = await repo.link_event_to_facts(
            event_id=event_id, fact_ids=fact_ids, relationship_type="test", strength=1.0
        )
        duration = time.time() - start

        logger.info("✅ batch insert: links created links in {duration * 1000:.2f}ms", links_created=links_created)
        logger.info("   performance: {duration / len(fact_ids) * 1000:.2f}ms per link")

        # Cleanup
        async with repo.acquire() as conn:
            await conn.execute(
                "DELETE FROM episodic_semantic_links WHERE event_id = $1", event_id
            )

        return duration

    finally:
        await repo.disconnect()


async def benchmark_kernel_loading():
    """Benchmark kernel loading with caching"""
    from pathlib import Path

    from runtime.kernel_loader import _load_kernel_yaml_cached

    kernel_path = "private/kernels/00_system/01_master_kernel.yaml"
    full_path = Path(kernel_path)

    if not full_path.exists():
        logger.info("⚠️  kernel file not found: kernel path", kernel_path=kernel_path)
        return None

    # First load (uncached)
    start = time.time()
    _load_kernel_yaml_cached(str(full_path))
    duration_uncached = time.time() - start

    # Second load (cached)
    start = time.time()
    _load_kernel_yaml_cached(str(full_path))
    duration_cached = time.time() - start

    speedup = duration_uncached / duration_cached if duration_cached > 0 else 0

    logger.info("✅ kernel loading:")
    logger.info("   uncached: {duration_uncached * 1000:.2f}ms")
    logger.info("   cached: {duration_cached * 1000:.2f}ms")
    logger.info("   speedup: {speedup:.1f}x faster")

    return duration_uncached, duration_cached


async def main():
    """Run all benchmarks"""
    logger.info("🚀 l9 performance benchmark")
    logger.info("=" * 60")
    logger.info("output", value=)

    # Benchmark 1: Batch insert
    logger.info("1. batch insert performance")
    logger.info("-" * 60")
    try:
        await benchmark_batch_insert()
    except Exception as e:
        logger.error("❌ batch insert benchmark failed: e", e=e)
    logger.info("output", value=)

    # Benchmark 2: Kernel caching
    logger.info("2. kernel loading performance")
    logger.info("-" * 60")
    try:
        await benchmark_kernel_loading()
    except Exception as e:
        logger.error("❌ kernel caching benchmark failed: e", e=e)
    logger.info("output", value=)

    logger.info("=" * 60")
    logger.info("✅ benchmark complete!")


if __name__ == "__main__":
    asyncio.run(main())
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-008",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["memory.substrate_repository", "runtime.kernel_loader"],
    "tags": [
        "async",
        "batch-processing",
        "caching",
        "event-driven",
        "filesystem",
        "operations",
        "performance",
        "scripts",
        "service",
        "testing",
    ],
    "keywords": ["batch", "benchmark", "insert", "kernel", "loading", "performance"],
    "business_value": "Utility module for benchmark performance",
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
