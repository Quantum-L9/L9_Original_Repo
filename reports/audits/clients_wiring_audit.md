# Package Wiring Audit: clients

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `clients`

Files checked: 2
- WIRED: 1
- PARTIAL: 1
- ORPHAN: 0
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `clients/memory_client.py` | 6 | 2 | Y | Y | OK |
| `clients/world_model_client.py` | 1 | 0 | - | - | PARTIAL |

## Level C: API Instantiation — `clients`

API Status: **HAS_API**
Symbols checked: 3
- USED: 3
- TEST_ONLY: 0
- UNUSED: 0

**API-pattern symbols NOT in `__all__`:**
- `get_world_model_client`
