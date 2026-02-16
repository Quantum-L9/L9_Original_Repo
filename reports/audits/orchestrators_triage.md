# Dead Code Triage: `orchestrators`

**Date:** 2026-02-14 05:43 UTC

## Symbol Classification

**USED** (7): `ActionToolOrchestrator`, `MemoryOrchestrator`, `ReasoningOrchestrator`, `ResearchSwarmOrchestrator`, `WorldModelOrchestrator`, `event_to_task`, `handle_ws_event`
**INTERNAL_ONLY** (2): `EvolutionOrchestrator`, `MetaOrchestrator`
**ZERO_REF** (3): `WSBridgeConfig`, `WSEventRouter`, `enqueue_ws_event`

## File Classification

**WIRED** (2):
- `orchestrators/orchestrator_registry.py`
- `orchestrators/ws_bridge.py`

## Recommended Actions

### Remove 2 internal-only symbols from `__all__`
These are used within the package but not externally. Remove from `__all__` to reduce API surface noise.

### Review 3 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.
