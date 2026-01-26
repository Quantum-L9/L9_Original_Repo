"""
L9 Motifs Layer

Reusable reasoning patterns, cross-domain compression, failure fingerprints,
and plan rerouting primitives. Motifs are epistemic accelerators that let
EOS recognize patterns: "I've seen this shape of reasoning before."

Components:
- MotifFeedbackGraph: Track motif activations and outcomes
- MultimodalPlanRanker: Rank plans using tensor + symbolic + motif signals
- TensorMotifLinker: Bind motif metadata to tensor packets
- ReasoningGovernor: Runtime gatekeeper using kernel rules + motifs
- SelfHealingPlanSynthesizer: Generate fallback plans from failure traces
- CrossDomainMotifClassifier: Predict motif structures from packets
"""

from .motif_feedback_graph import MotifFeedbackGraph, MotifEvent, MotifTrace
from .multimodal_plan_ranker import MultimodalPlanRanker, PlanCandidate, RankedPlan
from .tensor_motif_linker import TensorMotifLinker, MotifMetadata
from .reasoning_governor import ReasoningGovernor, GovernanceDecision
from .self_healing_plan_synthesizer import SelfHealingPlanSynthesizer, HealingPlan
from .cross_domain_motif_classifier import CrossDomainMotifClassifier, MotifPrediction

__version__ = "1.0.0"

__all__ = [
    # Core classes
    "MotifFeedbackGraph",
    "MultimodalPlanRanker",
    "TensorMotifLinker",
    "ReasoningGovernor",
    "SelfHealingPlanSynthesizer",
    "CrossDomainMotifClassifier",
    # Data classes
    "MotifEvent",
    "MotifTrace",
    "PlanCandidate",
    "RankedPlan",
    "MotifMetadata",
    "GovernanceDecision",
    "HealingPlan",
    "MotifPrediction",
]
