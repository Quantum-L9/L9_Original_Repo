"""
L9 Calibration Configuration Loader

Loads CalibrationConfig and GatingPolicyConfig from:
- YAML config file, or
- Environment variables

Reference: L9-Confidence-Calibration-Spec.md §5
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Config",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-28T21:06:46Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "config",
    "type": "config",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.calibration.__init__"],
    },
}
# ============================================================================

import os
from pathlib import Path

import yaml

from core.calibration.schemas import (
    CalibrationConfig,
    CalibrationMethod,
    GatingPolicyConfig,
    UncertaintyDecompositionMethod,
)


def _str_to_bool(value: str) -> bool:
    """
    Converts a string representation to a boolean value for calibration configuration parsing.
    Args:
        value: String input from environment variable or YAML file indicating boolean state.
    Returns:
        Boolean value corresponding to the input string.
    """
    return value.lower() in {"1", "true", "yes", "y", "on"}


def load_calibration_config(config_file: str | None = None) -> CalibrationConfig:
    """Load CalibrationConfig from YAML file or environment variables."""
    if config_file:
        path = Path(config_file)
        if not path.is_file():
            raise FileNotFoundError(f"Calibration config file not found: {config_file}")
        data = yaml.safe_load(path.read_text()) or {}
        return CalibrationConfig(**data.get("calibration", data))

    enabled = _str_to_bool(os.getenv("L9_CALIB_ENABLED", "true"))
    primary_method = CalibrationMethod(
        os.getenv("L9_CALIB_PRIMARY_METHOD", "temperature_scaling")
    )
    decomposition_method = UncertaintyDecompositionMethod(
        os.getenv("L9_CALIB_DECOMPOSITION_METHOD", "hybrid")
    )
    confidence_threshold_proceed = float(  # nosemgrep: l9-float-requires-try-except
        os.getenv("L9_CALIB_CONFIDENCE_THRESHOLD_PROCEED", "0.75")
    )
    confidence_threshold_defer = float(  # nosemgrep: l9-float-requires-try-except
        os.getenv("L9_CALIB_CONFIDENCE_THRESHOLD_DEFER", "0.60")
    )
    epistemic_threshold_high = float(  # nosemgrep: l9-float-requires-try-except
        os.getenv("L9_CALIB_EPISTEMIC_THRESHOLD_HIGH", "0.25")
    )
    aleatoric_threshold_high = float(  # nosemgrep: l9-float-requires-try-except
        os.getenv("L9_CALIB_ALEATORIC_THRESHOLD_HIGH", "0.20")
    )

    return CalibrationConfig(
        enabled=enabled,
        primary_method=primary_method,
        decomposition_method=decomposition_method,
        confidence_threshold_proceed=confidence_threshold_proceed,
        confidence_threshold_defer=confidence_threshold_defer,
        epistemic_threshold_high=epistemic_threshold_high,
        aleatoric_threshold_high=aleatoric_threshold_high,
    )


def load_gating_config(config_file: str | None = None) -> GatingPolicyConfig:
    """Load GatingPolicyConfig from YAML file or environment variables."""
    if config_file:
        path = Path(config_file)
        if not path.is_file():
            raise FileNotFoundError(f"Gating config file not found: {config_file}")
        data = yaml.safe_load(path.read_text()) or {}
        return GatingPolicyConfig(**data.get("gating", data))

    enabled = _str_to_bool(os.getenv("L9_GATE_ENABLED", "true"))
    high_stakes_confidence_min = float(  # nosemgrep: l9-float-requires-try-except
        os.getenv("L9_GATE_HIGH_STAKES_CONFIDENCE_MIN", "0.85")
    )
    defer_confidence_threshold = float(  # nosemgrep: l9-float-requires-try-except
        os.getenv("L9_GATE_DEFER_CONFIDENCE_THRESHOLD", "0.60")
    )
    defer_epistemic_threshold = float(  # nosemgrep: l9-float-requires-try-except
        os.getenv("L9_GATE_DEFER_EPISTEMIC_THRESHOLD", "0.30")
    )

    return GatingPolicyConfig(
        enabled=enabled,
        high_stakes_confidence_min=high_stakes_confidence_min,
        defer_confidence_threshold=defer_confidence_threshold,
        defer_epistemic_threshold=defer_epistemic_threshold,
    )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-060",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.calibration.schemas"],
    "tags": ["config", "core", "filesystem", "foundation"],
    "keywords": ["calibration", "gating", "load"],
    "business_value": "Utility module for config",
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
