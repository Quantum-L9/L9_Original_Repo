"""
L9 Motifs Layer

Reusable reasoning patterns, cross-domain compression, failure fingerprints,
and plan rerouting primitives. Motifs are epistemic accelerators that let
EOS recognize patterns: "I've seen this shape of reasoning before."

Components:
- MotifFeedbackGraph: Track motif activations and outcomes
- MultimodalPlanRanker: Rank plans using tensor + symbolic + motif signals
- TensorMotifLinker: Bind motif metadata to tensor packets
"""

from .motif_feedback_graph import MotifEvent, MotifFeedbackGraph, MotifTrace
from .multimodal_plan_ranker import MultimodalPlanRanker, PlanCandidate, RankedPlan
from .tensor_motif_linker import MotifMetadata, TensorMotifLinker

__version__ = "1.0.0"

__all__ = [
    # Data classes
    "MotifEvent",
    "MotifMetadata",
    "MotifTrace",
    "PlanCandidate",
    "RankedPlan",
    # Core classes
    "MotifFeedbackGraph",
    "MultimodalPlanRanker",
    "TensorMotifLinker",
]
