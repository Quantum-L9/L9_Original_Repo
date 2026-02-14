# Dead Code Triage: `workflows`

**Date:** 2026-02-14 05:43 UTC

## Symbol Classification

**USED** (5): `NodeType`, `SessionState`, `StepResult`, `StepStatus`, `create_initial_state`
**INTERNAL_ONLY** (12): `ExtractionPattern`, `FileMapping`, `GateType`, `SessionDAG`, `SessionEdge`, `SessionNode`, `ValidationCheck`, `WorkflowState`, `get_session_dag`, `list_session_dags`, `register_session_dag`, `session_dag_registry`

## File Classification

**INTERNAL_ONLY** (2):
- `workflows/harvest_deploy.py`
- `workflows/state.py`
**WIP** (8):
- `workflows/gmp_enforcer.py`
- `workflows/gmp_executor.py`
- `workflows/harvest_executor.py`
- `workflows/lint_fix_executor.py`
- `workflows/migrate_executor.py`
- `workflows/runner.py`
- `workflows/use_harvest_executor.py`
- `workflows/wire_executor.py`

## Recommended Actions

### Remove 12 internal-only symbols from `__all__`
These are used within the package but not externally. Remove from `__all__` to reduce API surface noise.

### Wire 8 WIP files
Recently created but not yet integrated.
