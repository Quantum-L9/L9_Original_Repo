"""
L9 Calibration Module

Confidence calibration, uncertainty decomposition, and decision gating
for probabilistic governance.

Components:
- schemas: Pydantic request/response models
- service: CalibrationService, GatingPolicyService
- methods: Temperature scaling, ensemble, MC-dropout calibration
- uncertainty: Aleatoric vs epistemic decomposition
- metrics: ECE, MCE, Brier score
- config: Configuration loaders
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-28T21:06:46Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from core.calibration.config import (
    load_calibration_config,
    load_gating_config,
)
from core.calibration.schemas import (
    # Request/Response (full)
    CalibrateRequest,
    # Config
    CalibrationConfig,
    # Enums
    CalibrationMethod,
    CalibrationResult,
    GateRequest,
    GateResult,
    GatingAction,
    GatingPolicyConfig,
    # Request/Response (simplified for executor integration)
    SimpleCalibrationRequest,
    SimpleCalibrationResult,
    SimpleGateRequest,
    SimpleGateResult,
    UncertaintyDecompositionMethod,
)
from core.calibration.service import (
    CalibrationService,
    GatingPolicyService,
)

__all__ = [
    # Enums
    "CalibrationMethod",
    "UncertaintyDecompositionMethod",
    "GatingAction",
    # Request/Response (full)
    "CalibrateRequest",
    "CalibrationResult",
    "GateRequest",
    "GateResult",
    # Request/Response (simplified for executor integration)
    "SimpleCalibrationRequest",
    "SimpleCalibrationResult",
    "SimpleGateRequest",
    "SimpleGateResult",
    # Config
    "CalibrationConfig",
    "GatingPolicyConfig",
    # Services
    "CalibrationService",
    "GatingPolicyService",
    # Loaders
    "load_calibration_config",
    "load_gating_config",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-062",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.calibration.config",
        "core.calibration.schemas",
        "core.calibration.service",
    ],
    "tags": ["core", "foundation", "metrics", "schema"],
    "keywords": [
        "calibration",
        "decomposition",
        "governance",
        "module",
        "service",
        "uncertainty",
    ],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:46Z",
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
