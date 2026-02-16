# Package Wiring Audit: workers

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `workers`

Files checked: 5
- WIRED: 0
- PARTIAL: 5
- ORPHAN: 0
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `workers/anomaly_classifier.py` | 0 | 1 | Y | Y | PARTIAL |
| `workers/anomaly_response_monitor.py` | 0 | 0 | - | Y | PARTIAL |
| `workers/remediation_engine.py` | 0 | 0 | - | Y | PARTIAL |
| `workers/violation_patterns.py` | 0 | 1 | - | Y | PARTIAL |
| `workers/violation_tracker_service.py` | 0 | 1 | - | Y | PARTIAL |

## Level C: API Instantiation — `workers`

API Status: **HAS_API**
Symbols checked: 15
- USED: 7
- TEST_ONLY: 2
- UNUSED: 6

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `AnomalyClassifierRequest` | 0 | 1 | TEST_ONLY |
| `AnomalyClassifierResponse` | 0 | 0 | UNUSED |
| `AnomalyResponseMonitorResponse` | 0 | 0 | UNUSED |
| `RemediationEngineRequest` | 0 | 0 | UNUSED |
| `RemediationEngineResponse` | 0 | 0 | UNUSED |
| `ViolationPatternsRequest` | 0 | 0 | UNUSED |
| `ViolationPatternsResponse` | 0 | 1 | TEST_ONLY |
| `ViolationTrackerServiceResponse` | 0 | 0 | UNUSED |

**API-pattern symbols NOT in `__all__`:**
- `create_anomaly_classifier`
- `create_anomaly_response_monitor`
- `create_remediation_engine`
- `create_violation_patterns`
- `create_violation_tracker_service`
