# Dead Code Triage: `workers`

**Date:** 2026-02-14 05:43 UTC

## Symbol Classification

**USED** (7): `AnomalyClassifier`, `AnomalyResponseMonitor`, `AnomalyResponseMonitorRequest`, `RemediationEngine`, `ViolationPatterns`, `ViolationTrackerService`, `ViolationTrackerServiceRequest`
**INTERNAL_ONLY** (3): `AnomalyClassifierRequest`, `RemediationEngineRequest`, `ViolationPatternsRequest`
**TEST_ONLY** (1): `ViolationPatternsResponse`
**ZERO_REF** (4): `AnomalyClassifierResponse`, `AnomalyResponseMonitorResponse`, `RemediationEngineResponse`, `ViolationTrackerServiceResponse`

## File Classification

**WIRED** (3):
- `workers/anomaly_classifier.py`
- `workers/violation_patterns.py`
- `workers/violation_tracker_service.py`
**INTERNAL_ONLY** (1):
- `workers/remediation_engine.py`
**WIP** (1):
- `workers/anomaly_response_monitor.py`

## Recommended Actions

### Remove 3 internal-only symbols from `__all__`
These are used within the package but not externally. Remove from `__all__` to reduce API surface noise.

### Review 4 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.

### Wire 1 WIP files
Recently created but not yet integrated.
