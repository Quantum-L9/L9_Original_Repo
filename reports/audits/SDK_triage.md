# Dead Code Triage: `SDK`

**Date:** 2026-02-14 05:42 UTC

## Symbol Classification

**USED** (3): `L9`, `execute_tool`, `run_task`
**TEST_ONLY** (2): `L9SDK`, `get_l9_sdk`
**ZERO_REF** (16): `CheckpointsInterface`, `ComplianceInterface`, `GovernanceInterface`, `L9Facade`, `LearningInterface`, `MCPInterface`, `ObservabilityInterface`, `ReasoningInterface`, `TaskQueueInterface`, `WorldModelInterface`, `close_l9`, `close_l9_facade`, `close_l9_sdk`, `get_l9`, `get_l9_facade`, `query_memory`

## File Classification

**WIP** (1):
- `SDK/SDK.py`

## Recommended Actions

### Review 16 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.

### Wire 1 WIP files
Recently created but not yet integrated.
