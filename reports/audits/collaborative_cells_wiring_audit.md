# Package Wiring Audit: collaborative_cells

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `collaborative_cells`

Files checked: 6
- WIRED: 5
- PARTIAL: 1
- ORPHAN: 0
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `collaborative_cells/architect_cell.py` | 1 | 0 | - | Y | OK |
| `collaborative_cells/base_cell.py` | 2 | 1 | Y | Y | OK |
| `collaborative_cells/cell_registry.py` | 1 | 1 | Y | - | PARTIAL |
| `collaborative_cells/coder_cell.py` | 1 | 0 | - | Y | OK |
| `collaborative_cells/reflection_cell.py` | 1 | 0 | - | Y | OK |
| `collaborative_cells/reviewer_cell.py` | 1 | 0 | - | Y | OK |

## Level C: API Instantiation — `collaborative_cells`

API Status: **HAS_API**
Symbols checked: 8
- USED: 7
- TEST_ONLY: 1
- UNUSED: 0

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `ConsensusStrategy` | 0 | 1 | TEST_ONLY |

**API-pattern symbols NOT in `__all__`:**
- `get_all_cells`
- `get_cell_snapshot`
- `get_cells_by_category`
