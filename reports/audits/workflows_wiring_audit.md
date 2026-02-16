# Package Wiring Audit: workflows

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `workflows`

Files checked: 10
- WIRED: 0
- PARTIAL: 3
- ORPHAN: 0
- ENTRYPOINT: 7
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `workflows/gmp_enforcer.py` | 0 | 0 | - | - | ENTRY |
| `workflows/gmp_executor.py` | 0 | 0 | - | - | ENTRY |
| `workflows/harvest_deploy.py` | 0 | 0 | - | Y | PARTIAL |
| `workflows/harvest_executor.py` | 0 | 0 | - | - | ENTRY |
| `workflows/lint_fix_executor.py` | 0 | 0 | - | - | ENTRY |
| `workflows/migrate_executor.py` | 0 | 0 | - | - | ENTRY |
| `workflows/runner.py` | 0 | 0 | - | Y | PARTIAL |
| `workflows/state.py` | 0 | 0 | - | Y | PARTIAL |
| `workflows/use_harvest_executor.py` | 0 | 0 | - | - | ENTRY |
| `workflows/wire_executor.py` | 0 | 0 | - | - | ENTRY |

## Level C: API Instantiation — `workflows`

API Status: **HAS_API**
Symbols checked: 17
- USED: 5
- TEST_ONLY: 0
- UNUSED: 12

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `ExtractionPattern` | 0 | 0 | UNUSED |
| `FileMapping` | 0 | 0 | UNUSED |
| `GateType` | 0 | 0 | UNUSED |
| `SessionDAG` | 0 | 0 | UNUSED |
| `SessionEdge` | 0 | 0 | UNUSED |
| `SessionNode` | 0 | 0 | UNUSED |
| `ValidationCheck` | 0 | 0 | UNUSED |
| `WorkflowState` | 0 | 0 | UNUSED |
| `get_session_dag` | 0 | 0 | UNUSED |
| `list_session_dags` | 0 | 0 | UNUSED |
| `register_session_dag` | 0 | 0 | UNUSED |
| `session_dag_registry` | 0 | 0 | UNUSED |

**API-pattern symbols NOT in `__all__`:**
- `create_harvest_deploy_graph`
