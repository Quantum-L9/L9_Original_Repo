# Package Wiring Audit: motifs

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `motifs`

Files checked: 3
- WIRED: 0
- PARTIAL: 0
- ORPHAN: 3
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `motifs/motif_feedback_graph.py` | 0 | 0 | - | - | ORPHAN |
| `motifs/multimodal_plan_ranker.py` | 0 | 0 | - | - | ORPHAN |
| `motifs/tensor_motif_linker.py` | 0 | 0 | - | - | ORPHAN |

## Level C: API Instantiation — `motifs`

API Status: **HAS_API**
Symbols checked: 8
- USED: 0
- TEST_ONLY: 0
- UNUSED: 8

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `MotifEvent` | 0 | 0 | UNUSED |
| `MotifFeedbackGraph` | 0 | 0 | UNUSED |
| `MotifMetadata` | 0 | 0 | UNUSED |
| `MotifTrace` | 0 | 0 | UNUSED |
| `MultimodalPlanRanker` | 0 | 0 | UNUSED |
| `PlanCandidate` | 0 | 0 | UNUSED |
| `RankedPlan` | 0 | 0 | UNUSED |
| `TensorMotifLinker` | 0 | 0 | UNUSED |
