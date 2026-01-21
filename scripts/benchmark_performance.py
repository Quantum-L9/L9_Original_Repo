#!/usr/bin/env python3
"""
L9 Performance Benchmark Script

Benchmarks performance improvements from:
- N+1 query fixes (batch operations)
- Kernel configuration caching

Usage:
    python scripts/benchmark_performance.py
"""

import asyncio
import time
from uuid import uuid4
from typing import List
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def benchmark_batch_insert():
    """Benchmark batch insert performance"""
    from memory.substrate_repository import SubstrateRepository
    import os
    
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/l9_memory")
    repo = SubstrateRepository(database_url)
    
    try:
        await repo.connect()
        
        # Test data
        event_id = uuid4()
        fact_ids = [uuid4() for _ in range(100)]
        
        # Benchmark
        start = time.time()
        links_created = await repo.link_event_to_facts(
            event_id=event_id,
            fact_ids=fact_ids,
            relationship_type="test",
            strength=1.0
        )
        duration = time.time() - start
        
        print(f"✅ Batch insert: {links_created} links in {duration*1000:.2f}ms")
        print(f"   Performance: {duration/len(fact_ids)*1000:.2f}ms per link")
        
        # Cleanup
        async with repo.acquire() as conn:
            await conn.execute(
                "DELETE FROM episodic_semantic_links WHERE event_id = $1",
                event_id
            )
        
        return duration
        
    finally:
        await repo.disconnect()


async def benchmark_kernel_loading():
    """Benchmark kernel loading with caching"""
    from runtime.kernel_loader import _load_kernel_yaml_cached
    from pathlib import Path
    
    kernel_path = "private/kernels/00_system/01_master_kernel.yaml"
    full_path = Path(kernel_path)
    
    if not full_path.exists():
        print(f"⚠️  Kernel file not found: {kernel_path}")
        return None
    
    # First load (uncached)
    start = time.time()
    data1 = _load_kernel_yaml_cached(str(full_path))
    duration_uncached = time.time() - start
    
    # Second load (cached)
    start = time.time()
    data2 = _load_kernel_yaml_cached(str(full_path))
    duration_cached = time.time() - start
    
    speedup = duration_uncached / duration_cached if duration_cached > 0 else 0
    
    print(f"✅ Kernel loading:")
    print(f"   Uncached: {duration_uncached*1000:.2f}ms")
    print(f"   Cached: {duration_cached*1000:.2f}ms")
    print(f"   Speedup: {speedup:.1f}x faster")
    
    return duration_uncached, duration_cached


async def main():
    """Run all benchmarks"""
    print("🚀 L9 Performance Benchmark")
    print("=" * 60)
    print()
    
    # Benchmark 1: Batch insert
    print("1. Batch Insert Performance")
    print("-" * 60)
    try:
        await benchmark_batch_insert()
    except Exception as e:
        print(f"❌ Batch insert benchmark failed: {e}")
    print()
    
    # Benchmark 2: Kernel caching
    print("2. Kernel Loading Performance")
    print("-" * 60)
    try:
        await benchmark_kernel_loading()
    except Exception as e:
        print(f"❌ Kernel caching benchmark failed: {e}")
    print()
    
    print("=" * 60)
    print("✅ Benchmark complete!")


if __name__ == "__main__":
    asyncio.run(main())
