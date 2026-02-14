# Package Wiring Audit: orchestrators

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `orchestrators`

Files checked: 2
- WIRED: 0
- PARTIAL: 2
- ORPHAN: 0
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `orchestrators/orchestrator_registry.py` | 1 | 1 | Y | - | PARTIAL |
| `orchestrators/ws_bridge.py` | 1 | 0 | - | - | PARTIAL |

## Level C: API Instantiation — `orchestrators`

API Status: **HAS_API**
Symbols checked: 12
- USED: 7
- TEST_ONLY: 1
- UNUSED: 4

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `EvolutionOrchestrator` | 0 | 0 | UNUSED |
| `MetaOrchestrator` | 0 | 2 | TEST_ONLY |
| `WSBridgeConfig` | 0 | 0 | UNUSED |
| `WSEventRouter` | 0 | 0 | UNUSED |
| `enqueue_ws_event` | 0 | 0 | UNUSED |

**API-pattern symbols NOT in `__all__`:**
- `get_all_orchestrators`
- `get_orchestrator_snapshot`
- `get_orchestrators_by_category`
- `get_orchestrators_by_domain`
