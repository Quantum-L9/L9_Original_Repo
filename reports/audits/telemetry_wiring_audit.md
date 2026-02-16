# Package Wiring Audit: telemetry

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `telemetry`

Files checked: 3
- WIRED: 0
- PARTIAL: 2
- ORPHAN: 0
- ENTRYPOINT: 1
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `telemetry/calibration_dashboard.py` | 0 | 0 | - | - | ENTRY |
| `telemetry/memory_metrics.py` | 5 | 3 | Y | - | PARTIAL |
| `telemetry/slack_metrics.py` | 3 | 2 | - | - | PARTIAL |

## Level C: API Instantiation — `telemetry`

API Status: **NO_API_NEEDED**
Symbols checked: 0
- USED: 0
- TEST_ONLY: 0
- UNUSED: 0
