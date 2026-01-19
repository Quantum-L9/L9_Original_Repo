# CURSOR-RUNBOOK

This runbook explains how to work with the new runtime + substrate registry wiring that will be introduced by this draft PR.

## Branch
- **Branch**: `feature/gmp-auto-wiring-runtimes`

## Scope
- Introduce a pluggable runtime abstraction under `runtime/`.
- Add a substrate registry that auto-wires memory substrates and their services.
- Do **not** touch `runtime/websocket_orchestrator.py`, `docker-compose.yml`, or `runtime/kernel_loader.py`.

## Developer Workflow
1. Checkout the feature branch:
   ```bash
   git fetch origin
   git checkout feature/gmp-auto-wiring-runtimes
   ```
2. Run tests:
   ```bash
   make test
   ```
3. To iterate on runtime wiring, focus on:
   - `runtime/` (new runtime abstractions)
   - `memory/substrate_*.py` and new `memory/substrate_registry.py`.
4. Open the draft PR in GitHub to review diffs and comments.
