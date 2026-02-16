# Package Wiring Audit: scripts

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `scripts`

Files checked: 26
- WIRED: 0
- PARTIAL: 1
- ORPHAN: 1
- ENTRYPOINT: 24
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `scripts/benchmark_caching_and_vector.py` | 0 | 0 | - | - | ENTRY |
| `scripts/benchmark_performance.py` | 0 | 0 | - | - | ENTRY |
| `scripts/benchmark_standalone.py` | 0 | 0 | - | - | ORPHAN |
| `scripts/cga_spec_generator.py` | 0 | 0 | - | - | ENTRY |
| `scripts/check_n_plus_1.py` | 0 | 0 | - | - | ENTRY |
| `scripts/diagnose_memory_search.py` | 0 | 0 | - | - | ENTRY |
| `scripts/extract_code_facts.py` | 0 | 0 | - | - | ENTRY |
| `scripts/fix_async_decorators.py` | 0 | 0 | - | - | ENTRY |
| `scripts/fix_decorator_wraps.py` | 0 | 0 | - | - | ENTRY |
| `scripts/fix_logging_to_structlog.py` | 0 | 0 | - | - | ENTRY |
| `scripts/fix_test_performance.py` | 0 | 0 | - | - | ENTRY |
| `scripts/fix_timezone_imports.py` | 0 | 0 | - | - | ENTRY |
| `scripts/fix_untyped_decorators.py` | 0 | 0 | - | - | ENTRY |
| `scripts/generate_gmp_report.py` | 0 | 0 | - | - | ENTRY |
| `scripts/generate_readme_superprompt.py` | 0 | 0 | - | - | ENTRY |
| `scripts/generate_subsystem_readmes.py` | 1 | 0 | - | - | PARTIAL |
| `scripts/gmp-validate-stage.py` | 0 | 0 | - | - | ENTRY |
| `scripts/load_agent_world_model.py` | 0 | 0 | - | - | ENTRY |
| `scripts/migrate_substrate_models.py` | 0 | 0 | - | - | ENTRY |
| `scripts/noqa_debt_eliminator.py` | 0 | 0 | - | - | ENTRY |
| `scripts/perplexity_audit_agent.py` | 0 | 0 | - | - | ENTRY |
| `scripts/refactor_dags_location.py` | 0 | 0 | - | - | ENTRY |
| `scripts/run_pattern.py` | 0 | 0 | - | - | ENTRY |
| `scripts/setup_gmail_accounts.py` | 0 | 0 | - | - | ENTRY |
| `scripts/update_workflow_state.py` | 0 | 0 | - | - | ENTRY |
| `scripts/validate_gmp_report.py` | 0 | 0 | - | - | ENTRY |

## Level C: API Instantiation — `scripts`

API Status: **NO_API_NEEDED**
Symbols checked: 0
- USED: 0
- TEST_ONLY: 0
- UNUSED: 0
