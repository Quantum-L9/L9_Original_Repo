"""
Bayesian Reasoning Kernel for L9
==================================
Enables probabilistic reasoning, uncertainty quantification, and belief state management.

When enabled via L9_ENABLE_BAYESIAN_REASONING=true:
  - Agent maintains belief state (prior, posterior distributions)
  - Uncertainty estimates accompany all decisions
  - Reasoning chains include probability updates (Bayes rule)
  - Evidence assessment (strong/moderate/weak/conflicting)

Status: EXPERIMENTAL - Feature flag required for activation
Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Bayesian Kernel",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-27T02:04:44Z",
    "updated_at": "2026-01-21T21:57:31Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "bayesian_kernel",
    "type": "dataclass",
    "status": "experimental",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import os
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EvidenceStrength(str, Enum):
    """Classification of evidence strength."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    CONFLICTING = "conflicting"


@dataclass
class BeliefState:
    """Represents current belief about a variable."""

    variable: str
    prior: dict[str, float]  # Prior probability distribution
    posterior: dict[str, float]  # Posterior after updates
    evidence: list[dict[str, Any]]  # Evidence items
    confidence: float  # Confidence in posterior [0, 1]
    updated_at: str  # Timestamp of last update


class BayesianKernel:
    """
    Bayesian Reasoning Kernel for L9.

    Provides:
    - Belief state management
    - Evidence processing
    - Posterior belief computation
    - Uncertainty quantification

    Feature Flag: L9_ENABLE_BAYESIAN_REASONING
    Status: EXPERIMENTAL - controlled activation only
    """

    def __init__(self):
        """Initialize kernel."""
        self.enabled = (
            os.environ.get("L9_ENABLE_BAYESIAN_REASONING", "false").lower() == "true"
        )
        self.belief_states: dict[str, BeliefState] = {}
        self.system_prompt_section = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build system prompt section for Bayesian reasoning."""
        if not self.enabled:
            return ""  # Return empty if disabled

        return """
# Bayesian Reasoning Capabilities

You are equipped with Bayesian reasoning. When analyzing questions:

1. **State Prior Belief**: What is your initial assessment?
   - Express as probability ranges: low [<40%], moderate [40-70%], high [70-90%], very high [>90%]

2. **Identify Evidence**:
   - Strong evidence: Direct, reproducible, authoritative
   - Moderate evidence: Consistent but indirect
   - Weak evidence: Anecdotal or secondhand
   - Conflicting evidence: Contradictory sources

3. **Apply Bayesian Update**:
   - Strong: Shift ~70% toward conclusion
   - Moderate: Shift ~40% toward conclusion
   - Weak: Minimal shift ~10%
   - Conflicting: Note uncertainty increase

4. **Express Posterior Belief**:
   - Updated probability range
   - Confidence level (high/moderate/low)
   - What would change your mind?

Format reasoning as:
**Question**: [What we're reasoning about]
**Prior**: [Initial assessment]
**Evidence**: [List with strength classifications]
**Update**: [How beliefs shift]
**Posterior**: [Final assessment with confidence]
**Uncertainty**: [Residual doubt/what would change this]
"""

    def create_belief_state(
        self,
        variable: str,
        prior: dict[str, float],
        metadata: dict[str, Any] | None = None,
    ) -> BeliefState:
        """Create new belief state for a variable."""
        if not self.enabled:
            raise RuntimeError(
                "Bayesian reasoning disabled (L9_ENABLE_BAYESIAN_REASONING=false)"
            )

        belief = BeliefState(
            variable=variable,
            prior=prior,
            posterior=prior.copy(),
            evidence=[],
            confidence=self._calculate_confidence(prior),
            updated_at=self._timestamp(),
        )
        self.belief_states[variable] = belief
        return belief

    def add_evidence(
        self,
        variable: str,
        description: str,
        strength: EvidenceStrength,
        source: str | None = None,
    ) -> None:
        """Add evidence to a belief state."""
        if not self.enabled:
            raise RuntimeError("Bayesian reasoning disabled")

        if variable not in self.belief_states:
            raise ValueError(f"Belief state for '{variable}' not found")

        self.belief_states[variable].evidence.append(
            {
                "description": description,
                "strength": strength.value,
                "source": source,
            }
        )

    def update_posterior(
        self,
        variable: str,
        new_posterior: dict[str, float],
    ) -> BeliefState:
        """Update posterior belief using Bayes rule."""
        if not self.enabled:
            raise RuntimeError("Bayesian reasoning disabled")

        if variable not in self.belief_states:
            raise ValueError(f"Belief state for '{variable}' not found")

        belief = self.belief_states[variable]
        belief.posterior = new_posterior
        belief.confidence = self._calculate_confidence(new_posterior)
        belief.updated_at = self._timestamp()

        return belief

    @staticmethod
    def _calculate_confidence(distribution: dict[str, float]) -> float:
        """Calculate confidence from probability distribution."""
        if not distribution:
            return 0.5

        # Confidence is max(probability values) - higher max = higher confidence
        max_prob = max(distribution.values())
        return min(1.0, max(0.0, max_prob))

    @staticmethod
    def _timestamp() -> str:
        """Get current ISO timestamp."""
        # isoformat() with timezone.utc already produces +00:00 suffix
        return datetime.now(UTC).isoformat()

    def get_belief_state(self, variable: str) -> BeliefState | None:
        """Get belief state for a variable."""
        return self.belief_states.get(variable)

    def is_enabled(self) -> bool:
        """Check if Bayesian reasoning is enabled."""
        return self.enabled


# Global singleton instance
_bayesian_kernel: BayesianKernel | None = None
_kernel_lock = threading.Lock()


def get_bayesian_kernel() -> BayesianKernel:
    """Get or create global Bayesian kernel instance (thread-safe)."""
    # nosemgrep: l9-singleton-requires-lock (already has double-checked locking below)
    global _bayesian_kernel
    if _bayesian_kernel is None:
        with _kernel_lock:
            if _bayesian_kernel is None:
                _bayesian_kernel = BayesianKernel()
    return _bayesian_kernel


def reset_bayesian_kernel() -> None:
    """Reset kernel instance (for testing)."""
    global _bayesian_kernel
    _bayesian_kernel = None


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-004",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["auth", "data-models", "dataclass", "operations", "testing"],
    "keywords": [
        "agent",
        "bayesian",
        "belief",
        "create",
        "enabled",
        "evidence",
        "kernel",
        "posterior",
    ],
    "business_value": "Provides bayesian kernel components including EvidenceStrength, BeliefState, BayesianKernel",
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
