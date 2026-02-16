# Dead Code Triage: `memory_cache`

**Date:** 2026-02-14 05:43 UTC

## Symbol Classification

**USED** (2): `WorkingMemoryService`, `WorkingMemorySnapshot`
**TEST_ONLY** (4): `OptimisticLockError`, `SubstrateWriteEvent`, `VersionedSnapshotService`, `WorkingMemoryInvalidationHook`
**ZERO_REF** (3): `CursorWorkingMemoryService`, `MemoryEventType`, `MemorySnapshot`

## File Classification

**WIRED** (3):
- `memory_cache/invalidation_hook.py`
- `memory_cache/versioned_snapshots.py`
- `memory_cache/working_memory_service.py`

## Recommended Actions

### Review 3 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.
