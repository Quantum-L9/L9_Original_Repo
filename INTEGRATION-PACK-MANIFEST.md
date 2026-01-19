# INTEGRATION-PACK-MANIFEST

This manifest tracks the integration artifacts and their purpose for this draft PR.

## Files Introduced/Owned by This PR
- `CURSOR-RUNBOOK.md` — developer-facing runbook.
- `GOD-MODE-ORCHESTRATOR.md` — orchestrator-level intent.
- `PHASES-2-6-CONSOLIDATED-PROMPT-PACK.md` — prompt pack for future agents.
- `EVIDENCE-REPORT-PHASE-2-IMPLEMENTATION.md` — evidence log for changes and tests.

## Runtime + Substrate Wiring (Planned)
- New runtime abstractions under `runtime/`.
- New substrate registry under `memory/substrate_registry.py`.

This PR is the first step: it creates the integration documents and sets the guardrails. Concrete code changes will follow in subsequent commits on this branch.
