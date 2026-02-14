# Package Wiring Audit: memory_cache

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `memory_cache`

Files checked: 3
- WIRED: 1
- PARTIAL: 2
- ORPHAN: 0
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `memory_cache/invalidation_hook.py` | 0 | 1 | - | Y | PARTIAL |
| `memory_cache/versioned_snapshots.py` | 0 | 1 | - | Y | PARTIAL |
| `memory_cache/working_memory_service.py` | 3 | 0 | - | Y | OK |

## Level C: API Instantiation — `memory_cache`

API Status: **HAS_API**
Symbols checked: 9
- USED: 2
- TEST_ONLY: 4
- UNUSED: 3

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `CursorWorkingMemoryService` | 0 | 0 | UNUSED |
| `MemoryEventType` | 0 | 0 | UNUSED |
| `MemorySnapshot` | 0 | 0 | UNUSED |
| `OptimisticLockError` | 0 | 1 | TEST_ONLY |
| `SubstrateWriteEvent` | 0 | 1 | TEST_ONLY |
| `VersionedSnapshotService` | 0 | 1 | TEST_ONLY |
| `WorkingMemoryInvalidationHook` | 0 | 1 | TEST_ONLY |
