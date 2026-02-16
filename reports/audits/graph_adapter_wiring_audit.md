# Package Wiring Audit: graph_adapter

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `graph_adapter`

Files checked: 1
- WIRED: 0
- PARTIAL: 1
- ORPHAN: 0
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `graph_adapter/packet_node_adapter.py` | 0 | 0 | - | Y | PARTIAL |

## Level C: API Instantiation — `graph_adapter`

API Status: **HAS_API**
Symbols checked: 1
- USED: 0
- TEST_ONLY: 0
- UNUSED: 1

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `PacketNodeAdapter` | 0 | 0 | UNUSED |
