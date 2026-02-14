# Package Wiring Audit: governance

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `governance`

Files checked: 1
- WIRED: 0
- PARTIAL: 1
- ORPHAN: 0
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `governance/rejection_recorder.py` | 0 | 1 | Y | Y | PARTIAL |

## Level C: API Instantiation — `governance`

API Status: **HAS_API**
Symbols checked: 3
- USED: 0
- TEST_ONLY: 3
- UNUSED: 0

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `record_governance_violation` | 0 | 1 | TEST_ONLY |
| `record_rejection` | 0 | 1 | TEST_ONLY |
| `record_test_failure` | 0 | 1 | TEST_ONLY |
