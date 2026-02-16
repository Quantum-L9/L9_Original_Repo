# Package Wiring Audit: tests

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `tests`

Files checked: 21
- WIRED: 0
- PARTIAL: 1
- ORPHAN: 10
- ENTRYPOINT: 10
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `tests/conftest.py` | 1 | 0 | - | - | PARTIAL |
| `tests/smoke_email.py` | 0 | 0 | - | - | ENTRY |
| `tests/smoke_test.py` | 0 | 0 | - | - | ENTRY |
| `tests/smoke_test_root.py` | 0 | 0 | - | - | ENTRY |
| `tests/test_ci_configuration.py` | 0 | 0 | - | - | ENTRY |
| `tests/test_code_facts_extraction.py` | 0 | 0 | - | - | ENTRY |
| `tests/test_imports.py` | 0 | 0 | - | - | ENTRY |
| `tests/test_integration_phase0.py` | 0 | 0 | - | - | ORPHAN |
| `tests/test_l_cto_kernel_activation.py` | 0 | 0 | - | - | ENTRY |
| `tests/test_memory_adapter.py` | 0 | 0 | - | - | ORPHAN |
| `tests/test_memory_governance_gate.py` | 0 | 0 | - | - | ORPHAN |
| `tests/test_memory_substrate_basic.py` | 0 | 0 | - | - | ENTRY |
| `tests/test_policy_engine.py` | 0 | 0 | - | - | ORPHAN |
| `tests/test_research_graph.py` | 0 | 0 | - | - | ORPHAN |
| `tests/test_retention_refcount.py` | 0 | 0 | - | - | ORPHAN |
| `tests/test_slack_adapter.py` | 0 | 0 | - | - | ENTRY |
| `tests/test_spec_normalizer_v2.py` | 0 | 0 | - | - | ORPHAN |
| `tests/test_tool_registry.py` | 0 | 0 | - | - | ORPHAN |
| `tests/test_toth_integration.py` | 0 | 0 | - | - | ENTRY |
| `tests/test_violation_tracker_smoke.py` | 0 | 0 | - | - | ORPHAN |
| `tests/test_wiring_integrity.py` | 0 | 0 | - | - | ORPHAN |

## Level C: API Instantiation — `tests`

API Status: **NO_API_NEEDED**
Symbols checked: 0
- USED: 0
- TEST_ONLY: 0
- UNUSED: 0
