
# memory_cache/__init__.py
"""
Memory Cache Module - Ephemeral working memory for L9 agents.

Provides TTL-based, Redis-backed working memory that expires naturally.
Shared across all agents (L-CTO, Cursor, future agents) on same repo/branch.
No auto-promotion to long-term memory without explicit signals.
"""

# Phase 0 Hardening: Cache Invalidation + Versioned Snapshots
from memory_cache.invalidation_hook import (
    SubstrateWriteEvent,
    WorkingMemoryInvalidationHook,
)
from memory_cache.versioned_snapshots import (
    MemorySnapshot,
    OptimisticLockError,
    VersionedSnapshotService,
)
from memory_cache.working_memory_service import (
    CursorWorkingMemoryService,  # Backwards compatibility alias
    MemoryEventType,
    WorkingMemoryService,
    WorkingMemorySnapshot,
)

__all__ = [
    "CursorWorkingMemoryService",  # Backwards compatibility alias
    "MemoryEventType",
    # Phase 0 Hardening
    "MemorySnapshot",
    "OptimisticLockError",
    "SubstrateWriteEvent",
    "VersionedSnapshotService",
    "WorkingMemoryInvalidationHook",
    "WorkingMemoryService",
    "WorkingMemorySnapshot",
]
# Runtime execution trace - updated automatically on every execution
