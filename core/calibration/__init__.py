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

from core.calibration.schemas import (
    # Enums
    CalibrationMethod,
    UncertaintyDecompositionMethod,
    GatingAction,
    # Request/Response (full)
    CalibrateRequest,
    CalibrationResult,
    GateRequest,
    GateResult,
    # Request/Response (simplified for executor integration)
    SimpleCalibrationRequest,
    SimpleCalibrationResult,
    SimpleGateRequest,
    SimpleGateResult,
    # Config
    CalibrationConfig,
    GatingPolicyConfig,
)

from core.calibration.service import (
    CalibrationService,
    GatingPolicyService,
)

from core.calibration.config import (
    load_calibration_config,
    load_gating_config,
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
