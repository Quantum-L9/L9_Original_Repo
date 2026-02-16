# Dead Code Triage: `motifs`

**Date:** 2026-02-14 05:43 UTC

## Symbol Classification

**INTERNAL_ONLY** (1): `MotifFeedbackGraph`
**ZERO_REF** (7): `MotifEvent`, `MotifMetadata`, `MotifTrace`, `MultimodalPlanRanker`, `PlanCandidate`, `RankedPlan`, `TensorMotifLinker`

## File Classification

**INTERNAL_ONLY** (1):
- `motifs/motif_feedback_graph.py`
**WIP** (2):
- `motifs/multimodal_plan_ranker.py`
- `motifs/tensor_motif_linker.py`

## Recommended Actions

### Remove 1 internal-only symbols from `__all__`
These are used within the package but not externally. Remove from `__all__` to reduce API surface noise.

### Review 7 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.

### Wire 2 WIP files
Recently created but not yet integrated.
