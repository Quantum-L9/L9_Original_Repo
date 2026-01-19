# GOD-MODE-ORCHESTRATOR

This document summarizes the orchestrator-level intent for the new runtime + memory substrate auto-wiring path.

## Design Intent
- Centralize runtime selection and wiring in `runtime/`.
- Keep kernel + websocket orchestrators stable; interact via new runtime bridge components only.
- Use a registry pattern for memory substrates similar to existing L9 registries (agents, tools, schemas, world_model).

## Protected Surfaces
- `runtime/websocket_orchestrator.py` — **never modified** by this PR.
- `docker-compose.yml` — **never modified** by this PR.
- `runtime/kernel_loader.py` — **never modified** by this PR.

## Where New Logic Lives
- `runtime/base_runtime.py` — abstract base.
- `runtime/registry.py` — runtime registry.
- `runtime/bridge_kernel.py` — glue to existing kernel loader/orchestrators.
- `memory/substrate_registry.py` — memory substrate registry and auto-wiring.

These filenames are placeholders until the concrete implementations land in later commits on this branch.
