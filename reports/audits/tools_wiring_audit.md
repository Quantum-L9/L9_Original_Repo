# Package Wiring Audit: tools

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `tools`

Files checked: 3
- WIRED: 0
- PARTIAL: 0
- ORPHAN: 1
- ENTRYPOINT: 2
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `tools/export_repo_indexes.py` | 0 | 0 | - | - | ENTRY |
| `tools/l9_cli.py` | 0 | 0 | Y | - | ENTRY |
| `tools/mac_protocol.py` | 0 | 0 | - | - | ORPHAN |

## Level C: API Instantiation — `tools`

API Status: **NO_API_NEEDED**
Symbols checked: 0
- USED: 0
- TEST_ONLY: 0
- UNUSED: 0
