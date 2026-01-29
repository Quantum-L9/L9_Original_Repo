"""
---
suite: "L9 Agent Framework v3.0 (Cursor Governance Suite 6)"
title: "Uncertainty"
component_id: "INT-RSN-003"
component_name: "Uncertainty"
layer: "intelligence"
domain: "reasoning"
type: "executable_script"
status: "active"
maturity_level: "production"

version: "1.0.0"
version_date: "2025-11-20"
created: "2025-11-20T16:42:01Z"
updated: "2025-11-20T16:42:01Z"
deprecated_date: null
changelog_url: "CHANGELOG.md#v1.0.0"
breaking_changes: false

author: "Igor Beylin"
owner: "Igor Beylin"
maintainer: "Igor Beylin"
team: "L9 Core"
contact: "igor@example.com"

governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"
requires_approval: true
approval_authority: "L9_Architect"

# === L9 REASONING METADATA ===
reasoning_modes: []
reasoning_stack: "hybrid_l9"
command_type: null
agent_permissions: []
requires_human_approval: false
autonomous_capable: false
strategic_impact: "high"
leverage_multiplier: "10x"

# === TECHNICAL METADATA ===
dependencies: []
integrates_with: []
replaces: null
api_endpoints: []
data_sources: []
outputs: []
runtime_requirements: []
implementation_status:
  component: null
  role: null
  status: "missing"
  runtime_location: null

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "interactive"
sla_response_time: "200ms"
resource_intensity: "medium"

# === BUSINESS METADATA ===
purpose: "Brief description of what this component does"
summary: "One-sentence summary of functionality and value"
business_value: "Description of business value delivered"
success_metrics: []
business_priority: "high"

# === INTEGRATION & MIGRATION ===
suite_origin: "Suite 6"
migration_source: null
migration_notes: ""
integration_pattern: "sync"

# === DEPLOYMENT & INFRASTRUCTURE ===
deployment_platform: "cursor"
deployment_environment: "production"
framework: "l9_v3"
phase: "1.0"

# === AI & AUTOMATION METADATA ===
ai_assisted: true
human_review_required: true
automation_level: "full"
self_healing: true
learning_enabled: true
meta_learning: true

# === GITHUB & VCS METADATA ===
github_repo: null
vcs_path: null
code_owners: ["@igor-beylin"]
branch_protection: true

# === OBSERVABILITY ===
metrics_enabled: true
alerts_configured: true
telemetry_level: "standard"

# === TAGS & DISCOVERY ===
tags: []
keywords: []
related_components: []
startup_required: false
mode_type: null
---

"""
# ============================================================================
__dora_meta__ = {
    "component_name": "Uncertainty",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-27T02:13:14Z",
    "updated_at": "2026-01-21T21:57:31Z",
    "layer": "foundation",
    "domain": "api_gateway",
    "module_name": "uncertainty",
    "type": "router",
    "status": "deprecated",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

"""
Bayesian Uncertainty Quantification Engine
Based on: Bayesian Reasoning Framework research + bayesian-torch + TFP

Every L9 decision must return epistemic + aleatoric uncertainty.
Reference: Bayesian Reasoning Frameworks.md Sections 5-7
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, Optional
import numpy as np
from collections import defaultdict
import structlog

logger = structlog.get_logger(__name__)

try:
    from bayesian_torch.layers import LinearReparameterization
    BAYESIAN_TORCH_AVAILABLE = True
except ImportError:
    BAYESIAN_TORCH_AVAILABLE = False


class BayesianUncertainty:
    """
    Complete Bayesian uncertainty quantification.
    
    Returns:
    - Epistemic uncertainty (model uncertainty, reducible with data)
    - Aleatoric uncertainty (data noise, irreducible)
    - Calibrated confidence (via temperature scaling)
    - OOD detection (via epistemic threshold)
    
    Methods:
    - MC Dropout for epistemic
    - Ensemble disagreement for epistemic
    - Heteroscedastic head for aleatoric
    - Temperature scaling for calibration
    """
    
    def __init__(
        self,
        n_samples: int = 100,
        ood_threshold: float = 0.5,
        temperature: float = 1.0
    ):
        """
        Initialize Bayesian uncertainty engine.
        
        Args:
            n_samples: MC samples for epistemic uncertainty
            ood_threshold: Epistemic std threshold for OOD detection
            temperature: Temperature for calibration (learned from val set)
        """
        self.n_samples = n_samples
        self.ood_threshold = ood_threshold
        self.temperature = temperature
        
        # Calibration history for ECE computation
        self.predictions = []
        self.outcomes = []
    
    def quantify(
        self,
        model: nn.Module,
        x: torch.Tensor,
        return_samples: bool = False
    ) -> Dict[str, Any]:
        """
        Compute full Bayesian posterior for prediction.
        
        Args:
            model: PyTorch model with dropout or ensemble
            x: Input tensor
            return_samples: Whether to return all MC samples
            
        Returns:
            Dictionary with:
            - mean: Posterior mean prediction
            - epistemic_std: Model uncertainty
            - aleatoric_std: Data uncertainty
            - confidence: Calibrated confidence score
            - is_ood: Whether input is out-of-distribution
            - samples: (optional) All MC samples
        """
        # Ensure input is batched
        if x.dim() == 1:
            x = x.unsqueeze(0)
        
        # Get epistemic uncertainty via MC sampling
        epistemic_std, samples = self._compute_epistemic(model, x)
        
        # Get aleatoric uncertainty from model
        aleatoric_std = self._compute_aleatoric(model, x)
        
        # Compute mean prediction
        mean = samples.mean(dim=0)
        
        # Apply temperature scaling for calibration
        calibrated_mean = self._temperature_scale(mean)
        
        # Compute calibrated confidence
        confidence = self._compute_confidence(epistemic_std, aleatoric_std)
        
        # OOD detection via epistemic threshold
        is_ood = epistemic_std > self.ood_threshold
        
        result = {
            'mean': float(calibrated_mean.item()) if calibrated_mean.numel() == 1 else calibrated_mean.cpu().numpy(),
            'epistemic_std': float(epistemic_std.item()),
            'aleatoric_std': float(aleatoric_std.item()),
            'confidence': float(confidence.item()),
            'is_ood': bool(is_ood.item())
        }
        
        if return_samples:
            result['samples'] = samples.cpu().numpy()
        
        return result
    
    def _compute_epistemic(
        self,
        model: nn.Module,
        x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Compute epistemic uncertainty via MC dropout.
        
        Model uncertainty that reduces with more training data.
        """
        # Enable dropout for uncertainty estimation
        model.train()
        
        # Multiple forward passes
        samples = []
        with torch.no_grad():
            for _ in range(self.n_samples):
                output = model(x)
                samples.append(output)
        
        samples = torch.stack(samples)
        
        # Epistemic = variance across predictions
        epistemic_std = samples.std(dim=0)
        
        # Return to eval mode
        model.eval()
        
        return epistemic_std, samples
    
    def _compute_aleatoric(
        self,
        model: nn.Module,
        x: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute aleatoric uncertainty.
        
        Data noise that persists regardless of model improvements.
        Requires model to have aleatoric_head that predicts noise.
        """
        if hasattr(model, 'aleatoric_head'):
            with torch.no_grad():
                # Model predicts its own uncertainty
                aleatoric = model.aleatoric_head(x)
                return aleatoric
        else:
            # If no aleatoric head, return zero
            # (assumes homoscedastic noise)
            return torch.zeros(1)
    
    def _temperature_scale(self, logits: torch.Tensor) -> torch.Tensor:
        """
        Apply temperature scaling for calibration.
        
        Temperature learned from validation set to minimize ECE.
        """
        if logits.dim() > 1 and logits.shape[-1] > 1:
            # Multi-class: apply softmax with temperature
            return F.softmax(logits / self.temperature, dim=-1)
        else:
            # Regression: scale directly
            return logits / self.temperature
    
    def _compute_confidence(
        self,
        epistemic: torch.Tensor,
        aleatoric: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute calibrated confidence score.
        
        Confidence decreases with total uncertainty.
        """
        # Total uncertainty (epistemic + aleatoric)
        total_uncertainty = torch.sqrt(epistemic**2 + aleatoric**2)
        
        # Confidence = 1 / (1 + uncertainty)
        confidence = 1.0 / (1.0 + total_uncertainty)
        
        return confidence
    
    def update_calibration(self, prediction: float, actual: float):
        """
        Update calibration history for ECE computation.
        
        Call this after observing outcome to track calibration.
        """
        self.predictions.append(prediction)
        self.outcomes.append(actual)
    
    def compute_ece(self, n_bins: int = 10) -> float:
        """
        Compute Expected Calibration Error.
        
        Measures gap between predicted confidence and actual accuracy.
        Target: ECE < 0.05
        
        Returns:
            ECE: Expected calibration error (lower is better)
        """
        if len(self.predictions) < n_bins:
            return float('nan')  # Not enough data
        
        predictions = np.array(self.predictions)
        outcomes = np.array(self.outcomes)
        
        # Create bins
        bins = np.linspace(0, 1, n_bins + 1)
        
        ece = 0.0
        for i in range(n_bins):
            # Find predictions in this bin
            mask = (predictions >= bins[i]) & (predictions < bins[i+1])
            
            if mask.sum() > 0:
                bin_predictions = predictions[mask]
                bin_outcomes = outcomes[mask]
                
                # Average confidence in bin
                avg_confidence = bin_predictions.mean()
                
                # Average accuracy in bin
                avg_accuracy = bin_outcomes.mean()
                
                # Contribution to ECE
                bin_size = mask.sum() / len(predictions)
                ece += bin_size * abs(avg_confidence - avg_accuracy)
        
        return ece
    
    def set_ood_threshold(self, validation_epistemic: np.ndarray, percentile: float = 95):
        """
        Set OOD threshold based on validation set epistemic uncertainty.
        
        Args:
            validation_epistemic: Epistemic std on validation set
            percentile: Percentile for threshold (95 = flag top 5% as OOD)
        """
        self.ood_threshold = np.percentile(validation_epistemic, percentile)


class DeepEnsemble:
    """
    Deep ensemble for implicit Bayesian inference.
    
    Train multiple models independently, aggregate predictions.
    Reference: Deep ensembles paper + Bayesian connection theory
    """
    
    def __init__(self, n_models: int = 5):
        """
        Initialize ensemble.
        
        Args:
            n_models: Number of models in ensemble (5 is good balance)
        """
        self.n_models = n_models
        self.models = []
    
    def add_model(self, model: nn.Module):
        """Add trained model to ensemble."""
        if len(self.models) >= self.n_models:
            raise ValueError(f"Ensemble already has {self.n_models} models")
        self.models.append(model)
    
    def predict_with_uncertainty(self, x: torch.Tensor) -> Dict[str, Any]:
        """
        Ensemble prediction with epistemic uncertainty.
        
        Disagreement across models = epistemic uncertainty.
        """
        predictions = []
        
        for model in self.models:
            model.eval()
            with torch.no_grad():
                pred = model(x)
                predictions.append(pred)
        
        predictions = torch.stack(predictions)
        
        # Mean = ensemble prediction
        mean = predictions.mean(dim=0)
        
        # Std = epistemic uncertainty
        epistemic_std = predictions.std(dim=0)
        
        return {
            'mean': mean,
            'epistemic_std': epistemic_std,
            'predictions': predictions
        }


# Example usage and validation
if __name__ == "__main__":
    logger.info("Testing Bayesian Uncertainty Engine...")
    
    # Create simple test model
    class TestModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(10, 1)
            self.dropout = nn.Dropout(0.5)
        
        def forward(self, x):
            x = self.dropout(x)
            return self.fc(x)
    
    model = TestModel()
    uncertainty = BayesianUncertainty(n_samples=100)
    
    # Test input
    x = torch.randn(1, 10)
    
    # Get posterior
    result = uncertainty.quantify(model, x)
    
    logger.info("Bayesian Posterior",
                mean=f"{result['mean']:.3f}",
                epistemic_std=f"{result['epistemic_std']:.3f}",
                aleatoric_std=f"{result['aleatoric_std']:.3f}",
                confidence=f"{result['confidence']:.3f}",
                is_ood=result['is_ood'])
    
    # Validate requirements
    assert 'epistemic_std' in result
    assert 'aleatoric_std' in result
    assert 'confidence' in result
    assert result['epistemic_std'] >= 0
    assert 0 <= result['confidence'] <= 1
    
    logger.info("Bayesian uncertainty engine validated", status="success")

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-FOUN-002",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "api-gateway", "audit-tool", "auth", "authorization", "batch-processing", "foundation", "logging", "metrics", "migration"],
    "keywords": ["agent", "bayesian", "beylin", "business", "calibration", "component", "compute", "cursor"],
    "business_value": "Provides uncertainty components including BayesianUncertainty, DeepEnsemble, TestModel",
    "last_modified": "2026-01-21T21:57:31Z",
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
