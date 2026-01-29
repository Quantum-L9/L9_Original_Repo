"""
L9 Calibration Module: Pydantic Schemas

Request/response models and enums for:
- Confidence calibration (post-inference, pre-gating)
- Uncertainty decomposition (aleatoric vs epistemic)
- Decision-aware gating (defer, fallback, approve, etc.)

All models have strict validation: extra="forbid"
All numeric fields have constraints: Field(..., ge=0.0, le=1.0)

Reference: L9-Confidence-Calibration-Spec.md §2.1.1
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────


class CalibrationMethod(str, Enum):
    """Supported calibration techniques."""

    TEMPERATURE_SCALING = "temperature_scaling"
    DIRICHLET_EVIDENTIAL = "dirichlet_evidential"
    ENSEMBLE = "ensemble"
    MC_DROPOUT = "mc_dropout"
    CONFORMAL = "conformal"
    MIXUP = "mixup"


class UncertaintyDecompositionMethod(str, Enum):
    """How aleatoric vs epistemic uncertainty is computed."""

    HETEROSCEDASTIC_HEAD = "heteroscedastic_head"
    ENSEMBLE_DISAGREEMENT = "ensemble_disagreement"
    MC_DROPOUT_VAR = "mc_dropout_variance"
    BAYESIAN_POSTERIOR = "bayesian_posterior"
    HYBRID = "hybrid"


class GatingAction(str, Enum):
    """Decision actions from gating policy."""

    PROCEED = "proceed"
    ROUTE_TO_FALLBACK = "route_to_fallback"
    DEFER_TO_HUMAN = "defer_to_human"
    REQUIRE_APPROVAL = "require_approval"
    TRIGGER_ACTIVE_LEARNING = "trigger_active_learning"
    ABSTAIN = "abstain"


# ─────────────────────────────────────────────────────────────────
# REQUEST/RESPONSE MODELS
# ─────────────────────────────────────────────────────────────────


class CalibrateRequest(BaseModel):
    """Request to calibrate raw model outputs."""

    task_id: UUID
    predicted_class: int = Field(..., ge=0)
    logits: list[float]
    class_probabilities: list[float]
    model_outputs: Optional[dict[str, Any]] = None
    domain_context: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    @field_validator("logits", "class_probabilities")
    @classmethod
    def validate_probability_like(cls, v: list[float]) -> list[float]:
        if not v:
            raise ValueError("Must not be empty")
        if len(v) < 2:
            raise ValueError("Must have at least 2 elements")
        return v

    model_config = {"extra": "forbid"}


class CalibrationResult(BaseModel):
    """Result of calibration."""

    calibration_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    predicted_class: int = Field(..., ge=0)

    # Calibrated confidence scores
    calibrated_probabilities: list[float]
    predicted_class_confidence: float = Field(..., ge=0.0, le=1.0)
    top_k_confidence: Optional[list[tuple[int, float]]] = None

    # Uncertainty decomposition
    aleatoric_uncertainty: float = Field(..., ge=0.0, le=1.0)
    epistemic_uncertainty: float = Field(..., ge=0.0, le=1.0)
    total_uncertainty: float = Field(..., ge=0.0, le=1.0)

    # Metadata
    calibration_method: CalibrationMethod
    decomposition_method: UncertaintyDecompositionMethod
    quality_score: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("calibrated_probabilities")
    @classmethod
    def validate_probability_distribution(cls, v: list[float]) -> list[float]:
        total = sum(v)
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Probabilities must sum to ~1.0, got {total}")
        return v

    model_config = {"extra": "forbid"}


class GateRequest(BaseModel):
    """Request for gating decision."""

    task_id: UUID
    agent_id: str
    action: str
    predicted_class: int = Field(..., ge=0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    aleatoric_uncertainty: float = Field(..., ge=0.0, le=1.0)
    epistemic_uncertainty: float = Field(..., ge=0.0, le=1.0)
    domain_context: Optional[str] = None
    action_is_high_stakes: bool = False
    action_is_exploratory: bool = False
    symbolic_constraints_met: Optional[int] = None
    metadata: Optional[dict[str, Any]] = None

    model_config = {"extra": "forbid"}


class GateResult(BaseModel):
    """Decision from gating policy."""

    gating_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    action: str

    # Decision
    gating_action: GatingAction
    approved: bool

    # Reasoning
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    aleatoric_uncertainty: float = Field(..., ge=0.0, le=1.0)
    epistemic_uncertainty: float = Field(..., ge=0.0, le=1.0)
    violated_thresholds: list[str] = Field(default_factory=list)
    decision_reason: str = Field(..., min_length=1, max_length=500)

    # Recommendations
    recommended_fallback: Optional[str] = None
    requested_approval_type: Optional[str] = None
    next_step: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("approved")
    @classmethod
    def validate_approved_consistency(cls, v: bool, info) -> bool:
        if "gating_action" in info.data:
            action = info.data["gating_action"]
            expected = action in [GatingAction.PROCEED, GatingAction.REQUIRE_APPROVAL]
            if v != expected:
                raise ValueError(
                    f"approved={v} inconsistent with gating_action={action}. "
                    f"Should be {expected}"
                )
        return v

    model_config = {"extra": "forbid"}


# ─────────────────────────────────────────────────────────────────
# CONFIGURATION MODELS
# ─────────────────────────────────────────────────────────────────


class CalibrationConfig(BaseModel):
    """Configuration for calibration module."""

    enabled: bool = True

    # Methods
    primary_method: CalibrationMethod = CalibrationMethod.TEMPERATURE_SCALING
    fallback_methods: list[CalibrationMethod] = Field(
        default=[CalibrationMethod.ENSEMBLE]
    )

    # Ensemble config
    ensemble_size: int = Field(default=5, ge=1, le=50)
    ensemble_aggregation: Literal["mean", "median", "max"] = "mean"

    # MC-Dropout config
    mc_samples: int = Field(default=10, ge=1, le=100)
    mc_dropout_rate: float = Field(default=0.1, ge=0.0, le=0.5)

    # Uncertainty decomposition
    decomposition_method: UncertaintyDecompositionMethod = (
        UncertaintyDecompositionMethod.HYBRID
    )
    compute_aleatoric: bool = True
    compute_epistemic: bool = True

    # Thresholds (tuned per domain)
    confidence_threshold_proceed: float = Field(default=0.7, ge=0.0, le=1.0)
    confidence_threshold_fallback: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence_threshold_defer: float = Field(default=0.6, ge=0.0, le=1.0)

    epistemic_threshold_high: float = Field(default=0.3, ge=0.0, le=1.0)
    aleatoric_threshold_high: float = Field(default=0.2, ge=0.0, le=1.0)

    model_config = {"extra": "forbid"}


class GatingPolicyConfig(BaseModel):
    """Configuration for decision gating."""

    enabled: bool = True

    # Thresholds
    high_stakes_confidence_min: float = Field(default=0.8, ge=0.0, le=1.0)
    high_stakes_epistemic_max: float = Field(default=0.1, ge=0.0, le=1.0)
    defer_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    defer_epistemic_threshold: float = Field(default=0.3, ge=0.0, le=1.0)

    # Behavior
    require_approval_high_stakes: bool = True
    trigger_active_learning: bool = True
    enable_fallback_routing: bool = True

    # Symbolic constraints
    enforce_symbolic_constraints: bool = True
    constraint_violation_penalty: float = Field(default=0.1, ge=0.0, le=1.0)

    model_config = {"extra": "forbid"}


# ─────────────────────────────────────────────────────────────────
# SIMPLIFIED EXECUTOR INTEGRATION MODELS
# ─────────────────────────────────────────────────────────────────
# These models provide a simpler interface for L9 executor integration.
# The executor provides basic confidence values; these models adapt
# to work with what L9 already produces without requiring executor changes.
# Rule: New code adapts to L9, not the other way around.


class SimpleCalibrationRequest(BaseModel):
    """
    Simplified calibration request for executor integration.
    
    Works with what executor naturally provides:
    - A single confidence value (0.0-1.0)
    - Optional task context
    
    This adapts to L9's existing patterns rather than forcing
    executor changes.
    """

    confidence: float = Field(..., ge=0.0, le=1.0, description="Raw model confidence")
    task_id: Optional[str] = None
    method: CalibrationMethod = CalibrationMethod.TEMPERATURE_SCALING

    model_config = {"extra": "forbid"}


class SimpleCalibrationResult(BaseModel):
    """
    Simplified calibration result for executor integration.
    
    Returns only what the executor needs:
    - Calibrated confidence
    - Uncertainty estimate
    - Whether to proceed
    """

    calibrated_confidence: float = Field(..., ge=0.0, le=1.0)
    uncertainty: float = Field(default=0.0, ge=0.0, le=1.0)
    should_proceed: bool = True
    reason: Optional[str] = None

    model_config = {"extra": "forbid"}


class SimpleGateRequest(BaseModel):
    """
    Simplified gating request for executor integration.
    
    Works with what executor naturally provides:
    - Confidence value
    - Tool being called
    - Optional context
    """

    confidence: float = Field(..., ge=0.0, le=1.0)
    tool_id: str
    task_id: Optional[str] = None
    context: Optional[dict[str, Any]] = None

    model_config = {"extra": "forbid"}


class SimpleGateResult(BaseModel):
    """
    Simplified gating result for executor integration.
    
    Returns only what executor needs:
    - Approved or not
    - Threshold used
    - Reason for decision
    """

    approved: bool
    threshold: float = Field(..., ge=0.0, le=1.0)
    reason: str
    action: GatingAction = GatingAction.PROCEED

    model_config = {"extra": "forbid"}
