"""
---
suite: "L9 Autonomous Agent OS"
title: "Subjective Logic Adapter"
component_id: "INT-SUBJ-002"
component_name: "Subjective Logic Adapter"
layer: "intelligence"
domain: "probabilistic_reasoning"
type: "reasoning_engine"
status: "active"
maturity_level: "production"
version: "1.0.0"
version_date: "2025-11-20"
created: "2025-11-20T18:04:00Z"
updated: "2025-11-20T18:04:00Z"
author: "Igor Beylin"
owner: "L9 Core"
governance_level: "medium"
reasoning_modes: ["deductive"]
reasoning_stack: "hybrid_l9"
autonomous_capable: true
strategic_impact: "high"
leverage_multiplier: "5x"
dependencies: []
integrates_with: ["INT-RSN-006"]
purpose: "Convert Bayesian probabilities to Subjective Logic opinions (belief/disbelief/uncertainty)"
summary: "Adapter providing Trust/Disbelief/Uncertainty representation for governance and TrustIndex"
business_value: "Enables nuanced confidence representation beyond simple probabilities for better governance decisions"
tags: ["subjective-logic", "bayesian", "confidence", "trust", "uncertainty"]
vcs_path: "core/bayesian/subjective_logic.py"
---

"""
# ============================================================================
__dora_meta__ = {
    "component_name": "Subjective Logic",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-27T02:13:14Z",
    "updated_at": "2026-01-21T21:57:31Z",
    "layer": "foundation",
    "domain": "current_work",
    "module_name": "subjective_logic",
    "type": "adapter",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

"""
Subjective Logic Adapter
Based on: Original L9 Vision + Subjective Logic Framework (Jøsang)
Reference: aeos/probability/subjective_logic_adapter.md

Converts Bayesian probabilities to Subjective Logic opinions:
- Belief (b): Evidence supporting proposition
- Disbelief (d): Evidence against proposition  
- Uncertainty (u): Lack of evidence
- Constraint: b + d + u = 1

Feature Flag: ENABLE_SUBJECTIVE_LOGIC (default: false)
"""
from typing import Dict, Any, Tuple
import os
import structlog
import math

logger = structlog.get_logger(__name__)


class SubjectiveLogicAdapter:
    """
    Adapter between Bayesian probabilities and Subjective Logic opinions.
    
    Provides Trust/Disbelief/Uncertainty representation for governance.
    
    Reference: Original L9 Vision - Probabilistic Reasoning Engine
    """
    
    def __init__(self):
        """Initialize Subjective Logic adapter."""
        logger.info("Subjective Logic adapter initialized")
    
    def from_probability(
        self,
        probability: float,
        uncertainty: float
    ) -> Dict[str, float]:
        """
        Convert probability + uncertainty to subjective logic opinion.
        
        Args:
            probability: Probability estimate [0, 1]
            uncertainty: Epistemic uncertainty [0, 1]
            
        Returns:
            Opinion with belief, disbelief, uncertainty
        """
        # Clamp inputs
        p = max(0.0, min(1.0, probability))
        u = max(0.0, min(1.0, uncertainty))
        
        # Map to subjective logic
        # High uncertainty → high u
        # Low uncertainty → distribute to b/d based on probability
        
        if u > 0.9:
            # Very uncertain → most weight to uncertainty
            belief = p * (1 - u)
            disbelief = (1 - p) * (1 - u)
            uncertainty_sl = u
        else:
            # More certain → distribute to belief/disbelief
            belief = p * (1 - u)
            disbelief = (1 - p) * (1 - u)
            uncertainty_sl = u
        
        # Normalize to ensure b + d + u = 1
        total = belief + disbelief + uncertainty_sl
        if total > 0:
            belief /= total
            disbelief /= total
            uncertainty_sl /= total
        
        opinion = {
            'belief': belief,
            'disbelief': disbelief,
            'uncertainty': uncertainty_sl
        }
        
        # Validate constraint
        assert abs(sum(opinion.values()) - 1.0) < 1e-6, "Subjective logic constraint violated"
        
        return opinion
    
    def from_beta(self, alpha: float, beta: float) -> Dict[str, float]:
        """
        Convert Beta distribution parameters to subjective logic opinion.
        
        Beta(α, β) represents posterior after observing evidence.
        
        Args:
            alpha: Beta alpha parameter (successes + 1)
            beta: Beta beta parameter (failures + 1)
            
        Returns:
            Opinion with belief, disbelief, uncertainty
        """
        # Total evidence
        W = alpha + beta - 2  # Remove prior counts
        
        if W == 0:
            # No evidence → maximum uncertainty
            return {
                'belief': 0.0,
                'disbelief': 0.0,
                'uncertainty': 1.0
            }
        
        # Subjective logic from Beta
        # Reference: Jøsang's mapping
        r = alpha - 1  # Positive evidence
        s = beta - 1   # Negative evidence
        
        belief = r / (W + 2)
        disbelief = s / (W + 2)
        uncertainty = 2 / (W + 2)
        
        opinion = {
            'belief': belief,
            'disbelief': disbelief,
            'uncertainty': uncertainty
        }
        
        # Validate
        assert abs(sum(opinion.values()) - 1.0) < 1e-6
        
        return opinion
    
    def to_probability(
        self,
        belief: float,
        disbelief: float,
        uncertainty: float,
        base_rate: float = 0.5
    ) -> float:
        """
        Convert subjective logic opinion to probability.
        
        Uses base rate to resolve uncertainty.
        
        Args:
            belief: Belief value
            disbelief: Disbelief value
            uncertainty: Uncertainty value
            base_rate: Prior probability (default: 0.5 = uninformative)
            
        Returns:
            Probability estimate
        """
        # Validate input
        total = belief + disbelief + uncertainty
        assert abs(total - 1.0) < 1e-6, f"Opinion must sum to 1.0, got {total}"
        
        # Probability = belief + (uncertainty × base_rate)
        probability = belief + (uncertainty * base_rate)
        
        return probability
    
    def combine_opinions(
        self,
        opinion1: Dict[str, float],
        opinion2: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Combine two subjective logic opinions.
        
        Uses consensus operator (averaging).
        
        Args:
            opinion1: First opinion
            opinion2: Second opinion
            
        Returns:
            Combined opinion
        """
        # Simple averaging (upgrade to proper operators later)
        combined = {
            'belief': (opinion1['belief'] + opinion2['belief']) / 2,
            'disbelief': (opinion1['disbelief'] + opinion2['disbelief']) / 2,
            'uncertainty': (opinion1['uncertainty'] + opinion2['uncertainty']) / 2
        }
        
        # Normalize
        total = sum(combined.values())
        if total > 0:
            for key in combined:
                combined[key] /= total
        
        return combined
    
    def opinion_to_confidence(self, opinion: Dict[str, float]) -> float:
        """
        Convert opinion to confidence score.
        
        Confidence = belief / (belief + disbelief + small_epsilon)
        
        Args:
            opinion: Subjective logic opinion
            
        Returns:
            Confidence score [0, 1]
        """
        b = opinion['belief']
        d = opinion['disbelief']
        u = opinion['uncertainty']
        
        # Confidence decreases with uncertainty
        # High belief + low uncertainty = high confidence
        confidence = b / (b + d + u + 1e-6)
        
        # Penalize high uncertainty
        confidence *= (1 - u)
        
        return max(0.0, min(1.0, confidence))


def subjective_logic_enabled() -> bool:
    """Check if Subjective Logic is enabled via feature flag."""
    return os.getenv("ENABLE_SUBJECTIVE_LOGIC", "false").lower() == "true"


# Validation
if __name__ == "__main__":
    logger.info("Testing Subjective Logic Adapter...")
    
    adapter = SubjectiveLogicAdapter()
    
    # Test from_probability
    opinion1 = adapter.from_probability(probability=0.8, uncertainty=0.2)
    logger.info("From probability (p=0.8, u=0.2)", 
                belief=f"{opinion1['belief']:.3f}",
                disbelief=f"{opinion1['disbelief']:.3f}",
                uncertainty=f"{opinion1['uncertainty']:.3f}",
                total=f"{sum(opinion1.values()):.6f}")
    
    # Test from_beta
    opinion2 = adapter.from_beta(alpha=10, beta=3)
    logger.info("From Beta(10, 3)",
                belief=f"{opinion2['belief']:.3f}",
                disbelief=f"{opinion2['disbelief']:.3f}",
                uncertainty=f"{opinion2['uncertainty']:.3f}")
    
    # Test to_probability
    prob = adapter.to_probability(**opinion1)
    logger.info("Back to probability", probability=f"{prob:.3f}")
    
    # Test combine
    combined = adapter.combine_opinions(opinion1, opinion2)
    logger.info("Combined opinion",
                belief=f"{combined['belief']:.3f}",
                disbelief=f"{combined['disbelief']:.3f}",
                uncertainty=f"{combined['uncertainty']:.3f}")
    
    # Test confidence
    confidence = adapter.opinion_to_confidence(opinion1)
    logger.info("Confidence", value=f"{confidence:.3f}")
    
    # Validate constraints
    assert abs(sum(opinion1.values()) - 1.0) < 1e-6
    assert abs(sum(opinion2.values()) - 1.0) < 1e-6
    assert abs(sum(combined.values()) - 1.0) < 1e-6
    assert 0.0 <= confidence <= 1.0
    
    logger.info("Subjective Logic adapter validated", status="success")

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["adapter", "adapter-pattern", "auth", "current-work", "foundation", "logging", "testing"],
    "keywords": ["adapter", "agent", "bayesian", "beta", "combine", "confidence", "core", "disbelief"],
    "business_value": "Implements SubjectiveLogicAdapter for subjective logic functionality",
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
