"""
L9 Workers - Autonomous Background Services
============================================

Governance-driven workers for anomaly detection, violation tracking,
and self-healing operations.

Workers:
    - AnomalyResponseMonitor: Main orchestrator for anomaly detection/response
    - AnomalyClassifier: Classifies anomalies by severity
    - RemediationEngine: Applies remediation or triggers rollback
    - ViolationTrackerService: Tracks lesson violations
    - ViolationPatterns: Pattern matching for violation detection
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Autonomous Background Services",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T12:13:08Z",
    "updated_at": "2026-01-31T22:21:57Z",
    "layer": "operations",
    "domain": "background_workers",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from workers.anomaly_classifier import (
    AnomalyClassifier,
    AnomalyClassifierRequest,
    AnomalyClassifierResponse,
)
from workers.anomaly_response_monitor import (
    AnomalyResponseMonitor,
    AnomalyResponseMonitorRequest,
    AnomalyResponseMonitorResponse,
)
from workers.remediation_engine import (
    RemediationEngine,
    RemediationEngineRequest,
    RemediationEngineResponse,
)
from workers.violation_patterns import (
    ViolationPatterns,
    ViolationPatternsRequest,
    ViolationPatternsResponse,
)
from workers.violation_tracker_service import (
    ViolationTrackerService,
    ViolationTrackerServiceRequest,
    ViolationTrackerServiceResponse,
)

__all__ = [
    # Classifier
    "AnomalyClassifier",
    "AnomalyClassifierRequest",
    "AnomalyClassifierResponse",
    # Anomaly Response
    "AnomalyResponseMonitor",
    "AnomalyResponseMonitorRequest",
    "AnomalyResponseMonitorResponse",
    # Remediation
    "RemediationEngine",
    "RemediationEngineRequest",
    "RemediationEngineResponse",
    # Patterns
    "ViolationPatterns",
    "ViolationPatternsRequest",
    "ViolationPatternsResponse",
    # Violation Tracking
    "ViolationTrackerService",
    "ViolationTrackerServiceRequest",
    "ViolationTrackerServiceResponse",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-012",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["background-workers", "monitoring", "operations", "utility"],
    "keywords": [
        "anomaly",
        "autonomous",
        "background",
        "detection",
        "governance",
        "orchestrator",
        "pattern",
        "services",
    ],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:57Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
